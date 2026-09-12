"""Factory de modelo compartida por el orquestador y los 5 agentes de fase.
No es un agente en sí — es configuración común, para no repetirla en cada
archivo de agents/.

Dos modelos distintos, a pedido explícito del dueño del producto (rama
gamificacion, migración al orquestador agéntico -- ver
C:\\Users\\Wendy\\.claude\\plans\\cosmic-zooming-tarjan.md): el orquestador
(agents/orquestador_agente.py) decide a qué fase invocar y compone la
respuesta final -- poco volumen de texto, pero es el único punto de
contacto real con la entrada/salida de la persona, así que usa Sonnet.
Cada agente de fase (agents/explorador.py y hermanos) hace el trabajo de
contenido pesado (explorar, sintetizar, validar) pero con una tarea acotada
y un prompt más liviano ahora que las reglas de flujo/transición viven solo
en el orquestador -- Haiku alcanza y sale bastante más barato/rápido,
compensando en parte que ahora cada turno paga dos invocaciones reales en
vez de una.

Ambos usan el ID de "global cross-region inference" (prefijo `global.`),
no el ID pelado del modelo: Claude Sonnet 4.5 no admite invocación
on-demand "In-Region" en la mayoría de las regiones (confirmado con un
ValidationException real en us-east-1: "Invocation of model ID ... with
on-demand throughput isn't supported"). El ID `global.` funciona desde
cualquier región del mundo (a diferencia de los `us.`/`eu.`/`au.`/`jp.`
que solo enrutan dentro de esa geografía) y además sale ~10% más barato
según la documentación de Bedrock. IDs verificados contra la
documentación oficial de Bedrock antes de escribirlos (model card de
Claude Haiku 4.5), no asumidos de memoria -- Guardrails está soportado
para Haiku 4.5 vía el endpoint bedrock-runtime/Converse (que es el que usa
Strands), confirmado en la misma documentación.
"""

import os

from strands import tool
from strands.models import BedrockModel

MODEL_ID_ORQUESTADOR = os.environ.get(
    "TELOS_MODEL_ID_ORQUESTADOR", "global.anthropic.claude-sonnet-4-5-20250929-v1:0"
)
MODEL_ID_SUBAGENTE = os.environ.get(
    "TELOS_MODEL_ID_SUBAGENTE", "global.anthropic.claude-haiku-4-5-20251001-v1:0"
)
REGION = os.environ.get("TELOS_AWS_REGION", "us-east-1")

# Guardrail de Bedrock (infra/stacks/telos_stack.py::GuardrailTelos) --
# denied topics (pedidos fuera del propósito de la app, intentos de
# jailbreak, consejo profesional regulado) + filtros de contenido dañino
# aplicados directo por Bedrock a cada invocación, antes/después del
# modelo. Complementa, no reemplaza, al guardrail de crisis
# (tools/crisis.py): ese sigue siendo el único mecanismo para señales de
# crisis (corre en código, antes de invocar a Bedrock, sin importar este
# guardrail) -- ver docs/agente-proposito-de-vida-prompts.md sección 10.
# Vacío en desarrollo local (sin GUARDRAIL_ID seteado) para no requerir
# el recurso desplegado solo para probar el flujo de agentes. Se aplica en
# los dos modelos (orquestador Y subagentes) -- el orquestador es el punto
# de contacto real con la persona, pero el texto de un subagente puede
# terminar mostrándose tal cual (ver informar_al_orquestador), así que no
# tiene sentido dejarlo desprotegido.
GUARDRAIL_ID = os.environ.get("GUARDRAIL_ID", "")
GUARDRAIL_VERSION = os.environ.get("GUARDRAIL_VERSION", "")


def _crear_modelo(model_id: str) -> BedrockModel:
    if GUARDRAIL_ID:
        return BedrockModel(
            model_id=model_id,
            region_name=REGION,
            guardrail_id=GUARDRAIL_ID,
            guardrail_version=GUARDRAIL_VERSION,
            # "enabled" (no "enabled_full"): alcanza con saber SI algo se
            # bloqueó, no hace falta el detalle completo de qué texto
            # exacto disparó cada filtro para esta app.
            guardrail_trace="enabled",
        )
    return BedrockModel(model_id=model_id, region_name=REGION)


def crear_modelo_orquestador() -> BedrockModel:
    """Sonnet -- decide a qué fase invocar y compone la respuesta final
    que ve la persona (agents/orquestador_agente.py)."""
    return _crear_modelo(MODEL_ID_ORQUESTADOR)


def crear_modelo_subagente() -> BedrockModel:
    """Haiku -- ejecuta la tarea puntual de una fase (explorar, sintetizar,
    validar, diseñar el sistema, hacer seguimiento). Usado por los 5
    factories de agents/{explorador,sintetizador,coach_validacion,
    estratega_sistemas,seguimiento}.py."""
    return _crear_modelo(MODEL_ID_SUBAGENTE)


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

# Compartida por los 5 prompts de fase (ES y EN): instrucción del informe
# estructurado al orquestador agéntico (rama gamificacion, ver
# agents/orquestador_agente.py). Reemplaza dos reglas de texto libre que
# vivían acá antes -- REGLA_TRANSICION_* (nunca anunciar que la
# conversación "pasa" a otro agente/fase) y REGLA_CIERRE_REAL_* (si decís
# que guardaste, tiene que ser verdad, no una descripción de algo que
# todavía no pasó) -- ambas motivadas por bugs reales en producción
# (el modelo anunciando el traspaso con otras palabras sin nombrar a
# nadie; un agente diciendo que ya había guardado y cerrado sin haber
# llamado a la tool). "Decir que cerró sin haber cerrado" deja de ser un
# problema de texto libre que un regex tiene que cazar -- es un booleano
# (`cerrado`) que agents/orquestador.py verifica contra AgentCore Memory
# antes de confiarle nada.
#
# OJO, corregido después de un bug real visto en producción: a diferencia
# de lo que este comentario decía antes, agents/orquestador.py NUNCA
# reescribe ni resume `texto_para_persona` -- lo muestra a la persona tal
# cual salió de ESTE subagente (ver SesionTelos._invocar_una_vez, que
# explícitamente ignora el texto propio del Agent orquestador). Eso
# significa que la regla de "no anunciar el traspaso" y, más grave, la de
# "hablale a la persona en segunda persona, no narres sobre ella en
# tercera" dependen 100% de que ESTA instrucción sea explícita -- no hay
# ningún paso posterior que reescriba o corrija el tono. Bug real: con
# Haiku, el nombre mismo de la tool ("informar AL ORQUESTADOR") llevó al
# modelo a redactar texto_para_persona como un reporte de caso en tercera
# persona ("Sam eligió su propósito... está anclado en...") en vez de
# hablarle directo a Sam -- de ahí la línea explícita de segunda persona
# de abajo, que no estaba antes.
#
# Antes vivía copiada casi textual en cada uno de los 5 archivos de fase
# (mismo anti-patrón que REGLA_CONJUGACION_ES ya evitaba) -- centralizada
# acá para que un ajuste futuro (ej. agregar un campo al informe) se
# edite en un solo lugar.
INSTRUCCION_INFORME_ES = (
    "Al final de CADA turno, sin excepción, llamá a la tool "
    "informar_al_orquestador como último paso: texto_para_persona es lo "
    "que el orquestador le va a mostrar a la persona tal cual, sin "
    "resumir ni reescribir -- tiene que ser el mensaje completo que "
    "querés que vea. IMPORTANTE: texto_para_persona tiene que estar "
    "escrito hablándole directamente a ella, en segunda persona (\"tú\"), "
    "exactamente como si fuera el mensaje de chat que ya venías "
    "redactando -- nunca narrado en tercera persona sobre ella ni como "
    "un resumen de caso para el orquestador (el orquestador no lo lee ni "
    "lo reformula, se lo muestra a la persona tal cual salió de vos). "
    "Nombrar a la persona por su nombre en tercera persona (\"Ana eligió "
    "su propósito...\") en vez de hablarle a ella (\"elegiste tu "
    "propósito...\") es un error grave acá. IMPORTANTE sobre las "
    "transiciones: nunca digas ni insinúes, en texto_para_persona, que la "
    "conversación va a pasar a otra persona, sistema o \"agente\" -- ni "
    "nombrándolo (\"el Sintetizador\", \"el Validador\") ni de forma "
    "genérica (\"alguien más te va a recibir\", \"ahora te va a ayudar "
    "otro agente\", \"te paso la posta\"). Para la persona esto tiene que "
    "sentirse como una sola conversación fluida con una sola presencia "
    "todo el tiempo -- cerrá tu parte con una frase breve y cálida, no "
    "narrando el mecanismo interno. cerrado=True solo si en ESTE "
    "turno llamaste de verdad a guardar_ficha_usuario; si no, "
    "cerrado=False. dato_nuevo es "
    "un hecho puntual que valga la pena recordar en fases futuras (o "
    "None si no hay nada nuevo)."
)
INSTRUCCION_INFORME_EN = (
    "At the end of EVERY turn, no exception, call the "
    "informar_al_orquestador tool as your last step: texto_para_persona "
    "is what the orchestrator will show the person verbatim, without "
    "summarizing or rewriting it -- it has to be the full message you "
    "want them to see. IMPORTANT: texto_para_persona has to be written "
    "speaking directly TO them, in second person (\"you\"), exactly like "
    "the chat message you were already writing -- never narrated in "
    "third person about them, and never as a case-report summary for "
    "the orchestrator (the orchestrator doesn't read or rephrase it, it "
    "shows it to the person exactly as you wrote it). Referring to the "
    "person by name in third person (\"Sam chose their purpose...\") "
    "instead of addressing them directly (\"you chose your "
    "purpose...\") is a serious error here. IMPORTANT about transitions: "
    "never say or imply, in texto_para_persona, that the conversation is "
    "moving to another person, system, or \"agent\" -- neither by name "
    "(\"the Synthesizer\", \"the Validator\") nor generically (\"someone "
    "else will take it from here\", \"another agent is going to help you "
    "with this\", \"I'll hand this off to...\"). To the person this has "
    "to feel like one continuous conversation with a single presence the "
    "whole time -- close your part with a brief, warm line instead of "
    "narrating the mechanism. cerrado=True only if you "
    "actually called guardar_ficha_usuario in THIS turn; otherwise "
    "cerrado=False. dato_nuevo is one concrete fact worth remembering in "
    "future phases (or None if there's nothing new)."
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
