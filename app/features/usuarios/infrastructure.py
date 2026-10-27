"""Infraestructura del slice de usuarios: modelos ORM y repositorio SQLAlchemy."""
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String, Table, select
from sqlalchemy.orm import Mapped, Session, mapped_column, relationship, selectinload

from app.core.database import Base, TimestampMixin

rol_permisos = Table(
    "rol_permisos",
    Base.metadata,
    Column("rol_id", ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
    Column("permiso_id", ForeignKey("permisos.id", ondelete="CASCADE"), primary_key=True),
)


class Permiso(Base):
    __tablename__ = "permisos"
    id: Mapped[int] = mapped_column(primary_key=True)
    clave: Mapped[str] = mapped_column(String(60), unique=True)
    descripcion: Mapped[str] = mapped_column(String(200))


class Rol(Base):
    __tablename__ = "roles"
    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(40), unique=True)
    descripcion: Mapped[str | None] = mapped_column(String(200))
    permisos: Mapped[list[Permiso]] = relationship(secondary=rol_permisos, lazy="selectin")


class Usuario(TimestampMixin, Base):
    __tablename__ = "usuarios"
    id: Mapped[int] = mapped_column(primary_key=True)
    rol_id: Mapped[int] = mapped_column(ForeignKey("roles.id"))
    nombre: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(160), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(100))
    activo: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    ultimo_acceso: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    rol: Mapped[Rol] = relationship(lazy="selectin")

    @property
    def permisos(self) -> set[str]:
        return {p.clave for p in self.rol.permisos}


class UsuarioRepository:
    def __init__(self, db: Session):
        self.db = db

    def obtener(self, usuario_id: int) -> Usuario | None:
        return self.db.get(Usuario, usuario_id)

    def obtener_por_email(self, email: str) -> Usuario | None:
        return self.db.scalar(select(Usuario).where(Usuario.email == email.lower()))

    def listar(self, activo: bool | None = None) -> list[Usuario]:
        stmt = select(Usuario).options(selectinload(Usuario.rol)).order_by(Usuario.nombre)
        if activo is not None:
            stmt = stmt.where(Usuario.activo == activo)
        return list(self.db.scalars(stmt))

    def obtener_rol(self, nombre: str) -> Rol | None:
        return self.db.scalar(select(Rol).where(Rol.nombre == nombre))

    def listar_roles(self) -> list[Rol]:
        return list(self.db.scalars(select(Rol).order_by(Rol.nombre)))

    def con_permiso(self, clave: str) -> list[Usuario]:
        """Usuarios activos cuyo rol incluye el permiso indicado (destinatarios de avisos)."""
        stmt = (select(Usuario).join(Rol).join(rol_permisos).join(Permiso)
                .where(Permiso.clave == clave, Usuario.activo.is_(True)))
        return list(self.db.scalars(stmt).unique())

    def agregar(self, usuario: Usuario) -> Usuario:
        self.db.add(usuario)
        self.db.flush()
        return usuario
