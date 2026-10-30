"""Endpoints del módulo de usuarios, roles y permisos."""
from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.core.deps import RESPUESTAS_PROTEGIDAS, DbSession, require_permission
from app.features.auditoria.application import Auditor
from app.features.usuarios import application as casos
from app.features.usuarios.domain import Permisos
from app.features.usuarios.infrastructure import Usuario, UsuarioRepository
from app.features.usuarios.schemas import PersonalOut, RolOut, UsuarioActualizar, UsuarioCrear, UsuarioOut

router = APIRouter(prefix="/usuarios", tags=["Usuarios, roles y permisos"], responses=RESPUESTAS_PROTEGIDAS)
Admin = Annotated[Usuario, Depends(require_permission(Permisos.USUARIOS_GESTIONAR))]


@router.get("", response_model=list[UsuarioOut], summary="Listar usuarios")
def listar_usuarios(db: DbSession, _: Admin, activo: bool | None = None):
    return [UsuarioOut.desde(u) for u in UsuarioRepository(db).listar(activo)]


@router.post("", response_model=UsuarioOut, status_code=status.HTTP_201_CREATED, summary="Crear usuario")
def crear_usuario(datos: UsuarioCrear, db: DbSession, actor: Admin):
    usuario = casos.crear_usuario(UsuarioRepository(db), Auditor(db, actor.id), datos)
    db.commit()
    return UsuarioOut.desde(usuario)


@router.patch("/{usuario_id}", response_model=UsuarioOut, summary="Modificar datos, rol o estado de un usuario")
def actualizar_usuario(usuario_id: int, datos: UsuarioActualizar, db: DbSession, actor: Admin):
    usuario = casos.actualizar_usuario(UsuarioRepository(db), Auditor(db, actor.id), usuario_id, datos, actor.id)
    db.commit()
    return UsuarioOut.desde(usuario)


@router.get("/personal", response_model=list[PersonalOut],
            summary="Personal activo que puede atender solicitudes (para asignar)")
def listar_personal(db: DbSession, _: Annotated[Usuario, Depends(require_permission(Permisos.PROPIEDADES_VER))]):
    return [PersonalOut.desde(u) for u in UsuarioRepository(db).con_permiso(Permisos.SOLICITUDES_GESTIONAR)]


@router.get("/roles", response_model=list[RolOut], summary="Listar roles con sus permisos")
def listar_roles(db: DbSession, _: Admin):
    return [RolOut.desde(r) for r in UsuarioRepository(db).listar_roles()]
