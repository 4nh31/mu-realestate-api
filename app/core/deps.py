"""Dependencias transversales: usuario autenticado y verificación de permisos (RBAC)."""
from collections.abc import Callable
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import decode_access_token
from app.features.usuarios.infrastructure import Usuario, UsuarioRepository

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

DbSession = Annotated[Session, Depends(get_db)]


def get_current_user(db: DbSession, token: Annotated[str, Depends(oauth2_scheme)]) -> Usuario:
    no_autenticado = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Credenciales inválidas o sesión expirada",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_access_token(token)
        usuario_id = int(payload["sub"])
    except (jwt.PyJWTError, KeyError, ValueError):
        raise no_autenticado from None
    usuario = UsuarioRepository(db).obtener(usuario_id)
    if usuario is None or not usuario.activo:
        raise no_autenticado
    return usuario


CurrentUser = Annotated[Usuario, Depends(get_current_user)]


def require_permission(clave: str) -> Callable[[Usuario], Usuario]:
    """Devuelve una dependencia que permite el acceso solo si el rol del usuario tiene el permiso."""

    def _verificar(usuario: CurrentUser) -> Usuario:
        if clave not in usuario.permisos:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"Permiso requerido: {clave}")
        return usuario

    return _verificar
