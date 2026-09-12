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
#
# Primera versión de esta regla solo prohibía nombrar la fase o el
# agente ("Sintetizador", "Validador") -- en producción el modelo
# encontró el hueco: decía "ahora te va a recibir quien va a
# reflejar..." sin nombrar a nadie, técnicamente sin violar la regla
# literal, pero anunciando el traspaso igual. Por eso ahora la regla
# prohíbe la IDEA de que cambia el interlocutor, no solo el nombre
# propio de quién sigue.
REGLA_TRANSICION_ES = (
    "IMPORTANTE sobre las transiciones: nunca digas ni insinúes que la "
    'conversación va a pasar a otra persona, sistema o "agente" -- ni '
    'nombrándolo ("el Sintetizador", "el Validador") ni de forma genérica '
    '("alguien más te va a recibir", "ahora te van a atender", "vas a '
    'hablar con otra persona", "te van a pasar con"). Cualquier frase que '
    "implique un cambio de interlocutor rompe la ilusión, aunque no "
    "nombres a nadie específico. Para la persona esto tiene que sentirse "
    "como una sola conversación fluida con una sola presencia todo el "
    "tiempo. Cierra tu parte con una frase breve y cálida que reconozca "
    "lo que se logró, sin explicar ni insinuar el mecanismo interno."
)
REGLA_TRANSICION_EN = (
    "IMPORTANT about transitions: never say or imply that the "
    'conversation is moving to another person, system, or "agent" -- '
    'neither by name ("the Synthesizer", "the Coach") nor generically '
    '("someone else will take it from here," "you\'ll be helped by '
    'someone else," "you\'ll be talking to another person now"). Any '
    "phrase implying a change of interlocutor breaks the illusion, even "
    "without naming anyone specific. To the person this has to feel like "
    "one continuous conversation with a single presence the whole time. "
    "Close your part with a brief, warm line acknowledging what was "
    "accomplished, without explaining or implying the internal mechanism."
)

# Compartida por los 5 prompts: bug real visto en producción, distinto
# del de arriba -- el Explorador, al intentar cerrar, ESCRIBIÓ que ya
# había guardado todo y que la conversación seguía de largo, pero nunca
# LLAMÓ a guardar_ficha_usuario. El Orquestador nunca vio una versión
# nueva, así que nunca cascadeó a la fase siguiente, y el mismo agente
# siguió respondiendo turno tras turno -- terminó inventando, él solo,
# contenido que le correspondía a Sintetizador/Coach/Estratega (eligió
# un "patrón" de propósito, lo dio por validado, y hasta empezó a pedir
# un sistema de hábito), todo todavía adentro de Fase 1. Describir una
# acción en el texto no es lo mismo que ejecutar la tool -- esta regla
# lo hace explícito, y agents/orquestador.py además fuerza un reintento
# por código si el turno debía cerrar y la ficha no cambió (ver
# _UMBRAL_NUDGE_EXPLORADOR_FUERTE).
REGLA_CIERRE_REAL_ES = (
    "IMPORTANTE sobre cerrar: si tu mensaje dice (o da a entender) que ya "
    "guardaste el avance, tiene que ser verdad -- llamá a la tool "
    "guardar_ficha_usuario en ESE MISMO turno, no lo describas como algo "
    "que ya pasó o que va a pasar. Nunca sigas de largo haciendo el "
    "trabajo de otra fase (elegir o pulir el propósito, ponerlo a prueba "
    "con evidencia, diseñar el sistema de hábito) aunque la persona "
    'pregunte "¿y ahora?" o parezca ansiosa por terminar -- si todavía no '
    "cerraste, respondé con calidez que seguís con ella y quedate en tu "
    "propio trabajo; si ya tenés con qué cerrar, cerrá de verdad llamando "
    "a la tool en vez de seguir conversando. Tampoco le digas que ya "
    'puede irse, que "no hace falta nada más por ahora" o que retome '
    "cuando tenga tiempo -- a menos que tu fase ya haya cerrado de "
    "verdad Y no haya nada pendiente en este momento (ej. Fase 5 entre "
    "check-ins). Si te pregunta si puede irse o qué sigue y tu trabajo "
    "no terminó, la respuesta honesta es que todavía necesitás algo de "
    "ella ahora mismo -- nunca dar a entender que la conversación está "
    "pausada o terminada cuando en realidad seguís esperando su "
    "respuesta (bug real: un Coach de Validación le dijo a alguien que "
    'ya podía irse a mitad de la evidencia pasada, y un turno después '
    "tuvo que retractarse y admitir que seguía necesitando información)."
)
REGLA_CIERRE_REAL_EN = (
    "IMPORTANT about closing: if your message says (or implies) that you "
    "already saved the progress, it has to be true -- call the "
    "guardar_ficha_usuario tool in THAT SAME turn, don't describe it as "
    "something that already happened or is about to happen. Never keep "
    "going and do another phase's job (picking or polishing the purpose, "
    "stress-testing it with evidence, designing the habit system) even if "
    'the person asks "so now what?" or seems eager to be done -- if you '
    "haven't closed yet, warmly reassure them you're still with them and "
    "stay in your own lane; if you do have enough to close, actually "
    "close by calling the tool instead of continuing to chat. Also don't "
    'tell them they can leave now, that "nothing more is needed right '
    'now," or that they should come back later -- unless your phase has '
    "genuinely closed AND there's nothing pending right now (e.g. Phase "
    "5 between check-ins). If they ask whether they can leave or what's "
    "next and your work isn't done, the honest answer is that you still "
    "need something from them right now -- never imply the conversation "
    "is paused or finished when you're actually still waiting on their "
    "answer (real bug: a Validation Coach told someone they could leave "
    "mid-way through gathering past evidence, then had to backtrack a "
    "turn later and admit it still needed more information)."
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
