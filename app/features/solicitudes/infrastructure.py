"""Modelos del centro de solicitudes y avisos internos (endpoints en el Sprint 5)."""
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.core.types import pg_enum
from app.features.solicitudes.domain import EstadoSolicitud, TipoSolicitud


class Solicitud(Base):
    __tablename__ = "solicitudes"
    id: Mapped[int] = mapped_column(primary_key=True)
    tipo: Mapped[TipoSolicitud] = mapped_column(pg_enum(TipoSolicitud, "tipo_solicitud"))
    propiedad_id: Mapped[int | None] = mapped_column(ForeignKey("propiedades.id", ondelete="SET NULL"))
    nombre: Mapped[str] = mapped_column(String(120))
    telefono: Mapped[str | None] = mapped_column(String(20))
    email: Mapped[str | None] = mapped_column(String(160))
    mensaje: Mapped[str | None] = mapped_column(Text)
    fecha_preferida: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    estado: Mapped[EstadoSolicitud] = mapped_column(pg_enum(EstadoSolicitud, "estado_solicitud"),
                                                    default=EstadoSolicitud.NUEVA, server_default="nueva", index=True)
    asignado_a: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id", ondelete="SET NULL"))
    prospecto_id: Mapped[int | None] = mapped_column(ForeignKey("prospectos.id", ondelete="SET NULL"))
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    atendido_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Aviso(Base):
    __tablename__ = "avisos"
    id: Mapped[int] = mapped_column(primary_key=True)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id", ondelete="CASCADE"), index=True)
    solicitud_id: Mapped[int | None] = mapped_column(ForeignKey("solicitudes.id", ondelete="CASCADE"))
    titulo: Mapped[str] = mapped_column(String(150))
    leido: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
