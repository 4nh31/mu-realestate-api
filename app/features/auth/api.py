from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from app.core.deps import CurrentUser, DbSession
from app.features.auth.application import CredencialesInvalidas, iniciar_sesion
from app.features.auth.schemas import Perfil, Token
from app.features.usuarios.infrastructure import UsuarioRepository

router = APIRouter(prefix="/auth", tags=["Autenticación"])


@router.post("/login", response_model=Token, summary="Iniciar sesión y obtener un token JWT")
def login(db: DbSession, form: Annotated[OAuth2PasswordRequestForm, Depends()]):
    """Recibe `username` (correo) y `password` como formulario OAuth2 y devuelve un token Bearer."""
    try:
        token = iniciar_sesion(UsuarioRepository(db), form.username, form.password)
    except CredencialesInvalidas:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Correo o contraseña incorrectos") from None
    db.commit()
    return Token(access_token=token)


@router.get("/me", response_model=Perfil, summary="Perfil y permisos del usuario autenticado")
def me(usuario: CurrentUser):
    return Perfil(id=usuario.id, nombre=usuario.nombre, email=usuario.email, rol=usuario.rol.nombre,
                  permisos=sorted(usuario.permisos))
