from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.features.prospectos.domain import EtapaProspecto, TipoSeguimiento


class ProspectoIn(BaseModel):
    nombre: str = Field(min_length=3, max_length=120)
    telefono: str | None = Field(default=None, max_length=20)
    email: EmailStr | None = None
    origen: str | None = Field(default=None, max_length=40, examples=["sitio web"])
    asesor_id: int | None = None
    presupuesto_min: Decimal | None = Field(default=None, ge=0, max_digits=14, decimal_places=2)
    presupuesto_max: Decimal | None = Field(default=None, ge=0, max_digits=14, decimal_places=2)
    propiedad_ids: list[int] = []


class ProspectoActualizar(BaseModel):
    nombre: str | None = Field(default=None, min_length=3, max_length=120)
    telefono: str | None = Field(default=None, max_length=20)
    email: EmailStr | None = None
    origen: str | None = Field(default=None, max_length=40)
    asesor_id: int | None = None
    presupuesto_min: Decimal | None = Field(default=None, ge=0, max_digits=14, decimal_places=2)
    presupuesto_max: Decimal | None = Field(default=None, ge=0, max_digits=14, decimal_places=2)
    propiedad_ids: list[int] | None = None


class ProspectoOut(BaseModel):
    id: int
    nombre: str
    telefono: str | None
    email: str | None
    origen: str | None
    etapa: EtapaProspecto
    asesor_id: int | None
    presupuesto_min: Decimal | None
    presupuesto_max: Decimal | None
    propiedad_ids: list[int]
    creado_en: datetime
    actualizado_en: datetime

    @classmethod
    def desde(cls, p) -> "ProspectoOut":
        return cls(id=p.id, nombre=p.nombre, telefono=p.telefono, email=p.email, origen=p.origen, etapa=p.etapa,
                   asesor_id=p.asesor_id, presupuesto_min=p.presupuesto_min, presupuesto_max=p.presupuesto_max,
                   propiedad_ids=sorted(x.id for x in p.propiedades), creado_en=p.creado_en,
                   actualizado_en=p.actualizado_en)


class CambioEtapa(BaseModel):
    etapa: EtapaProspecto
    comentario: str | None = Field(default=None, max_length=500)


class SeguimientoIn(BaseModel):
    tipo: TipoSeguimiento
    descripcion: str = Field(min_length=3, max_length=2000)


class SeguimientoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    tipo: TipoSeguimiento
    descripcion: str
    usuario_id: int | None
    fecha: datetime
