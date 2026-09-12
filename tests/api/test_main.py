"""Primera suite de tests automatizados del repo (antes solo había
verificación manual vía scripts/chat_terminal.py y
scripts/simular_conversacion.py contra Bedrock real -- ver plan de
migración sección E). Corre sin AWS: reemplaza SesionTelos por un doble
que respeta su misma interfaz (generadores de (fase, texto, opciones)),
así se prueba la capa HTTP/SSE de verdad (framing, orden, auth, lock por
usuario) sin depender de credenciales ni de Bedrock."""

import json

import pytest
from fastapi.testclient import TestClient

from api import main
from api.auth import obtener_usuario_actual


class _SesionFalsa:
    """Doble de agents.orquestador.SesionTelos: misma interfaz pública
    (constructor, .nombre, abrir_conversacion, enviar_mensaje como
    generadores), sin tocar Bedrock ni AgentCore."""

    def __init__(self, usuario_id: str, idioma: str = "es"):
        self.usuario_id = usuario_id
        self.idioma = idioma
        self.nombre = "Simón"
        self.fase_actual = 1

    def abrir_conversacion(self):
        yield 1, "Hola, ¿qué te trae por acá?", []

    def enviar_mensaje(self, texto: str):
        yield 1, f"Recibido: {texto}", ["opción A", "opción B"]
        yield 2, "Pasamos a Sintetizador.", []

    def contar_versiones_ficha(self) -> int:
        return 0

    def ficha_actualizada(self, total_versiones_antes: int) -> dict:
        # El doble no necesita reintentar de verdad -- basta con devolver
        # lo que ya haya quedado monkeypatchado como main.leer_ficha_usuario.
        return main.leer_ficha_usuario(self.usuario_id)


_FICHA_FALSA = {
    "existe": True,
    "actual": {"fase": 2, "datos": {"proposito": "Vivir con intención"}, "motivo_version": "cierre", "fecha": "2026-01-01T00:00:00+00:00"},
    "historial": [],
}


@pytest.fixture(autouse=True)
def _sin_estado_compartido():
    """El cache de sesiones/locks de api/main.py vive a nivel de módulo
    (mismo patrón que clave_sesion en ui/app.py) -- lo limpio entre tests
    para que uno no filtre estado al siguiente."""
    main._sesiones.clear()
    main._locks.clear()
    yield
    main._sesiones.clear()
    main._locks.clear()


@pytest.fixture
def cliente(monkeypatch):
    monkeypatch.setattr(main, "SesionTelos", _SesionFalsa)
    monkeypatch.setattr(main, "leer_ficha_usuario", lambda usuario_id: _FICHA_FALSA)
    monkeypatch.setattr(main, "leer_nombre_usuario", lambda usuario_id: "Simón")
    main.app.dependency_overrides[obtener_usuario_actual] = lambda: "usuario-test"
    try:
        yield TestClient(main.app)
    finally:
        main.app.dependency_overrides.clear()


def _leer_eventos(texto_sse: str) -> list[tuple[str, dict]]:
    eventos = []
    nombre_actual = None
    for linea in texto_sse.splitlines():
        if linea.startswith("event: "):
            nombre_actual = linea.removeprefix("event: ")
        elif linea.startswith("data: "):
            eventos.append((nombre_actual, json.loads(linea.removeprefix("data: "))))
    return eventos


def test_salud(cliente):
    assert cliente.get("/api/salud").json() == {"estado": "ok"}


def test_abrir_sesion_transmite_mensaje_y_ficha_en_orden(cliente):
    respuesta = cliente.post("/api/sesion/abrir", json={"idioma": "es"})
    assert respuesta.status_code == 200

    eventos = _leer_eventos(respuesta.text)
    nombres = [nombre for nombre, _ in eventos]
    assert nombres == ["mensaje", "ficha", "done"]
    assert eventos[0][1] == {"fase": 1, "texto": "Hola, ¿qué te trae por acá?", "opciones": []}
    assert eventos[1][1]["racha"] == 0
    assert eventos[1][1]["nombre"] == "Simón"


def test_enviar_mensaje_preserva_orden_de_cascada_de_fase(cliente):
    respuesta = cliente.post("/api/sesion/mensaje", json={"texto": "hola", "idioma": "es"})
    eventos = _leer_eventos(respuesta.text)
    mensajes = [datos for nombre, datos in eventos if nombre == "mensaje"]
    assert [m["fase"] for m in mensajes] == [1, 2]


def test_ficha_requiere_autenticacion_sin_override():
    main.app.dependency_overrides.clear()
    with TestClient(main.app) as cliente_sin_auth:
        respuesta = cliente_sin_auth.get("/api/ficha")
    assert respuesta.status_code == 401


def test_ficha_devuelve_snapshot(cliente):
    respuesta = cliente.get("/api/ficha")
    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["existe"] is True
    assert cuerpo["nombre"] == "Simón"
    assert "Vivir con intención" in cuerpo["vista_resumen"]


def test_auth_me_devuelve_usuario(cliente):
    respuesta = cliente.get("/api/auth/me")
    assert respuesta.status_code == 200
    assert respuesta.json() == {"usuarioId": "usuario-test", "nombre": "Simón"}


def test_auth_me_401_sin_sesion():
    main.app.dependency_overrides.clear()
    with TestClient(main.app) as cliente_sin_auth:
        respuesta = cliente_sin_auth.get("/api/auth/me")
    assert respuesta.status_code == 401
