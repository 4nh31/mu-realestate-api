"""Infraestructura de la agenda de visitas: modelo ORM y repositorio."""
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Text, select
from sqlalchemy.orm import Mapped, Session, mapped_column

from app.core.database import Base, TimestampMixin
from app.core.types import pg_enum
from app.features.agenda.domain import DURACION_VISITA, ESTADOS_ACTIVOS, EstadoCita, TipoCita


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


class CitaRepository:
    def __init__(self, db: Session):
        self.db = db

    def obtener(self, cita_id: int) -> Cita | None:
        return self.db.get(Cita, cita_id)

    def agregar(self, cita: Cita) -> Cita:
        self.db.add(cita)
        self.db.flush()
        return cita

    def empalmadas(self, asesor_id: int, fecha_hora: datetime, excluir_id: int | None = None) -> list[Cita]:
        """Visitas activas del asesor que se cruzan con una visita de una hora que inicia en fecha_hora."""
        stmt = select(Cita).where(Cita.asesor_id == asesor_id, Cita.estado.in_(ESTADOS_ACTIVOS),
                                  Cita.fecha_hora > fecha_hora - DURACION_VISITA,
                                  Cita.fecha_hora < fecha_hora + DURACION_VISITA)
        if excluir_id is not None:
            stmt = stmt.where(Cita.id != excluir_id)
        return list(self.db.scalars(stmt))

    def listar(self, desde: datetime | None, hasta: datetime | None, asesor_id: int | None,
               estado: EstadoCita | None, prospecto_id: int | None) -> list[Cita]:
        stmt = select(Cita).order_by(Cita.fecha_hora)
        if desde:
            stmt = stmt.where(Cita.fecha_hora >= desde)
        if hasta:
            stmt = stmt.where(Cita.fecha_hora < hasta)
        if asesor_id is not None:
            stmt = stmt.where(Cita.asesor_id == asesor_id)
        if estado:
            stmt = stmt.where(Cita.estado == estado)
        if prospecto_id is not None:
            stmt = stmt.where(Cita.prospecto_id == prospecto_id)
        return list(self.db.scalars(stmt))

    def existen_para_prospecto(self, prospecto_id: int) -> bool:
        return self.db.scalar(select(Cita.id).where(Cita.prospecto_id == prospecto_id).limit(1)) is not None
