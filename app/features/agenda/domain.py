"""Dominio de la agenda de visitas: estados, transiciones y regla de empalmes (RN-05)."""
import enum
from datetime import datetime, timedelta

from app.core.exceptions import ReglaDeNegocio


class TipoCita(str, enum.Enum):
    PRESENCIAL = "presencial"
    VIRTUAL = "virtual"


class EstadoCita(str, enum.Enum):
    PROGRAMADA = "programada"
    CONFIRMADA = "confirmada"
    REPROGRAMADA = "reprogramada"
    CANCELADA = "cancelada"
    REALIZADA = "realizada"


DURACION_VISITA = timedelta(minutes=60)
E = EstadoCita
TRANSICIONES: dict[EstadoCita, set[EstadoCita]] = {
    E.PROGRAMADA: {E.CONFIRMADA, E.REPROGRAMADA, E.CANCELADA},
    E.CONFIRMADA: {E.REPROGRAMADA, E.CANCELADA, E.REALIZADA},
    E.REPROGRAMADA: {E.CONFIRMADA, E.REPROGRAMADA, E.CANCELADA, E.REALIZADA},
    E.CANCELADA: set(),
    E.REALIZADA: set(),
}
ESTADOS_ACTIVOS = {E.PROGRAMADA, E.CONFIRMADA, E.REPROGRAMADA}


def validar_transicion(actual: EstadoCita, nuevo: EstadoCita) -> None:
    if nuevo not in TRANSICIONES[actual]:
        raise ReglaDeNegocio(f"Una visita '{actual.value}' no puede pasar a '{nuevo.value}'")


def validar_fecha_futura(fecha_hora: datetime, ahora: datetime) -> None:
    if fecha_hora <= ahora:
        raise ReglaDeNegocio("La visita debe agendarse en una fecha y hora futuras")


def se_empalman(inicio_a: datetime, inicio_b: datetime) -> bool:
    """Dos visitas de una hora se empalman si sus intervalos [inicio, inicio + 1 h) se intersectan."""
    return inicio_a < inicio_b + DURACION_VISITA and inicio_b < inicio_a + DURACION_VISITA
