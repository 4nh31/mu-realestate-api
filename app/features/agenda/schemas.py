from datetime import datetime

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field

from app.features.agenda.domain import EstadoCita, TipoCita


class CitaIn(BaseModel):
    propiedad_id: int
    prospecto_id: int
    asesor_id: int
    fecha_hora: AwareDatetime = Field(description="Fecha y hora con zona horaria, p. ej. 2026-11-07T10:00:00-05:00")
    tipo: TipoCita = TipoCita.PRESENCIAL
    notas: str | None = Field(default=None, max_length=1000)


class ReprogramacionIn(BaseModel):
    fecha_hora: AwareDatetime
    motivo: str | None = Field(default=None, max_length=500)


class CancelacionIn(BaseModel):
    motivo: str = Field(min_length=3, max_length=500)


class CitaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    propiedad_id: int
    prospecto_id: int
    asesor_id: int | None
    fecha_hora: datetime
    tipo: TipoCita
    estado: EstadoCita
    notas: str | None
