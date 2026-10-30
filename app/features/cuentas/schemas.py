from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, EmailStr, Field

from app.features.propiedades.domain import EstadoPublicacion, Operacion, TipoPropiedad

Codigo = Field(pattern=r"^\d{6}$", description="Código de 6 dígitos enviado por correo")
Password = Field(min_length=8, max_length=72, description="Mínimo 8 caracteres")


class RegistroIn(BaseModel):
    nombre: str = Field(min_length=3, max_length=120, examples=["Juan García"])
    email: EmailStr
    telefono: str | None = Field(default=None, max_length=20)
    password: str = Password
    quiere_publicar: bool = Field(default=False, description="true registra la cuenta como propietario")


class CorreoIn(BaseModel):
    email: EmailStr


class VerificacionIn(BaseModel):
    email: EmailStr
    codigo: str = Codigo


class RestablecimientoIn(VerificacionIn):
    password: str = Password


class MensajeOut(BaseModel):
    mensaje: str


class SincronizarFavoritosIn(BaseModel):
    propiedad_ids: list[int] = Field(max_length=200)


class OfertaCuentaIn(BaseModel):
    """Datos de la propiedad que ofrece el dueño desde su cuenta; el contacto sale de su perfil."""
    titulo: str = Field(min_length=5, max_length=150)
    descripcion: str | None = None
    operacion: Operacion
    tipo: TipoPropiedad
    zona_id: int | None = None
    direccion: str = Field(min_length=5, max_length=255, description="Dirección exacta (se guarda como dato interno)")
    recamaras: int | None = Field(default=None, ge=0, le=50)
    banos: Decimal | None = Field(default=None, ge=0, le=50, decimal_places=1)
    estacionamientos: int | None = Field(default=None, ge=0, le=50)
    superficie_m2: Decimal | None = Field(default=None, gt=0, decimal_places=2)
    antiguedad_anios: int | None = Field(default=None, ge=0, le=200)
    precio_pedido: Decimal = Field(gt=0, max_digits=14, decimal_places=2)
    mensaje: str | None = Field(default=None, max_length=1000)
    amenidad_ids: list[int] = []
    bien_ids: list[int] = []


class PropiedadCuentaOut(BaseModel):
    """Lo que el dueño ve de las propiedades que ofreció: su estado y, si se rechazó, el motivo."""
    id: int
    clave: str | None
    titulo: str
    operacion: Operacion
    tipo: TipoPropiedad
    estado_publicacion: EstadoPublicacion
    motivo_rechazo: str | None
    portada: str | None
    creado_en: datetime
    revisado_en: datetime | None
    publicada_en: datetime | None

    @classmethod
    def desde(cls, p) -> "PropiedadCuentaOut":
        portada = next((m.url for m in p.medios if m.es_portada), p.medios[0].url if p.medios else None)
        motivo = p.motivo_rechazo if p.estado_publicacion == EstadoPublicacion.RECHAZADA else None
        return cls(id=p.id, clave=p.clave, titulo=p.titulo, operacion=p.operacion, tipo=p.tipo,
                   estado_publicacion=p.estado_publicacion, motivo_rechazo=motivo, portada=portada,
                   creado_en=p.creado_en, revisado_en=p.revisado_en, publicada_en=p.publicada_en)
