"""Almacenamiento de archivos: fotos públicas y documentos privados (expedientes, firmas).

En desarrollo se guardan en disco (STORAGE_DIR) y la API los sirve; en producción se usa un bucket
compatible con S3 (DigitalOcean Spaces). Los archivos privados nunca tienen URL directa: solo se
accede a ellos con una URL firmada que expira (RN-10).
"""
import hashlib
import hmac
import time
import uuid
from abc import ABC, abstractmethod
from functools import lru_cache
from pathlib import Path

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import FileResponse

from app.core.config import get_settings

PUBLICO = "publico"
PRIVADO = "privado"
EXTENSIONES = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp", "application/pdf": ".pdf"}


def nueva_clave(visibilidad: str, carpeta: str, mime: str) -> str:
    return f"{visibilidad}/{carpeta.strip('/')}/{uuid.uuid4().hex}{EXTENSIONES.get(mime, '')}"


class Almacenamiento(ABC):
    @abstractmethod
    def guardar(self, contenido: bytes, clave: str, mime: str) -> None: ...

    @abstractmethod
    def eliminar(self, clave: str) -> None: ...

    @abstractmethod
    def url_publica(self, clave: str) -> str: ...

    @abstractmethod
    def url_firmada(self, clave: str, segundos: int) -> str: ...

    def guardar_nuevo(self, contenido: bytes, visibilidad: str, carpeta: str, mime: str) -> str:
        """Guarda con un nombre aleatorio (nunca el nombre original del usuario) y devuelve la clave."""
        clave = nueva_clave(visibilidad, carpeta, mime)
        self.guardar(contenido, clave, mime)
        return clave


def _firma(clave: str, expira: int) -> str:
    secreto = get_settings().jwt_secret_key.encode()
    return hmac.new(secreto, f"{clave}:{expira}".encode(), hashlib.sha256).hexdigest()


class AlmacenamientoLocal(Almacenamiento):
    def __init__(self, raiz: str, base_url: str):
        self.raiz = Path(raiz).resolve()
        self.base_url = base_url.rstrip("/")
        (self.raiz / PUBLICO).mkdir(parents=True, exist_ok=True)
        (self.raiz / PRIVADO).mkdir(parents=True, exist_ok=True)

    def ruta(self, clave: str) -> Path:
        ruta = (self.raiz / clave).resolve()
        if not ruta.is_relative_to(self.raiz):
            raise ValueError("Clave de archivo inválida")
        return ruta

    def guardar(self, contenido: bytes, clave: str, mime: str) -> None:
        ruta = self.ruta(clave)
        ruta.parent.mkdir(parents=True, exist_ok=True)
        ruta.write_bytes(contenido)

    def eliminar(self, clave: str) -> None:
        self.ruta(clave).unlink(missing_ok=True)

    def url_publica(self, clave: str) -> str:
        return f"{self.base_url}/archivos/{clave.removeprefix(PUBLICO + '/')}"

    def url_firmada(self, clave: str, segundos: int) -> str:
        expira = int(time.time()) + segundos
        return f"{self.base_url}/api/v1/archivos/privados/{clave}?expira={expira}&firma={_firma(clave, expira)}"


class AlmacenamientoS3(Almacenamiento):
    def __init__(self):
        import boto3  # solo se necesita en producción

        s = get_settings()
        self.bucket = s.s3_bucket
        self.base_url = s.s3_public_base_url.rstrip("/")
        self.cliente = boto3.client("s3", endpoint_url=s.s3_endpoint_url, aws_access_key_id=s.s3_access_key,
                                    aws_secret_access_key=s.s3_secret_key)

    def guardar(self, contenido: bytes, clave: str, mime: str) -> None:
        acl = "public-read" if clave.startswith(PUBLICO + "/") else "private"
        self.cliente.put_object(Bucket=self.bucket, Key=clave, Body=contenido, ContentType=mime, ACL=acl)

    def eliminar(self, clave: str) -> None:
        self.cliente.delete_object(Bucket=self.bucket, Key=clave)

    def url_publica(self, clave: str) -> str:
        return f"{self.base_url}/{clave}"

    def url_firmada(self, clave: str, segundos: int) -> str:
        return self.cliente.generate_presigned_url("get_object", Params={"Bucket": self.bucket, "Key": clave},
                                                   ExpiresIn=segundos)


@lru_cache
def get_almacenamiento() -> Almacenamiento:
    s = get_settings()
    if s.storage_backend == "s3":
        return AlmacenamientoS3()
    return AlmacenamientoLocal(s.storage_dir, s.api_public_url)


# Solo para el almacenamiento local: entrega archivos privados si la firma es válida y no expiró.
router = APIRouter(prefix="/archivos", include_in_schema=False)


@router.get("/privados/{clave:path}")
def archivo_privado(clave: str, expira: int, firma: str) -> FileResponse:
    almacen = get_almacenamiento()
    valida = hmac.compare_digest(firma, _firma(clave, expira)) and expira >= time.time()
    if not isinstance(almacen, AlmacenamientoLocal) or not valida:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Enlace inválido o expirado")
    ruta = almacen.ruta(clave)
    if not ruta.is_file():
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Archivo no encontrado")
    return FileResponse(ruta)
