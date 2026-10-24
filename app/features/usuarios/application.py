"""Casos de uso del slice de usuarios."""
from app.core.exceptions import Conflicto, NoEncontrado, ReglaDeNegocio
from app.core.security import hash_password
from app.features.auditoria.application import Auditor
from app.features.usuarios.infrastructure import Usuario, UsuarioRepository
from app.features.usuarios.schemas import UsuarioActualizar, UsuarioCrear


def crear_usuario(repo: UsuarioRepository, auditor: Auditor, datos: UsuarioCrear) -> Usuario:
    email = datos.email.lower()
    if repo.obtener_por_email(email):
        raise Conflicto("Ya existe un usuario con ese correo")
    rol = repo.obtener_rol(datos.rol)
    if rol is None:
        raise ReglaDeNegocio(f"El rol '{datos.rol}' no existe")
    usuario = repo.agregar(Usuario(nombre=datos.nombre, email=email, rol=rol, password_hash=hash_password(datos.password)))
    auditor.registrar("usuarios", usuario.id, "crear", "rol", None, rol.nombre)
    return usuario


def actualizar_usuario(repo: UsuarioRepository, auditor: Auditor, usuario_id: int, datos: UsuarioActualizar,
                       actor_id: int) -> Usuario:
    usuario = repo.obtener(usuario_id)
    if usuario is None:
        raise NoEncontrado("Usuario no encontrado")
    if datos.nombre is not None:
        usuario.nombre = datos.nombre
    if datos.rol is not None and datos.rol != usuario.rol.nombre:
        rol = repo.obtener_rol(datos.rol)
        if rol is None:
            raise ReglaDeNegocio(f"El rol '{datos.rol}' no existe")
        auditor.registrar("usuarios", usuario.id, "asignar", "rol", usuario.rol.nombre, rol.nombre)
        usuario.rol = rol
    if datos.activo is not None and datos.activo != usuario.activo:
        if usuario.id == actor_id and not datos.activo:
            raise ReglaDeNegocio("Un usuario no puede desactivarse a sí mismo")
        auditor.registrar("usuarios", usuario.id, "actualizar" if datos.activo else "desactivar", "activo",
                          usuario.activo, datos.activo)
        usuario.activo = datos.activo
    if datos.password is not None:
        usuario.password_hash = hash_password(datos.password)
    return usuario
