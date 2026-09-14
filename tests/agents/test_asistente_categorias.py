"""Cobertura de agents/asistente_categorias.py -- chat de apoyo real de
Fase 1. Sin Bedrock: solo se ejercita la parte determinística (la tabla
de referencia que se le arma al modelo, y la revalidación de una
sugerencia contra la taxonomía real) -- la llamada al modelo en sí
(`sugerir_categoria`) queda sin probar a nivel unitario, mismo criterio
que el resto del proyecto para no depender de Bedrock en tests."""

from agents.asistente_categorias import SugerenciaCategoria, _tabla_categorias
from tools.categorias_ikigai import DOMINIOS, HOJAS, VERBOS


def test_tabla_categorias_es_incluye_todos_los_verbos_y_dominios():
    tabla = _tabla_categorias("es")
    for verbo in VERBOS["es"]:
        assert f'"{verbo["id"]}"' in tabla
    for dominio_id in DOMINIOS["es"]:
        assert f'"{dominio_id}"' in tabla


def test_tabla_categorias_en_incluye_todas_las_hojas():
    tabla = _tabla_categorias("en")
    for lista in HOJAS["en"].values():
        for hoja in lista:
            assert f'"{hoja["id"]}"' in tabla


def test_sugerencia_categoria_encontrada_false_sin_ids():
    s = SugerenciaCategoria(encontrada=False, explicacion="no hay match")
    assert s.verbo_id is None
    assert s.dominio_id is None
    assert s.hoja_id is None
