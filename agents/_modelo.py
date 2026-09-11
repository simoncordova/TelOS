"""Factory de modelo compartido por los 5 agentes de fase. No es un agente
en sí — es configuración común a los 5, para no repetirla en cada
archivo de agents/.

Usa el ID de "global cross-region inference" (prefijo `global.`), no el
ID pelado del modelo: Claude Sonnet 4.5 no admite invocación on-demand
"In-Region" en la mayoría de las regiones (confirmado con un
ValidationException real en us-east-1: "Invocation of model ID ... with
on-demand throughput isn't supported"). El ID `global.` funciona desde
cualquier región del mundo (a diferencia de los `us.`/`eu.`/`au.`/`jp.`
que solo enrutan dentro de esa geografía) y además sale ~10% más barato
según la documentación de Bedrock.
"""

import os

from strands import tool
from strands.models import BedrockModel

MODEL_ID = os.environ.get("TELOS_MODEL_ID", "global.anthropic.claude-sonnet-4-5-20250929-v1:0")
REGION = os.environ.get("TELOS_AWS_REGION", "us-east-1")


def crear_modelo() -> BedrockModel:
    return BedrockModel(model_id=MODEL_ID, region_name=REGION)


# Compartida por los 5 prompts en español (antes estaba copiada casi
# textual en cada uno, un archivo por fix cuando se detectó el bug de
# voseo). Un solo lugar para editarla si hace falta ajustarla de nuevo.
# El chequeo real (que efectivamente se cumpla) es agents/_calidad.py —
# esto es la instrucción, no la garantía.
REGLA_CONJUGACION_ES = (
    'IMPORTANTE sobre la conjugación: usa siempre las formas de "tú" '
    '(tienes, quieres, eres, puedes, sientes) — nunca las de "vos" '
    '(tenés, querés, sos, podés, sentís). El voseo se nota en cómo se '
    'conjuga el verbo, no solo en si aparece la palabra "vos" escrita, '
    'así que evita esas conjugaciones aunque nunca escribas el pronombre.'
)

# Compartida por los 5 prompts (ES y EN): la app ya encadena el cierre de
# una fase con la apertura de la siguiente en el mismo turno (ver
# agents/orquestador.py) -- si el agente encima ANUNCIA el mecanismo
# ("te voy a pasar con el siguiente agente", "ahora te recibe el
# Validador", "cambio de rol"), la persona ve la costura interna del
# sistema en vez de vivirlo como una sola conversación. La transición
# tiene que sentirse invisible: cerrar con calidez y, si corresponde,
# seguir de largo -- nunca nombrar "agente", "fase" ni "otro sistema".
REGLA_TRANSICION_ES = (
    "IMPORTANTE sobre las transiciones: nunca anuncies que la conversación "
    "va a pasar a \"otro agente\", que \"cambias de rol\", ni menciones el "
    "nombre de una fase o de otro agente (Explorador, Sintetizador, Coach, "
    "Estratega, Seguimiento). Para la persona esto tiene que sentirse como "
    "una sola conversación fluida con un solo interlocutor, nunca como un "
    "traspaso entre sistemas. Cierra tu parte con una frase breve y cálida "
    "que reconozca lo que se logró, sin explicar el mecanismo interno."
)
REGLA_TRANSICION_EN = (
    "IMPORTANT about transitions: never announce that the conversation is "
    "handing off to \"another agent,\" never say you're \"switching roles,\" "
    "and never name a phase or another agent (Explorer, Synthesizer, Coach, "
    "Strategist, Follow-up). To the person this has to feel like one "
    "continuous conversation with a single presence, never a handoff "
    "between systems. Close your part with a brief, warm line "
    "acknowledging what was accomplished, without explaining the internal "
    "mechanism."
)

# Compartida por los 5 prompts: el nombre de pila se captura una sola vez
# antes de Fase 1 (agents/orquestador.py, código, no un tool del modelo)
# y se inyecta acá para que cada agente pueda usarlo. "{nombre}" puede
# venir vacío (retrocompatibilidad con fichas viejas sin nombre guardado
# o con TELOS_REQUIRE_LOGIN=0 en desarrollo) -- cada prompt de fase debe
# poder abrir igual de bien sin un nombre para dirigirse a la persona.
def regla_nombre(nombre: str | None, idioma: str = "es") -> str:
    if not nombre:
        return ""
    if idioma == "en":
        return (
            f'The person\'s first name is "{nombre}". Address them by it '
            "naturally a few times over the conversation (not in every "
            "single message) -- it should feel personal, not like a mail "
            "merge."
        )
    return (
        f'El primer nombre de la persona es "{nombre}". Dirígete a ella por '
        "ese nombre con naturalidad algunas veces a lo largo de la "
        "conversación (no en cada mensaje) -- tiene que sentirse personal, "
        "no como un mail merge."
    )


def crear_tool_presentar_opciones(contenedor: list):
    """Fabrica un tool `presentar_opciones` que un agente de fase puede
    llamar para que la interfaz muestre botones de elección en vez de
    obligar a la persona a escribir la respuesta (ver punto 6 del pedido
    de UX que motivó esto: formularios para decisiones cerradas, como el
    candidato de propósito que elige en Fase 2).

    `contenedor` es una lista mutable que le pasa
    agents/orquestador.py: la limpia antes de cada invocación al agente y
    lee lo que haya quedado después de que el modelo responda -- así la
    sesión se entera de las opciones ofrecidas sin necesitar interceptar
    la tool call con un hook de Strands, con el mismo patrón de closure
    sobre una variable de sesión que ya usa cada agents/*.py para
    guardar_ficha_usuario sobre usuario_id."""

    @tool
    def presentar_opciones(opciones: list[str]) -> str:
        """Además del mensaje de texto que ya estás escribiendo, mostrá \
estas opciones como botones para que la persona elija sin tener que \
escribir. Pasale las frases cortas, en el mismo orden en que las \
presentaste en el mensaje."""
        contenedor.clear()
        contenedor.extend(opciones)
        return "Opciones mostradas a la persona como botones."

    return presentar_opciones
