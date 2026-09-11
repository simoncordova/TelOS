"""Tests de la Fase 3/4 (Web Push) -- sin depender de un navegador ni de
un proveedor de push real: se monkeypatchea api.push.enviar_push (la
única función que hace una llamada de red real, vía pywebpush) y el
store de suscripciones, mismo criterio que tests/api/test_main.py con
SesionTelos."""

import pytest
from fastapi.testclient import TestClient

from api import auth as api_auth
from api import main
from api.auth import obtener_usuario_actual

_SUSCRIPCION = {"endpoint": "https://push.example.com/abc", "keys": {"p256dh": "clave-p256dh", "auth": "clave-auth"}}


@pytest.fixture(autouse=True)
def _estado_limpio():
    main._sesiones.clear()
    main._locks.clear()
    yield
    main._sesiones.clear()
    main._locks.clear()


@pytest.fixture
def store_en_memoria(monkeypatch):
    """Doble en memoria de tools/push_suscripcion_local.py -- prueba la
    capa HTTP (api/main.py) sin tocar disco."""
    registro: dict[str, list[dict]] = {}

    def _guardar(usuario_id, suscripcion):
        suscripciones = registro.setdefault(usuario_id, [])
        suscripciones[:] = [s for s in suscripciones if s.get("endpoint") != suscripcion.get("endpoint")]
        suscripciones.append(suscripcion)

    def _eliminar(usuario_id, endpoint):
        if usuario_id in registro:
            registro[usuario_id] = [s for s in registro[usuario_id] if s.get("endpoint") != endpoint]

    monkeypatch.setattr(main, "guardar_suscripcion_push", _guardar)
    monkeypatch.setattr(main, "eliminar_suscripcion_push", _eliminar)
    monkeypatch.setattr(main, "listar_suscripciones_push", lambda usuario_id: registro.get(usuario_id, []))
    monkeypatch.setattr(main, "listar_todas_las_suscripciones", lambda: dict(registro))
    return registro


@pytest.fixture
def cliente(store_en_memoria):
    main.app.dependency_overrides[obtener_usuario_actual] = lambda: "usuario-test"
    try:
        yield TestClient(main.app)
    finally:
        main.app.dependency_overrides.clear()


def test_push_config_refleja_si_hay_claves(monkeypatch, cliente):
    monkeypatch.setattr(main.push, "configurado", lambda: True)
    monkeypatch.setattr(main.push, "clave_publica", lambda: "clave-publica-fake")
    respuesta = cliente.get("/api/push/config")
    assert respuesta.json() == {"configurado": True, "clavePublica": "clave-publica-fake"}


def test_guardar_y_eliminar_suscripcion(cliente, store_en_memoria):
    r1 = cliente.post("/api/push/suscripcion", json=_SUSCRIPCION)
    assert r1.status_code == 204
    assert store_en_memoria["usuario-test"] == [_SUSCRIPCION]

    r2 = cliente.request("DELETE", "/api/push/suscripcion", json={"endpoint": _SUSCRIPCION["endpoint"]})
    assert r2.status_code == 204
    assert store_en_memoria["usuario-test"] == []


def test_enviar_prueba_cuenta_envios_exitosos(monkeypatch, cliente, store_en_memoria):
    store_en_memoria["usuario-test"] = [_SUSCRIPCION]
    monkeypatch.setattr(main.push, "enviar_push", lambda suscripcion, mensaje: None)

    respuesta = cliente.post("/api/push/enviar-prueba", json={"idioma": "es"})
    assert respuesta.status_code == 200
    assert respuesta.json() == {"enviados": 1, "invalidasEliminadas": 0}


def test_enviar_prueba_poda_suscripciones_invalidas(monkeypatch, cliente, store_en_memoria):
    store_en_memoria["usuario-test"] = [_SUSCRIPCION]

    def _fallar(suscripcion, mensaje):
        raise main.push.SuscripcionInvalida("410 Gone")

    monkeypatch.setattr(main.push, "enviar_push", _fallar)

    respuesta = cliente.post("/api/push/enviar-prueba", json={"idioma": "es"})
    assert respuesta.json() == {"enviados": 0, "invalidasEliminadas": 1}
    assert store_en_memoria["usuario-test"] == []


def test_enviar_recordatorios_requiere_secreto_valido(monkeypatch, cliente):
    monkeypatch.setattr(api_auth, "_SECRETO_SCHEDULER", "secreto-de-prueba")

    sin_header = cliente.post("/api/push/enviar-recordatorios")
    assert sin_header.status_code == 403

    header_incorrecto = cliente.post(
        "/api/push/enviar-recordatorios", headers={"X-Telos-Scheduler-Secret": "otro-valor"}
    )
    assert header_incorrecto.status_code == 403


def test_enviar_recordatorios_manda_a_todas_las_suscripciones(monkeypatch, cliente, store_en_memoria):
    monkeypatch.setattr(api_auth, "_SECRETO_SCHEDULER", "secreto-de-prueba")
    store_en_memoria["usuario-a"] = [_SUSCRIPCION]
    store_en_memoria["usuario-b"] = [_SUSCRIPCION, {**_SUSCRIPCION, "endpoint": "https://push.example.com/def"}]
    monkeypatch.setattr(main, "leer_ficha_usuario", lambda usuario_id: {"existe": False, "actual": None, "historial": []})
    monkeypatch.setattr(main.push, "enviar_push", lambda suscripcion, mensaje: None)

    respuesta = cliente.post("/api/push/enviar-recordatorios", headers={"X-Telos-Scheduler-Secret": "secreto-de-prueba"})
    assert respuesta.status_code == 200
    assert respuesta.json() == {"enviados": 3, "invalidasEliminadas": 0}
