import enum


class TipoCita(str, enum.Enum):
    PRESENCIAL = "presencial"
    VIRTUAL = "virtual"


class EstadoCita(str, enum.Enum):
    PROGRAMADA = "programada"
    CONFIRMADA = "confirmada"
    REPROGRAMADA = "reprogramada"
    CANCELADA = "cancelada"
    REALIZADA = "realizada"
