from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict

from app.core.deps import RESPUESTAS_PROTEGIDAS, DbSession, require_permission
from app.features.auditoria.infrastructure import AuditoriaRepository
from app.features.usuarios.domain import Permisos

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


@router.get("", response_model=list[RegistroOut], summary="Consultar cambios relevantes")
def consultar(
    db: DbSession,
    _: Annotated[object, Depends(require_permission(Permisos.AUDITORIA_VER))],
    entidad: str | None = Query(default=None, examples=["propiedades"]),
    entidad_id: int | None = None,
    usuario_id: int | None = None,
    limite: int = Query(default=50, ge=1, le=200),
    desplazamiento: int = Query(default=0, ge=0),
):
    return AuditoriaRepository(db).consultar(entidad, entidad_id, usuario_id, limite, desplazamiento)
