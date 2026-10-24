"""Crea el primer usuario administrador.

Uso:  python -m app.scripts.crear_admin --email admin@mu.mx --nombre "Administrador"
La contraseña se solicita por consola (no queda en el historial).
"""
import argparse
import getpass

from app.core.database import SessionLocal
from app.core.security import hash_password
from app.features.usuarios.domain import ROL_ADMINISTRADOR
from app.features.usuarios.infrastructure import Usuario, UsuarioRepository


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--email", required=True)
    parser.add_argument("--nombre", default="Administrador")
    args = parser.parse_args()
    password = getpass.getpass("Contraseña (mín. 8 caracteres): ")
    if len(password) < 8:
        raise SystemExit("La contraseña debe tener al menos 8 caracteres")
    with SessionLocal() as db:
        repo = UsuarioRepository(db)
        if repo.obtener_por_email(args.email):
            raise SystemExit("Ya existe un usuario con ese correo")
        rol = repo.obtener_rol(ROL_ADMINISTRADOR)
        if rol is None:
            raise SystemExit("Ejecute primero: alembic upgrade head")
        repo.agregar(Usuario(nombre=args.nombre, email=args.email.lower(), rol=rol,
                             password_hash=hash_password(password)))
        db.commit()
    print(f"Administrador {args.email} creado.")


if __name__ == "__main__":
    main()
