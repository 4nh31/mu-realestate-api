"""Dominio de notificaciones: tipos de aviso que reciben personal y clientes."""
import enum


class TipoAviso(str, enum.Enum):
    SOLICITUD = "solicitud"
    PUBLICACION = "publicacion"
    CITA = "cita"
    FAVORITO = "favorito"
    BUSQUEDA = "busqueda"
    RESENA = "resena"
    DOCUMENTO = "documento"
    INTERNO = "interno"
    SISTEMA = "sistema"
