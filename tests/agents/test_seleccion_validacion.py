"""Cobertura de agents/orquestador.py::SesionTelos.confirmar_seleccion_validacion
y ._invocar_coach_validacion -- el híbrido selección + conversación
acotada de Fase 3. Sin AWS, sin Bedrock: solo se ejercita lo
determinístico (validación, transición de etapa, el aviso fijo mientras
la selección sigue pendiente). El camino que sí invoca al modelo (la 2da
selección, que dispara _abrir_refinado, y la conversación real de
"refinando") no se prueba acá -- mismo criterio que el resto del
proyecto para no depender de Bedrock en tests."""

import os

os.environ.setdefault("TELOS_FICHA_BACKEND", "local")

import pytest

from agents.orquestador import SesionTelos
from tools.selecciones_estructuradas import borrar_selecciones_estructuradas


def _sesion_fase_3(usuario_id: str) -> SesionTelos:
    borrar_selecciones_estructuradas(usuario_id)
    sesion = SesionTelos(usuario_id, idioma="es")
    sesion.fase_actual = 3
    return sesion


def test_primera_seleccion_pasa_a_friccion_futura_sin_invocar_bedrock():
    sesion = _sesion_fase_3("test_seleccion_validacion_u1")
    resultado = sesion.confirmar_seleccion_validacion("trabajo_carrera", detalle_libre="Lideré un proyecto difícil")
    assert resultado["etapa"] == "friccion_futura"
    assert resultado["mensaje_apertura_refinado"] is None


def test_area_desconocida_lanza():
    sesion = _sesion_fase_3("test_seleccion_validacion_u2")
    with pytest.raises(ValueError):
        sesion.confirmar_seleccion_validacion("area_que_no_existe")


def test_fuera_de_fase_3_lanza():
    sesion = _sesion_fase_3("test_seleccion_validacion_u3")
    sesion.fase_actual = 2
    with pytest.raises(ValueError):
        sesion.confirmar_seleccion_validacion("trabajo_carrera")


def test_texto_libre_mientras_sigue_en_etapa_de_seleccion_devuelve_aviso_fijo():
    sesion = _sesion_fase_3("test_seleccion_validacion_u4")
    # Ni una selección hecha todavía -- etapa "evidencia_pasada" por
    # default (progreso vacío).
    texto, cerrado = sesion._invocar_coach_validacion("hola, quiero contarte algo", turn_id=None)
    assert cerrado is False
    assert texto  # el aviso fijo, no vacío

    sesion.confirmar_seleccion_validacion("trabajo_carrera")  # -> friccion_futura, sin Bedrock
    texto2, cerrado2 = sesion._invocar_coach_validacion("otra vez texto libre", turn_id=None)
    assert cerrado2 is False
    assert texto2 == texto  # mismo aviso fijo mientras la selección sigue pendiente
