"""Infraestructura del centro de solicitudes y avisos internos: modelos ORM y repositorios."""
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, Text, func, select, update
from sqlalchemy.orm import Mapped, Session, mapped_column, relationship

from app.core.database import Base
from app.core.types import pg_enum
from app.features.notificaciones.domain import TipoAviso
from app.features.solicitudes.domain import EstadoSolicitud, TipoSolicitud


class Solicitud(Base):
    __tablename__ = "solicitudes"
    id: Mapped[int] = mapped_column(primary_key=True)
    tipo: Mapped[TipoSolicitud] = mapped_column(pg_enum(TipoSolicitud, "tipo_solicitud"))
    propiedad_id: Mapped[int | None] = mapped_column(ForeignKey("propiedades.id", ondelete="SET NULL"))
    nombre: Mapped[str] = mapped_column(String(120))
    telefono: Mapped[str | None] = mapped_column(String(20))
    email: Mapped[str | None] = mapped_column(String(160))
    mensaje: Mapped[str | None] = mapped_column(Text)
    fecha_preferida: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    estado: Mapped[EstadoSolicitud] = mapped_column(pg_enum(EstadoSolicitud, "estado_solicitud"),
                                                    default=EstadoSolicitud.NUEVA, server_default="nueva", index=True)
    asignado_a: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id", ondelete="SET NULL"))
    prospecto_id: Mapped[int | None] = mapped_column(ForeignKey("prospectos.id", ondelete="SET NULL"))
    motivo_descarte: Mapped[str | None] = mapped_column(Text)
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    atendido_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    propiedad = relationship("Propiedad", lazy="joined")


class Aviso(Base):
    __tablename__ = "avisos"
    id: Mapped[int] = mapped_column(primary_key=True)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id", ondelete="CASCADE"), index=True)
    solicitud_id: Mapped[int | None] = mapped_column(ForeignKey("solicitudes.id", ondelete="CASCADE"))
    tipo: Mapped[TipoAviso] = mapped_column(pg_enum(TipoAviso, "tipo_aviso"), default=TipoAviso.SOLICITUD,
                                            server_default=TipoAviso.SOLICITUD.value)
    titulo: Mapped[str] = mapped_column(String(150))
    mensaje: Mapped[str | None] = mapped_column(Text)
    enlace: Mapped[str | None] = mapped_column(String(255))
    autor_id: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id", ondelete="SET NULL"))
    por_correo: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    leido: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (Index("ix_avisos_usuario_leido", "usuario_id", "leido"),)


class SolicitudRepository:
    def __init__(self, db: Session):
        self.db = db

    def obtener(self, solicitud_id: int) -> Solicitud | None:
        return self.db.get(Solicitud, solicitud_id)

    def agregar(self, solicitud: Solicitud) -> Solicitud:
        self.db.add(solicitud)
        self.db.flush()
        return solicitud

    def listar(self, tipo: TipoSolicitud | None, estado: EstadoSolicitud | None, asignado_a: int | None,
               limite: int, desplazamiento: int) -> list[Solicitud]:
        stmt = select(Solicitud).order_by(Solicitud.creado_en.desc(), Solicitud.id.desc())
        if tipo:
            stmt = stmt.where(Solicitud.tipo == tipo)
        if estado:
            stmt = stmt.where(Solicitud.estado == estado)
        if asignado_a is not None:
            stmt = stmt.where(Solicitud.asignado_a == asignado_a)
        return list(self.db.scalars(stmt.limit(limite).offset(desplazamiento)).unique())

    # ---- avisos ----
    def avisar(self, usuario_ids: list[int], titulo: str, solicitud_id: int | None) -> None:
        for uid in dict.fromkeys(usuario_ids):
            self.db.add(Aviso(usuario_id=uid, titulo=titulo[:150], solicitud_id=solicitud_id,
                              enlace=f"/admin/solicitudes?id={solicitud_id}" if solicitud_id else None))

    def avisos_de(self, usuario_id: int, solo_no_leidos: bool) -> list[Aviso]:
        stmt = select(Aviso).where(Aviso.usuario_id == usuario_id).order_by(Aviso.creado_en.desc(), Aviso.id.desc())
        if solo_no_leidos:
            stmt = stmt.where(Aviso.leido.is_(False))
        return list(self.db.scalars(stmt))

    def obtener_aviso(self, aviso_id: int) -> Aviso | None:
        return self.db.get(Aviso, aviso_id)

    def marcar_todos_leidos(self, usuario_id: int) -> int:
        stmt = update(Aviso).where(Aviso.usuario_id == usuario_id, Aviso.leido.is_(False)).values(leido=True)
        return self.db.execute(stmt).rowcount
