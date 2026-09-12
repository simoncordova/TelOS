"""Cobertura del detector de voseo (tools/estilo.py) -- lo usa
agents/_calidad.py::GuardaEstilo como chequeo determinístico antes de
dejar pasar una respuesta. Sin estos tests, nada garantiza que el regex
siga detectando voseo real ni que los modismos con "tú" sigan sin
disparar falsos positivos.
"""

from tools.estilo import detectar_voseo


def test_detecta_voseo_simple():
    assert detectar_voseo("vos tenés que confiar en tu propósito") is True


def test_detecta_voseo_con_acento_diferencial():
    # "hacés"/"sabés" solo se distinguen de "haces"/"sabes" por el acento.
    assert detectar_voseo("¿qué hacés cuando te sentís sin energía?") is True


def test_detecta_imperativo_con_pronombre_pegado():
    assert detectar_voseo("contame más sobre eso") is True


def test_no_dispara_con_forma_tu_correcta():
    assert detectar_voseo("tienes que confiar en tu propósito, ¿qué sientes?") is False


def test_no_dispara_con_falso_positivo_conocido():
    # "café", "inglés", "país", "así" no son voseo aunque terminen en
    # "-és"/"-ís" -- el detector usa formas completas, no un sufijo genérico.
    assert detectar_voseo("tomamos un café y hablamos de un país lejano, así fue") is False


def test_distingue_fijate_de_fijate_con_tilde():
    assert detectar_voseo("fijate en los detalles") is True
    assert detectar_voseo("fíjate en los detalles") is False


def test_no_dispara_con_texto_vacio():
    assert detectar_voseo("") is False
    assert detectar_voseo(None) is False
