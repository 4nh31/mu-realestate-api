import enum


class TipoSolicitud(str, enum.Enum):
    CONTACTO = "contacto"
    VISITA = "visita"
    VENDER_RENTAR = "vender_rentar"


class EstadoSolicitud(str, enum.Enum):
    NUEVA = "nueva"
    ASIGNADA = "asignada"
    ATENDIDA = "atendida"
    DESCARTADA = "descartada"
