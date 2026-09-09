"""Guardrail de crisis. Ver docs/agente-proposito-de-vida-prompts.md sección 10.

Determinístico y sin llamada a modelo a propósito: la respuesta de
seguridad no puede depender de que el LLM decida generarla bien.
"""

import re
import unicodedata

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

_CATEGORIAS_COMPILADAS = {
    categoria: [re.compile(p, re.IGNORECASE) for p in patrones]
    for categoria, patrones in _CATEGORIAS.items()
}

# Modismos benignos que de otro modo dispararían el guardrail por error
# (ej. "morirme de la risa" = reír mucho, no una señal de crisis).
_EXCEPCIONES = [
    re.compile(r"\bmorir(me)?\s+de\s+(la\s+)?risa\b", re.IGNORECASE),
    re.compile(r"\bmuero\s+de\s+(la\s+)?risa\b", re.IGNORECASE),
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

    for categoria, patrones in _CATEGORIAS_COMPILADAS.items():
        for patron in patrones:
            if patron.search(texto_normalizado):
                return {"disparado": True, "categoria": categoria}

    return {"disparado": False, "categoria": None}


MENSAJE_CRISIS = (
    "Lo que acabas de compartir suena a que estás pasando por un momento "
    "muy difícil. Quiero pausar esta conversación un momento porque esto "
    "importa más que el propósito o el sistema que estábamos armando.\n\n"
    "Si estás en México, puedes llamar a la Línea 106, gratuita las 24 "
    "horas. Si estás en España, puedes llamar al Teléfono de la Esperanza: "
    "717 003 717. Si estás en otro país, por favor contacta a los "
    "servicios de emergencia locales o a alguien de confianza ahora mismo.\n\n"
    "Cuando quieras, seguimos con la conversación — no hay ninguna prisa."
)
