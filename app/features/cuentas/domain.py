"""Dominio de cuentas del sitio público: códigos de verificación y límites (sin dependencias de frameworks)."""
import enum
import secrets
from datetime import datetime, timedelta

from app.core.exceptions import ReglaDeNegocio

MAX_INTENTOS = 5
SEGUNDOS_ENTRE_REENVIOS = 60
MAX_IMAGENES_OFERTA = 10


class PropositoCodigo(str, enum.Enum):
    VERIFICAR_CORREO = "verificar_correo"
    RESTABLECER_PASSWORD = "restablecer_password"


def generar_codigo() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


def validar_vigencia(expira_en: datetime, intentos: int, ahora: datetime) -> None:
    if intentos >= MAX_INTENTOS:
        raise ReglaDeNegocio("Se agotaron los intentos; solicita un código nuevo")
    if ahora > expira_en:
        raise ReglaDeNegocio("El código expiró; solicita uno nuevo")


def puede_reenviar(ultimo_envio: datetime | None, ahora: datetime) -> bool:
    return ultimo_envio is None or ahora - ultimo_envio >= timedelta(seconds=SEGUNDOS_ENTRE_REENVIOS)
