from tests.conftest import _crear_usuario


def test_login_correcto_devuelve_token(client):
    _crear_usuario("ana@murealestate.mx", "asesor")
    r = client.post("/api/v1/auth/login", data={"username": "ana@murealestate.mx", "password": "Secreta123"})
    assert r.status_code == 200
    assert r.json()["token_type"] == "bearer"


def test_login_con_contrasena_incorrecta_responde_401(client):
    _crear_usuario("ana@murealestate.mx", "asesor")
    r = client.post("/api/v1/auth/login", data={"username": "ana@murealestate.mx", "password": "otra-clave"})
    assert r.status_code == 401


def test_login_usuario_inexistente_mismo_mensaje(client):
    r = client.post("/api/v1/auth/login", data={"username": "nadie@murealestate.mx", "password": "Secreta123"})
    assert r.status_code == 401
    assert r.json()["detail"] == "Correo o contraseña incorrectos"


def test_endpoint_protegido_sin_token_responde_401(client):
    assert client.get("/api/v1/auth/me").status_code == 401


def test_token_alterado_responde_401(client, admin):
    token = admin["Authorization"] + "x"
    assert client.get("/api/v1/auth/me", headers={"Authorization": token}).status_code == 401


def test_perfil_incluye_permisos_del_rol(client, asesor):
    r = client.get("/api/v1/auth/me", headers=asesor)
    assert r.status_code == 200
    assert r.json()["rol"] == "asesor"
    assert "propiedades:ver_interno" not in r.json()["permisos"]


def test_admin_crea_usuario_y_queda_auditado(client, admin):
    r = client.post("/api/v1/usuarios", headers=admin,
                    json={"nombre": "Luis Asesor", "email": "Luis@MUREALESTATE.mx", "password": "Secreta123", "rol": "asesor"})
    assert r.status_code == 201, r.text
    assert r.json()["email"] == "luis@murealestate.mx"
    auditoria = client.get("/api/v1/auditoria", headers=admin, params={"entidad": "usuarios"}).json()
    assert auditoria[0]["accion"] == "crear"


def test_correo_duplicado_responde_409(client, admin):
    datos = {"nombre": "Luis Asesor", "email": "luis@murealestate.mx", "password": "Secreta123", "rol": "asesor"}
    client.post("/api/v1/usuarios", headers=admin, json=datos)
    assert client.post("/api/v1/usuarios", headers=admin, json=datos).status_code == 409


def test_asesor_no_puede_administrar_usuarios(client, asesor):
    assert client.get("/api/v1/usuarios", headers=asesor).status_code == 403


def test_usuario_desactivado_no_puede_iniciar_sesion(client, admin):
    u = client.post("/api/v1/usuarios", headers=admin,
                    json={"nombre": "Temporal", "email": "tmp@murealestate.mx", "password": "Secreta123", "rol": "asesor"}).json()
    client.patch(f"/api/v1/usuarios/{u['id']}", headers=admin, json={"activo": False})
    r = client.post("/api/v1/auth/login", data={"username": "tmp@murealestate.mx", "password": "Secreta123"})
    assert r.status_code == 401


def test_contrasena_se_guarda_con_hash_bcrypt(client, admin):
    from app.core.database import SessionLocal
    from app.features.usuarios.infrastructure import UsuarioRepository
    with SessionLocal() as db:
        u = UsuarioRepository(db).obtener_por_email("admin@murealestate.mx")
        assert u.password_hash.startswith("$2b$") and "Secreta123" not in u.password_hash
