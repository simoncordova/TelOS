"""Cobertura de agents/orquestador.py::exit_criteria_cumplido -- la
función pura que reemplaza al chequeo inline de campos obligatorios al
cerrar una fase (revisión de arquitectura externa, 12/09/2026, sección 6:
"reemplazar cerrado por invariantes"). No depende de Bedrock ni de
AgentCore Memory, es lógica determinística sobre un dict."""

import os

os.environ.setdefault("TELOS_FICHA_BACKEND", "local")

from agents.orquestador import exit_criteria_cumplido


def test_fase_1_no_tiene_campos_obligatorios():
    cumplido, faltantes = exit_criteria_cumplido(1, {})
    assert cumplido is True
    assert faltantes == ()


def test_fase_2_requiere_proposito():
    cumplido, faltantes = exit_criteria_cumplido(2, {})
    assert cumplido is False
    assert faltantes == ("proposito",)

    cumplido, faltantes = exit_criteria_cumplido(2, {"proposito": "algo"})
    assert cumplido is True
    assert faltantes == ()


def test_fase_4_requiere_proposito_y_sistema():
    cumplido, faltantes = exit_criteria_cumplido(4, {"proposito": "algo"})
    assert cumplido is False
    assert faltantes == ("sistema",)

    cumplido, faltantes = exit_criteria_cumplido(4, {"proposito": "algo", "sistema": "otro"})
    assert cumplido is True


def test_fase_5_cumplido_false_no_es_faltante():
    # "cumplido" es un booleano legítimo en False (la persona no sostuvo
    # el hábito) -- eso NO es lo mismo que la clave faltar del todo.
    datos = {"proposito": "algo", "sistema": "otro", "cumplido": False}
    cumplido, faltantes = exit_criteria_cumplido(5, datos)
    assert cumplido is True
    assert faltantes == ()


def test_fase_5_sin_clave_cumplido_si_falta():
    datos = {"proposito": "algo", "sistema": "otro"}
    cumplido, faltantes = exit_criteria_cumplido(5, datos)
    assert cumplido is False
    assert faltantes == ("cumplido",)
