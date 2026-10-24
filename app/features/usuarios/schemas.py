from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class RolOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    nombre: str
    descripcion: str | None
    permisos: list[str] = []

    @classmethod
    def desde(cls, rol) -> "RolOut":
        return cls(id=rol.id, nombre=rol.nombre, descripcion=rol.descripcion, permisos=sorted(p.clave for p in rol.permisos))


class UsuarioCrear(BaseModel):
    nombre: str = Field(min_length=3, max_length=120)
    email: EmailStr
    password: str = Field(min_length=8, max_length=72, description="Mínimo 8 caracteres")
    rol: str = Field(examples=["asesor"])


class UsuarioActualizar(BaseModel):
    nombre: str | None = Field(default=None, min_length=3, max_length=120)
    rol: str | None = None
    activo: bool | None = None
    password: str | None = Field(default=None, min_length=8, max_length=72)


class UsuarioOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    nombre: str
    email: EmailStr
    rol: str
    activo: bool
    ultimo_acceso: datetime | None
    creado_en: datetime

    @classmethod
    def desde(cls, u) -> "UsuarioOut":
        return cls(id=u.id, nombre=u.nombre, email=u.email, rol=u.rol.nombre, activo=u.activo,
                   ultimo_acceso=u.ultimo_acceso, creado_en=u.creado_en)
