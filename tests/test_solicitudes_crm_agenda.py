from datetime import UTC, datetime, timedelta

from app.features.agenda.domain import se_empalman
from app.features.prospectos.domain import EtapaProspecto as P
from app.features.prospectos.domain import validar_transicion as transicion_prospecto
from app.core.exceptions import ReglaDeNegocio
import pytest

from tests.test_propiedades import nueva, publicar

API = "/api/v1"


def futura(horas: int) -> str:
    return (datetime.now(UTC) + timedelta(days=2, hours=horas)).replace(microsecond=0).isoformat()


def propiedad_publicada(client, admin) -> int:
    p = nueva(client, admin)
    publicar(client, admin, p["id"])
    return p["id"]


def id_asesor(client, admin) -> int:
    return next(u["id"] for u in client.get(f"{API}/usuarios", headers=admin).json() if u["rol"] == "asesor")


# ---- Dominio (unitarias) ----
def test_visitas_de_una_hora_se_empalman_si_se_cruzan():
    base = datetime(2026, 11, 10, 10, tzinfo=UTC)
    assert se_empalman(base, base + timedelta(minutes=30))
    assert not se_empalman(base, base + timedelta(minutes=60))


def test_prospecto_cerrado_no_cambia_de_etapa():
    with pytest.raises(ReglaDeNegocio):
        transicion_prospecto(P.CERRADO, P.CONTACTADO)


# ---- Solicitudes y avisos ----
def test_solicitud_publica_genera_aviso_interno(client, admin):
    pid = propiedad_publicada(client, admin)
    r = client.post(f"{API}/publico/solicitudes", json={"tipo": "visita", "propiedad_id": pid, "nombre": "Ana Pérez",
                                                         "telefono": "9981234567"})
    assert r.status_code == 201 and r.json()["estado"] == "nueva"
    avisos = client.get(f"{API}/avisos", headers=admin, params={"solo_no_leidos": True}).json()
    assert any("Nueva solicitud de visita" in a["titulo"] for a in avisos)


def test_solicitud_sobre_propiedad_no_publicada_responde_404(client, admin):
    p = nueva(client, admin)
    r = client.post(f"{API}/publico/solicitudes", json={"tipo": "contacto", "propiedad_id": p["id"],
                                                         "nombre": "Ana Pérez", "email": "ana@correo.mx"})
    assert r.status_code == 404


def test_solicitud_sin_telefono_ni_correo_responde_422(client, admin):
    pid = propiedad_publicada(client, admin)
    r = client.post(f"{API}/publico/solicitudes", json={"tipo": "contacto", "propiedad_id": pid, "nombre": "Ana Pérez"})
    assert r.status_code == 422


def test_oferta_de_particular_ingresa_en_revision_y_sin_datos_publicos(client, admin):
    r = client.post(f"{API}/publico/propiedades/ofrecer", json={
        "nombre": "Dueño Uno", "telefono": "9980000000", "titulo": "Casa en Huayacán", "operacion": "venta",
        "tipo": "casa", "zona_id": 6, "direccion": "Calle 10 #5, Huayacán", "precio_pedido": "3500000"})
    assert r.status_code == 201, r.text
    pid = r.json()["propiedad_id"]
    detalle = client.get(f"{API}/propiedades/{pid}", headers=admin).json()
    assert detalle["origen"] == "particular" and detalle["estado_publicacion"] == "en_revision"
    assert client.get(f"{API}/publico/propiedades/{pid}").status_code == 404
    internos = client.get(f"{API}/propiedades/{pid}/interno", headers=admin).json()
    assert internos["precio_real"] == "3500000.00" and internos["propietario"]["nombre"] == "Dueño Uno"


def test_asignar_atender_y_crear_prospecto(client, admin, asesor):
    pid = propiedad_publicada(client, admin)
    s = client.post(f"{API}/publico/solicitudes", json={"tipo": "contacto", "propiedad_id": pid, "nombre": "Luis Mora",
                                                         "email": "luis@correo.mx"}).json()
    aid = id_asesor(client, admin)
    r = client.patch(f"{API}/solicitudes/{s['id']}/asignacion", headers=admin, json={"asesor_id": aid})
    assert r.json()["estado"] == "asignada"
    assert any(f"#{s['id']}" in a["titulo"] for a in client.get(f"{API}/avisos", headers=asesor).json())
    r = client.patch(f"{API}/solicitudes/{s['id']}/atencion", headers=asesor, json={"crear_prospecto": True})
    assert r.json()["estado"] == "atendida" and r.json()["prospecto_id"]
    prospecto = client.get(f"{API}/prospectos/{r.json()['prospecto_id']}", headers=asesor).json()
    assert prospecto["propiedad_ids"] == [pid] and prospecto["asesor_id"] == aid


def test_descartar_exige_motivo_y_no_se_puede_reabrir(client, admin):
    pid = propiedad_publicada(client, admin)
    s = client.post(f"{API}/publico/solicitudes", json={"tipo": "contacto", "propiedad_id": pid, "nombre": "Luis Mora",
                                                         "email": "luis@correo.mx"}).json()
    assert client.patch(f"{API}/solicitudes/{s['id']}/descarte", headers=admin, json={"motivo": ""}).status_code == 422
    r = client.patch(f"{API}/solicitudes/{s['id']}/descarte", headers=admin, json={"motivo": "Datos de contacto falsos"})
    assert r.json()["estado"] == "descartada"
    assert client.patch(f"{API}/solicitudes/{s['id']}/atencion", headers=admin, json={}).status_code == 422


# ---- Prospectos (CRM) ----
def test_crud_y_busqueda_de_prospectos(client, asesor):
    p = client.post(f"{API}/prospectos", headers=asesor, json={"nombre": "Carla Ruiz", "telefono": "9987776655",
                                                                "presupuesto_min": "2000000", "presupuesto_max": "3000000"})
    assert p.status_code == 201
    pid = p.json()["id"]
    assert client.patch(f"{API}/prospectos/{pid}", headers=asesor, json={"email": "carla@correo.mx"}).status_code == 200
    assert [x["id"] for x in client.get(f"{API}/prospectos", headers=asesor, params={"q": "carla"}).json()] == [pid]
    assert client.delete(f"{API}/prospectos/{pid}", headers=asesor).status_code == 204
    assert client.get(f"{API}/prospectos/{pid}", headers=asesor).status_code == 404


def test_presupuesto_minimo_mayor_al_maximo_responde_422(client, asesor):
    r = client.post(f"{API}/prospectos", headers=asesor, json={"nombre": "Carla Ruiz", "presupuesto_min": "5",
                                                                "presupuesto_max": "1"})
    assert r.status_code == 422


def test_seguimiento_mueve_a_contactado_y_cierre_exige_comentario(client, asesor):
    pid = client.post(f"{API}/prospectos", headers=asesor, json={"nombre": "Carla Ruiz"}).json()["id"]
    client.post(f"{API}/prospectos/{pid}/seguimientos", headers=asesor, json={"tipo": "llamada",
                                                                              "descripcion": "Primera llamada"})
    assert client.get(f"{API}/prospectos/{pid}", headers=asesor).json()["etapa"] == "contactado"
    for etapa in ("en_visita", "en_oferta"):
        assert client.patch(f"{API}/prospectos/{pid}/etapa", headers=asesor, json={"etapa": etapa}).status_code == 200
    assert client.patch(f"{API}/prospectos/{pid}/etapa", headers=asesor, json={"etapa": "cerrado"}).status_code == 422
    r = client.patch(f"{API}/prospectos/{pid}/etapa", headers=asesor, json={"etapa": "cerrado",
                                                                            "comentario": "Firmó promesa de compraventa"})
    assert r.json()["etapa"] == "cerrado"
    historial = client.get(f"{API}/prospectos/{pid}/seguimientos", headers=asesor).json()
    assert len(historial) == 4


# ---- Agenda de visitas ----
def preparar_cita(client, admin, asesor, horas=0):
    pid = propiedad_publicada(client, admin) if horas == 0 else client.get(
        f"{API}/publico/propiedades").json()["elementos"][0]["id"]
    prospecto = client.post(f"{API}/prospectos", headers=asesor, json={"nombre": f"Cliente {horas}"}).json()
    return {"propiedad_id": pid, "prospecto_id": prospecto["id"], "asesor_id": id_asesor(client, admin),
            "fecha_hora": futura(horas)}


def test_agendar_mueve_prospecto_a_visita_y_rechaza_empalme(client, admin, asesor):
    datos = preparar_cita(client, admin, asesor)
    r = client.post(f"{API}/citas", headers=asesor, json=datos)
    assert r.status_code == 201, r.text
    assert client.get(f"{API}/prospectos/{datos['prospecto_id']}", headers=asesor).json()["etapa"] == "en_visita"
    otra = preparar_cita(client, admin, asesor, horas=1) | {"fecha_hora": (datetime.fromisoformat(datos["fecha_hora"]) + timedelta(minutes=30)).isoformat()}
    assert client.post(f"{API}/citas", headers=asesor, json=otra).status_code == 409


def test_cita_en_el_pasado_responde_422(client, admin, asesor):
    datos = preparar_cita(client, admin, asesor) | {"fecha_hora": "2020-01-01T10:00:00-05:00"}
    assert client.post(f"{API}/citas", headers=asesor, json=datos).status_code == 422


def test_confirmar_reprogramar_y_cancelar(client, admin, asesor):
    cid = client.post(f"{API}/citas", headers=asesor, json=preparar_cita(client, admin, asesor)).json()["id"]
    assert client.patch(f"{API}/citas/{cid}/confirmacion", headers=asesor).json()["estado"] == "confirmada"
    r = client.patch(f"{API}/citas/{cid}/reprogramacion", headers=asesor, json={"fecha_hora": futura(5),
                                                                                "motivo": "Pidió otro horario"})
    assert r.json()["estado"] == "reprogramada"
    r = client.patch(f"{API}/citas/{cid}/cancelacion", headers=asesor, json={"motivo": "Ya compró otra casa"})
    assert r.json()["estado"] == "cancelada"
    assert client.patch(f"{API}/citas/{cid}/confirmacion", headers=asesor).status_code == 422


# ---- Dashboard y reportes ----
def test_indicadores_y_reporte_csv(client, admin, asesor):
    pid = propiedad_publicada(client, admin)
    client.post(f"{API}/publico/solicitudes", json={"tipo": "contacto", "propiedad_id": pid, "nombre": "Ana Pérez",
                                                     "telefono": "9981234567"})
    ind = client.get(f"{API}/dashboard/indicadores", headers=asesor).json()
    assert ind["propiedades"]["por_estado_publicacion"]["publicada"] == 1
    assert ind["solicitudes"]["nueva"] == 1
    hoy = datetime.now(UTC)
    params = {"desde": (hoy - timedelta(days=1)).isoformat(), "hasta": (hoy + timedelta(days=1)).isoformat()}
    filas = client.get(f"{API}/dashboard/reporte", headers=asesor, params=params).json()
    assert {"indicador": "Solicitudes de contacto recibidas", "valor": 1} in filas
    csv = client.get(f"{API}/dashboard/reporte", headers=asesor, params=params | {"formato": "csv"})
    assert csv.headers["content-type"].startswith("text/csv") and "indicador,valor" in csv.text
