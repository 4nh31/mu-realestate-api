"""Endpoints del dashboard administrativo y reportes."""
import csv
import io
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.core.deps import RESPUESTAS_PROTEGIDAS, DbSession, require_permission
from app.core.exceptions import ReglaDeNegocio
from app.features.dashboard import application as consultas
from app.features.usuarios.domain import Permisos
from app.features.usuarios.infrastructure import Usuario

router = APIRouter(prefix="/dashboard", tags=["Dashboard y reportes"], responses=RESPUESTAS_PROTEGIDAS)
Lector = Annotated[Usuario, Depends(require_permission(Permisos.DASHBOARD_VER))]


class FilaReporte(BaseModel):
    indicador: str
    valor: int


@router.get("/indicadores", summary="Consultar indicadores del dashboard")
def indicadores(db: DbSession, usuario: Lector) -> dict:
    return consultas.indicadores(db, usuario.id)


@router.get("/reporte", response_model=list[FilaReporte],
            responses={200: {"content": {"text/csv": {}}, "description": "JSON o CSV según el parámetro formato"}},
            summary="Generar reporte de la operación por periodo (JSON o CSV)")
def reporte(db: DbSession, _: Lector, desde: datetime, hasta: datetime,
            formato: str = Query(default="json", pattern="^(json|csv)$")):
    if desde >= hasta:
        raise ReglaDeNegocio("La fecha inicial debe ser anterior a la final")
    filas = consultas.reporte_periodo(db, desde, hasta)
    if formato == "json":
        return filas
    salida = io.StringIO()
    escritor = csv.DictWriter(salida, fieldnames=["indicador", "valor"])
    escritor.writeheader()
    escritor.writerows(filas)
    nombre = f"reporte_{desde:%Y%m%d}_{hasta:%Y%m%d}.csv"
    return StreamingResponse(iter([salida.getvalue().encode("utf-8-sig")]), media_type="text/csv",
                             headers={"Content-Disposition": f'attachment; filename="{nombre}"'})
