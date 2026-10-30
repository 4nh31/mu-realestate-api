"""Punto de entrada de la API de MU Real Estate."""
import logging

from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

import app.core.models  # noqa: F401  (registra todos los modelos)
from app.core.config import get_settings
from app.core.exceptions import register_exception_handlers
from app.core.storage import PUBLICO, AlmacenamientoLocal, get_almacenamiento
from app.core.storage import router as archivos_router
from app.features.auditoria.api import router as auditoria_router
from app.features.agenda.api import router as agenda_router
from app.features.auth.api import router as auth_router
from app.features.catalogos.api import router as catalogos_router
from app.features.cuentas.api import auth as cuentas_auth_router
from app.features.cuentas.api import cuenta as cuenta_router
from app.features.dashboard.api import router as dashboard_router
from app.features.propiedades.api import medios as medios_router
from app.features.propiedades.api import panel as propiedades_panel
from app.features.propiedades.api import publico as propiedades_publico
from app.features.prospectos.api import router as prospectos_router
from app.features.solicitudes.api import avisos as avisos_router
from app.features.solicitudes.api import panel as solicitudes_panel
from app.features.solicitudes.api import publico as solicitudes_publico
from app.features.usuarios.api import router as usuarios_router

settings = get_settings()
# Mensajes propios de la API (p. ej. los correos sin SMTP en desarrollo) en la consola.
logging.basicConfig(level=logging.INFO, format="%(levelname)s:     %(name)s - %(message)s")

DESCRIPCION = """
API REST del panel administrativo y CRM de **MU Real Estate** (unidad inmobiliaria de Cano & Asociados).

* Autenticación con **JWT** (`POST /api/v1/auth/login`) y control de acceso **basado en roles**.
* Los endpoints bajo `/publico` no requieren sesión y **nunca** devuelven datos internos
  (precio real, valor mínimo, propietario, comisión, dirección exacta ni notas).
* Los cambios relevantes quedan registrados en la **bitácora de auditoría**.
* Clientes y propietarios se registran en `POST /api/v1/auth/registro` y usan los endpoints bajo `/cuenta`.
"""

TAGS = [
    {"name": "Autenticación", "description": "Inicio de sesión, registro, verificación de correo y contraseña."},
    {"name": "Mi cuenta", "description": "Favoritos y propiedades ofrecidas por clientes y propietarios."},
    {"name": "Usuarios, roles y permisos", "description": "Administración de usuarios (solo administrador)."},
    {"name": "Propiedades (panel)", "description": "Inventario, datos internos y publicación."},
    {"name": "Propiedades (público)", "description": "Buscador y ficha pública del sitio."},
    {"name": "Catálogos", "description": "Ciudades, zonas y amenidades para filtros."},
    {"name": "Solicitudes (público)", "description": "Contacto, visita y «Vende o renta con nosotros»."},
    {"name": "Centro de solicitudes", "description": "Asignación, atención y descarte de solicitudes."},
    {"name": "Avisos internos", "description": "Notificaciones del usuario autenticado (personal o cliente)."},
    {"name": "Prospectos (CRM)", "description": "Registro, seguimiento y etapas de los prospectos."},
    {"name": "Agenda de visitas", "description": "Agendar, confirmar, reprogramar y cancelar visitas (RN-05)."},
    {"name": "Dashboard y reportes", "description": "Indicadores de la operación y reportes por periodo."},
    {"name": "Auditoría de cambios", "description": "Bitácora de cambios relevantes (RN-06)."},
]

app = FastAPI(title=settings.app_name, version=settings.app_version, description=DESCRIPCION,
              openapi_tags=TAGS, docs_url="/docs", redoc_url="/redoc")
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins, allow_credentials=True,
                   allow_methods=["*"], allow_headers=["*"])
register_exception_handlers(app)

API_PREFIX = "/api/v1"
for router in (auth_router, cuentas_auth_router, cuenta_router, usuarios_router, propiedades_panel,
               propiedades_publico, medios_router, catalogos_router, solicitudes_publico, solicitudes_panel,
               avisos_router, prospectos_router, agenda_router, dashboard_router, auditoria_router, archivos_router):
    app.include_router(router, prefix=API_PREFIX)

# En desarrollo la API sirve las fotos públicas; en producción salen directo del bucket.
almacen = get_almacenamiento()
if isinstance(almacen, AlmacenamientoLocal):
    app.mount("/archivos", StaticFiles(directory=almacen.raiz / PUBLICO), name="archivos")


@app.get("/", include_in_schema=False)
def raiz() -> RedirectResponse:
    """La raíz redirige a la documentación interactiva."""
    return RedirectResponse(url="/docs")


@app.get("/health", tags=["Sistema"], summary="Verificación de estado")
def health() -> dict[str, str]:
    return {"status": "ok"}
