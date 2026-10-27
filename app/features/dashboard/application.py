"""Consultas de indicadores y reportes de la operación (solo lectura)."""
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.features.agenda.domain import ESTADOS_ACTIVOS, EstadoCita
from app.features.agenda.infrastructure import Cita
from app.features.propiedades.domain import Disponibilidad, EstadoPublicacion, Origen
from app.features.propiedades.infrastructure import Propiedad
from app.features.prospectos.domain import EtapaProspecto
from app.features.prospectos.infrastructure import Prospecto
from app.features.solicitudes.domain import EstadoSolicitud, TipoSolicitud
from app.features.solicitudes.infrastructure import Aviso, Solicitud


def _conteo(db: Session, columna, enum_cls, *filtros) -> dict[str, int]:
    filas = db.execute(select(columna, func.count()).where(*filtros).group_by(columna)).all()
    datos = {m.value: 0 for m in enum_cls}
    datos.update({k.value: n for k, n in filas})
    return datos


def indicadores(db: Session, usuario_id: int, ahora: datetime | None = None) -> dict:
    ahora = ahora or datetime.now(UTC)
    activas = Propiedad.activo.is_(True)
    prospectos = _conteo(db, Prospecto.etapa, EtapaProspecto)
    total_prospectos = sum(prospectos.values())
    return {
        "propiedades": {
            "total_activas": db.scalar(select(func.count()).select_from(Propiedad).where(activas)),
            "por_estado_publicacion": _conteo(db, Propiedad.estado_publicacion, EstadoPublicacion, activas),
            "por_disponibilidad": _conteo(db, Propiedad.disponibilidad, Disponibilidad, activas),
            "ofrecidas_por_particulares_en_revision": db.scalar(
                select(func.count()).select_from(Propiedad).where(
                    activas, Propiedad.origen == Origen.PARTICULAR,
                    Propiedad.estado_publicacion == EstadoPublicacion.EN_REVISION)),
        },
        "solicitudes": _conteo(db, Solicitud.estado, EstadoSolicitud),
        "prospectos": {
            "por_etapa": prospectos,
            "tasa_cierre_pct": round(100 * prospectos["cerrado"] / total_prospectos, 1) if total_prospectos else 0.0,
        },
        "visitas": {
            "proximos_7_dias": db.scalar(select(func.count()).select_from(Cita).where(
                Cita.estado.in_(ESTADOS_ACTIVOS), Cita.fecha_hora >= ahora,
                Cita.fecha_hora < ahora + timedelta(days=7))),
            "por_estado": _conteo(db, Cita.estado, EstadoCita),
        },
        "avisos_sin_leer": db.scalar(select(func.count()).select_from(Aviso).where(
            Aviso.usuario_id == usuario_id, Aviso.leido.is_(False))),
    }


def reporte_periodo(db: Session, desde: datetime, hasta: datetime) -> list[dict]:
    """Resumen de la operación en un periodo: altas, solicitudes, prospectos y visitas."""
    en = lambda col: (col >= desde, col < hasta)  # noqa: E731
    filas = [
        ("Propiedades registradas por la empresa", select(func.count()).select_from(Propiedad).where(
            *en(Propiedad.creado_en), Propiedad.origen == Origen.INTERNA)),
        ("Propiedades ofrecidas por particulares", select(func.count()).select_from(Propiedad).where(
            *en(Propiedad.creado_en), Propiedad.origen == Origen.PARTICULAR)),
        ("Solicitudes de contacto recibidas", select(func.count()).select_from(Solicitud).where(
            *en(Solicitud.creado_en), Solicitud.tipo == TipoSolicitud.CONTACTO)),
        ("Solicitudes de visita recibidas", select(func.count()).select_from(Solicitud).where(
            *en(Solicitud.creado_en), Solicitud.tipo == TipoSolicitud.VISITA)),
        ("Solicitudes atendidas", select(func.count()).select_from(Solicitud).where(
            *en(Solicitud.atendido_en), Solicitud.estado == EstadoSolicitud.ATENDIDA)),
        ("Solicitudes descartadas", select(func.count()).select_from(Solicitud).where(
            *en(Solicitud.atendido_en), Solicitud.estado == EstadoSolicitud.DESCARTADA)),
        ("Prospectos registrados", select(func.count()).select_from(Prospecto).where(*en(Prospecto.creado_en))),
        ("Visitas agendadas en el periodo", select(func.count()).select_from(Cita).where(*en(Cita.fecha_hora))),
        ("Visitas realizadas en el periodo", select(func.count()).select_from(Cita).where(
            *en(Cita.fecha_hora), Cita.estado == EstadoCita.REALIZADA)),
    ]
    return [{"indicador": nombre, "valor": db.scalar(q) or 0} for nombre, q in filas]
