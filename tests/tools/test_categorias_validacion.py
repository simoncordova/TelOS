"""Cobertura de tools/categorias_validacion.py -- el selector plano de
áreas de vida de Fase 3. Sin AWS, sin Bedrock: dato puro + búsqueda
determinística."""

from tools.categorias_validacion import AREAS_VIDA, buscar_area_vida


def test_buscar_area_conocida():
    area = buscar_area_vida("es", "trabajo_carrera")
    assert area is not None
    assert area["id"] == "trabajo_carrera"


def test_buscar_area_desconocida_devuelve_none():
    assert buscar_area_vida("es", "no_existe") is None


def test_es_y_en_tienen_los_mismos_ids():
    ids_es = {a["id"] for a in AREAS_VIDA["es"]}
    ids_en = {a["id"] for a in AREAS_VIDA["en"]}
    assert ids_es == ids_en


def test_hay_varias_areas_para_elegir():
    assert len(AREAS_VIDA["es"]) >= 5
