"""Cobertura de tools/categorias_sistema.py -- los 4 árboles
independientes de Fase 4. Sin AWS, sin Bedrock: dato puro + búsqueda
determinística."""

from tools.categorias_sistema import (
    CATEGORIAS_SISTEMA,
    FALLBACK_PLAN_OBSTACULO,
    PREGUNTAS_SISTEMA_IDS,
    buscar_nodo_sistema_con_ruta,
    plan_por_defecto_obstaculo,
)


def test_preguntas_son_las_4_del_spec():
    assert PREGUNTAS_SISTEMA_IDS == ("accion", "cuando_donde", "metrica", "obstaculo")


def test_buscar_nodo_conocido_devuelve_nodo_y_ruta():
    encontrado = buscar_nodo_sistema_con_ruta("es", "accion", "ejercicio_cardio")
    assert encontrado is not None
    nodo, ruta = encontrado
    assert nodo["id"] == "ejercicio_cardio"
    assert ruta == ["movimiento_salud", "ejercicio_cardio"]


def test_buscar_nodo_hoja_de_un_solo_nivel():
    # "metrica" no tiene sub-niveles -- sus nodos son hojas directas.
    encontrado = buscar_nodo_sistema_con_ruta("es", "metrica", "binario_si_no")
    assert encontrado is not None
    _nodo, ruta = encontrado
    assert ruta == ["binario_si_no"]


def test_buscar_nodo_en_pregunta_equivocada_devuelve_none():
    # "ejercicio_cardio" existe, pero solo bajo "accion", no "obstaculo".
    assert buscar_nodo_sistema_con_ruta("es", "obstaculo", "ejercicio_cardio") is None


def test_buscar_nodo_desconocido_devuelve_none():
    assert buscar_nodo_sistema_con_ruta("es", "accion", "no_existe") is None


def test_es_y_en_tienen_las_mismas_preguntas_y_los_mismos_ids():
    def _ids(nodos: list[dict]) -> set[str]:
        ids = set()
        for nodo in nodos:
            ids.add(nodo["id"])
            ids |= _ids(nodo.get("hijos") or [])
        return ids

    assert set(CATEGORIAS_SISTEMA["es"].keys()) == set(CATEGORIAS_SISTEMA["en"].keys())
    for pregunta_id in PREGUNTAS_SISTEMA_IDS:
        assert _ids(CATEGORIAS_SISTEMA["es"][pregunta_id]) == _ids(CATEGORIAS_SISTEMA["en"][pregunta_id])


def test_cada_pregunta_tiene_al_menos_una_categoria():
    for pregunta_id in PREGUNTAS_SISTEMA_IDS:
        assert len(CATEGORIAS_SISTEMA["es"][pregunta_id]) > 0


def test_toda_categoria_de_nivel_1_de_obstaculo_tiene_plan_por_defecto():
    for idioma in ("es", "en"):
        for categoria in CATEGORIAS_SISTEMA[idioma]["obstaculo"]:
            assert plan_por_defecto_obstaculo(idioma, categoria["id"]) == FALLBACK_PLAN_OBSTACULO[idioma][categoria["id"]]


def test_plan_por_defecto_categoria_desconocida_devuelve_none():
    assert plan_por_defecto_obstaculo("es", "no_existe") is None


def test_nodos_con_desc_lo_incluyen_en_el_dict():
    nodo = buscar_nodo_sistema_con_ruta("es", "accion", "ejercicio_cardio")[0]
    assert nodo["desc"] == "Correr, caminar fuerte, bicicleta, nadar."
