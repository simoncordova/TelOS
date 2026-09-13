"""Cobertura de tools/categorias_ikigai.py -- el grafo único del selector
visual (reemplaza al banco de preguntas del Explorer v2). Sin AWS, sin
Bedrock: es dato puro + una búsqueda determinística."""

from tools.categorias_ikigai import CATEGORIAS_IKIGAI, DIMENSIONES_IKIGAI, buscar_nodo_con_ruta


def test_dimensiones_son_las_5_del_ikigai_hibrido():
    assert DIMENSIONES_IKIGAI == ("amas", "sos_bueno", "mundo_necesita", "pueden_pagar", "valores")


def test_buscar_nodo_conocido_devuelve_nodo_y_ruta():
    encontrado = buscar_nodo_con_ruta("es", "crear_apps")
    assert encontrado is not None
    nodo, ruta = encontrado
    assert nodo["id"] == "crear_apps"
    assert set(nodo["dimensiones"]) == {"amas", "sos_bueno", "pueden_pagar"}
    assert ruta == ["crear_construir", "software_tecnologia", "crear_apps"]


def test_buscar_nodo_desconocido_devuelve_none():
    assert buscar_nodo_con_ruta("es", "no_existe_este_id") is None


def test_es_y_en_tienen_los_mismos_ids():
    def _ids(nodos: list[dict]) -> set[str]:
        ids = set()
        for nodo in nodos:
            ids.add(nodo["id"])
            ids |= _ids(nodo.get("hijos") or [])
        return ids

    assert _ids(CATEGORIAS_IKIGAI["es"]) == _ids(CATEGORIAS_IKIGAI["en"])


def test_cada_dimension_tiene_cobertura_real_en_hojas():
    # Sanity check del contenido semilla -- si alguna dimensión quedara
    # sin ninguna hoja que la etiquete, _cobertura_suficiente nunca
    # podría cumplirse y Fase 1 se bloquearía para siempre.
    def _hojas(nodos: list[dict]) -> list[dict]:
        hojas = []
        for nodo in nodos:
            hijos = nodo.get("hijos")
            if hijos:
                hojas.extend(_hojas(hijos))
            else:
                hojas.append(nodo)
        return hojas

    hojas = _hojas(CATEGORIAS_IKIGAI["es"])
    for dimension in DIMENSIONES_IKIGAI:
        tocada_por = [h for h in hojas if dimension in h["dimensiones"]]
        assert len(tocada_por) >= 2, f"dimensión {dimension!r} sin cobertura suficiente en la semilla"


def test_convergencia_algunas_hojas_tocan_varias_dimensiones():
    # El punto del rediseño en grafo (vs. un árbol por eje): algunas
    # categorías tienen que aportar a 3+ dimensiones a la vez.
    def _hojas(nodos: list[dict]) -> list[dict]:
        hojas = []
        for nodo in nodos:
            hijos = nodo.get("hijos")
            if hijos:
                hojas.extend(_hojas(hijos))
            else:
                hojas.append(nodo)
        return hojas

    hojas = _hojas(CATEGORIAS_IKIGAI["es"])
    convergentes = [h for h in hojas if len(h["dimensiones"]) >= 3]
    assert len(convergentes) >= 1
