"""Bitácora de auditoría de cambios relevantes."""
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func, select
from sqlalchemy.orm import Mapped, Session, mapped_column

from app.core.database import Base


class RegistroAuditoria(Base):
    __tablename__ = "auditoria"
    id: Mapped[int] = mapped_column(primary_key=True)
    usuario_id: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id", ondelete="SET NULL"), index=True)
    entidad: Mapped[str] = mapped_column(String(50))
    entidad_id: Mapped[int]
    accion: Mapped[str] = mapped_column(String(20))
    campo: Mapped[str | None] = mapped_column(String(50))
    valor_anterior: Mapped[str | None] = mapped_column(Text)
    valor_nuevo: Mapped[str | None] = mapped_column(Text)
    fecha: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)


class AuditoriaRepository:
    def __init__(self, db: Session):
        self.db = db

    def agregar(self, registro: RegistroAuditoria) -> None:
        self.db.add(registro)

    def consultar(self, entidad: str | None, entidad_id: int | None, usuario_id: int | None,
                  limite: int, desplazamiento: int, desde: datetime | None = None, hasta: datetime | None = None,
                  accion: str | None = None) -> list[RegistroAuditoria]:
        stmt = select(RegistroAuditoria).order_by(RegistroAuditoria.fecha.desc(), RegistroAuditoria.id.desc())
        if desde is not None:
            stmt = stmt.where(RegistroAuditoria.fecha >= desde)
        if hasta is not None:
            stmt = stmt.where(RegistroAuditoria.fecha < hasta)
        if accion:
            stmt = stmt.where(RegistroAuditoria.accion == accion)
        if entidad:
            stmt = stmt.where(RegistroAuditoria.entidad == entidad)
        if entidad_id is not None:
            stmt = stmt.where(RegistroAuditoria.entidad_id == entidad_id)
        if usuario_id is not None:
            stmt = stmt.where(RegistroAuditoria.usuario_id == usuario_id)
        return list(self.db.scalars(stmt.limit(limite).offset(desplazamiento)))

    def nombres_usuarios(self, ids: set[int]) -> dict[int, str]:
        from app.features.usuarios.infrastructure import Usuario

        if not ids:
            return {}
        return dict(self.db.execute(select(Usuario.id, Usuario.nombre).where(Usuario.id.in_(ids))).all())

    def titulos_propiedades(self, ids: set[int]) -> dict[int, tuple[str, str | None]]:
        """Título y zona de las propiedades citadas en la bitácora."""
        from app.features.catalogos.infrastructure import Zona
        from app.features.propiedades.infrastructure import Propiedad

        if not ids:
            return {}
        filas = self.db.execute(select(Propiedad.id, Propiedad.titulo, Zona.nombre)
                                .outerjoin(Zona, Zona.id == Propiedad.zona_id).where(Propiedad.id.in_(ids)))
        return {pid: (titulo, zona) for pid, titulo, zona in filas}
