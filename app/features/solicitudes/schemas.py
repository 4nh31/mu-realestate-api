from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.features.notificaciones.domain import TipoAviso
from app.features.propiedades.domain import Operacion, TipoPropiedad
from app.features.solicitudes.domain import EstadoSolicitud, TipoSolicitud


class SolicitudPublicaIn(BaseModel):
    """Solicitud de contacto o de visita. El contacto general del sitio va sin propiedad."""
    tipo: TipoSolicitud = Field(description="contacto o visita")
    propiedad_id: int | None = Field(default=None, description="Obligatoria para visitas")
    nombre: str = Field(min_length=3, max_length=120)
    telefono: str | None = Field(default=None, max_length=20)
    email: EmailStr | None = None
    mensaje: str | None = Field(default=None, max_length=1000)
    fecha_preferida: datetime | None = Field(default=None, description="Solo para solicitudes de visita")


class OfertaPropiedadIn(BaseModel):
    """Formulario «Vende o renta con nosotros»: el propietario ofrece su inmueble."""
    nombre: str = Field(min_length=3, max_length=120)
    telefono: str | None = Field(default=None, max_length=20)
    email: EmailStr | None = None
    titulo: str = Field(min_length=5, max_length=150)
    descripcion: str | None = None
    operacion: Operacion
    tipo: TipoPropiedad
    zona_id: int | None = None
    direccion: str = Field(min_length=5, max_length=255, description="Dirección exacta (se guarda como dato interno)")
    recamaras: int | None = Field(default=None, ge=0, le=50)
    banos: Decimal | None = Field(default=None, ge=0, le=50, decimal_places=1)
    superficie_m2: Decimal | None = Field(default=None, gt=0, decimal_places=2)
    precio_pedido: Decimal = Field(gt=0, max_digits=14, decimal_places=2)
    mensaje: str | None = Field(default=None, max_length=1000)


class OfertaRecibida(BaseModel):
    solicitud_id: int
    propiedad_id: int
    mensaje: str = "Recibimos tu propiedad; nuestro equipo la revisará y te contactará."


class SolicitudOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    tipo: TipoSolicitud
    estado: EstadoSolicitud
    propiedad_id: int | None
    nombre: str
    telefono: str | None
    email: str | None
    mensaje: str | None
    fecha_preferida: datetime | None
    asignado_a: int | None
    prospecto_id: int | None
    motivo_descarte: str | None
    notas: str | None
    creado_en: datetime
    atendido_en: datetime | None


class AsignacionIn(BaseModel):
    asesor_id: int


class AtencionIn(BaseModel):
    crear_prospecto: bool = Field(default=True, description="Registrar al solicitante como prospecto en el CRM")


class NotasIn(BaseModel):
    notas: str = Field(max_length=2000)


class DescarteIn(BaseModel):
    motivo: str = Field(min_length=5, max_length=500)


class AvisoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    tipo: TipoAviso
    titulo: str
    mensaje: str | None
    enlace: str | None
    solicitud_id: int | None
    autor_id: int | None
    por_correo: bool
    leido: bool
    creado_en: datetime


class AvisoIn(BaseModel):
    """Aviso interno manual: a un usuario concreto o a todos los de un rol."""
    tipo: TipoAviso = TipoAviso.INTERNO
    titulo: str = Field(min_length=3, max_length=150)
    mensaje: str | None = Field(default=None, max_length=2000)
    enlace: str | None = Field(default=None, max_length=255, pattern="^/")
    usuario_id: int | None = None
    rol: str | None = Field(default=None, examples=["asesor"])
    por_correo: bool = False


class AvisosMarcados(BaseModel):
    actualizados: int
