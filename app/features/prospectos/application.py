"""Casos de uso del CRM de prospectos."""
from app.core.exceptions import Conflicto, NoEncontrado, ReglaDeNegocio
from app.features.auditoria.application import Auditor
from app.features.propiedades.infrastructure import Propiedad
from app.features.prospectos import domain
from app.features.prospectos.domain import EtapaProspecto, TipoSeguimiento
from app.features.prospectos.infrastructure import Prospecto, ProspectoRepository, Seguimiento
from app.features.prospectos.schemas import CambioEtapa, ProspectoActualizar, ProspectoIn, SeguimientoIn
from app.features.usuarios.infrastructure import UsuarioRepository

ENTIDAD = "prospectos"


def _obtener(repo: ProspectoRepository, prospecto_id: int) -> Prospecto:
    prospecto = repo.obtener(prospecto_id)
    if prospecto is None:
        raise NoEncontrado("Prospecto no encontrado")
    return prospecto


def _validar_asesor(repo: ProspectoRepository, asesor_id: int | None) -> None:
    if asesor_id is not None:
        asesor = UsuarioRepository(repo.db).obtener(asesor_id)
        if asesor is None or not asesor.activo:
            raise ReglaDeNegocio("El asesor indicado no existe o está inactivo")


def _propiedades(repo: ProspectoRepository, ids: list[int]) -> list[Propiedad]:
    encontradas = [repo.db.get(Propiedad, i) for i in dict.fromkeys(ids)]
    if any(p is None for p in encontradas):
        raise ReglaDeNegocio("Alguna de las propiedades indicadas no existe")
    return encontradas


def registrar_prospecto(repo: ProspectoRepository, auditor: Auditor, datos: ProspectoIn) -> Prospecto:
    domain.validar_presupuesto(datos.presupuesto_min, datos.presupuesto_max)
    _validar_asesor(repo, datos.asesor_id)
    prospecto = Prospecto(**datos.model_dump(exclude={"propiedad_ids"}),
                          propiedades=_propiedades(repo, datos.propiedad_ids))
    repo.agregar(prospecto)
    auditor.registrar(ENTIDAD, prospecto.id, "crear", "etapa", None, prospecto.etapa)
    if prospecto.asesor_id:
        auditor.registrar(ENTIDAD, prospecto.id, "asignar", "asesor_id", None, prospecto.asesor_id)
    return prospecto


def editar_prospecto(repo: ProspectoRepository, auditor: Auditor, prospecto_id: int,
                     datos: ProspectoActualizar) -> Prospecto:
    prospecto = _obtener(repo, prospecto_id)
    cambios = datos.model_dump(exclude_unset=True, exclude={"propiedad_ids"})
    domain.validar_presupuesto(cambios.get("presupuesto_min", prospecto.presupuesto_min),
                               cambios.get("presupuesto_max", prospecto.presupuesto_max))
    if "asesor_id" in cambios:
        _validar_asesor(repo, cambios["asesor_id"])
        if cambios["asesor_id"] != prospecto.asesor_id:
            auditor.registrar(ENTIDAD, prospecto.id, "asignar", "asesor_id", prospecto.asesor_id, cambios["asesor_id"])
    for campo, valor in cambios.items():
        setattr(prospecto, campo, valor)
    if datos.propiedad_ids is not None:
        prospecto.propiedades = _propiedades(repo, datos.propiedad_ids)
    return prospecto


def eliminar_prospecto(repo: ProspectoRepository, auditor: Auditor, prospecto_id: int) -> None:
    from app.features.agenda.infrastructure import CitaRepository  # evita importación circular

    prospecto = _obtener(repo, prospecto_id)
    if CitaRepository(repo.db).existen_para_prospecto(prospecto.id):
        raise Conflicto("El prospecto tiene visitas registradas; márquelo como perdido en lugar de eliminarlo")
    auditor.registrar(ENTIDAD, prospecto.id, "eliminar", "nombre", prospecto.nombre, None)
    repo.eliminar(prospecto)


def cambiar_etapa(repo: ProspectoRepository, auditor: Auditor, prospecto_id: int, cambio: CambioEtapa,
                  usuario_id: int) -> Prospecto:
    """Mueve al prospecto por el embudo; cerrar o perder un prospecto es un cambio de etapa final."""
    prospecto = _obtener(repo, prospecto_id)
    domain.validar_transicion(prospecto.etapa, cambio.etapa)
    if cambio.etapa in domain.ETAPAS_FINALES and not cambio.comentario:
        raise ReglaDeNegocio("Indique un comentario al cerrar o marcar como perdido un prospecto")
    auditor.registrar(ENTIDAD, prospecto.id, "actualizar", "etapa", prospecto.etapa, cambio.etapa)
    nota = f"Cambio de etapa: {prospecto.etapa.value} → {cambio.etapa.value}"
    if cambio.comentario:
        nota += f". {cambio.comentario}"
    repo.agregar_seguimiento(Seguimiento(prospecto_id=prospecto.id, usuario_id=usuario_id,
                                         tipo=TipoSeguimiento.NOTA, descripcion=nota))
    prospecto.etapa = cambio.etapa
    return prospecto


def registrar_seguimiento(repo: ProspectoRepository, prospecto_id: int, datos: SeguimientoIn,
                          usuario_id: int) -> Seguimiento:
    prospecto = _obtener(repo, prospecto_id)
    if prospecto.etapa in domain.ETAPAS_FINALES:
        raise ReglaDeNegocio("No se registran seguimientos de un prospecto cerrado o perdido")
    seguimiento = repo.agregar_seguimiento(Seguimiento(prospecto_id=prospecto.id, usuario_id=usuario_id,
                                                       tipo=datos.tipo, descripcion=datos.descripcion))
    # El primer contacto registrado mueve al prospecto de «nuevo» a «contactado».
    if prospecto.etapa == EtapaProspecto.NUEVO and datos.tipo != TipoSeguimiento.NOTA:
        prospecto.etapa = EtapaProspecto.CONTACTADO
    return seguimiento
