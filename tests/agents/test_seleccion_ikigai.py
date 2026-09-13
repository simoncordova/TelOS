"""Cobertura de agents/orquestador.py::SesionTelos.confirmar_seleccion y
._cobertura_suficiente -- el selector visual Ikigai que reemplaza al
Explorador conversacional (Explorer v2, sacado el 13/09/2026). Sin AWS,
sin Bedrock: solo se ejercita la parte determinística (cobertura,
validación, guardado de la selección) -- el camino de cierre (que sí
invoca al modelo una vez, ver _sintetizar_selecciones) no se prueba acá,
mismo criterio que el resto del proyecto para no depender de Bedrock en
tests."""

import os

os.environ.setdefault("TELOS_FICHA_BACKEND", "local")

import pytest

from agents.orquestador import DIMENSIONES_IKIGAI, SesionTelos
from tools.selecciones_estructuradas import borrar_selecciones_estructuradas


def _sesion(usuario_id: str) -> SesionTelos:
    borrar_selecciones_estructuradas(usuario_id)
    return SesionTelos(usuario_id, idioma="es")


def test_cobertura_suficiente_vacia_es_false():
    sesion = _sesion("test_seleccion_ikigai_u1")
    assert sesion._cobertura_suficiente({}) is False


def test_cobertura_suficiente_todas_las_dimensiones_al_minimo():
    sesion = _sesion("test_seleccion_ikigai_u2")
    cobertura = {dim: 2 for dim in DIMENSIONES_IKIGAI}
    assert sesion._cobertura_suficiente(cobertura) is True


def test_cobertura_suficiente_una_dimension_corta():
    sesion = _sesion("test_seleccion_ikigai_u3")
    cobertura = {dim: 2 for dim in DIMENSIONES_IKIGAI}
    cobertura["valores"] = 1  # una sola dimensión por debajo del mínimo
    assert sesion._cobertura_suficiente(cobertura) is False


def test_confirmar_seleccion_primera_vez_no_cierra():
    sesion = _sesion("test_seleccion_ikigai_u4")
    resultado = sesion.confirmar_seleccion("crear_apps")
    assert resultado["cerrado"] is False
    assert resultado["mensaje_cierre"] is None
    # "crear_apps" aporta a estas 3 dimensiones (ver tools/categorias_ikigai.py)
    assert resultado["cobertura"]["amas"] == 1
    assert resultado["cobertura"]["sos_bueno"] == 1
    assert resultado["cobertura"]["pueden_pagar"] == 1
    assert resultado["cobertura"].get("mundo_necesita", 0) == 0


def test_confirmar_seleccion_acumula_cobertura_entre_llamadas():
    sesion = _sesion("test_seleccion_ikigai_u5")
    sesion.confirmar_seleccion("crear_apps")  # amas, sos_bueno, pueden_pagar
    resultado = sesion.confirmar_seleccion("mentorear")  # sos_bueno, mundo_necesita, valores
    assert resultado["cobertura"]["sos_bueno"] == 2
    assert resultado["cobertura"]["mundo_necesita"] == 1
    assert resultado["cobertura"]["valores"] == 1


def test_confirmar_seleccion_fuera_de_fase_1_lanza():
    sesion = _sesion("test_seleccion_ikigai_u6")
    sesion.fase_actual = 2
    with pytest.raises(ValueError):
        sesion.confirmar_seleccion("crear_apps")


def test_confirmar_seleccion_nodo_desconocido_lanza():
    sesion = _sesion("test_seleccion_ikigai_u7")
    with pytest.raises(ValueError):
        sesion.confirmar_seleccion("id_que_no_existe")
