from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict, Field

from app.core.deps import RESPUESTAS_PROTEGIDAS, DbSession, require_permission
from app.features.auditoria.infrastructure import AuditoriaRepository
from app.features.usuarios.domain import Permisos

ENTIDADES_PROPIEDAD = {"propiedades", "datos_internos"}
router = APIRouter(prefix="/auditoria", tags=["Auditoría de cambios"], responses=RESPUESTAS_PROTEGIDAS)


class RegistroOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    usuario_id: int | None
    entidad: str
    entidad_id: int
    accion: str
    campo: str | None
    valor_anterior: str | None
    valor_nuevo: str | None
    fecha: datetime
    usuario_nombre: str | None = None
    entidad_titulo: str | None = Field(default=None, description="Título de la propiedad, si aplica")
    entidad_zona: str | None = None


@router.get("", response_model=list[RegistroOut], summary="Consultar cambios relevantes")
def consultar(
    db: DbSession,
    _: Annotated[object, Depends(require_permission(Permisos.AUDITORIA_VER))],
    entidad: str | None = Query(default=None, examples=["propiedades"]),
    entidad_id: int | None = None,
    usuario_id: int | None = None,
    accion: str | None = Query(default=None, examples=["publicar"]),
    desde: datetime | None = None,
    hasta: datetime | None = None,
    limite: int = Query(default=50, ge=1, le=200),
    desplazamiento: int = Query(default=0, ge=0),
):
    repo = AuditoriaRepository(db)
    registros = repo.consultar(entidad, entidad_id, usuario_id, limite, desplazamiento, desde, hasta, accion)
    nombres = repo.nombres_usuarios({r.usuario_id for r in registros if r.usuario_id})
    titulos = repo.titulos_propiedades({r.entidad_id for r in registros if r.entidad in ENTIDADES_PROPIEDAD})
    salida = []
    for r in registros:
        titulo, zona = titulos.get(r.entidad_id, (None, None)) if r.entidad in ENTIDADES_PROPIEDAD else (None, None)
        salida.append(RegistroOut.model_validate(r).model_copy(update={
            "usuario_nombre": nombres.get(r.usuario_id), "entidad_titulo": titulo, "entidad_zona": zona}))
    return salida
