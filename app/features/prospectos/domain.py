"""Dominio del CRM: etapas del prospecto, transiciones y reglas (sin dependencias de frameworks)."""
import enum
from decimal import Decimal

from app.core.exceptions import ReglaDeNegocio


class EtapaProspecto(str, enum.Enum):
    NUEVO = "nuevo"
    CONTACTADO = "contactado"
    EN_VISITA = "en_visita"
    EN_OFERTA = "en_oferta"
    CERRADO = "cerrado"
    PERDIDO = "perdido"


class TipoSeguimiento(str, enum.Enum):
    LLAMADA = "llamada"
    WHATSAPP = "whatsapp"
    CORREO = "correo"
    VISITA = "visita"
    NOTA = "nota"


E = EtapaProspecto
# Diagrama de estados de un prospecto en el CRM (ver memoria, Actividad 4).
TRANSICIONES: dict[EtapaProspecto, set[EtapaProspecto]] = {
    E.NUEVO: {E.CONTACTADO, E.PERDIDO},
    E.CONTACTADO: {E.EN_VISITA, E.PERDIDO},
    E.EN_VISITA: {E.EN_OFERTA, E.CONTACTADO, E.PERDIDO},
    E.EN_OFERTA: {E.CERRADO, E.PERDIDO},
    E.CERRADO: set(),
    E.PERDIDO: set(),
}
ETAPAS_FINALES = {E.CERRADO, E.PERDIDO}


def validar_transicion(actual: EtapaProspecto, nueva: EtapaProspecto) -> None:
    if nueva not in TRANSICIONES[actual]:
        raise ReglaDeNegocio(f"Un prospecto en etapa '{actual.value}' no puede pasar a '{nueva.value}'")


def validar_presupuesto(minimo: Decimal | None, maximo: Decimal | None) -> None:
    if minimo is not None and maximo is not None and minimo > maximo:
        raise ReglaDeNegocio("El presupuesto mínimo no puede ser mayor que el máximo")
