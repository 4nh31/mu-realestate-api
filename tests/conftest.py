"""Fixtures: base de datos PostgreSQL de prueba migrada con Alembic y cliente HTTP."""
import os

os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://postgres:postgres@localhost:5432/mu_realestate_test")
os.environ["JWT_SECRET_KEY"] = "clave-de-pruebas-con-al-menos-32-caracteres"

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.core.database import SessionLocal, engine
from app.core.security import hash_password
from app.features.usuarios.infrastructure import Usuario, UsuarioRepository
from app.main import app

TABLAS_DATOS = ["auditoria", "avisos", "solicitudes", "seguimientos", "citas", "prospectos", "medios",
                "propiedad_amenidades", "datos_internos", "propiedades", "propietarios", "usuarios"]


@pytest.fixture(scope="session", autouse=True)
def esquema():
    cfg = Config("alembic.ini")
    command.downgrade(cfg, "base")
    command.upgrade(cfg, "head")
    yield


@pytest.fixture(autouse=True)
def limpiar():
    yield
    with engine.begin() as conn:
        conn.execute(text(f"TRUNCATE {', '.join(TABLAS_DATOS)} RESTART IDENTITY CASCADE"))


@pytest.fixture
def client():
    return TestClient(app)


def _crear_usuario(email: str, rol: str, password: str = "Secreta123") -> Usuario:
    with SessionLocal() as db:
        repo = UsuarioRepository(db)
        u = repo.agregar(Usuario(nombre=email.split("@")[0], email=email, rol=repo.obtener_rol(rol),
                                 password_hash=hash_password(password)))
        db.commit()
        return u


def _token(client: TestClient, email: str, password: str = "Secreta123") -> dict[str, str]:
    r = client.post("/api/v1/auth/login", data={"username": email, "password": password})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture
def admin(client):
    _crear_usuario("admin@murealestate.mx", "administrador")
    return _token(client, "admin@murealestate.mx")


@pytest.fixture
def asesor(client):
    _crear_usuario("asesor@murealestate.mx", "asesor")
    return _token(client, "asesor@murealestate.mx")
