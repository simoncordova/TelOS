"""Guardrail de crisis. Ver docs/agente-proposito-de-vida-prompts.md sección 10.

Determinístico y sin llamada a modelo a propósito: la respuesta de
seguridad no puede depender de que el LLM decida generarla bien.
"""

import json
import os
import re
import unicodedata
from datetime import datetime, timezone

_RUTA_EVENTOS = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "eventos_crisis.jsonl")

# Curada de forma conservadora: mejor falso positivo que falso negativo.
# Patrones escritos sin tildes/ñ: tanto el texto de entrada como estos
# patrones se normalizan quitando acentos (incluida la ñ -> n) antes de
# comparar, para no depender de que la persona escriba con acentos.
_CATEGORIAS = {
    "ideacion_suicida": [
        r"\bquiero\s+(morir(me)?|matarme|suicidarme)\b",
        r"\bme\s+quiero\s+(morir|matar|suicidar)\b",
        r"\bpensando en (matarme|suicidarme|quitarme la vida)\b",
        r"\bsuicid\w*\b",
        r"\bquitarme la vida\b",
        r"\bacabar con (mi vida|todo)\b",
        r"\bno\s+(quiero|puedo)\s+(seguir\s+)?vivir\b",
    ],
    "plan_o_metodo": [
        r"\btengo (un plan|los medios) para (matarme|suicidarme|acabar con mi vida)\b",
    ],
    "autolesion": [
        r"\bautolesion\w*\b",
        r"\bcortarme\b",
        r"\bhacerme dano\b",
    ],
    "desesperanza_extrema": [
        r"\bya no (quiero|puedo) (seguir|mas|vivir)\b",
        r"\bno\s+(le\s+)?importo a nadie\b",
        r"\bseria mejor si no estuviera\b",
        r"\bnadie me (extranaria|va a extranar)\b",
        r"\bdesaparecer para siempre\b",
    ],
}

# English patterns. Se revisan SIEMPRE junto con los de español, sin
# importar qué idioma esté seleccionado en la UI — ver sección 0.5 del
# spec: el guardrail no puede depender de que la persona haya elegido el
# idioma "correcto" antes de escribir algo grave.
_CATEGORIES_EN = {
    "ideacion_suicida": [
        r"\bi\s+want\s+to\s+(die|kill myself)\b",
        r"\bthinking (about|of) (killing myself|suicide|ending my life)\b",
        r"\bsuicid\w*\b",
        r"\bend(ing)?\s+my\s+life\b",
        r"\bi\s+don'?t\s+want\s+to\s+(live|be alive)\b",
        r"\bi\s+can'?t\s+(go on|keep going)\b",
    ],
    "plan_o_metodo": [
        r"\bi\s+have\s+a\s+plan\s+to\s+(kill myself|end my life)\b",
    ],
    "autolesion": [
        r"\bself[\s-]?harm\w*\b",
        r"\bcutting\s+myself\b",
        r"\bhurt(ing)?\s+myself\b",
    ],
    "desesperanza_extrema": [
        r"\bi\s+don'?t\s+matter\s+to\s+anyone\b",
        r"\b(everyone|they)\s+would\s+be\s+better\s+off\s+without\s+me\b",
        r"\bno\s+one\s+would\s+(miss|notice) me\b",
        r"\bdisappear\s+forever\b",
    ],
}

_CATEGORIAS_COMPILADAS = {
    categoria: [re.compile(p, re.IGNORECASE) for p in patrones]
    for categoria, patrones in _CATEGORIAS.items()
}
_CATEGORIAS_COMPILADAS_EN = {
    categoria: [re.compile(p, re.IGNORECASE) for p in patrones]
    for categoria, patrones in _CATEGORIES_EN.items()
}

# Modismos benignos que de otro modo dispararían el guardrail por error
# (ej. "morirme de la risa" = reír mucho, "dying laughing" en inglés, no
# son señales de crisis).
_EXCEPCIONES = [
    re.compile(r"\bmorir(me)?\s+de\s+(la\s+)?risa\b", re.IGNORECASE),
    re.compile(r"\bmuero\s+de\s+(la\s+)?risa\b", re.IGNORECASE),
    re.compile(r"\b(die|died|dying)\s+(of\s+)?laugh(ing|ter)?\b", re.IGNORECASE),
]


def _normalizar(texto: str) -> str:
    texto = texto.lower().strip()
    texto = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in texto if not unicodedata.combining(c))


def detectar_señal_crisis(texto: str) -> dict:
    """Analiza un mensaje del usuario en busca de señales de crisis.

    Returns:
        {"disparado": bool, "categoria": str | None}
    """
    if not texto:
        return {"disparado": False, "categoria": None}

    texto_normalizado = _normalizar(texto)

    if any(excepcion.search(texto_normalizado) for excepcion in _EXCEPCIONES):
        return {"disparado": False, "categoria": None}

    # Se revisan español e inglés siempre, sin importar el idioma
    # seleccionado en la UI (sección 0.5 del spec).
    for categorias_compiladas in (_CATEGORIAS_COMPILADAS, _CATEGORIAS_COMPILADAS_EN):
        for categoria, patrones in categorias_compiladas.items():
            for patron in patrones:
                if patron.search(texto_normalizado):
                    return {"disparado": True, "categoria": categoria}

    return {"disparado": False, "categoria": None}


def registrar_evento_crisis(usuario_id: str, categoria: str) -> None:
    """Deja constancia de que el guardrail se activó, sin guardar el texto
    disparador (ver sección 9 del spec: privacidad y desacoplamiento de
    identidad — flag + timestamp, nada evaluativo ni el contenido crudo)."""
    os.makedirs(os.path.dirname(_RUTA_EVENTOS), exist_ok=True)
    evento = {
        "usuario_id": usuario_id,
        "categoria": categoria,
        "fecha": datetime.now(timezone.utc).isoformat(),
    }
    with open(_RUTA_EVENTOS, "a", encoding="utf-8") as f:
        f.write(json.dumps(evento, ensure_ascii=False) + "\n")


MENSAJE_CRISIS_ES = (
    "Lo que acabas de compartir suena a que estás pasando por un momento "
    "muy difícil. Quiero pausar esta conversación un momento porque esto "
    "importa más que el propósito o el sistema que estábamos armando.\n\n"
    "Si estás en México, puedes llamar a la Línea 106, gratuita las 24 "
    "horas. Si estás en España, puedes llamar al Teléfono de la Esperanza: "
    "717 003 717. Si estás en otro país, por favor contacta a los "
    "servicios de emergencia locales o a alguien de confianza ahora mismo.\n\n"
    "Cuando quieras, seguimos con la conversación — no hay ninguna prisa."
)

MENSAJE_CRISIS_EN = (
    "What you just shared sounds like you're going through a really "
    "difficult moment. I want to pause this conversation for a moment, "
    "because this matters more than the purpose or the system we were "
    "building.\n\n"
    "If you're in the US or Canada, you can call or text 988 (Suicide & "
    "Crisis Lifeline), available 24/7. If you're elsewhere, please "
    "contact your local emergency services or someone you trust right "
    "now.\n\n"
    "Whenever you're ready, we can pick this back up — there's no rush "
    "at all."
)


def mensaje_crisis(idioma: str) -> str:
    return MENSAJE_CRISIS_EN if idioma == "en" else MENSAJE_CRISIS_ES
