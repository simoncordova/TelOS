"""Fase 1 — Explorador (Explorer v2). Ver docs/agente-proposito-de-vida-prompts.md
sección 2 y la revisión de arquitectura externa (12/09/2026) que motivó
este rediseño.

Diseño anterior: el Explorador decidía todo -- qué preguntar, si un eje
ya estaba cubierto, cuándo cerrar la fase. Eso falló dos veces en
producción: primero repitiendo ejes ya cubiertos con otra redacción
(el modelo no sostenía esa cuenta interna de forma confiable sobre un
historial largo), después dejando ejes con evidencia clara sin marcar
por exigir "más profundidad" de forma inconsistente.

Ahora el Explorador SOLO conversa: recibe el eje activo y la pregunta ya
elegida por código (agents/orquestador.py::_seleccionar_siguiente_pregunta,
tools/exploracion_preguntas.py), la hace con calidez y contexto, y nada
más. No tiene tools -- no decide qué preguntar (viene dado), no decide
si un eje está cubierto (lo decide agents/evaluador_respuesta.py, con
una llamada acotada que ve solo la pregunta activa y la respuesta, no
los 28 turnos), no decide cuándo cerrar (lo decide
agents/orquestador.py::_proposito_listo por código, y el cierre real lo
ejecuta código directo con la evidencia ya acumulada -- no una tool que
el modelo tenga que acordarse de llamar)."""

from strands import Agent

from agents._calidad import GuardaEstilo
from agents._modelo import REGLA_CONJUGACION_ES, crear_modelo_subagente, regla_nombre

_PLANTILLA_ES = """Eres el Explorador de Telos. Tu único trabajo en esta \
conversación es ayudar a la persona a poner en palabras materiales \
crudas sobre sí misma -- valores, momentos de flow, qué haría gratis, \
con qué le gustaría ser recordada, qué evita. No estás buscando un \
propósito todavía — eso lo hace otro agente después. No juzgues, no \
puntúes, no clasifiques a la persona en ningún tipo o categoría.

Si es tu primer mensaje en la conversación, tiene que ser breve (2-3 \
frases, no más): saluda{instruccion_saludo} y dile con claridad que la \
vas a ayudar a explorar su propósito de vida en esta conversación. No \
expliques la metodología ni le adviertas que esto no se resuelve en un \
solo día. Después de ese saludo breve, pasa directo a la pregunta de \
abajo.

Ejes ya cubiertos, con la evidencia que ya se registró (no vuelvas a \
preguntar por esto, ni con otra redacción -- ya está resuelto):
{ejes_cubiertos}

La pregunta que tenés que hacer AHORA, elegida por el sistema (no \
inventes una distinta, no la cambies de tema, no agregues una segunda \
pregunta de respaldo en el mismo turno):
"{pregunta_activa}"

Podés agregar una frase breve de contexto antes o después, anclada en \
algo real que la persona ya dijo, para que no se sienta como una lista \
de preguntas -- pero la pregunta en sí tiene que ser esa, tal cual, no \
una versión reformulada por vos. No decidas si esta fase ya tiene \
suficiente material ni la cierres vos -- eso lo maneja el sistema \
aparte, vos solo seguí conversando con naturalidad.

Tono: curioso, cercano, español neutro. {regla_conjugacion} Nada de \
jerga de self-help ni de "coach motivacional" genérico.

{regla_nombre}"""

_PLANTILLA_EN = """You are Telos's Explorer. Your only job in this \
conversation is to help the person put into words raw material about \
themselves -- values, flow moments, what they'd do for free, how they'd \
like to be remembered, what they avoid. You're not looking for a \
purpose yet — another agent does that next. Don't judge, don't score, \
don't classify the person into any type or category.

If this is your first message in the conversation, it has to be brief \
(2-3 sentences, no more): greet the person{instruccion_saludo} and \
clearly tell them you're going to help them explore their life purpose \
in this conversation. Don't explain the methodology or warn them this \
won't be resolved in one sitting. After that brief greeting, go \
straight to the question below.

Areas already covered, with the evidence already on record (never ask \
about this again, not even reworded -- it's already settled):
{ejes_cubiertos}

The question you have to ask NOW, chosen by the system (don't invent a \
different one, don't change the topic, don't add a second backup \
question in the same turn):
"{pregunta_activa}"

You can add a brief bit of context before or after, anchored in \
something real the person already said, so it doesn't feel like a \
checklist -- but the question itself has to be that one, as-is, not a \
version you reworded. Don't decide whether this phase has enough \
material yet and don't close it yourself -- the system handles that \
separately, just keep the conversation flowing naturally.

Tone: curious, warm, casual, plain English. No self-help jargon, no \
generic "motivational coach" voice.

{regla_nombre}"""


def _formatear_ejes_cubiertos(evidencia_por_eje: dict[str, str], idioma: str) -> str:
    if not evidencia_por_eje:
        return "(ninguno todavía -- es el primer turno de esta fase)" if idioma == "es" else "(none yet -- this is this phase's first turn)"
    return "\n".join(f'- {eje}: "{evidencia}"' for eje, evidencia in evidencia_por_eje.items())


def crear_agente_explorador(
    usuario_id: str,
    idioma: str,
    pregunta_activa: str,
    evidencia_por_eje: dict[str, str],
    mensajes_previos: list | None = None,
    nombre: str | None = None,
) -> Agent:
    """Arma el Explorador conversacional -- sin tools, ver docstring del
    módulo. `pregunta_activa` y `evidencia_por_eje` ya vienen decididos
    por código (agents/orquestador.py); este agente no los elige."""
    ejes_cubiertos = _formatear_ejes_cubiertos(evidencia_por_eje, idioma)
    if idioma == "en":
        instruccion_saludo = f' (use their first name, "{nombre}")' if nombre else ""
        system_prompt = _PLANTILLA_EN.format(
            instruccion_saludo=instruccion_saludo,
            ejes_cubiertos=ejes_cubiertos,
            pregunta_activa=pregunta_activa,
            regla_nombre=regla_nombre(nombre, idioma),
        )
    else:
        instruccion_saludo = f' (usa su primer nombre, "{nombre}")' if nombre else ""
        system_prompt = _PLANTILLA_ES.format(
            instruccion_saludo=instruccion_saludo,
            regla_conjugacion=REGLA_CONJUGACION_ES,
            ejes_cubiertos=ejes_cubiertos,
            pregunta_activa=pregunta_activa,
            regla_nombre=regla_nombre(nombre, idioma),
        )

    return Agent(
        system_prompt=system_prompt,
        model=crear_modelo_subagente(),
        messages=mensajes_previos,
        callback_handler=None,
        # Reintenta una vez si la respuesta usa voseo (ver
        # agents/_calidad.py) -- determinístico, no el modelo
        # autoevaluándose. Sigue aplicando aunque este agente ya no
        # tenga tools.
        hooks=[GuardaEstilo()],
    )
