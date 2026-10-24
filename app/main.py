"""Punto de entrada de la API de MU Real Estate."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import app.core.models  # noqa: F401  (registra todos los modelos)
from app.core.config import get_settings
from app.core.exceptions import register_exception_handlers
from app.features.auditoria.api import router as auditoria_router
from app.features.auth.api import router as auth_router
from app.features.catalogos.api import router as catalogos_router
from app.features.propiedades.api import panel as propiedades_panel
from app.features.propiedades.api import publico as propiedades_publico
from app.features.usuarios.api import router as usuarios_router

settings = get_settings()

DESCRIPCION = """
API REST del panel administrativo y CRM de **MU Real Estate** (unidad inmobiliaria de Cano & Asociados).

* Autenticación con **JWT** (`POST /api/v1/auth/login`) y control de acceso **basado en roles**.
* Los endpoints bajo `/publico` no requieren sesión y **nunca** devuelven datos internos
  (precio real, valor mínimo, propietario, comisión, dirección exacta ni notas).
* Los cambios relevantes quedan registrados en la **bitácora de auditoría**.
"""

TAGS = [
    {"name": "Autenticación", "description": "Inicio de sesión y perfil del usuario."},
    {"name": "Usuarios, roles y permisos", "description": "Administración de usuarios (solo administrador)."},
    {"name": "Propiedades (panel)", "description": "Inventario, datos internos y publicación."},
    {"name": "Propiedades (público)", "description": "Buscador y ficha pública del sitio."},
    {"name": "Catálogos", "description": "Ciudades, zonas y amenidades para filtros."},
    {"name": "Auditoría de cambios", "description": "Bitácora de cambios relevantes (RN-06)."},
]

app = FastAPI(title=settings.app_name, version=settings.app_version, description=DESCRIPCION,
              openapi_tags=TAGS, docs_url="/docs", redoc_url="/redoc")
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins, allow_credentials=True,
                   allow_methods=["*"], allow_headers=["*"])
register_exception_handlers(app)

API_PREFIX = "/api/v1"
for router in (auth_router, usuarios_router, propiedades_panel, propiedades_publico, catalogos_router,
               auditoria_router):
    app.include_router(router, prefix=API_PREFIX)


@app.get("/health", tags=["Sistema"], summary="Verificación de estado")
def health() -> dict[str, str]:
    return {"status": "ok"}
