"""Prueba que agents/orquestador_agente.py::crear_agente_orquestador arme
el Agent con las 5 fases expuestas como tools -- sin llamar a Bedrock de
verdad (envolver un Agent con .as_tool() no hace ninguna llamada de red,
solo arma la config/schema de la tool)."""

import os

os.environ.setdefault("TELOS_FICHA_BACKEND", "local")

from agents.coach_validacion import crear_agente_coach_validacion
from agents.estratega_sistemas import crear_agente_estratega_sistemas
from agents.explorador import crear_agente_explorador
from agents.orquestador_agente import crear_agente_orquestador
from agents.seguimiento import crear_agente_seguimiento
from agents.sintetizador import crear_agente_sintetizador

_FABRICAS = {
    1: crear_agente_explorador,
    2: crear_agente_sintetizador,
    3: crear_agente_coach_validacion,
    4: crear_agente_estratega_sistemas,
    5: crear_agente_seguimiento,
}


def _construir_agentes_fase(usuario_id: str, idioma: str = "es"):
    return {fase: fabrica(usuario_id, idioma, nombre="Ana") for fase, fabrica in _FABRICAS.items()}


def test_expone_las_5_fases_como_tools():
    agentes = _construir_agentes_fase("test_orquestador_1")
    orquestador = crear_agente_orquestador(agentes, "estado de prueba", [], idioma="es")
    assert orquestador.tool_names == ["fase_1", "fase_2", "fase_3", "fase_4", "fase_5"]


def test_prompt_incluye_estado_y_insights():
    agentes = _construir_agentes_fase("test_orquestador_2")
    orquestador = crear_agente_orquestador(
        agentes, "Última fase cerrada: 2.", ["canta en karaoke los martes"], idioma="es"
    )
    assert "Última fase cerrada: 2." in orquestador.system_prompt
    assert "canta en karaoke los martes" in orquestador.system_prompt


def test_sin_insights_muestra_placeholder():
    agentes = _construir_agentes_fase("test_orquestador_3")
    orquestador_es = crear_agente_orquestador(agentes, "estado", [], idioma="es")
    assert "ninguno todavía" in orquestador_es.system_prompt

    agentes_en = _construir_agentes_fase("test_orquestador_4", idioma="en")
    orquestador_en = crear_agente_orquestador(agentes_en, "state", [], idioma="en")
    assert "none yet" in orquestador_en.system_prompt


def test_usa_modelo_orquestador_no_subagente():
    from agents._modelo import MODEL_ID_ORQUESTADOR, MODEL_ID_SUBAGENTE

    agentes = _construir_agentes_fase("test_orquestador_5")
    orquestador = crear_agente_orquestador(agentes, "estado", [], idioma="es")
    assert orquestador.model.config["model_id"] == MODEL_ID_ORQUESTADOR
    assert orquestador.model.config["model_id"] != MODEL_ID_SUBAGENTE
