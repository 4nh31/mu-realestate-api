"""Catálogos: ciudades, zonas y amenidades."""
from sqlalchemy import ForeignKey, String, UniqueConstraint, select
from sqlalchemy.orm import Mapped, Session, mapped_column, relationship

from app.core.database import Base


class Ciudad(Base):
    __tablename__ = "ciudades"
    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(80))
    estado: Mapped[str] = mapped_column(String(80))
    zonas: Mapped[list["Zona"]] = relationship(back_populates="ciudad", order_by="Zona.nombre")
    __table_args__ = (UniqueConstraint("nombre", "estado", name="uq_ciudades_nombre_estado"),)


class Zona(Base):
    __tablename__ = "zonas"
    id: Mapped[int] = mapped_column(primary_key=True)
    ciudad_id: Mapped[int] = mapped_column(ForeignKey("ciudades.id"), index=True)
    nombre: Mapped[str] = mapped_column(String(100))
    ciudad: Mapped[Ciudad] = relationship(back_populates="zonas", lazy="joined")
    __table_args__ = (UniqueConstraint("ciudad_id", "nombre", name="uq_zonas_ciudad_nombre"),)


class Amenidad(Base):
    __tablename__ = "amenidades"
    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(80), unique=True)


class CatalogoRepository:
    def __init__(self, db: Session):
        self.db = db

    def ciudades(self) -> list[Ciudad]:
        return list(self.db.scalars(select(Ciudad).order_by(Ciudad.nombre)))

    def zonas(self, ciudad_id: int | None = None) -> list[Zona]:
        stmt = select(Zona).order_by(Zona.nombre)
        if ciudad_id is not None:
            stmt = stmt.where(Zona.ciudad_id == ciudad_id)
        return list(self.db.scalars(stmt))

    def amenidades(self) -> list[Amenidad]:
        return list(self.db.scalars(select(Amenidad).order_by(Amenidad.nombre)))
