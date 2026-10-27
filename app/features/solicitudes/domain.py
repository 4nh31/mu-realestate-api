"""Dominio de solicitudes: tipos, estados y transiciones válidas (sin dependencias de frameworks)."""
import enum

from app.core.exceptions import ReglaDeNegocio


class TipoSolicitud(str, enum.Enum):
    CONTACTO = "contacto"
    VISITA = "visita"
    VENDER_RENTAR = "vender_rentar"


class EstadoSolicitud(str, enum.Enum):
    NUEVA = "nueva"
    ASIGNADA = "asignada"
    ATENDIDA = "atendida"
    DESCARTADA = "descartada"


E = EstadoSolicitud
TRANSICIONES: dict[EstadoSolicitud, set[EstadoSolicitud]] = {
    E.NUEVA: {E.ASIGNADA, E.DESCARTADA},
    E.ASIGNADA: {E.ASIGNADA, E.ATENDIDA, E.DESCARTADA},  # reasignar a otro asesor está permitido
    E.ATENDIDA: set(),
    E.DESCARTADA: set(),
}


def validar_transicion(actual: EstadoSolicitud, nuevo: EstadoSolicitud) -> None:
    if nuevo not in TRANSICIONES[actual]:
        raise ReglaDeNegocio(f"Una solicitud '{actual.value}' no puede pasar a '{nuevo.value}'")


def validar_contacto(telefono: str | None, email: str | None) -> None:
    if not telefono and not email:
        raise ReglaDeNegocio("Indique al menos un teléfono o un correo de contacto")
