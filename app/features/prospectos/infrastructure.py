"""Modelos del CRM de prospectos (endpoints en el Sprint 5)."""
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, TimestampMixin
from app.core.types import pg_enum
from app.features.prospectos.domain import EtapaProspecto, TipoSeguimiento


class Prospecto(TimestampMixin, Base):
    __tablename__ = "prospectos"
    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(120))
    telefono: Mapped[str | None] = mapped_column(String(20))
    email: Mapped[str | None] = mapped_column(String(160))
    origen: Mapped[str | None] = mapped_column(String(40))
    etapa: Mapped[EtapaProspecto] = mapped_column(pg_enum(EtapaProspecto, "etapa_prospecto"),
                                                  default=EtapaProspecto.NUEVO, server_default="nuevo", index=True)
    asesor_id: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id", ondelete="SET NULL"), index=True)
    presupuesto_min: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    presupuesto_max: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))


class Seguimiento(Base):
    __tablename__ = "seguimientos"
    id: Mapped[int] = mapped_column(primary_key=True)
    prospecto_id: Mapped[int] = mapped_column(ForeignKey("prospectos.id", ondelete="CASCADE"), index=True)
    usuario_id: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id", ondelete="SET NULL"))
    tipo: Mapped[TipoSeguimiento] = mapped_column(pg_enum(TipoSeguimiento, "tipo_seguimiento"))
    descripcion: Mapped[str] = mapped_column(Text)
    fecha: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
