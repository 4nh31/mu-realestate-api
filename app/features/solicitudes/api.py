"""Endpoints del centro de solicitudes y avisos internos."""
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.core.deps import RESPUESTAS_PROTEGIDAS, CurrentUser, DbSession, require_permission
from app.core.exceptions import NoEncontrado
from app.features.auditoria.application import Auditor
from app.features.solicitudes import application as casos
from app.features.solicitudes.domain import EstadoSolicitud, TipoSolicitud
from app.features.solicitudes.infrastructure import SolicitudRepository
from app.features.solicitudes.schemas import (AsignacionIn, AtencionIn, AvisoOut, DescarteIn, OfertaPropiedadIn,
                                              OfertaRecibida, SolicitudOut, SolicitudPublicaIn)
from app.features.usuarios.domain import Permisos
from app.features.usuarios.infrastructure import Usuario

publico = APIRouter(prefix="/publico", tags=["Solicitudes (público)"])
panel = APIRouter(prefix="/solicitudes", tags=["Centro de solicitudes"], responses=RESPUESTAS_PROTEGIDAS)
avisos = APIRouter(prefix="/avisos", tags=["Avisos internos"], responses=RESPUESTAS_PROTEGIDAS)
Gestor = Annotated[Usuario, Depends(require_permission(Permisos.SOLICITUDES_GESTIONAR))]


@publico.post("/solicitudes", response_model=SolicitudOut, status_code=status.HTTP_201_CREATED,
              summary="Solicitar contacto o visita de una propiedad publicada")
def solicitar(datos: SolicitudPublicaIn, db: DbSession):
    s = casos.recibir_solicitud(SolicitudRepository(db), datos)
    db.commit()
    db.refresh(s)
    return s


@publico.post("/propiedades/ofrecer", response_model=OfertaRecibida, status_code=status.HTTP_201_CREATED,
              summary="Ofrecer una propiedad para venta o renta («Vende o renta con nosotros»)")
def ofrecer(datos: OfertaPropiedadIn, db: DbSession):
    s, p = casos.recibir_oferta(SolicitudRepository(db), datos)
    db.commit()
    return OfertaRecibida(solicitud_id=s.id, propiedad_id=p.id)


@panel.get("", response_model=list[SolicitudOut], summary="Consultar solicitudes")
def listar(db: DbSession, _: Gestor, tipo: TipoSolicitud | None = None, estado: EstadoSolicitud | None = None,
           asignado_a: int | None = None, limite: int = Query(default=50, ge=1, le=200),
           desplazamiento: int = Query(default=0, ge=0)):
    return SolicitudRepository(db).listar(tipo, estado, asignado_a, limite, desplazamiento)


@panel.get("/{solicitud_id}", response_model=SolicitudOut, summary="Consultar detalle de una solicitud")
def detalle(solicitud_id: int, db: DbSession, _: Gestor):
    s = SolicitudRepository(db).obtener(solicitud_id)
    if s is None:
        raise NoEncontrado("Solicitud no encontrada")
    return s


def _responder(db, s):
    db.commit()
    db.refresh(s)
    return s


@panel.patch("/{solicitud_id}/asignacion", response_model=SolicitudOut, summary="Asignar solicitud a un asesor")
def asignar(solicitud_id: int, datos: AsignacionIn, db: DbSession, actor: Gestor):
    return _responder(db, casos.asignar_solicitud(SolicitudRepository(db), Auditor(db, actor.id), solicitud_id,
                                                  datos.asesor_id))


@panel.patch("/{solicitud_id}/atencion", response_model=SolicitudOut,
             summary="Registrar la atención de una solicitud (opcionalmente crea el prospecto)")
def atender(solicitud_id: int, datos: AtencionIn, db: DbSession, actor: Gestor):
    return _responder(db, casos.atender_solicitud(SolicitudRepository(db), Auditor(db, actor.id), solicitud_id, datos))


@panel.patch("/{solicitud_id}/descarte", response_model=SolicitudOut, summary="Descartar solicitud con motivo")
def descartar(solicitud_id: int, datos: DescarteIn, db: DbSession, actor: Gestor):
    return _responder(db, casos.descartar_solicitud(SolicitudRepository(db), Auditor(db, actor.id), solicitud_id, datos))


@avisos.get("", response_model=list[AvisoOut], summary="Consultar mis avisos internos")
def mis_avisos(db: DbSession, usuario: CurrentUser, solo_no_leidos: bool = False):
    return SolicitudRepository(db).avisos_de(usuario.id, solo_no_leidos)


@avisos.patch("/{aviso_id}/leido", response_model=AvisoOut, summary="Marcar aviso como leído")
def leido(aviso_id: int, db: DbSession, usuario: CurrentUser):
    a = casos.marcar_aviso_leido(SolicitudRepository(db), aviso_id, usuario.id)
    db.commit()
    db.refresh(a)
    return a
