"""Evaluador de confirmación -- Fase 3 (Coach de Validación), etapa
"refinando". Agente nuevo, sin tools, con una sola responsabilidad
acotada: dado el propósito que se está afinando y la última respuesta de
la persona, decidir si ya lo confirmó como redacción final -- y si es
así, cuál es esa redacción (normalmente la propuesta vigente, salvo que
la persona la haya ajustado en su propia respuesta).

Es la única pieza de Fase 3 que sigue siendo conversación real y
necesita juicio del modelo (ver tools/categorias_validacion.py): las
etapas de evidencia pasada/fricción futura ya se resolvieron por
selección de categoría, código puro, sin nada que evaluar. El cierre de
ESTA etapa sí depende de interpretar una respuesta de texto libre ("sí,
así está bien", "me gusta más si dice...", "no, todavía no") -- pero
acotado a una sola pregunta bien definida ("¿esto es un sí?"), el mismo
patrón que ya probó ser confiable en el resto del proyecto
(structured_output_model, no un tool que el modelo tenga que acordarse
de llamar)."""

from pydantic import BaseModel
from strands import Agent

from agents._modelo import crear_modelo_subagente

_PROMPT_ES = """Una persona está afinando la redacción final de su \
propósito de vida junto a un coach. Tu ÚNICA responsabilidad es decidir \
si, con su última respuesta, la persona ya confirmó una redacción final \
-- no evalúes si el propósito "está bien" ni sugieras cambios vos.

Contá como confirmación cualquier variante de "sí, así está bien", "me \
gusta", "quedó perfecto", incluso una respuesta corta como "sí" o "dale" \
si el contexto deja claro que está aceptando la propuesta vigente. NO \
cuenta como confirmación si la persona pide un cambio, duda, hace una \
pregunta, o da una respuesta ambigua que no se puede leer como un sí \
claro -- en ese caso, `confirmado=false` y `redaccion_final=null`.

Si confirmó, `redaccion_final` es la propuesta vigente tal cual, EXCEPTO \
si en su misma respuesta la persona propuso un cambio de redacción que \
vos podés ver que fue aceptado en el mismo mensaje -- en ese caso, usá \
la versión ajustada.

Propuesta vigente: {propuesta}

Última respuesta de la persona: {respuesta}"""

_PROMPT_EN = """A person is refining the final wording of their life \
purpose together with a coach. Your ONLY responsibility is to decide \
whether, with their latest reply, the person just confirmed a final \
wording -- don't evaluate whether the purpose "is good" or suggest \
changes yourself.

Count as confirmation any variant of "yes, that's it", "I like it", \
"that's perfect", even a short reply like "yes" or "sounds good" if the \
context makes clear they're accepting the current proposal. Do NOT \
count it as confirmation if the person asks for a change, hesitates, \
asks a question, or gives an ambiguous reply that can't be read as a \
clear yes -- in that case, `confirmado=false` and `redaccion_final=null`.

If confirmed, `redaccion_final` is the current proposal as-is, UNLESS \
the person's own reply proposed a wording change that you can see was \
accepted in that same message -- in that case, use the adjusted version.

Current proposal: {propuesta}

Person's latest reply: {respuesta}"""


class EvaluacionConfirmacion(BaseModel):
    """Contrato forzado (structured_output_model) de la evaluación -- ver
    docstring del módulo."""

    confirmado: bool
    redaccion_final: str | None = None


def evaluar_confirmacion(propuesta_actual: str, respuesta_persona: str, idioma: str = "es") -> EvaluacionConfirmacion | None:
    """Clasifica `respuesta_persona` contra `propuesta_actual` con una
    llamada forzada (structured_output_model). Devuelve None si la
    llamada falla por una razón real (no un caso esperado); quien llama
    decide el fallback (ver agents/orquestador.py)."""
    plantilla = _PROMPT_EN if idioma == "en" else _PROMPT_ES
    agente = Agent(model=crear_modelo_subagente(), callback_handler=None)
    prompt = plantilla.format(propuesta=propuesta_actual, respuesta=respuesta_persona)
    try:
        resultado = agente(prompt, structured_output_model=EvaluacionConfirmacion)
    except Exception:  # noqa: BLE001 -- fallo real forzando la forma, no un caso esperado
        return None
    return resultado.structured_output
