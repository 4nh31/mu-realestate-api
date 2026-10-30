"""Infraestructura de cuentas: códigos de verificación, favoritos y consultas del dueño."""
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, SmallInteger, String, delete, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Mapped, Session, mapped_column

from app.core.database import Base
from app.core.types import pg_enum
from app.features.cuentas.domain import PropositoCodigo
from app.features.propiedades.domain import EstadoPublicacion
from app.features.propiedades.infrastructure import DatosInternos, Propiedad, Propietario


class CodigoVerificacion(Base):
    __tablename__ = "codigos_verificacion"
    id: Mapped[int] = mapped_column(primary_key=True)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id", ondelete="CASCADE"), index=True)
    proposito: Mapped[PropositoCodigo] = mapped_column(pg_enum(PropositoCodigo, "proposito_codigo"))
    codigo_hash: Mapped[str] = mapped_column(String(100))
    expira_en: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    intentos: Mapped[int] = mapped_column(SmallInteger, default=0, server_default="0")
    usado_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (CheckConstraint("intentos >= 0 AND intentos <= 5", name="intentos_rango"),)


class Favorito(Base):
    __tablename__ = "favoritos"
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id", ondelete="CASCADE"), primary_key=True)
    propiedad_id: Mapped[int] = mapped_column(ForeignKey("propiedades.id", ondelete="CASCADE"), primary_key=True,
                                              index=True)
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


def _publicada():
    return (Propiedad.estado_publicacion == EstadoPublicacion.PUBLICADA) & Propiedad.activo.is_(True)


class CuentaRepository:
    def __init__(self, db: Session):
        self.db = db

    # ---- códigos ----
    def codigo_vigente(self, usuario_id: int, proposito: PropositoCodigo) -> CodigoVerificacion | None:
        """El último código sin usar; los anteriores quedan invalidados al emitir uno nuevo."""
        stmt = (select(CodigoVerificacion)
                .where(CodigoVerificacion.usuario_id == usuario_id, CodigoVerificacion.proposito == proposito,
                       CodigoVerificacion.usado_en.is_(None))
                .order_by(CodigoVerificacion.creado_en.desc(), CodigoVerificacion.id.desc()).limit(1))
        return self.db.scalar(stmt)

    def invalidar_codigos(self, usuario_id: int, proposito: PropositoCodigo, ahora: datetime) -> None:
        for codigo in self.db.scalars(select(CodigoVerificacion).where(
                CodigoVerificacion.usuario_id == usuario_id, CodigoVerificacion.proposito == proposito,
                CodigoVerificacion.usado_en.is_(None))):
            codigo.usado_en = ahora

    # ---- favoritos ----
    def favoritos(self, usuario_id: int) -> list[Propiedad]:
        stmt = (select(Propiedad).join(Favorito, Favorito.propiedad_id == Propiedad.id)
                .where(Favorito.usuario_id == usuario_id, _publicada()).order_by(Favorito.creado_en.desc()))
        return list(self.db.scalars(stmt).unique())

    def guardar_favoritos(self, usuario_id: int, propiedad_ids: list[int]) -> None:
        """Idempotente: ignora los que ya estaban guardados."""
        if propiedad_ids:
            filas = [{"usuario_id": usuario_id, "propiedad_id": pid} for pid in dict.fromkeys(propiedad_ids)]
            self.db.execute(insert(Favorito).values(filas).on_conflict_do_nothing())

    def quitar_favorito(self, usuario_id: int, propiedad_id: int) -> None:
        self.db.execute(delete(Favorito).where(Favorito.usuario_id == usuario_id,
                                               Favorito.propiedad_id == propiedad_id))

    def ids_publicadas(self, propiedad_ids: list[int]) -> list[int]:
        if not propiedad_ids:
            return []
        return list(self.db.scalars(select(Propiedad.id).where(Propiedad.id.in_(propiedad_ids), _publicada())))

    def usuarios_con_favorito(self, propiedad_id: int) -> list[int]:
        return list(self.db.scalars(select(Favorito.usuario_id).where(Favorito.propiedad_id == propiedad_id)))

    # ---- propiedades del dueño ----
    def propietario_de(self, usuario_id: int) -> Propietario | None:
        return self.db.scalar(select(Propietario).where(Propietario.usuario_id == usuario_id))

    def propiedades_de(self, usuario_id: int) -> list[Propiedad]:
        stmt = (select(Propiedad).join(DatosInternos, DatosInternos.propiedad_id == Propiedad.id)
                .join(Propietario, Propietario.id == DatosInternos.propietario_id)
                .where(Propietario.usuario_id == usuario_id).order_by(Propiedad.creado_en.desc()))
        return list(self.db.scalars(stmt).unique())
