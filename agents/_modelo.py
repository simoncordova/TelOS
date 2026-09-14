"""Factory de modelo compartida por los 5 agentes de fase. No es un
agente en sí — es configuración común, para no repetirla en cada archivo
de agents/.

Un solo modelo (Haiku) para todo el sistema. Hubo, brevemente, un diseño
de dos niveles -- Sonnet para un Agent orquestador (rama gamificacion,
`agents/orquestador_agente.py`) que decidía a qué fase invocar y
componía la respuesta final, Haiku para los subagentes de contenido
pesado -- pero ese orquestador agéntico se revirtió a favor de ruteo
100% determinístico en código plano (ver
agents/orquestador.py::SesionTelos, sección "Sacado" en su docstring):
`self.fase_actual` ya resuelve la única pregunta que el orquestador
"decidía" con juicio semántico, así que esa invocación de Sonnet no
aportaba nada que el código no supiera ya, y sacarla de encima además
mejora la latencia (una invocación real menos por turno). `crear_modelo_orquestador`/
`MODEL_ID_ORQUESTADOR` quedaron sin ningún caller real tras ese revert
-- eliminados acá (14/09/2026) en vez de mantenerlos como código muerto.

El ID de modelo usa el prefijo de "global cross-region inference"
(`global.`), no el ID pelado del modelo: funciona desde cualquier región
del mundo (a diferencia de los `us.`/`eu.`/`au.`/`jp.` que solo enrutan
dentro de esa geografía) y sale ~10% más barato según la documentación
de Bedrock. ID verificado contra la documentación oficial de Bedrock
antes de escribirlo (model card de Claude Haiku 4.5), no asumido de
memoria -- Guardrails está soportado para Haiku 4.5 vía el endpoint
bedrock-runtime/Converse (que es el que usa Strands), confirmado en la
misma documentación.
"""

import os

from pydantic import BaseModel
from strands import tool
from strands.models import BedrockModel

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
# el recurso desplegado solo para probar el flujo de agentes.
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


def crear_modelo_subagente() -> BedrockModel:
    """Haiku -- ejecuta la tarea puntual de una fase (sintetizar,
    validar, hacer seguimiento, sugerir una categoría) o una llamada
    acotada de una sola invocación (agents/orquestador.py::SesionTelos.
    _sintetizar_selecciones, _extraer_nombre). Único modelo del sistema
    -- ver docstring del módulo. Usado por los factories de
    agents/{sintetizador,coach_validacion,seguimiento,
    asistente_categorias,evaluador_confirmacion}.py y directo por
    agents/orquestador.py para sus propias llamadas acotadas -- Fases 1
    y 4 ya no tienen agente conversacional propio, ver docstring de
    agents/orquestador.py."""
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
# estructurado que cada subagente le deja a SesionTelos
# (agents/orquestador.py -- código plano, no un Agent orquestador; ese
# diseño se probó y se revirtió, ver docstring de agents/_modelo.py).
# Reemplaza dos reglas de texto libre que
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
    de UX que motivó esto: formularios para decisiones cerradas).

    `contenedor` es una lista mutable que le pasa
    agents/orquestador.py: la limpia antes de cada invocación al agente y
    lee lo que haya quedado después de que el modelo responda -- así la
    sesión se entera de las opciones ofrecidas sin necesitar interceptar
    la tool call con un hook de Strands, con el mismo patrón de closure
    sobre una variable de sesión que ya usa cada agents/*.py para
    guardar_ficha_usuario sobre usuario_id.

    Fase 2 (el ejemplo original que motivó esta tool) dejó de usarla --
    ver crear_tool_presentar_candidatos_proposito más abajo, con el
    mismo patrón de closure pero devolviendo datos estructurados en vez
    de solo la frase corta, para que la interfaz arme tarjetas
    editoriales en vez de una lista de botones sin contexto. Esta queda
    disponible para cualquier fase futura que solo necesite botones
    simples, sin explicación ni ejemplo por opción."""

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


class CandidatoProposito(BaseModel):
    """Un propósito candidato que el Sintetizador (Fase 2) le refleja a
    la persona -- ver crear_tool_presentar_candidatos_proposito. Los
    tres campos son obligatorios: sin "explicacion" ni "ejemplo" la
    tarjeta editorial del frontend queda vacía, y sin "frase" no hay
    nada para que la persona elija."""

    frase: str
    explicacion: str
    ejemplo: str


def crear_tool_presentar_candidatos_proposito(contenedor: list):
    """Fabrica un tool `presentar_candidatos_proposito` para el
    Sintetizador (Fase 2, agents/sintetizador.py) -- mismo patrón de
    closure que crear_tool_presentar_opciones (ver docstring de esa),
    pero entregando cada candidato como datos estructurados (frase +
    explicación + ejemplo) en vez de solo la frase corta.

    Motivo del cambio (14/09/2026, pedido explícito del dueño del
    producto): la interfaz mostraba los 2-3 candidatos como texto libre
    de prosa dentro de la burbuja de chat -- "el diseño de sintetizador
    antiguo", inconsistente con las tarjetas editoriales que ya usan
    ArbolSelector/ValidacionSelector/SistemaSelector para presentar
    contenido central (propósito, sistema). Con esta tool, el modelo
    entrega los tres campos de cada candidato por separado; el frontend
    arma las tarjetas directo desde esos datos, sin parsear el texto
    libre del mensaje (que ahora es solo un marco breve alrededor de las
    tarjetas, ver el prompt de agents/sintetizador.py)."""

    @tool
    def presentar_candidatos_proposito(candidatos: list[CandidatoProposito]) -> str:
        """Llamar SIEMPRE, en el mismo turno en que presentás los \
candidatos por primera vez -- ver instrucción completa en el prompt. \
`candidatos` es una lista de 2 o 3 elementos, cada uno con "frase" \
(el propósito corto y concreto), "explicacion" (por qué se ajusta a \
esta persona, anclado en algo puntual que dijo) y "ejemplo" (una \
escena o analogía real de su ficha que muestre cómo se vería en la \
práctica). Mismo orden en que los mencionás en tu mensaje."""
        contenedor.clear()
        contenedor.extend(c.model_dump() for c in candidatos)
        return "Candidatos mostrados a la persona como tarjetas."

    return presentar_candidatos_proposito
