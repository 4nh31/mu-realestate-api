"""Infraestructura del slice de propiedades: modelos ORM y repositorio."""
from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy import (Boolean, CheckConstraint, Column, ForeignKey, Index, Numeric, SmallInteger, String,
                        Table, Text, func, select)
from sqlalchemy.orm import Mapped, Session, mapped_column, relationship, selectinload

from app.core.database import Base, TimestampMixin
from app.core.types import pg_enum
from app.features.catalogos.infrastructure import Amenidad, Ciudad, Zona
from app.features.propiedades.domain import (Disponibilidad, EstadoPublicacion, Operacion, Origen,
                                             TipoMedio, TipoPropiedad)

propiedad_amenidades = Table(
    "propiedad_amenidades",
    Base.metadata,
    Column("propiedad_id", ForeignKey("propiedades.id", ondelete="CASCADE"), primary_key=True),
    Column("amenidad_id", ForeignKey("amenidades.id", ondelete="CASCADE"), primary_key=True),
)


class Propietario(TimestampMixin, Base):
    __tablename__ = "propietarios"
    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(120))
    telefono: Mapped[str | None] = mapped_column(String(20))
    email: Mapped[str | None] = mapped_column(String(160))


class Propiedad(TimestampMixin, Base):
    __tablename__ = "propiedades"
    id: Mapped[int] = mapped_column(primary_key=True)
    clave: Mapped[str | None] = mapped_column(String(20), unique=True)
    titulo: Mapped[str] = mapped_column(String(150))
    descripcion: Mapped[str | None] = mapped_column(Text)
    operacion: Mapped[Operacion] = mapped_column(pg_enum(Operacion, "operacion"))
    tipo: Mapped[TipoPropiedad] = mapped_column(pg_enum(TipoPropiedad, "tipo_propiedad"))
    zona_id: Mapped[int | None] = mapped_column(ForeignKey("zonas.id"))
    recamaras: Mapped[int | None] = mapped_column(SmallInteger)
    banos: Mapped[Decimal | None] = mapped_column(Numeric(3, 1))
    estacionamientos: Mapped[int | None] = mapped_column(SmallInteger)
    superficie_m2: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    precio_publico: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    moneda: Mapped[str] = mapped_column(String(3), default="MXN", server_default="MXN")
    estado_publicacion: Mapped[EstadoPublicacion] = mapped_column(
        pg_enum(EstadoPublicacion, "estado_publicacion"), default=EstadoPublicacion.BORRADOR,
        server_default=EstadoPublicacion.BORRADOR.value)
    disponibilidad: Mapped[Disponibilidad] = mapped_column(
        pg_enum(Disponibilidad, "disponibilidad"), default=Disponibilidad.DISPONIBLE,
        server_default=Disponibilidad.DISPONIBLE.value)
    origen: Mapped[Origen] = mapped_column(pg_enum(Origen, "origen_propiedad"), default=Origen.INTERNA,
                                           server_default=Origen.INTERNA.value)
    asesor_id: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id", ondelete="SET NULL"))
    activo: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")

    zona: Mapped[Zona | None] = relationship(lazy="joined")
    amenidades: Mapped[list[Amenidad]] = relationship(secondary=propiedad_amenidades, lazy="selectin")
    medios: Mapped[list["Medio"]] = relationship(back_populates="propiedad", order_by="Medio.orden",
                                                 lazy="selectin", cascade="all, delete-orphan")
    datos_internos: Mapped["DatosInternos | None"] = relationship(back_populates="propiedad", uselist=False,
                                                                  cascade="all, delete-orphan")

    __table_args__ = (
        CheckConstraint("precio_publico IS NULL OR precio_publico >= 0", name="precio_publico_no_negativo"),
        # Índice compuesto para el buscador público (RN-02 + filtros más frecuentes).
        Index("ix_propiedades_busqueda", "estado_publicacion", "activo", "operacion", "tipo", "zona_id"),
        Index("ix_propiedades_precio_publico", "precio_publico"),
    )


class DatosInternos(TimestampMixin, Base):
    """Información confidencial separada en relación 1:1 (RN-01): nunca se une en consultas públicas."""
    __tablename__ = "datos_internos"
    propiedad_id: Mapped[int] = mapped_column(ForeignKey("propiedades.id", ondelete="CASCADE"), primary_key=True)
    propietario_id: Mapped[int | None] = mapped_column(ForeignKey("propietarios.id", ondelete="SET NULL"))
    precio_real: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    valor_minimo: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    comision_pct: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    direccion_exacta: Mapped[str | None] = mapped_column(String(255))
    notas: Mapped[str | None] = mapped_column(Text)

    propiedad: Mapped[Propiedad] = relationship(back_populates="datos_internos")
    propietario: Mapped[Propietario | None] = relationship(lazy="joined")
    __table_args__ = (
        CheckConstraint("valor_minimo IS NULL OR precio_real IS NULL OR valor_minimo <= precio_real",
                        name="valor_minimo_menor_o_igual_precio_real"),
        CheckConstraint("comision_pct IS NULL OR (comision_pct >= 0 AND comision_pct <= 100)",
                        name="comision_rango"),
    )


class Medio(TimestampMixin, Base):
    __tablename__ = "medios"
    id: Mapped[int] = mapped_column(primary_key=True)
    propiedad_id: Mapped[int] = mapped_column(ForeignKey("propiedades.id", ondelete="CASCADE"), index=True)
    tipo: Mapped[TipoMedio] = mapped_column(pg_enum(TipoMedio, "tipo_medio"))
    url: Mapped[str] = mapped_column(String(500))
    public_id: Mapped[str | None] = mapped_column(String(200))
    orden: Mapped[int] = mapped_column(SmallInteger, default=0, server_default="0")
    es_portada: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    propiedad: Mapped[Propiedad] = relationship(back_populates="medios")


@dataclass
class FiltrosBusqueda:
    operacion: Operacion | None = None
    tipo: TipoPropiedad | None = None
    ciudad_id: int | None = None
    zona_id: int | None = None
    recamaras_min: int | None = None
    banos_min: Decimal | None = None
    precio_min: Decimal | None = None
    precio_max: Decimal | None = None
    estacionamientos_min: int | None = None
    amenidad_ids: list[int] | None = None


class PropiedadRepository:
    def __init__(self, db: Session):
        self.db = db

    def obtener(self, propiedad_id: int) -> Propiedad | None:
        return self.db.get(Propiedad, propiedad_id)

    def agregar(self, propiedad: Propiedad) -> Propiedad:
        self.db.add(propiedad)
        self.db.flush()
        if not propiedad.clave:
            propiedad.clave = f"MU-{propiedad.id:05d}"
        return propiedad

    def _aplicar_filtros(self, stmt, f: FiltrosBusqueda):
        if f.operacion:
            stmt = stmt.where(Propiedad.operacion == f.operacion)
        if f.tipo:
            stmt = stmt.where(Propiedad.tipo == f.tipo)
        if f.zona_id:
            stmt = stmt.where(Propiedad.zona_id == f.zona_id)
        if f.ciudad_id:
            stmt = stmt.join(Zona, Propiedad.zona_id == Zona.id).where(Zona.ciudad_id == f.ciudad_id)
        if f.recamaras_min is not None:
            stmt = stmt.where(Propiedad.recamaras >= f.recamaras_min)
        if f.banos_min is not None:
            stmt = stmt.where(Propiedad.banos >= f.banos_min)
        if f.estacionamientos_min is not None:
            stmt = stmt.where(Propiedad.estacionamientos >= f.estacionamientos_min)
        if f.precio_min is not None:
            stmt = stmt.where(Propiedad.precio_publico >= f.precio_min)
        if f.precio_max is not None:
            stmt = stmt.where(Propiedad.precio_publico <= f.precio_max)
        for amenidad_id in f.amenidad_ids or []:
            stmt = stmt.where(Propiedad.amenidades.any(Amenidad.id == amenidad_id))
        return stmt

    def buscar_publicas(self, f: FiltrosBusqueda, limite: int, desplazamiento: int) -> tuple[list[Propiedad], int]:
        """RN-01 y RN-02: solo propiedades publicadas y activas; nunca se consulta datos_internos."""
        base = select(Propiedad).where(Propiedad.estado_publicacion == EstadoPublicacion.PUBLICADA,
                                       Propiedad.activo.is_(True))
        base = self._aplicar_filtros(base, f)
        total = self.db.scalar(select(func.count()).select_from(base.subquery()))
        filas = self.db.scalars(base.order_by(Propiedad.creado_en.desc()).limit(limite).offset(desplazamiento))
        return list(filas.unique()), total or 0

    def listar_panel(self, f: FiltrosBusqueda, estado: EstadoPublicacion | None, disponibilidad: Disponibilidad | None,
                     incluir_inactivas: bool, limite: int, desplazamiento: int) -> tuple[list[Propiedad], int]:
        base = self._aplicar_filtros(select(Propiedad), f)
        if estado:
            base = base.where(Propiedad.estado_publicacion == estado)
        if disponibilidad:
            base = base.where(Propiedad.disponibilidad == disponibilidad)
        if not incluir_inactivas:
            base = base.where(Propiedad.activo.is_(True))
        total = self.db.scalar(select(func.count()).select_from(base.subquery()))
        filas = self.db.scalars(base.order_by(Propiedad.actualizado_en.desc()).limit(limite).offset(desplazamiento))
        return list(filas.unique()), total or 0

    def obtener_internos(self, propiedad_id: int) -> DatosInternos | None:
        stmt = (select(DatosInternos).options(selectinload(DatosInternos.propietario))
                .where(DatosInternos.propiedad_id == propiedad_id))
        return self.db.scalar(stmt)

    def obtener_o_crear_propietario(self, nombre: str, telefono: str | None, email: str | None) -> Propietario:
        existente = None
        if email:
            existente = self.db.scalar(select(Propietario).where(Propietario.email == email))
        if existente is None and telefono:
            existente = self.db.scalar(select(Propietario).where(Propietario.telefono == telefono))
        if existente:
            return existente
        propietario = Propietario(nombre=nombre, telefono=telefono, email=email)
        self.db.add(propietario)
        self.db.flush()
        return propietario

    def zona_existe(self, zona_id: int) -> bool:
        return self.db.get(Zona, zona_id) is not None

    def amenidades(self, ids: list[int]) -> list[Amenidad]:
        return list(self.db.scalars(select(Amenidad).where(Amenidad.id.in_(ids)))) if ids else []


__all__ = ["Ciudad", "DatosInternos", "FiltrosBusqueda", "Medio", "Propiedad", "PropiedadRepository", "Propietario"]
