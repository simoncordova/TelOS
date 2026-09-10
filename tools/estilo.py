"""Detector de voseo en la respuesta generada. Ver agents/_calidad.py para
cómo se usa (hook de reintento) y docs/agente-proposito-de-vida-prompts.md
sección 8 para la regla de tono que esto verifica.

Curado para precisión, no para cobertura total (al revés que
tools/crisis.py): un falso positivo acá dispara una regeneración
innecesaria, así que la lista son formas de voseo conocidas y sin
ambigüedad, no un patrón de sufijo genérico ("-és"/"-ás"/"-ís" como
sufijo tendría demasiados falsos positivos: "café", "inglés", "país",
"así", etc. no son voseo).

A propósito NO se sacan los acentos antes de comparar (al revés que
crisis.py): para varios verbos regulares en "-er" (hacés/haces,
sabés/sabes, creés/crees...) el acento es la ÚNICA diferencia entre la
forma de vos y la de tú — sacarlo generaría falsos positivos constantes.
Esto es seguro porque el texto que se revisa es la respuesta del modelo
(que escribe con acentos correctos), no texto casual de un usuario.
"""

import re

_FORMAS_VOSEO = [
    "tenés", "tené", "querés", "sos", "podés", "sentís", "sentí",
    "decís", "decí", "venís", "vení", "sabés", "sabé", "creés",
    "hacés", "hacé", "pensás", "pensá", "mirás", "mirá",
    "escribís", "escribí", "contás", "contá",
    # "fijate" (sin acento) es voseo; "fíjate" (con acento) es la forma
    # correcta de "tú" -- confundirlas fue un bug real detectado al
    # probar este mismo detector, no incluir "fíjate" acá.
    "fijate",
    "avisás", "avisá", "guardás", "guardá", "pasás", "pasá",
    "empezás", "empezá", "esperás", "esperá", "preguntás", "preguntá",
    "respondés", "respondé", "anotás", "anotá", "dejás", "dejá",
    "tomás", "tomá", "andás", "andá", "volvés", "volvé",
    "entendés", "entendé", "recordás", "recordá", "vivís", "viví",
    "escuchás", "escuchá",
    # Imperativos de voseo con pronombre pegado (sin acento en la forma
    # de vos; la de "tú" lleva acento y se escribe distinto: "cuéntame",
    # "dime", "avísame", "escúchame", "ayúdame", "mándame", "pásame",
    # "mírame" -- no colisionan).
    "contame", "decime", "avisame", "escuchame", "ayudame", "mandame",
    "pasame", "mirame",
    # Encontrados de verdad al revisar los prompts propios (no del
    # modelo) con este mismo detector -- "léela"/"presenta"/"reconoce"/
    # "elige" son las formas de "tú" que hay que usar en su lugar.
    "leela", "presentá", "reconocé", "elegí", "elegi",
]

_PATRON = re.compile(
    r"\b(" + "|".join(re.escape(forma) for forma in _FORMAS_VOSEO) + r")\b",
    re.IGNORECASE,
)


def detectar_voseo(texto: str) -> bool:
    """True si el texto usa alguna conjugación de voseo conocida."""
    if not texto:
        return False
    return bool(_PATRON.search(texto))
