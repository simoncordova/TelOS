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

    @property
    def candidatos_pendientes(self) -> list[dict]:
        # Ver SesionTelos.candidatos_pendientes -- vacío por default,
        # ningún test de este archivo ejercita candidatos estructurados
        # de Fase 2 todavía.
        return []

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

    def confirmar_seleccion(self, nodo_id: str, detalle_libre: str | None = None) -> dict:
        if nodo_id == "id_desconocido":
            raise ValueError("nodo_id desconocido en la taxonomía de Fase 1: 'id_desconocido'")
        return {"cobertura": {"L": 1, "G": 1}, "puede_cerrar": False, "mostrar_valores": False}

    def cerrar_fase_1_manual(self) -> dict:
        return {"cerrado": True, "mensaje_cierre": "Con esto ya tengo material real."}

    def confirmar_seleccion_sistema(self, pregunta_id: str, nodo_id: str, detalle_libre: str | None = None) -> dict:
        return {"respuestas": {pregunta_id: {"nodo_id": nodo_id}}, "cerrado": False, "mensaje_cierre": None}

    def confirmar_seleccion_validacion(self, area_id: str, detalle_libre: str | None = None) -> dict:
        if area_id == "trabajo_carrera":
            return {"etapa": "friccion_futura", "mensaje_apertura_refinado": None}
        return {"etapa": "refinando", "mensaje_apertura_refinado": "¿Sentís que 'crear con propósito' te representa?"}


_FICHA_FALSA = {
    "existe": True,
    "actual": {"fase": 2, "datos": {"proposito": "Vivir con intención"}, "motivo_version": "cierre", "fecha": "2026-01-01T00:00:00+00:00"},
    "historial": [],
}


@pytest.fixture(autouse=True)
def _sin_estado_compartido():
    """El cache de sesiones/locks de api/main.py vive a nivel de módulo --
    lo limpio entre tests para que uno no filtre estado al siguiente."""
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
    assert eventos[0][1] == {"fase": 1, "texto": "Hola, ¿qué te trae por acá?", "opciones": [], "candidatos": []}
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


def test_obtener_categorias_fase_1(cliente):
    respuesta = cliente.get("/api/categorias/1?idioma=es")
    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["dimensiones"] == ["L", "G", "V", "N"]
    assert len(cuerpo["verbos"]) > 0
    assert len(cuerpo["dominios"]) > 0
    assert len(cuerpo["hojas"]) > 0
    assert len(cuerpo["valoresDisponibles"]) >= cuerpo["maxValores"]


def test_obtener_categorias_fase_4(cliente):
    respuesta = cliente.get("/api/categorias/4?idioma=es")
    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["preguntas"] == ["accion", "cuando_donde", "metrica", "obstaculo"]
    assert len(cuerpo["categorias"]["accion"]) > 0


def test_obtener_categorias_fase_3(cliente):
    respuesta = cliente.get("/api/categorias/3?idioma=es")
    assert respuesta.status_code == 200
    areas = respuesta.json()["areas"]
    assert len(areas) > 0
    assert {"id", "label"} <= areas[0].keys()


def test_obtener_categorias_fase_sin_taxonomia_404(cliente):
    respuesta = cliente.get("/api/categorias/2")
    assert respuesta.status_code == 404


def test_confirmar_seleccion_devuelve_cobertura(cliente):
    respuesta = cliente.post("/api/seleccion/confirmar", json={"nodo_id": "crear/tech/IA", "idioma": "es"})
    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["cobertura"] == {"L": 1, "G": 1}
    assert cuerpo["puede_cerrar"] is False
    assert cuerpo["cerrado"] is False
    assert cuerpo["fase_actual"] == 1


def test_cerrar_fase1_manual(cliente):
    respuesta = cliente.post("/api/seleccion/cerrar-fase1", json={"idioma": "es"})
    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["cerrado"] is True
    assert cuerpo["mensaje_cierre"]


def test_confirmar_seleccion_nodo_desconocido_400(cliente):
    respuesta = cliente.post("/api/seleccion/confirmar", json={"nodo_id": "id_desconocido", "idioma": "es"})
    assert respuesta.status_code == 400


def test_confirmar_seleccion_fase_4_devuelve_respuestas(cliente):
    respuesta = cliente.post(
        "/api/seleccion/confirmar",
        json={"fase": 4, "pregunta_id": "accion", "nodo_id": "ejercicio_cardio", "idioma": "es"},
    )
    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["respuestas"] == {"accion": {"nodo_id": "ejercicio_cardio"}}
    assert cuerpo["cobertura"] is None


def test_confirmar_seleccion_fase_4_sin_pregunta_id_400(cliente):
    respuesta = cliente.post("/api/seleccion/confirmar", json={"fase": 4, "nodo_id": "ejercicio_cardio"})
    assert respuesta.status_code == 400


def test_confirmar_seleccion_fase_3_primera_etapa_no_abre_refinado(cliente):
    respuesta = cliente.post(
        "/api/seleccion/confirmar", json={"fase": 3, "nodo_id": "trabajo_carrera", "idioma": "es"}
    )
    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["etapa"] == "friccion_futura"
    assert cuerpo["mensaje_apertura_refinado"] is None
    assert cuerpo["cerrado"] is False


def test_confirmar_seleccion_fase_3_segunda_etapa_abre_refinado(cliente):
    respuesta = cliente.post(
        "/api/seleccion/confirmar", json={"fase": 3, "nodo_id": "hobby_proyecto_personal", "idioma": "es"}
    )
    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["etapa"] == "refinando"
    assert cuerpo["mensaje_apertura_refinado"]


def test_confirmar_seleccion_requiere_autenticacion_sin_override():
    main.app.dependency_overrides.clear()
    with TestClient(main.app) as cliente_sin_auth:
        respuesta = cliente_sin_auth.post("/api/seleccion/confirmar", json={"nodo_id": "crear_apps"})
    assert respuesta.status_code == 401
