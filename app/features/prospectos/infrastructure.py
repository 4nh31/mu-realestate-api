"""Infraestructura del CRM de prospectos: modelos ORM y repositorio."""
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Column, DateTime, ForeignKey, Numeric, String, Table, Text, func, or_, select
from sqlalchemy.orm import Mapped, Session, mapped_column, relationship

from app.core.database import Base, TimestampMixin
from app.core.types import pg_enum
from app.features.prospectos.domain import EtapaProspecto, TipoSeguimiento

prospecto_propiedades = Table(
    "prospecto_propiedades",
    Base.metadata,
    Column("prospecto_id", ForeignKey("prospectos.id", ondelete="CASCADE"), primary_key=True),
    Column("propiedad_id", ForeignKey("propiedades.id", ondelete="CASCADE"), primary_key=True),
)


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

    propiedades = relationship("Propiedad", secondary=prospecto_propiedades, lazy="selectin")
    seguimientos: Mapped[list["Seguimiento"]] = relationship(back_populates="prospecto", order_by="Seguimiento.fecha.desc()",
                                                             cascade="all, delete-orphan")


class Seguimiento(Base):
    __tablename__ = "seguimientos"
    id: Mapped[int] = mapped_column(primary_key=True)
    prospecto_id: Mapped[int] = mapped_column(ForeignKey("prospectos.id", ondelete="CASCADE"), index=True)
    usuario_id: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id", ondelete="SET NULL"))
    tipo: Mapped[TipoSeguimiento] = mapped_column(pg_enum(TipoSeguimiento, "tipo_seguimiento"))
    descripcion: Mapped[str] = mapped_column(Text)
    fecha: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    prospecto: Mapped[Prospecto] = relationship(back_populates="seguimientos")


class ProspectoRepository:
    def __init__(self, db: Session):
        self.db = db

    def obtener(self, prospecto_id: int) -> Prospecto | None:
        return self.db.get(Prospecto, prospecto_id)

    def agregar(self, prospecto: Prospecto) -> Prospecto:
        self.db.add(prospecto)
        self.db.flush()
        return prospecto

    def eliminar(self, prospecto: Prospecto) -> None:
        self.db.delete(prospecto)

    def buscar(self, texto: str | None, etapa: EtapaProspecto | None, asesor_id: int | None,
               limite: int, desplazamiento: int) -> list[Prospecto]:
        stmt = select(Prospecto).order_by(Prospecto.actualizado_en.desc(), Prospecto.id.desc())
        if texto:
            patron = f"%{texto}%"
            stmt = stmt.where(or_(Prospecto.nombre.ilike(patron), Prospecto.email.ilike(patron),
                                  Prospecto.telefono.ilike(patron)))
        if etapa:
            stmt = stmt.where(Prospecto.etapa == etapa)
        if asesor_id is not None:
            stmt = stmt.where(Prospecto.asesor_id == asesor_id)
        return list(self.db.scalars(stmt.limit(limite).offset(desplazamiento)))

    def agregar_seguimiento(self, seguimiento: Seguimiento) -> Seguimiento:
        self.db.add(seguimiento)
        self.db.flush()
        return seguimiento

    def seguimientos(self, prospecto_id: int) -> list[Seguimiento]:
        stmt = select(Seguimiento).where(Seguimiento.prospecto_id == prospecto_id).order_by(Seguimiento.fecha.desc(),
                                                                                             Seguimiento.id.desc())
        return list(self.db.scalars(stmt))
