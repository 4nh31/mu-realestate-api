"""Endpoints de la agenda de visitas."""
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.core.deps import RESPUESTAS_PROTEGIDAS, DbSession, require_permission
from app.core.exceptions import NoEncontrado
from app.features.agenda import application as casos
from app.features.agenda.domain import EstadoCita
from app.features.agenda.infrastructure import CitaRepository
from app.features.agenda.schemas import CancelacionIn, CitaIn, CitaOut, ReprogramacionIn
from app.features.auditoria.application import Auditor
from app.features.usuarios.domain import Permisos
from app.features.usuarios.infrastructure import Usuario

router = APIRouter(prefix="/citas", tags=["Agenda de visitas"], responses=RESPUESTAS_PROTEGIDAS)
Asesor = Annotated[Usuario, Depends(require_permission(Permisos.CITAS_GESTIONAR))]


@router.get("", response_model=list[CitaOut], summary="Consultar la agenda de visitas")
def listar(db: DbSession, _: Asesor, desde: datetime | None = None, hasta: datetime | None = None,
           asesor_id: int | None = None, estado: EstadoCita | None = None, prospecto_id: int | None = None):
    return CitaRepository(db).listar(desde, hasta, asesor_id, estado, prospecto_id)


@router.post("", response_model=CitaOut, status_code=status.HTTP_201_CREATED, summary="Agendar visita")
def agendar(datos: CitaIn, db: DbSession, actor: Asesor):
    c = casos.agendar_visita(CitaRepository(db), Auditor(db, actor.id), datos)
    db.commit()
    db.refresh(c)
    return c


@router.get("/{cita_id}", response_model=CitaOut, summary="Consultar visita")
def consultar(cita_id: int, db: DbSession, _: Asesor):
    c = CitaRepository(db).obtener(cita_id)
    if c is None:
        raise NoEncontrado("Visita no encontrada")
    return c


def _responder(db, c):
    db.commit()
    db.refresh(c)
    return c


@router.patch("/{cita_id}/confirmacion", response_model=CitaOut, summary="Confirmar visita")
def confirmar(cita_id: int, db: DbSession, actor: Asesor):
    return _responder(db, casos.confirmar_visita(CitaRepository(db), Auditor(db, actor.id), cita_id))


@router.patch("/{cita_id}/reprogramacion", response_model=CitaOut, summary="Reprogramar visita")
def reprogramar(cita_id: int, datos: ReprogramacionIn, db: DbSession, actor: Asesor):
    return _responder(db, casos.reprogramar_visita(CitaRepository(db), Auditor(db, actor.id), cita_id, datos))


@router.patch("/{cita_id}/cancelacion", response_model=CitaOut, summary="Cancelar visita")
def cancelar(cita_id: int, datos: CancelacionIn, db: DbSession, actor: Asesor):
    return _responder(db, casos.cancelar_visita(CitaRepository(db), Auditor(db, actor.id), cita_id, datos))


@router.patch("/{cita_id}/realizacion", response_model=CitaOut, summary="Registrar visita realizada")
def realizada(cita_id: int, db: DbSession, actor: Asesor):
    return _responder(db, casos.registrar_visita_realizada(CitaRepository(db), Auditor(db, actor.id), cita_id))
