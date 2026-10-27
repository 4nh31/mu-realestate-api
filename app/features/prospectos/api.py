"""Endpoints del CRM de prospectos."""
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.core.deps import RESPUESTAS_PROTEGIDAS, DbSession, require_permission
from app.core.exceptions import NoEncontrado
from app.features.auditoria.application import Auditor
from app.features.prospectos import application as casos
from app.features.prospectos.domain import EtapaProspecto
from app.features.prospectos.infrastructure import ProspectoRepository
from app.features.prospectos.schemas import (CambioEtapa, ProspectoActualizar, ProspectoIn, ProspectoOut,
                                             SeguimientoIn, SeguimientoOut)
from app.features.usuarios.domain import Permisos
from app.features.usuarios.infrastructure import Usuario

router = APIRouter(prefix="/prospectos", tags=["Prospectos (CRM)"], responses=RESPUESTAS_PROTEGIDAS)
Asesor = Annotated[Usuario, Depends(require_permission(Permisos.PROSPECTOS_GESTIONAR))]


@router.get("", response_model=list[ProspectoOut], summary="Buscar prospectos")
def buscar(db: DbSession, _: Asesor, q: str | None = Query(default=None, description="Nombre, correo o teléfono"),
           etapa: EtapaProspecto | None = None, asesor_id: int | None = None,
           limite: int = Query(default=50, ge=1, le=200), desplazamiento: int = Query(default=0, ge=0)):
    return [ProspectoOut.desde(p) for p in ProspectoRepository(db).buscar(q, etapa, asesor_id, limite, desplazamiento)]


@router.post("", response_model=ProspectoOut, status_code=status.HTTP_201_CREATED, summary="Registrar prospecto")
def registrar(datos: ProspectoIn, db: DbSession, actor: Asesor):
    p = casos.registrar_prospecto(ProspectoRepository(db), Auditor(db, actor.id), datos)
    db.commit()
    db.refresh(p)
    return ProspectoOut.desde(p)


@router.get("/{prospecto_id}", response_model=ProspectoOut, summary="Consultar prospecto")
def consultar(prospecto_id: int, db: DbSession, _: Asesor):
    p = ProspectoRepository(db).obtener(prospecto_id)
    if p is None:
        raise NoEncontrado("Prospecto no encontrado")
    return ProspectoOut.desde(p)


@router.patch("/{prospecto_id}", response_model=ProspectoOut, summary="Editar prospecto")
def editar(prospecto_id: int, datos: ProspectoActualizar, db: DbSession, actor: Asesor):
    p = casos.editar_prospecto(ProspectoRepository(db), Auditor(db, actor.id), prospecto_id, datos)
    db.commit()
    db.refresh(p)
    return ProspectoOut.desde(p)


@router.delete("/{prospecto_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Eliminar prospecto")
def eliminar(prospecto_id: int, db: DbSession, actor: Asesor):
    casos.eliminar_prospecto(ProspectoRepository(db), Auditor(db, actor.id), prospecto_id)
    db.commit()


@router.patch("/{prospecto_id}/etapa", response_model=ProspectoOut,
              summary="Cambiar etapa del prospecto (incluye cerrar o marcar como perdido)")
def etapa(prospecto_id: int, cambio: CambioEtapa, db: DbSession, actor: Asesor):
    p = casos.cambiar_etapa(ProspectoRepository(db), Auditor(db, actor.id), prospecto_id, cambio, actor.id)
    db.commit()
    db.refresh(p)
    return ProspectoOut.desde(p)


@router.get("/{prospecto_id}/seguimientos", response_model=list[SeguimientoOut], summary="Historial de seguimiento")
def seguimientos(prospecto_id: int, db: DbSession, _: Asesor):
    repo = ProspectoRepository(db)
    if repo.obtener(prospecto_id) is None:
        raise NoEncontrado("Prospecto no encontrado")
    return repo.seguimientos(prospecto_id)


@router.post("/{prospecto_id}/seguimientos", response_model=SeguimientoOut, status_code=status.HTTP_201_CREATED,
             summary="Registrar seguimiento (llamada, WhatsApp, correo, visita o nota)")
def nuevo_seguimiento(prospecto_id: int, datos: SeguimientoIn, db: DbSession, actor: Asesor):
    s = casos.registrar_seguimiento(ProspectoRepository(db), prospecto_id, datos, actor.id)
    db.commit()
    db.refresh(s)
    return s
