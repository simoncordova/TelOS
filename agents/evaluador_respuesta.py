"""Evaluador de respuesta -- Explorer v2 (revisión de arquitectura
externa, 12/09/2026). Agente nuevo, sin tools, con una sola
responsabilidad acotada: clasificar si la última respuesta de la persona
contestó la pregunta activa. No decide si la fase terminó, no decide si
hay "suficiente" información para sintetizar un propósito, no ve el
historial completo -- solo el eje/pregunta activos y la respuesta.

Reemplaza dejarle esa evaluación al mismo Explorador que además
conversa: ese diseño anterior fallaba en producción porque el modelo
exigía inconsistentemente "más profundidad" antes de marcar un eje
cubierto, y terminaba repitiendo la misma pregunta (ver
agents/explorador.py). Acá la pregunta es mucho más chica y objetiva
("¿esto responde lo que se preguntó?"), lo que la hace más confiable.
"""

from typing import Literal

from pydantic import BaseModel
from strands import Agent

from agents._modelo import crear_modelo_subagente

_PROMPT_ES = """Tu ÚNICA responsabilidad es clasificar si la última \
respuesta de la persona contestó la pregunta activa que se le hizo. No \
sos parte de la conversación, no generás preguntas, no evaluás si hay \
"suficiente" información para nada más que esta pregunta puntual.

Una respuesta breve, directa y relacionada con el tema CUENTA como \
"answered" -- no exijas profundidad, no exijas una respuesta elaborada, \
no la juzgues por su extensión. Ejemplo: pregunta "¿Cómo te gustaría \
ser recordado?", respuesta "Como un gran creador de aplicaciones" → \
answered, con evidence "Quiere ser recordado como creador de \
aplicaciones que tuvieron impacto." (una frase breve, no la respuesta \
textual).

Usá "partial" solo si la respuesta es relevante pero deja afuera algo \
concreto y necesario para tener una idea clara (no por falta de \
elaboración literaria). Usá "off_topic" si habla de otra cosa \
completamente distinta. Usá "refusal" si la persona explícitamente no \
quiere responder o dice "no sé" sin nada más. Usá "clarification" si la \
persona está pidiendo que le expliques o repitas la pregunta, no \
respondiéndola.

Pregunta activa: {pregunta}

Respuesta de la persona: {respuesta}"""

_PROMPT_EN = """Your ONLY responsibility is to classify whether the \
person's latest reply answered the active question they were asked. \
You're not part of the conversation, you don't generate questions, you \
don't evaluate whether there's "enough" information for anything beyond \
this one question.

A short, direct, on-topic reply COUNTS as "answered" -- don't require \
depth, don't require an elaborate answer, don't judge it by length. \
Example: question "How would you like to be remembered?", reply "As a \
great creator of apps" → answered, with evidence "Wants to be \
remembered as a creator of apps that had real impact." (a short \
paraphrase, not the literal reply).

Use "partial" only if the reply is relevant but leaves out something \
concrete and necessary for a clear picture (not because it's short). \
Use "off_topic" if it's about something entirely different. Use \
"refusal" if the person explicitly doesn't want to answer or says "I \
don't know" with nothing else. Use "clarification" if the person is \
asking you to explain or repeat the question, not answering it.

Active question: {pregunta}

Person's reply: {respuesta}"""


class EvaluacionRespuesta(BaseModel):
    """Contrato forzado (structured_output_model) de la evaluación --
    ver docstring del módulo. `evidence` es una frase breve propia, no
    la respuesta textual de la persona."""

    status: Literal["answered", "partial", "off_topic", "refusal", "clarification"]
    evidence: str | None = None
    confidence: Literal["high", "medium", "low"] = "medium"


def evaluar_respuesta(pregunta: str, respuesta_persona: str, idioma: str = "es") -> EvaluacionRespuesta | None:
    """Clasifica `respuesta_persona` contra `pregunta` con una llamada
    forzada (structured_output_model) -- garantiza la forma, no una tool
    que el modelo tenga que recordar llamar. Devuelve None si la llamada
    falla por una razón real (no un caso esperado); quien llama decide
    el fallback (ver agents/orquestador.py)."""
    plantilla = _PROMPT_EN if idioma == "en" else _PROMPT_ES
    agente = Agent(
        model=crear_modelo_subagente(),
        callback_handler=None,
    )
    prompt = plantilla.format(pregunta=pregunta, respuesta=respuesta_persona)
    try:
        resultado = agente(prompt, structured_output_model=EvaluacionRespuesta)
    except Exception:  # noqa: BLE001 -- fallo real forzando la forma, no un caso esperado
        return None
    return resultado.structured_output
