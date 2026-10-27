"""Casos de uso de la agenda de visitas."""
from datetime import UTC, datetime

from app.core.exceptions import Conflicto, NoEncontrado, ReglaDeNegocio
from app.features.agenda import domain
from app.features.agenda.domain import EstadoCita
from app.features.agenda.infrastructure import Cita, CitaRepository
from app.features.agenda.schemas import CancelacionIn, CitaIn, ReprogramacionIn
from app.features.auditoria.application import Auditor
from app.features.propiedades.infrastructure import Propiedad
from app.features.prospectos.domain import EtapaProspecto
from app.features.prospectos.infrastructure import Prospecto
from app.features.usuarios.infrastructure import UsuarioRepository

ENTIDAD = "citas"


def _obtener(repo: CitaRepository, cita_id: int) -> Cita:
    cita = repo.obtener(cita_id)
    if cita is None:
        raise NoEncontrado("Visita no encontrada")
    return cita


def _validar_sin_empalme(repo: CitaRepository, asesor_id: int, fecha_hora: datetime, excluir_id: int | None = None):
    """RN-05: un asesor no puede tener dos visitas activas en el mismo horario."""
    if repo.empalmadas(asesor_id, fecha_hora, excluir_id):
        raise Conflicto("El asesor ya tiene una visita en ese horario")


def agendar_visita(repo: CitaRepository, auditor: Auditor, datos: CitaIn) -> Cita:
    domain.validar_fecha_futura(datos.fecha_hora, datetime.now(UTC))
    propiedad = repo.db.get(Propiedad, datos.propiedad_id)
    if propiedad is None or not propiedad.activo:
        raise ReglaDeNegocio("La propiedad no existe o está desactivada")
    prospecto = repo.db.get(Prospecto, datos.prospecto_id)
    if prospecto is None:
        raise ReglaDeNegocio("El prospecto no existe")
    asesor = UsuarioRepository(repo.db).obtener(datos.asesor_id)
    if asesor is None or not asesor.activo:
        raise ReglaDeNegocio("El asesor no existe o está inactivo")
    _validar_sin_empalme(repo, datos.asesor_id, datos.fecha_hora)
    cita = repo.agregar(Cita(**datos.model_dump()))
    auditor.registrar(ENTIDAD, cita.id, "crear", "fecha_hora", None, cita.fecha_hora.isoformat())
    # Agendar una visita mueve al prospecto a la etapa «en visita» cuando aún no llegaba a ella.
    if prospecto.etapa in (EtapaProspecto.NUEVO, EtapaProspecto.CONTACTADO):
        auditor.registrar("prospectos", prospecto.id, "actualizar", "etapa", prospecto.etapa, EtapaProspecto.EN_VISITA)
        prospecto.etapa = EtapaProspecto.EN_VISITA
    return cita


def _cambiar_estado(auditor: Auditor, cita: Cita, nuevo: EstadoCita, nota: str | None = None) -> Cita:
    domain.validar_transicion(cita.estado, nuevo)
    auditor.registrar(ENTIDAD, cita.id, "actualizar", "estado", cita.estado, nuevo)
    cita.estado = nuevo
    if nota:
        cita.notas = f"{cita.notas}\n{nota}" if cita.notas else nota
    return cita


def confirmar_visita(repo: CitaRepository, auditor: Auditor, cita_id: int) -> Cita:
    return _cambiar_estado(auditor, _obtener(repo, cita_id), EstadoCita.CONFIRMADA)


def reprogramar_visita(repo: CitaRepository, auditor: Auditor, cita_id: int, datos: ReprogramacionIn) -> Cita:
    cita = _obtener(repo, cita_id)
    domain.validar_transicion(cita.estado, EstadoCita.REPROGRAMADA)
    domain.validar_fecha_futura(datos.fecha_hora, datetime.now(UTC))
    if cita.asesor_id is not None:
        _validar_sin_empalme(repo, cita.asesor_id, datos.fecha_hora, excluir_id=cita.id)
    auditor.registrar(ENTIDAD, cita.id, "actualizar", "fecha_hora", cita.fecha_hora.isoformat(),
                      datos.fecha_hora.isoformat())
    cita.fecha_hora = datos.fecha_hora
    return _cambiar_estado(auditor, cita, EstadoCita.REPROGRAMADA,
                           f"Reprogramada: {datos.motivo}" if datos.motivo else None)


def cancelar_visita(repo: CitaRepository, auditor: Auditor, cita_id: int, datos: CancelacionIn) -> Cita:
    return _cambiar_estado(auditor, _obtener(repo, cita_id), EstadoCita.CANCELADA, f"Cancelada: {datos.motivo}")


def registrar_visita_realizada(repo: CitaRepository, auditor: Auditor, cita_id: int) -> Cita:
    return _cambiar_estado(auditor, _obtener(repo, cita_id), EstadoCita.REALIZADA)
