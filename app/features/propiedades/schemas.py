"""Esquemas Pydantic del slice de propiedades. PropiedadPublica NO contiene campos internos (RN-01)."""
from datetime import datetime
from decimal import Decimal
from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.features.propiedades.domain import (Disponibilidad, EstadoPublicacion, Operacion, Origen,
                                             TipoMedio, TipoPropiedad)

T = TypeVar("T")
Dinero = Field(default=None, ge=0, max_digits=14, decimal_places=2)


class Pagina(BaseModel, Generic[T]):
    total: int
    limite: int
    desplazamiento: int
    elementos: list[T]


class PropiedadBase(BaseModel):
    titulo: str = Field(min_length=5, max_length=150)
    descripcion: str | None = None
    operacion: Operacion
    tipo: TipoPropiedad
    zona_id: int | None = None
    recamaras: int | None = Field(default=None, ge=0, le=50)
    banos: Decimal | None = Field(default=None, ge=0, le=50, decimal_places=1)
    estacionamientos: int | None = Field(default=None, ge=0, le=50)
    superficie_m2: Decimal | None = Field(default=None, gt=0, decimal_places=2)
    precio_publico: Decimal | None = Dinero
    moneda: str = Field(default="MXN", pattern="^(MXN|USD)$")


class PropiedadCrear(PropiedadBase):
    disponibilidad: Disponibilidad = Disponibilidad.DISPONIBLE
    asesor_id: int | None = None
    amenidad_ids: list[int] = []


class PropiedadActualizar(BaseModel):
    titulo: str | None = Field(default=None, min_length=5, max_length=150)
    descripcion: str | None = None
    operacion: Operacion | None = None
    tipo: TipoPropiedad | None = None
    zona_id: int | None = None
    recamaras: int | None = Field(default=None, ge=0, le=50)
    banos: Decimal | None = Field(default=None, ge=0, le=50, decimal_places=1)
    estacionamientos: int | None = Field(default=None, ge=0, le=50)
    superficie_m2: Decimal | None = Field(default=None, gt=0, decimal_places=2)
    precio_publico: Decimal | None = Dinero
    moneda: str | None = Field(default=None, pattern="^(MXN|USD)$")
    disponibilidad: Disponibilidad | None = None
    asesor_id: int | None = None
    amenidad_ids: list[int] | None = None


class MedioOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    tipo: TipoMedio
    url: str
    orden: int
    es_portada: bool


class UbicacionOut(BaseModel):
    zona_id: int | None
    zona: str | None
    ciudad: str | None


class PropiedadPublica(BaseModel):
    """Lo que ve el cliente: fotos, video, precio público, ubicación aproximada y características."""
    id: int
    clave: str | None
    titulo: str
    descripcion: str | None
    operacion: Operacion
    tipo: TipoPropiedad
    ubicacion: UbicacionOut
    recamaras: int | None
    banos: Decimal | None
    estacionamientos: int | None
    superficie_m2: Decimal | None
    precio_publico: Decimal | None
    moneda: str
    disponibilidad: Disponibilidad
    amenidades: list[str]
    medios: list[MedioOut]

    @classmethod
    def desde(cls, p) -> "PropiedadPublica":
        return cls(
            id=p.id, clave=p.clave, titulo=p.titulo, descripcion=p.descripcion, operacion=p.operacion, tipo=p.tipo,
            ubicacion=UbicacionOut(zona_id=p.zona_id, zona=p.zona.nombre if p.zona else None,
                                   ciudad=p.zona.ciudad.nombre if p.zona else None),
            recamaras=p.recamaras, banos=p.banos, estacionamientos=p.estacionamientos, superficie_m2=p.superficie_m2,
            precio_publico=p.precio_publico, moneda=p.moneda, disponibilidad=p.disponibilidad,
            amenidades=sorted(a.nombre for a in p.amenidades), medios=[MedioOut.model_validate(m) for m in p.medios],
        )


class PropiedadPanel(PropiedadPublica):
    estado_publicacion: EstadoPublicacion
    origen: Origen
    asesor_id: int | None
    activo: bool
    creado_en: datetime
    actualizado_en: datetime

    @classmethod
    def desde(cls, p) -> "PropiedadPanel":
        base = PropiedadPublica.desde(p).model_dump()
        return cls(**base, estado_publicacion=p.estado_publicacion, origen=p.origen, asesor_id=p.asesor_id,
                   activo=p.activo, creado_en=p.creado_en, actualizado_en=p.actualizado_en)


class CambioPublicacion(BaseModel):
    estado: EstadoPublicacion
    motivo: str | None = Field(default=None, max_length=300, description="Obligatorio al rechazar")


class PropietarioIn(BaseModel):
    nombre: str = Field(min_length=3, max_length=120)
    telefono: str | None = Field(default=None, max_length=20)
    email: EmailStr | None = None


class PropietarioOut(PropietarioIn):
    model_config = ConfigDict(from_attributes=True)
    id: int
    email: str | None = None


class DatosInternosIn(BaseModel):
    precio_real: Decimal | None = Dinero
    valor_minimo: Decimal | None = Dinero
    comision_pct: Decimal | None = Field(default=None, ge=0, le=100, decimal_places=2)
    direccion_exacta: str | None = Field(default=None, max_length=255)
    notas: str | None = None
    propietario: PropietarioIn | None = None


class DatosInternosOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    propiedad_id: int
    precio_real: Decimal | None
    valor_minimo: Decimal | None
    comision_pct: Decimal | None
    direccion_exacta: str | None
    notas: str | None
    propietario: PropietarioOut | None
    actualizado_en: datetime
