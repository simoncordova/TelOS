"""Cobertura del guardrail de crisis (tools/crisis.py) -- CLAUDE.md lo marca
no negociable: "debe ser invocable de verdad, no un comentario en el
prompt". Sin estos tests, nada garantiza en cada cambio que el regex
siga detectando lo que dice detectar.
"""

from tools.crisis import detectar_señal_crisis


def test_detecta_ideacion_suicida_es():
    resultado = detectar_señal_crisis("quiero morirme, ya no aguanto más")
    assert resultado["disparado"] is True
    assert resultado["categoria"] == "ideacion_suicida"


def test_detecta_ideacion_suicida_en():
    resultado = detectar_señal_crisis("I want to kill myself")
    assert resultado["disparado"] is True
    assert resultado["categoria"] == "ideacion_suicida"


def test_detecta_plan_o_metodo():
    resultado = detectar_señal_crisis("tengo un plan para matarme")
    assert resultado["disparado"] is True
    assert resultado["categoria"] == "plan_o_metodo"


def test_detecta_autolesion_es():
    resultado = detectar_señal_crisis("estuve pensando en cortarme")
    assert resultado["disparado"] is True
    assert resultado["categoria"] == "autolesion"


def test_detecta_autolesion_en():
    resultado = detectar_señal_crisis("I've been hurting myself")
    assert resultado["disparado"] is True
    assert resultado["categoria"] == "autolesion"


def test_detecta_desesperanza_extrema():
    resultado = detectar_señal_crisis("nadie me extrañaría si desapareciera para siempre")
    assert resultado["disparado"] is True
    assert resultado["categoria"] == "desesperanza_extrema"


def test_detecta_sin_importar_idioma_seleccionado():
    # El guardrail revisa ES y EN siempre, sin importar el idioma de la UI
    # (sección 0.5 del spec) -- alguien con la UI en "en" puede escribir en
    # español y viceversa.
    resultado = detectar_señal_crisis("I don't want to live anymore")
    assert resultado["disparado"] is True


def test_detecta_sin_acentos():
    # El texto de entrada se normaliza sin acentos/ñ antes de comparar.
    resultado = detectar_señal_crisis("quiero matarme")
    assert resultado["disparado"] is True


def test_no_dispara_con_texto_benigno():
    resultado = detectar_señal_crisis("hoy tuve un buen día, avancé con mi propósito")
    assert resultado == {"disparado": False, "categoria": None}


def test_no_dispara_con_modismo_benigno_morirse_de_risa():
    resultado = detectar_señal_crisis("me moría de la risa con ese chiste")
    assert resultado["disparado"] is False


def test_no_dispara_con_modismo_benigno_dying_laughing_en():
    resultado = detectar_señal_crisis("I was dying laughing at that")
    assert resultado["disparado"] is False


def test_no_dispara_con_texto_vacio():
    assert detectar_señal_crisis("") == {"disparado": False, "categoria": None}
    assert detectar_señal_crisis(None) == {"disparado": False, "categoria": None}
