"""Caso de uso: iniciar sesión."""
from datetime import UTC, datetime

from app.core.security import create_access_token, verify_password
from app.features.usuarios.infrastructure import UsuarioRepository


class CredencialesInvalidas(Exception):
    pass


def iniciar_sesion(repo: UsuarioRepository, email: str, password: str) -> str:
    usuario = repo.obtener_por_email(email)
    # Mismo mensaje para correo inexistente y contraseña incorrecta: no revela qué correos existen.
    if usuario is None or not usuario.activo or not verify_password(password, usuario.password_hash):
        raise CredencialesInvalidas()
    usuario.ultimo_acceso = datetime.now(UTC)
    return create_access_token(str(usuario.id), usuario.rol.nombre)
