import enum


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
