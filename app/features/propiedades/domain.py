"""Dominio de propiedades: enumeraciones y reglas de negocio puras (sin FastAPI ni SQLAlchemy)."""
import enum
from decimal import Decimal

from app.core.exceptions import ReglaDeNegocio


class Operacion(str, enum.Enum):
    VENTA = "venta"
    RENTA = "renta"


class TipoPropiedad(str, enum.Enum):
    CASA = "casa"
    DEPARTAMENTO = "departamento"
    TERRENO = "terreno"
    LOTE = "lote"
    COMERCIAL = "comercial"
    BODEGA = "bodega"


class EstadoPublicacion(str, enum.Enum):
    BORRADOR = "borrador"
    EN_REVISION = "en_revision"
    PUBLICADA = "publicada"
    OCULTA = "oculta"
    RECHAZADA = "rechazada"


class Disponibilidad(str, enum.Enum):
    DISPONIBLE = "disponible"
    APARTADA = "apartada"
    VENDIDA = "vendida"
    RENTADA = "rentada"


class Origen(str, enum.Enum):
    INTERNA = "interna"
    PARTICULAR = "particular"


class TipoMedio(str, enum.Enum):
    FOTO = "foto"
    VIDEO = "video"


E = EstadoPublicacion
# Diagrama de estados de publicación (ver memoria, Actividad 4).
TRANSICIONES: dict[EstadoPublicacion, set[EstadoPublicacion]] = {
    E.BORRADOR: {E.EN_REVISION},
    E.EN_REVISION: {E.PUBLICADA, E.RECHAZADA},
    E.PUBLICADA: {E.OCULTA},
    E.OCULTA: {E.PUBLICADA},
    E.RECHAZADA: {E.BORRADOR},
}


def validar_transicion(actual: EstadoPublicacion, nuevo: EstadoPublicacion) -> None:
    if nuevo not in TRANSICIONES[actual]:
        raise ReglaDeNegocio(f"No se puede pasar de '{actual.value}' a '{nuevo.value}'")


def validar_valor_minimo(precio_real: Decimal | None, valor_minimo: Decimal | None) -> None:
    """RN-04: el valor mínimo de negociación no puede superar el precio real."""
    if precio_real is not None and valor_minimo is not None and valor_minimo > precio_real:
        raise ReglaDeNegocio("El valor mínimo no puede ser mayor que el precio real")


def validar_publicable(tiene_zona: bool, precio_publico: Decimal | None, activa: bool) -> None:
    if not activa:
        raise ReglaDeNegocio("Una propiedad desactivada no puede publicarse")
    if not tiene_zona or not precio_publico:
        raise ReglaDeNegocio("Para publicar se requiere zona y precio público")
