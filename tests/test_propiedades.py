from decimal import Decimal

import pytest

from app.core.exceptions import ReglaDeNegocio
from app.features.propiedades.domain import EstadoPublicacion as E
from app.features.propiedades.domain import validar_transicion, validar_valor_minimo

CAMPOS_INTERNOS = {"precio_real", "valor_minimo", "comision_pct", "direccion_exacta", "notas", "propietario"}


def nueva(client, headers, **extra):
    datos = {"titulo": "Casa en Residencial Cumbres", "operacion": "venta", "tipo": "casa", "zona_id": 4,
             "recamaras": 3, "banos": 2, "precio_publico": "4800000.00", "amenidad_ids": [1, 3]} | extra
    r = client.post("/api/v1/propiedades", headers=headers, json=datos)
    assert r.status_code == 201, r.text
    return r.json()


def publicar(client, headers, pid):
    client.patch(f"/api/v1/propiedades/{pid}/publicacion", headers=headers, json={"estado": "en_revision"})
    r = client.patch(f"/api/v1/propiedades/{pid}/publicacion", headers=headers, json={"estado": "publicada"})
    assert r.status_code == 200, r.text


# ---- Dominio (pruebas unitarias, sin base de datos) ----
def test_valor_minimo_mayor_que_precio_real_es_rechazado():
    with pytest.raises(ReglaDeNegocio):
        validar_valor_minimo(Decimal("100"), Decimal("120"))


def test_valor_minimo_igual_al_precio_real_es_valido():
    validar_valor_minimo(Decimal("100"), Decimal("100"))


@pytest.mark.parametrize("actual,nuevo", [(E.BORRADOR, E.PUBLICADA), (E.RECHAZADA, E.PUBLICADA), (E.PUBLICADA, E.BORRADOR)])
def test_transiciones_no_permitidas(actual, nuevo):
    with pytest.raises(ReglaDeNegocio):
        validar_transicion(actual, nuevo)


# ---- Integración (API + PostgreSQL) ----
def test_crear_propiedad_asigna_clave_y_estado_borrador(client, asesor):
    p = nueva(client, asesor)
    assert p["clave"] == "MU-00001"
    assert p["estado_publicacion"] == "borrador"
    assert p["ubicacion"]["ciudad"] == "Cancún"


def test_borrador_no_aparece_en_busqueda_publica(client, admin):
    nueva(client, admin)
    assert client.get("/api/v1/publico/propiedades").json()["total"] == 0


def test_busqueda_publica_filtra_y_no_expone_datos_internos(client, admin):
    p = nueva(client, admin)
    client.put(f"/api/v1/propiedades/{p['id']}/interno", headers=admin,
               json={"precio_real": "4500000", "valor_minimo": "4300000", "comision_pct": "5",
                     "direccion_exacta": "Calle 1 #23", "propietario": {"nombre": "Dueño Uno"}})
    publicar(client, admin, p["id"])
    nueva(client, admin, titulo="Departamento en renta", operacion="renta", tipo="departamento", recamaras=1)
    r = client.get("/api/v1/publico/propiedades", params={"operacion": "venta", "ciudad_id": 1, "recamaras_min": 3,
                                                          "precio_max": 5000000})
    cuerpo = r.json()
    assert cuerpo["total"] == 1
    elemento = cuerpo["elementos"][0]
    assert CAMPOS_INTERNOS.isdisjoint(elemento)
    assert "4300000" not in r.text and "Dueño Uno" not in r.text


def test_asesor_no_puede_ver_datos_internos(client, admin, asesor):
    p = nueva(client, admin)
    client.put(f"/api/v1/propiedades/{p['id']}/interno", headers=admin, json={"precio_real": "4500000"})
    assert client.get(f"/api/v1/propiedades/{p['id']}/interno", headers=asesor).status_code == 403
    assert client.get(f"/api/v1/propiedades/{p['id']}/interno", headers=admin).status_code == 200


def test_valor_minimo_mayor_al_precio_real_responde_422(client, admin):
    p = nueva(client, admin)
    r = client.put(f"/api/v1/propiedades/{p['id']}/interno", headers=admin,
                   json={"precio_real": "4000000", "valor_minimo": "4100000"})
    assert r.status_code == 422


def test_cambio_de_precio_y_datos_internos_queda_en_auditoria(client, admin):
    p = nueva(client, admin)
    client.patch(f"/api/v1/propiedades/{p['id']}", headers=admin, json={"precio_publico": "4700000.00"})
    client.put(f"/api/v1/propiedades/{p['id']}/interno", headers=admin, json={"valor_minimo": "4200000"})
    registros = client.get("/api/v1/auditoria", headers=admin, params={"entidad_id": p["id"]}).json()
    cambios = {(r["entidad"], r["campo"]): r for r in registros}
    assert cambios[("propiedades", "precio_publico")]["valor_anterior"] == "4800000.00"
    assert cambios[("propiedades", "precio_publico")]["valor_nuevo"] == "4700000.00"
    assert ("datos_internos", "valor_minimo") in cambios


def test_publicar_sin_pasar_por_revision_responde_422(client, admin):
    p = nueva(client, admin)
    r = client.patch(f"/api/v1/propiedades/{p['id']}/publicacion", headers=admin, json={"estado": "publicada"})
    assert r.status_code == 422


def test_rechazo_exige_motivo(client, admin):
    p = nueva(client, admin)
    client.patch(f"/api/v1/propiedades/{p['id']}/publicacion", headers=admin, json={"estado": "en_revision"})
    r = client.patch(f"/api/v1/propiedades/{p['id']}/publicacion", headers=admin, json={"estado": "rechazada"})
    assert r.status_code == 422


def test_asesor_no_puede_publicar(client, asesor):
    p = nueva(client, asesor)
    r = client.patch(f"/api/v1/propiedades/{p['id']}/publicacion", headers=asesor, json={"estado": "en_revision"})
    assert r.status_code == 403


def test_desactivar_oculta_la_propiedad_publicada(client, admin):
    p = nueva(client, admin)
    publicar(client, admin, p["id"])
    assert client.delete(f"/api/v1/propiedades/{p['id']}", headers=admin).status_code == 204
    assert client.get(f"/api/v1/publico/propiedades/{p['id']}").status_code == 404
    detalle = client.get(f"/api/v1/propiedades/{p['id']}", headers=admin).json()
    assert detalle["activo"] is False and detalle["estado_publicacion"] == "oculta"


def test_bodega_es_un_tipo_de_inmueble(client, admin):
    p = nueva(client, admin, titulo="Bodega industrial en Cancún", tipo="bodega", recamaras=None, banos=None)
    publicar(client, admin, p["id"])
    r = client.get("/api/v1/publico/propiedades", params={"tipo": "bodega"}).json()
    assert r["total"] == 1 and r["elementos"][0]["tipo"] == "bodega"
