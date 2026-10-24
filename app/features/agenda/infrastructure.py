"""Modelos de la agenda de visitas (endpoints en el Sprint 6)."""
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, TimestampMixin
from app.core.types import pg_enum
from app.features.agenda.domain import EstadoCita, TipoCita


class Cita(TimestampMixin, Base):
    __tablename__ = "citas"
    id: Mapped[int] = mapped_column(primary_key=True)
    propiedad_id: Mapped[int] = mapped_column(ForeignKey("propiedades.id", ondelete="CASCADE"))
    prospecto_id: Mapped[int] = mapped_column(ForeignKey("prospectos.id", ondelete="CASCADE"))
    asesor_id: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id", ondelete="SET NULL"))
    fecha_hora: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    tipo: Mapped[TipoCita] = mapped_column(pg_enum(TipoCita, "tipo_cita"), default=TipoCita.PRESENCIAL,
                                           server_default="presencial")
    estado: Mapped[EstadoCita] = mapped_column(pg_enum(EstadoCita, "estado_cita"), default=EstadoCita.PROGRAMADA,
                                               server_default="programada")
    notas: Mapped[str | None] = mapped_column(Text)
    # Soporta la regla RN-05 (un asesor no puede tener dos visitas en el mismo horario).
    __table_args__ = (Index("ix_citas_asesor_fecha", "asesor_id", "fecha_hora"),)
