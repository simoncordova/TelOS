"""Cobertura de tools/categorias_ikigai.py -- contenido y mecánica
portados del prototipo interactivo real de Claude Design (13/09/2026).
Sin AWS, sin Bedrock: es dato puro + una búsqueda/unión determinística."""

from tools.categorias_ikigai import (
    DIMENSIONES_IKIGAI,
    DOMINIOS,
    HOJAS,
    MAX_VALORES,
    VALORES_DISPONIBLES,
    VERBOS,
    buscar_hoja,
    unir_dimensiones,
)


def test_dimensiones_son_las_4_del_prototipo():
    assert DIMENSIONES_IKIGAI == ("L", "G", "V", "N")


def test_unir_dimensiones_sin_duplicados_preserva_orden():
    assert unir_dimensiones("LG", "LV") == ["L", "G", "V"]
    assert unir_dimensiones("GV", "NV") == ["G", "V", "N"]


def test_buscar_hoja_conocida_une_dimensiones_de_verbo_y_hoja():
    # crear (LG) + IA (LG) -> LG (sin duplicar)
    encontrado = buscar_hoja("es", "crear", "tech", "IA")
    assert encontrado is not None
    verbo, hoja, dims = encontrado
    assert verbo["id"] == "crear"
    assert hoja["id"] == "IA"
    assert dims == ["L", "G"]


def test_buscar_hoja_convergencia_real_de_3_dimensiones():
    # crear (LG) + Apps (LV) -> L, G, V (3 dimensiones -- punto de
    # convergencia real, el mismo caso que muestra el prototipo).
    encontrado = buscar_hoja("es", "crear", "tech", "Apps")
    assert encontrado is not None
    _verbo, _hoja, dims = encontrado
    assert dims == ["L", "G", "V"]


def test_buscar_hoja_dominio_no_valido_para_ese_verbo():
    # "ciencia" no está en los dominios de "crear".
    assert buscar_hoja("es", "crear", "ciencia", "Método") is None


def test_buscar_hoja_desconocida_en_dominio_valido():
    assert buscar_hoja("es", "crear", "tech", "No existe") is None


def test_verbo_desconocido():
    assert buscar_hoja("es", "no_existe", "tech", "IA") is None


def test_mismo_dominio_hoja_por_verbos_distintos_da_dimensiones_distintas():
    # "tech" es dominio de "crear" (LG) y de "resolver" (GV) -- la misma
    # hoja "IA" (LG) da una unión distinta según por qué verbo se llegó.
    _v1, _h1, dims_crear = buscar_hoja("es", "crear", "tech", "IA")
    _v2, _h2, dims_resolver = buscar_hoja("es", "resolver", "tech", "IA")
    assert dims_crear == ["L", "G"]
    assert set(dims_resolver) == {"G", "V", "L"}


def test_es_y_en_tienen_los_mismos_ids_de_verbos_y_dominios():
    ids_verbos_es = {v["id"] for v in VERBOS["es"]}
    ids_verbos_en = {v["id"] for v in VERBOS["en"]}
    assert ids_verbos_es == ids_verbos_en
    assert set(DOMINIOS["es"].keys()) == set(DOMINIOS["en"].keys())
    assert set(HOJAS["es"].keys()) == set(HOJAS["en"].keys())


def test_cada_dominio_de_cada_verbo_tiene_hojas_definidas():
    for verbo in VERBOS["es"]:
        for dominio_id in verbo["dominios"]:
            assert dominio_id in DOMINIOS["es"], f"dominio {dominio_id!r} sin label"
            assert len(HOJAS["es"].get(dominio_id, [])) > 0, f"dominio {dominio_id!r} sin hojas"


def test_valores_disponibles_maximo_3():
    assert MAX_VALORES == 3
    assert len(VALORES_DISPONIBLES["es"]) >= MAX_VALORES
    assert len(VALORES_DISPONIBLES["es"]) == len(VALORES_DISPONIBLES["en"])
