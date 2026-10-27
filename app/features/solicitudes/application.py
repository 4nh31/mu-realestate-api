"""Casos de uso del centro de solicitudes y avisos internos."""
from datetime import UTC, datetime

from app.core.exceptions import NoEncontrado, ReglaDeNegocio
from app.features.auditoria.application import Auditor
from app.features.propiedades.domain import EstadoPublicacion, Origen
from app.features.propiedades.infrastructure import DatosInternos, Propiedad, PropiedadRepository
from app.features.prospectos.infrastructure import Prospecto
from app.features.solicitudes import domain
from app.features.solicitudes.domain import EstadoSolicitud, TipoSolicitud
from app.features.solicitudes.infrastructure import Solicitud, SolicitudRepository
from app.features.solicitudes.schemas import (AtencionIn, DescarteIn, OfertaPropiedadIn, SolicitudPublicaIn)
from app.features.usuarios.domain import Permisos
from app.features.usuarios.infrastructure import UsuarioRepository

ENTIDAD = "solicitudes"


def _obtener(repo: SolicitudRepository, solicitud_id: int) -> Solicitud:
    solicitud = repo.obtener(solicitud_id)
    if solicitud is None:
        raise NoEncontrado("Solicitud no encontrada")
    return solicitud


def _avisar_a(repo: SolicitudRepository, permiso: str, titulo: str, solicitud_id: int) -> None:
    destinatarios = [u.id for u in UsuarioRepository(repo.db).con_permiso(permiso)]
    repo.avisar(destinatarios, titulo, solicitud_id)


def recibir_solicitud(repo: SolicitudRepository, datos: SolicitudPublicaIn) -> Solicitud:
    """Contacto o visita enviados desde la ficha pública; solo sobre propiedades publicadas (RN-02)."""
    if datos.tipo == TipoSolicitud.VENDER_RENTAR:
        raise ReglaDeNegocio("Para ofrecer una propiedad use el formulario «Vende o renta con nosotros»")
    domain.validar_contacto(datos.telefono, datos.email)
    propiedad = repo.db.get(Propiedad, datos.propiedad_id)
    if propiedad is None or not propiedad.activo or propiedad.estado_publicacion != EstadoPublicacion.PUBLICADA:
        raise NoEncontrado("Propiedad no encontrada")
    solicitud = repo.agregar(Solicitud(**datos.model_dump()))
    _avisar_a(repo, Permisos.SOLICITUDES_GESTIONAR,
              f"Nueva solicitud de {datos.tipo.value}: {propiedad.clave} · {datos.nombre}", solicitud.id)
    return solicitud


def recibir_oferta(repo: SolicitudRepository, datos: OfertaPropiedadIn) -> tuple[Solicitud, Propiedad]:
    """«Vende o renta con nosotros»: la propiedad ingresa como particular y en revisión (RN-03)."""
    domain.validar_contacto(datos.telefono, datos.email)
    prepo = PropiedadRepository(repo.db)
    if datos.zona_id is not None and not prepo.zona_existe(datos.zona_id):
        raise ReglaDeNegocio("La zona indicada no existe")
    propietario = prepo.obtener_o_crear_propietario(datos.nombre, datos.telefono, datos.email)
    propiedad = prepo.agregar(Propiedad(
        titulo=datos.titulo, descripcion=datos.descripcion, operacion=datos.operacion, tipo=datos.tipo,
        zona_id=datos.zona_id, recamaras=datos.recamaras, banos=datos.banos, superficie_m2=datos.superficie_m2,
        origen=Origen.PARTICULAR, estado_publicacion=EstadoPublicacion.EN_REVISION))
    # Lo que pide el dueño y su dirección son datos internos: nunca se publican (RN-01).
    repo.db.add(DatosInternos(propiedad_id=propiedad.id, propietario_id=propietario.id,
                              precio_real=datos.precio_pedido, direccion_exacta=datos.direccion))
    solicitud = repo.agregar(Solicitud(tipo=TipoSolicitud.VENDER_RENTAR, propiedad_id=propiedad.id, nombre=datos.nombre,
                                       telefono=datos.telefono, email=datos.email, mensaje=datos.mensaje))
    _avisar_a(repo, Permisos.PROPIEDADES_PUBLICAR,
              f"Propiedad ofrecida por particular para revisión: {propiedad.clave}", solicitud.id)
    return solicitud, propiedad


def asignar_solicitud(repo: SolicitudRepository, auditor: Auditor, solicitud_id: int, asesor_id: int) -> Solicitud:
    solicitud = _obtener(repo, solicitud_id)
    domain.validar_transicion(solicitud.estado, EstadoSolicitud.ASIGNADA)
    asesor = UsuarioRepository(repo.db).obtener(asesor_id)
    if asesor is None or not asesor.activo or Permisos.SOLICITUDES_GESTIONAR not in asesor.permisos:
        raise ReglaDeNegocio("El usuario indicado no puede atender solicitudes")
    auditor.registrar(ENTIDAD, solicitud.id, "asignar", "asignado_a", solicitud.asignado_a, asesor_id)
    solicitud.asignado_a = asesor_id
    solicitud.estado = EstadoSolicitud.ASIGNADA
    repo.avisar([asesor_id], f"Se te asignó la solicitud #{solicitud.id} de {solicitud.nombre}", solicitud.id)
    return solicitud


def atender_solicitud(repo: SolicitudRepository, auditor: Auditor, solicitud_id: int, datos: AtencionIn) -> Solicitud:
    """Marca la solicitud como atendida y, si se indica, registra al solicitante como prospecto del CRM."""
    solicitud = _obtener(repo, solicitud_id)
    domain.validar_transicion(solicitud.estado, EstadoSolicitud.ATENDIDA)
    if datos.crear_prospecto and solicitud.tipo != TipoSolicitud.VENDER_RENTAR and solicitud.prospecto_id is None:
        prospecto = Prospecto(nombre=solicitud.nombre, telefono=solicitud.telefono, email=solicitud.email,
                              origen=f"solicitud de {solicitud.tipo.value}", asesor_id=solicitud.asignado_a)
        if solicitud.propiedad is not None:
            prospecto.propiedades = [solicitud.propiedad]
        repo.db.add(prospecto)
        repo.db.flush()
        solicitud.prospecto_id = prospecto.id
        auditor.registrar("prospectos", prospecto.id, "crear", "origen", None, prospecto.origen)
    auditor.registrar(ENTIDAD, solicitud.id, "actualizar", "estado", solicitud.estado, EstadoSolicitud.ATENDIDA)
    solicitud.estado = EstadoSolicitud.ATENDIDA
    solicitud.atendido_en = datetime.now(UTC)
    return solicitud


def descartar_solicitud(repo: SolicitudRepository, auditor: Auditor, solicitud_id: int, datos: DescarteIn) -> Solicitud:
    solicitud = _obtener(repo, solicitud_id)
    domain.validar_transicion(solicitud.estado, EstadoSolicitud.DESCARTADA)
    auditor.registrar(ENTIDAD, solicitud.id, "actualizar", "estado", solicitud.estado, EstadoSolicitud.DESCARTADA)
    solicitud.estado = EstadoSolicitud.DESCARTADA
    solicitud.motivo_descarte = datos.motivo
    solicitud.atendido_en = datetime.now(UTC)
    return solicitud


def marcar_aviso_leido(repo: SolicitudRepository, aviso_id: int, usuario_id: int):
    aviso = repo.obtener_aviso(aviso_id)
    if aviso is None or aviso.usuario_id != usuario_id:
        raise NoEncontrado("Aviso no encontrado")
    aviso.leido = True
    return aviso
