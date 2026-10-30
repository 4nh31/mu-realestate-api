import json
import re

from app.core.email import BANDEJA_DESARROLLO
from tests.conftest import _token
from tests.test_propiedades import nueva, publicar

API = "/api/v1"
PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64
JPG = b"\xff\xd8\xff\xe0" + b"\x00" * 64


def ultimo_codigo(email: str) -> str:
    correo = next(c for c in reversed(BANDEJA_DESARROLLO) if c.para == email)
    return re.search(r"\b(\d{6})\b", correo.cuerpo).group(1)


def crear_cuenta(client, email="cliente@correo.mx", verificar=True, publicar_=False) -> dict[str, str]:
    r = client.post(f"{API}/auth/registro", json={"nombre": "Cliente Uno", "email": email, "telefono": "9981112233",
                                                  "password": "Secreta123", "quiere_publicar": publicar_})
    assert r.status_code == 201, r.text
    if verificar:
        r = client.post(f"{API}/auth/verificar-correo", json={"email": email, "codigo": ultimo_codigo(email)})
        assert r.status_code == 200, r.text
    return _token(client, email)


def propiedad_publicada(client, admin, **extra) -> int:
    p = nueva(client, admin, **extra)
    publicar(client, admin, p["id"])
    return p["id"]


# ---- Registro y verificación ----
def test_registro_verificacion_y_perfil(client):
    headers = crear_cuenta(client, verificar=False)
    perfil = client.get(f"{API}/auth/me", headers=headers).json()
    assert perfil["rol"] == "cliente" and perfil["permisos"] == ["cuenta:usar"] and not perfil["email_verificado"]
    r = client.post(f"{API}/auth/verificar-correo", json={"email": "cliente@correo.mx", "codigo": "000000"})
    assert r.status_code == 422
    r = client.post(f"{API}/auth/verificar-correo", json={"email": "cliente@correo.mx", "codigo": "000000"})
    assert "3 intentos" in r.json()["detail"]  # el intento fallido anterior quedó guardado
    r = client.post(f"{API}/auth/verificar-correo",
                    json={"email": "cliente@correo.mx", "codigo": ultimo_codigo("cliente@correo.mx")})
    assert r.status_code == 200
    assert client.get(f"{API}/auth/me", headers=headers).json()["email_verificado"]


def test_registro_con_correo_existente_no_lo_revela_ni_cambia_la_contrasena(client):
    crear_cuenta(client)
    r = client.post(f"{API}/auth/registro", json={"nombre": "Intruso", "email": "cliente@correo.mx",
                                                  "password": "OtraClave99"})
    assert r.status_code == 201
    assert client.post(f"{API}/auth/login", data={"username": "cliente@correo.mx",
                                                   "password": "OtraClave99"}).status_code == 401


def test_cliente_no_entra_al_panel_y_el_personal_no_usa_la_cuenta(client, admin):
    cliente = crear_cuenta(client)
    assert client.get(f"{API}/propiedades", headers=cliente).status_code == 403
    assert client.get(f"{API}/cuenta/favoritos", headers=admin).status_code == 403
    permisos_admin = client.get(f"{API}/auth/me", headers=admin).json()["permisos"]
    assert "expedientes:validar" in permisos_admin and "cuenta:usar" not in permisos_admin


def test_restablecer_contrasena(client):
    crear_cuenta(client)
    assert client.post(f"{API}/auth/restablecer-password", json={"email": "cliente@correo.mx"}).status_code == 202
    assert client.post(f"{API}/auth/restablecer-password", json={"email": "nadie@correo.mx"}).status_code == 202
    r = client.post(f"{API}/auth/restablecer-password/confirmar", json={
        "email": "cliente@correo.mx", "codigo": ultimo_codigo("cliente@correo.mx"), "password": "NuevaClave1"})
    assert r.status_code == 200, r.text
    _token(client, "cliente@correo.mx", "NuevaClave1")


# ---- Favoritos ----
def test_favoritos_guardar_sincronizar_y_quitar(client, admin):
    cliente = crear_cuenta(client)
    a, b = propiedad_publicada(client, admin), propiedad_publicada(client, admin)
    borrador = nueva(client, admin)["id"]
    assert client.put(f"{API}/cuenta/favoritos/{a}", headers=cliente).status_code == 204
    assert client.put(f"{API}/cuenta/favoritos/{a}", headers=cliente).status_code == 204  # idempotente
    assert client.put(f"{API}/cuenta/favoritos/{borrador}", headers=cliente).status_code == 404
    r = client.post(f"{API}/cuenta/favoritos/sincronizar", headers=cliente, json={"propiedad_ids": [b, borrador]})
    assert sorted(p["id"] for p in r.json()) == sorted([a, b])
    assert client.delete(f"{API}/cuenta/favoritos/{a}", headers=cliente).status_code == 204
    assert [p["id"] for p in client.get(f"{API}/cuenta/favoritos", headers=cliente).json()] == [b]


def test_bajada_de_precio_avisa_a_quien_la_guardo(client, admin):
    cliente = crear_cuenta(client)
    pid = propiedad_publicada(client, admin)
    client.put(f"{API}/cuenta/favoritos/{pid}", headers=cliente)
    client.patch(f"{API}/propiedades/{pid}", headers=admin, json={"precio_publico": "4500000.00"})
    avisos = client.get(f"{API}/avisos", headers=cliente).json()
    assert avisos[0]["tipo"] == "favorito" and avisos[0]["enlace"] == f"/propiedad/{pid}"
    assert any("Bajó de precio" in c.asunto for c in BANDEJA_DESARROLLO)


# ---- Propiedades ofrecidas desde la cuenta y moderación ----
def ofrecer(client, headers, imagenes=(("imagenes", ("frente.png", PNG, "image/png")),), **extra):
    datos = {"titulo": "Casa en Huayacán", "operacion": "venta", "tipo": "casa", "zona_id": 6,
             "direccion": "Calle 10 #5, Huayacán", "precio_pedido": "3500000", "estacionamientos": 2,
             "antiguedad_anios": 5, "amenidad_ids": [1], "bien_ids": [1, 2]} | extra
    return client.post(f"{API}/cuenta/propiedades", headers=headers, data={"datos": json.dumps(datos)},
                       files=list(imagenes))


def test_ofrecer_requiere_correo_verificado(client):
    sin_verificar = crear_cuenta(client, verificar=False, publicar_=True)
    assert ofrecer(client, sin_verificar).status_code == 403


def test_ofrecer_con_fotos_y_ver_el_rechazo_con_motivo(client, admin):
    dueno = crear_cuenta(client, "dueno@correo.mx", publicar_=True)
    r = ofrecer(client, dueno)
    assert r.status_code == 201, r.text
    oferta = r.json()
    assert oferta["estado_publicacion"] == "en_revision" and oferta["portada"].startswith("http")

    cola = client.get(f"{API}/propiedades", headers=admin, params={"origen": "particular", "estado": "en_revision"})
    detalle = cola.json()["elementos"][0]
    assert detalle["id"] == oferta["id"] and detalle["bienes"] == ["Estufa", "Refrigerador"]
    assert detalle["antiguedad_anios"] == 5 and len(detalle["medios"]) == 1
    assert client.get(f"{API}/propiedades/{oferta['id']}/interno", headers=admin).json()["propietario"]["email"] == \
        "dueno@correo.mx"

    r = client.patch(f"{API}/propiedades/{oferta['id']}/publicacion", headers=admin,
                     json={"estado": "rechazada", "motivo": "Faltan fotos del interior"})
    assert r.status_code == 200 and r.json()["motivo_rechazo"] == "Faltan fotos del interior"
    assert r.json()["revisado_en"] is not None

    mias = client.get(f"{API}/cuenta/propiedades", headers=dueno).json()
    assert mias[0]["estado_publicacion"] == "rechazada" and mias[0]["motivo_rechazo"] == "Faltan fotos del interior"
    aviso = client.get(f"{API}/avisos", headers=dueno).json()[0]
    assert aviso["tipo"] == "publicacion" and "Faltan fotos" in aviso["mensaje"]


def test_ofrecer_rechaza_archivos_que_no_son_imagen(client):
    dueno = crear_cuenta(client, "dueno@correo.mx", publicar_=True)
    r = ofrecer(client, dueno, imagenes=[("imagenes", ("foto.png", b"no soy una imagen", "image/png"))])
    assert r.status_code == 422 and "no es un tipo permitido" in r.json()["detail"]
    assert client.get(f"{API}/cuenta/propiedades", headers=dueno).json() == []


def test_ofrecer_con_datos_invalidos_responde_422(client):
    dueno = crear_cuenta(client, "dueno@correo.mx", publicar_=True)
    assert ofrecer(client, dueno, precio_pedido="-1").status_code == 422


def test_publicar_registra_fecha_y_rechazar_sin_motivo_falla(client, admin):
    p = nueva(client, admin)
    client.patch(f"{API}/propiedades/{p['id']}/publicacion", headers=admin, json={"estado": "en_revision"})
    r = client.patch(f"{API}/propiedades/{p['id']}/publicacion", headers=admin, json={"estado": "rechazada",
                                                                                     "motivo": "   "})
    assert r.status_code == 422
    r = client.patch(f"{API}/propiedades/{p['id']}/publicacion", headers=admin, json={"estado": "publicada"})
    assert r.json()["publicada_en"] is not None and r.json()["revisado_por"] is not None


# ---- Medios ----
def test_subir_ordenar_y_eliminar_fotos(client, admin):
    pid = nueva(client, admin)["id"]
    r = client.post(f"{API}/propiedades/{pid}/medios", headers=admin,
                    files=[("archivos", ("a.png", PNG, "image/png")), ("archivos", ("b.jpg", JPG, "image/jpeg"))])
    assert r.status_code == 201, r.text
    a, b = r.json()
    assert a["es_portada"] and not b["es_portada"]
    assert client.get(a["url"].removeprefix("http://localhost:8000")).content == PNG  # la API sirve el archivo

    assert client.patch(f"{API}/medios/{b['id']}", headers=admin, json={"es_portada": True}).json()["es_portada"]
    assert client.delete(f"{API}/medios/{b['id']}", headers=admin).status_code == 204
    medios = client.get(f"{API}/propiedades/{pid}", headers=admin).json()["medios"]
    assert [m["id"] for m in medios] == [a["id"]] and medios[0]["es_portada"]


def test_maximo_diez_fotos_por_propiedad(client, admin):
    pid = nueva(client, admin)["id"]
    archivos = [("archivos", (f"{i}.png", PNG, "image/png")) for i in range(11)]
    assert client.post(f"{API}/propiedades/{pid}/medios", headers=admin, files=archivos).status_code == 422


# ---- Búsqueda, catálogo y avisos ----
def test_busqueda_por_texto_y_destacadas(client, admin):
    propiedad_publicada(client, admin, titulo="Penthouse frente al mar", destacada=True)
    propiedad_publicada(client, admin)
    r = client.get(f"{API}/publico/propiedades", params={"q": "penthouse"}).json()
    assert r["total"] == 1 and r["elementos"][0]["destacada"]
    assert client.get(f"{API}/publico/propiedades", params={"q": "Cumbres"}).json()["total"] == 2  # por zona
    assert client.get(f"{API}/publico/propiedades", params={"destacada": True}).json()["total"] == 1


def test_catalogo_de_bienes_agrupado(client):
    grupos = client.get(f"{API}/publico/catalogos/bienes").json()
    assert grupos[0]["categoria"] and sum(len(g["bienes"]) for g in grupos) == 25


def test_avisos_manuales_y_marcar_todos_leidos(client, admin, asesor):
    r = client.post(f"{API}/avisos", headers=admin, json={"titulo": "Junta el lunes", "rol": "asesor"})
    assert r.status_code == 201 and r.json()["actualizados"] == 1
    assert client.post(f"{API}/avisos", headers=asesor, json={"titulo": "Hola", "rol": "asesor"}).status_code == 403
    aviso = client.get(f"{API}/avisos", headers=asesor).json()[0]
    assert aviso["tipo"] == "interno" and aviso["autor_id"] is not None
    assert client.patch(f"{API}/avisos/leidos", headers=asesor).json()["actualizados"] == 1
    assert client.get(f"{API}/avisos", headers=asesor, params={"solo_no_leidos": True}).json() == []


# ---- Apoyos para el panel ----
def test_personal_notas_y_bitacora_con_nombres(client, admin, asesor):
    personal = client.get(f"{API}/usuarios/personal", headers=asesor).json()
    assert {p["rol"] for p in personal} == {"administrador", "asesor"}
    s = client.post(f"{API}/publico/solicitudes", json={"tipo": "contacto", "nombre": "Ana Pérez",
                                                         "email": "ana@correo.mx"}).json()
    r = client.patch(f"{API}/solicitudes/{s['id']}/notas", headers=asesor, json={"notas": "Llamar el lunes"})
    assert r.status_code == 200 and r.json()["notas"] == "Llamar el lunes"
    nueva(client, admin, titulo="Casa para la bitácora")
    registro = client.get(f"{API}/auditoria", headers=admin, params={"entidad": "propiedades"}).json()[0]
    assert registro["usuario_nombre"] == "admin" and registro["entidad_titulo"] == "Casa para la bitácora"
    assert registro["entidad_zona"] == "Residencial Cumbres"
