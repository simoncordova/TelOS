"""Cobertura de agents/orquestador.py::SesionTelos._seleccionar_siguiente_pregunta
y ._proposito_listo -- Explorer v2 (revisión de arquitectura externa,
12/09/2026): el control de flujo de la Fase 1 (qué preguntar, cuándo
cerrar) es código puro, nunca una decisión del modelo. No depende de
Bedrock -- estas dos funciones son determinísticas sobre un dict."""

import os

os.environ.setdefault("TELOS_FICHA_BACKEND", "local")

from agents.orquestador import MAX_INTENTOS_POR_EJE, SesionTelos
from tools.exploracion_preguntas import EJES, PREGUNTAS_EXPLORACION

_PREGUNTAS = PREGUNTAS_EXPLORACION["es"]


def _progreso_vacio() -> dict:
    return {
        "active_axis": None,
        "active_question_id": None,
        "axes": {eje: {"status": "pending", "question_id": None, "evidence": None, "attempts": 0} for eje in EJES},
    }


def _sesion() -> SesionTelos:
    # usuario_id sin datos previos -- local backend, sin tocar AWS.
    return SesionTelos("test_explorer_v2_sin_ficha", idioma="es")


def test_primer_turno_elige_el_primer_eje_en_orden():
    sesion = _sesion()
    progreso = _progreso_vacio()
    eje, id_pregunta, texto = sesion._seleccionar_siguiente_pregunta(progreso, _PREGUNTAS)
    assert eje == EJES[0]
    assert id_pregunta == _PREGUNTAS[EJES[0]][0]["id"]
    assert texto == _PREGUNTAS[EJES[0]][0]["text"]


def test_eje_pending_con_intento_repite_con_pregunta_de_profundizacion():
    sesion = _sesion()
    progreso = _progreso_vacio()
    eje = EJES[0]
    progreso["active_axis"] = eje
    progreso["axes"][eje]["attempts"] = 1  # ya fallo un intento (partial/off_topic)
    eje_elegido, id_pregunta, _texto = sesion._seleccionar_siguiente_pregunta(progreso, _PREGUNTAS)
    assert eje_elegido == eje
    assert id_pregunta == _PREGUNTAS[eje][1]["id"]  # la segunda pregunta del mismo eje


def test_eje_agota_intentos_pasa_al_siguiente_eje():
    sesion = _sesion()
    progreso = _progreso_vacio()
    eje = EJES[0]
    progreso["active_axis"] = eje
    progreso["axes"][eje]["attempts"] = MAX_INTENTOS_POR_EJE  # ya no quedan preguntas de este eje
    eje_elegido, _id, _texto = sesion._seleccionar_siguiente_pregunta(progreso, _PREGUNTAS)
    assert eje_elegido == EJES[1]
    assert progreso["axes"][eje]["status"] == "skipped"  # se marcó terminal por código


def test_eje_answered_no_se_vuelve_a_elegir():
    sesion = _sesion()
    progreso = _progreso_vacio()
    progreso["axes"][EJES[0]]["status"] = "answered"
    progreso["axes"][EJES[0]]["evidence"] = "ya cubierto"
    eje_elegido, _id, _texto = sesion._seleccionar_siguiente_pregunta(progreso, _PREGUNTAS)
    assert eje_elegido == EJES[1]


def test_ninguna_pregunta_si_todos_los_ejes_son_terminales():
    sesion = _sesion()
    progreso = _progreso_vacio()
    for eje in EJES:
        progreso["axes"][eje]["status"] = "answered"
    assert sesion._seleccionar_siguiente_pregunta(progreso, _PREGUNTAS) is None


def test_proposito_no_listo_con_pocos_ejes_respondidos():
    sesion = _sesion()
    progreso = _progreso_vacio()
    progreso["axes"][EJES[0]]["status"] = "answered"
    assert sesion._proposito_listo(progreso) is False


def test_proposito_listo_con_suficientes_ejes_respondidos():
    sesion = _sesion()
    progreso = _progreso_vacio()
    for eje in EJES[:3]:
        progreso["axes"][eje]["status"] = "answered"
    assert sesion._proposito_listo(progreso) is True


def test_proposito_listo_si_todos_terminales_aunque_esten_skipped():
    # Nunca se bloquea indefinidamente -- si los 5 ejes ya llegaron a un
    # estado terminal (aunque sea a fuerza de skips), hay que cerrar.
    sesion = _sesion()
    progreso = _progreso_vacio()
    for eje in EJES:
        progreso["axes"][eje]["status"] = "skipped"
    assert sesion._proposito_listo(progreso) is True
