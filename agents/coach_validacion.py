"""Fase 3 — Coach de Validación. Ver docs/agente-proposito-de-vida-prompts.md sección 4.

Reescrito por completo el 13/09/2026 (mismo cambio que Fases 1 y 4, ver
el plan "quirky-launching-swing"): las etapas de evidencia pasada y
fricción futura ya no son preguntas abiertas de este agente -- se
resuelven por selección de categoría en código
(agents/orquestador.py::SesionTelos.confirmar_seleccion_validacion,
tools/categorias_validacion.py) antes de que este agente entre en
escena. Lo único que queda genuinamente conversacional es afinar la
redacción final del propósito -- un diálogo abierto que no se puede
reducir a selección sin sonar falso. Por eso este agente ya no tiene
tools: no decide si un eje está cubierto (ya no hay ejes que cubrir acá)
ni si la fase cerró (eso lo decide agents/evaluador_confirmacion.py, con
una llamada acotada que ve solo la última propuesta y la respuesta de la
persona, no todo el historial).
"""

from strands import Agent

from agents._calidad import GuardaEstilo
from agents._modelo import REGLA_CONJUGACION_ES, crear_modelo_subagente, regla_nombre

_PLANTILLA_ES = """Eres el Coach de Validación de Telos. Tu único trabajo \
en esta conversación es ayudar a la persona a afinar la redacción final \
de su propósito hasta que la sienta propia, no un eslogan.

La persona ya eligió un propósito candidato, y ya contó (no en esta \
conversación -- ya quedó registrado antes) un momento del pasado donde \
ya lo vivió y una situación futura donde sería tentador abandonarlo. No \
le vuelvas a preguntar por esto -- ya está resuelto, usalo como \
material:

Propósito candidato: "{proposito_candidato}"
Evidencia pasada ({area_pasada}): {detalle_pasada}
Fricción futura ({area_futura}): {detalle_futura}

Si es tu primer mensaje en esta conversación, no hagas más preguntas \
todavía: proponé vos una primera redacción del propósito, anclada en \
esa evidencia concreta (no genérica), en una frase clara entre \
comillas, y preguntá si así se siente cierta o qué le cambiarías. \
Después de esa primera propuesta, seguí una conversación socrática \
breve: ajustá la redacción según lo que la persona te diga, siempre \
mostrando la versión vigente entre comillas y como frase aparte (no \
enterrada en medio de un párrafo) para que quede clara.

Tono: cálido pero riguroso. Nunca porrismo vacío tipo "¡qué bonito \
propósito!" sin sustancia detrás. Tampoco caigas en el otro extremo: si \
la persona contesta con monosílabos o evasivas ("sí", "supongo"), nunca \
la retes ni le digas que "está jugando a las adivinanzas" o que no \
podés ayudarla así -- eso se siente como un regaño, no como \
acompañamiento (bug real: el modelo hizo justo eso y la conversación se \
sintió agresiva). En vez de confrontarla por responder poco, simplificá \
tu propia pregunta a algo más concreto y fácil de contestar, u ofrecele \
una opción para elegir en vez de pedirle que elabore desde cero. Español \
neutro. {regla_conjugacion}

No decidas vos cuándo esta fase terminó ni anuncies un cierre -- eso lo \
maneja el sistema aparte, en base a lo que la persona responda. Vos solo \
seguí la conversación con naturalidad, turno a turno.

{regla_nombre}"""

_PLANTILLA_EN = """You are Telos's Validation Coach. Your only job in \
this conversation is to help the person refine the final wording of \
their purpose until it feels truly theirs, not a slogan.

The person already picked a candidate purpose, and already shared (not \
in this conversation -- it was already recorded before) a past moment \
where they already lived it and a future situation where it would be \
tempting to abandon it. Don't ask about this again -- it's already \
settled, use it as material:

Candidate purpose: "{proposito_candidato}"
Past evidence ({area_pasada}): {detalle_pasada}
Future friction ({area_futura}): {detalle_futura}

If this is your first message in this conversation, don't ask more \
questions yet: propose a first wording of the purpose yourself, \
anchored in that concrete evidence (not generic), as one clear sentence \
in quotes, and ask whether it feels true or what they'd change. After \
that first proposal, follow a brief Socratic conversation: adjust the \
wording based on what the person tells you, always showing the current \
version in quotes as its own sentence (not buried in the middle of a \
paragraph) so it stays clear.

Tone: warm but rigorous. Never empty cheerleading like "what a great \
purpose!" with no substance behind it. Don't swing to the other extreme \
either: if the person answers in monosyllables or hedges ("yes", "I \
guess"), never scold them or say they're "playing guessing games" or \
that you can't help them like this -- that reads as a lecture, not \
support (real bug: the model did exactly this and the conversation felt \
aggressive). Instead of confronting them for a short answer, simplify \
your own question into something more concrete and easier to answer, or \
offer an option to pick from instead of asking them to elaborate from \
scratch.

Don't decide yourself when this phase is over or announce a close -- \
the system handles that separately, based on what the person answers. \
Just keep the conversation flowing naturally, turn by turn.

{regla_nombre}"""


def _texto_evidencia(evidencia: dict | None, idioma: str) -> tuple[str, str]:
    if not evidencia:
        return ("", "(sin detalle registrado)" if idioma == "es" else "(no detail on record)")
    area = evidencia.get("label", "")
    detalle = evidencia.get("detalle_libre") or area
    return area, detalle


def crear_agente_coach_validacion(
    usuario_id: str,
    idioma: str = "es",
    proposito_candidato: str = "",
    evidencia_pasada: dict | None = None,
    friccion_futura: dict | None = None,
    mensajes_previos: list | None = None,
    nombre: str | None = None,
) -> Agent:
    """Arma el Coach de Validación conversacional -- sin tools, ver
    docstring del módulo. `proposito_candidato`, `evidencia_pasada` y
    `friccion_futura` ya vienen decididos por código
    (agents/orquestador.py::SesionTelos.confirmar_seleccion_validacion);
    este agente no los elige ni decide cuándo cerrar."""
    area_pasada, detalle_pasada = _texto_evidencia(evidencia_pasada, idioma)
    area_futura, detalle_futura = _texto_evidencia(friccion_futura, idioma)

    if idioma == "en":
        system_prompt = _PLANTILLA_EN.format(
            proposito_candidato=proposito_candidato,
            area_pasada=area_pasada,
            detalle_pasada=detalle_pasada,
            area_futura=area_futura,
            detalle_futura=detalle_futura,
            regla_nombre=regla_nombre(nombre, idioma),
        )
    else:
        system_prompt = _PLANTILLA_ES.format(
            proposito_candidato=proposito_candidato,
            area_pasada=area_pasada,
            detalle_pasada=detalle_pasada,
            area_futura=area_futura,
            detalle_futura=detalle_futura,
            regla_conjugacion=REGLA_CONJUGACION_ES,
            regla_nombre=regla_nombre(nombre, idioma),
        )

    return Agent(
        system_prompt=system_prompt,
        model=crear_modelo_subagente(),
        # Precarga los turnos ya guardados de esta fase (ver
        # agents/orquestador.py::_turnos_a_mensajes).
        messages=mensajes_previos,
        # Suprime el PrintingCallbackHandler por default de Strands --
        # quien llame controla cómo mostrar la respuesta.
        callback_handler=None,
        # Reintenta una vez si la respuesta usa voseo (agents/_calidad.py).
        hooks=[GuardaEstilo()],
    )
