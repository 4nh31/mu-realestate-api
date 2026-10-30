"""Registro de todos los modelos ORM para que Alembic los detecte (autogenerate)."""
from app.core.database import Base  # noqa: F401
from app.features.agenda.infrastructure import Cita  # noqa: F401
from app.features.auditoria.infrastructure import RegistroAuditoria  # noqa: F401
from app.features.catalogos.infrastructure import Amenidad, Bien, Ciudad, Zona  # noqa: F401
from app.features.cuentas.infrastructure import CodigoVerificacion, Favorito  # noqa: F401
from app.features.propiedades.infrastructure import DatosInternos, Medio, Propiedad, Propietario  # noqa: F401
from app.features.prospectos.infrastructure import Prospecto, Seguimiento, prospecto_propiedades  # noqa: F401
from app.features.solicitudes.infrastructure import Aviso, Solicitud  # noqa: F401
from app.features.usuarios.infrastructure import Permiso, Rol, Usuario  # noqa: F401
