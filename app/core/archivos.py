"""Validación de archivos subidos: tamaño máximo y tipo real según su firma de bytes, no su extensión."""
import hashlib
from dataclasses import dataclass

from fastapi import UploadFile

from app.core.config import get_settings
from app.core.exceptions import ReglaDeNegocio

IMAGENES = {"image/jpeg", "image/png", "image/webp"}
DOCUMENTOS = {"application/pdf", "image/jpeg", "image/png"}


def detectar_mime(contenido: bytes) -> str | None:
    if contenido.startswith(b"%PDF-"):
        return "application/pdf"
    if contenido.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if contenido.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if contenido[:4] == b"RIFF" and contenido[8:12] == b"WEBP":
        return "image/webp"
    return None


@dataclass
class ArchivoValidado:
    nombre: str
    mime: str
    contenido: bytes

    @property
    def tamano(self) -> int:
        return len(self.contenido)

    @property
    def sha256(self) -> str:
        return hashlib.sha256(self.contenido).hexdigest()


def validar_archivo(archivo: UploadFile, permitidos: set[str]) -> ArchivoValidado:
    maximo = get_settings().max_upload_mb * 1024 * 1024
    contenido = archivo.file.read(maximo + 1)
    nombre = (archivo.filename or "archivo")[:200]
    if not contenido:
        raise ReglaDeNegocio(f"El archivo «{nombre}» está vacío")
    if len(contenido) > maximo:
        raise ReglaDeNegocio(f"El archivo «{nombre}» supera el máximo de {get_settings().max_upload_mb} MB")
    mime = detectar_mime(contenido)
    if mime not in permitidos:
        tipos = ", ".join(sorted(t.split("/")[1].upper() for t in permitidos))
        raise ReglaDeNegocio(f"El archivo «{nombre}» no es un tipo permitido ({tipos})")
    return ArchivoValidado(nombre=nombre, mime=mime, contenido=contenido)
