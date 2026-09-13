"""Cobertura de agents/orquestador.py::SesionTelos.confirmar_seleccion,
.confirmar_valores y ._puede_cerrar -- el selector visual Ikigai
(contenido y mecánica portados del prototipo real de Claude Design,
13/09/2026). Sin AWS, sin Bedrock: solo se ejercita la parte
determinística (cobertura, validación, guardado) -- el camino de cierre
(que sí invoca al modelo una vez, ver _sintetizar_selecciones) no se
prueba acá, mismo criterio que el resto del proyecto para no depender de
Bedrock en tests."""

import os

os.environ.setdefault("TELOS_FICHA_BACKEND", "local")

import pytest

from agents.orquestador import SesionTelos
from tools.selecciones_estructuradas import borrar_selecciones_estructuradas


def _sesion(usuario_id: str) -> SesionTelos:
    borrar_selecciones_estructuradas(usuario_id)
    return SesionTelos(usuario_id, idioma="es")


def test_puede_cerrar_con_menos_de_4_selecciones_es_false():
    sesion = _sesion("test_seleccion_ikigai_u1")
    assert sesion._puede_cerrar({"selecciones": [{}, {}, {}]}) is False


def test_puede_cerrar_con_4_selecciones_es_true():
    sesion = _sesion("test_seleccion_ikigai_u2")
    assert sesion._puede_cerrar({"selecciones": [{}, {}, {}, {}]}) is True


def test_confirmar_seleccion_primera_vez_no_cierra():
    sesion = _sesion("test_seleccion_ikigai_u3")
    resultado = sesion.confirmar_seleccion("crear/tech/IA")
    assert resultado["cerrado"] is False
    assert resultado["mensaje_cierre"] is None
    assert resultado["mostrar_valores"] is False
    # crear (LG) + IA (LG) -> L y G tocadas, V y N en 0.
    assert resultado["cobertura"]["L"] == 1
    assert resultado["cobertura"]["G"] == 1
    assert resultado["cobertura"]["V"] == 0
    assert resultado["cobertura"]["N"] == 0


def test_confirmar_seleccion_segunda_vez_pide_mostrar_valores():
    sesion = _sesion("test_seleccion_ikigai_u4")
    sesion.confirmar_seleccion("crear/tech/IA")
    resultado = sesion.confirmar_seleccion("ayudar/personas/Mentoría")
    assert resultado["mostrar_valores"] is True
    assert resultado["cerrado"] is False


def test_confirmar_valores_apaga_mostrar_valores_para_la_siguiente():
    sesion = _sesion("test_seleccion_ikigai_u5")
    sesion.confirmar_seleccion("crear/tech/IA")
    sesion.confirmar_seleccion("ayudar/personas/Mentoría")
    sesion.confirmar_valores(["Autonomía", "Coherencia"])
    resultado = sesion.confirmar_seleccion("resolver/datos/Análisis")
    assert resultado["mostrar_valores"] is False


def test_confirmar_valores_mas_del_maximo_lanza():
    sesion = _sesion("test_seleccion_ikigai_u6")
    with pytest.raises(ValueError):
        sesion.confirmar_valores(["Autonomía", "Honestidad", "Calma", "Justicia"])


def test_confirmar_valores_desconocido_lanza():
    sesion = _sesion("test_seleccion_ikigai_u7")
    with pytest.raises(ValueError):
        sesion.confirmar_valores(["Un valor inventado"])


def test_confirmar_seleccion_reemplaza_la_misma_ruta_sin_duplicar():
    sesion = _sesion("test_seleccion_ikigai_u8")
    sesion.confirmar_seleccion("crear/tech/IA", detalle_libre="primero")
    resultado = sesion.confirmar_seleccion("crear/tech/IA", detalle_libre="ajustado")
    assert resultado["cobertura"]["L"] == 1  # sigue contando como UNA selección, no dos
    assert resultado["cobertura"]["G"] == 1


def test_confirmar_seleccion_fuera_de_fase_1_lanza():
    sesion = _sesion("test_seleccion_ikigai_u9")
    sesion.fase_actual = 2
    with pytest.raises(ValueError):
        sesion.confirmar_seleccion("crear/tech/IA")


def test_confirmar_seleccion_nodo_id_mal_formado_lanza():
    sesion = _sesion("test_seleccion_ikigai_u10")
    with pytest.raises(ValueError):
        sesion.confirmar_seleccion("crear/tech")  # faltan partes


def test_confirmar_seleccion_combinacion_desconocida_lanza():
    sesion = _sesion("test_seleccion_ikigai_u11")
    with pytest.raises(ValueError):
        sesion.confirmar_seleccion("crear/ciencia/Método")  # ciencia no es dominio de crear
