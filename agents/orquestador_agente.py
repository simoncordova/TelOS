"""Orquestador agéntico (rama gamificacion). Ver
C:\\Users\\Wendy\\.claude\\plans\\cosmic-zooming-tarjan.md para el diseño
completo y el porqué -- reemplaza el dispatch por `dict` de fase +
verificación por regex de la máquina de estados anterior por un `Agent`
de Strands real, con los 5 agentes de fase expuestos como tools
(`Agent.as_tool`), que decide con juicio semántico a cuál invocar.

Este módulo SOLO arma ese `Agent` (prompt + tools). El guardrail de
crisis, el Paso 0, la invocación real, la verificación de cierre contra
AgentCore Memory y el avance de fase siguen viviendo en
agents/orquestador.py::SesionTelos -- ese archivo no cambia de
responsabilidad, solo de cómo decide a qué fase invocar en cada turno.

Las descripciones de cada fase-tool son la única "regla de orden" que ve
el modelo -- el freno duro sigue siendo el mismo de siempre (código,
verificado contra AgentCore Memory después de cada turno en
SesionTelos._avanzar_fase_si_corresponde), esto es la capa de juicio, no
la de garantía."""

from strands import Agent

from agents._modelo import crear_modelo_orquestador

_DESCRIPCION_POR_FASE_ES = {
    1: (
        'Fase 1, Explorador: reúne material crudo sobre la persona '
        "(valores, momentos de flow, qué haría gratis, cómo quiere ser "
        "recordada, qué evita). Usar solo si la ficha todavía NO tiene "
        "ninguna fase cerrada."
    ),
    2: (
        "Fase 2, Sintetizador: refleja 2-3 propósitos candidatos a partir "
        "del material que dejó el Explorador. Usar solo si la fase 1 ya "
        "cerró y la fase 2 todavía no."
    ),
    3: (
        "Fase 3, Coach de Validación: pone a prueba el propósito elegido "
        "contra evidencia real y afina su redacción. Usar solo si la fase "
        "2 ya cerró y la fase 3 todavía no, o si el estado dice que hay "
        "un reingreso pendiente a esta fase desde Fase 5."
    ),
    4: (
        "Fase 4, Estratega de Sistemas: convierte el propósito validado "
        "en un sistema de 4 preguntas (acción, cuándo/dónde, métrica, "
        "obstáculo) y cierra la ficha completa. Usar solo si la fase 3 "
        "ya cerró y la fase 4 todavía no, o si el estado dice que hay un "
        "reingreso pendiente a esta fase desde Fase 5."
    ),
    5: (
        "Fase 5, Seguimiento: check-in breve sobre el propósito/sistema "
        "ya definidos. Usar solo si la ficha ya tiene la fase 4 cerrada "
        "(o ya está en fase 5) y no hay un reingreso pendiente a fase "
        "3 o 4."
    ),
}

_DESCRIPCION_POR_FASE_EN = {
    1: (
        "Phase 1, Explorer: gathers raw material about the person "
        "(values, flow moments, what they'd do for free, how they want "
        "to be remembered, what they avoid). Use only if the ficha has "
        "NO phase closed yet."
    ),
    2: (
        "Phase 2, Synthesizer: reflects back 2-3 candidate purposes from "
        "what the Explorer gathered. Use only if phase 1 already closed "
        "and phase 2 hasn't."
    ),
    3: (
        "Phase 3, Validation Coach: stress-tests the chosen purpose "
        "against real evidence and refines its wording. Use only if "
        "phase 2 already closed and phase 3 hasn't, or if the state "
        "below says there's a pending re-entry into this phase from "
        "Phase 5."
    ),
    4: (
        "Phase 4, Systems Strategist: turns the validated purpose into a "
        "4-question system (action, when/where, metric, obstacle) and "
        "closes the full intake. Use only if phase 3 already closed and "
        "phase 4 hasn't, or if the state below says there's a pending "
        "re-entry into this phase from Phase 5."
    ),
    5: (
        "Phase 5, Follow-up: a brief check-in on the already-defined "
        "purpose/system. Use only if the ficha already has phase 4 "
        "closed (or is already in phase 5) and there's no pending "
        "re-entry into phase 3 or 4."
    ),
}

_PROMPT_ORQUESTADOR_ES = """Sos el orquestador de Telos, un acompañante \
conversacional de propósito de vida y sistemas de hábito. NO hablás de \
contenido de propósito directamente -- tu único trabajo en cada turno es \
decidir a qué especialista invocar (una tool por cada uno, ver sus \
descripciones) y transmitirle a la persona, tal cual, el mensaje que ese \
especialista te devuelva. Nunca inventes ni resumas el contenido de \
coaching (preguntas, reflexiones, propósitos candidatos) -- eso rompe \
reglas de privacidad y tono que solo el especialista conoce.

El flujo tiene un orden fijo que no se puede saltear: Fase 1 (Explorador) \
→ Fase 2 (Sintetizador) → Fase 3 (Coach de Validación) → Fase 4 \
(Estratega de Sistemas) → Fase 5 (Seguimiento, recién en una conversación \
nueva). Desde Fase 5, la persona puede reingresar a Fase 3 o Fase 4 si el \
propósito ya no resuena o el sistema necesita rediseño -- eso lo decide \
el propio especialista de Fase 5 guardándolo en la ficha; vos lo vas a \
ver reflejado en el estado de abajo la próxima vez.

Estado real de esta persona ahora mismo (viene de la ficha en AgentCore \
Memory, no lo supongas vos):
{estado_ficha}

Hechos ya conocidos de conversaciones anteriores -- no hace falta \
volver a preguntarlos, y el especialista que invoques tampoco debería:
{insights_conocidos}

IMPORTANTE sobre las transiciones: nunca digas ni insinúes que la \
conversación va a pasar a otra persona, sistema o "agente" -- ni \
nombrándolo ("el Sintetizador", "el Validador") ni de forma genérica \
("alguien más te va a recibir", "ahora te van a atender"). Para la \
persona esto tiene que sentirse como una sola conversación fluida con \
una sola presencia todo el tiempo.

En cada turno, invocá EXACTAMENTE una tool -- la que corresponda al \
estado real de arriba, nunca la que "suene mejor" para lo que la persona \
acaba de escribir. Pasale a esa tool el mensaje de la persona tal cual \
(incluida cualquier nota interna del sistema entre corchetes al final, \
si la hay -- pasala sin resumir, es para el especialista, no para vos). \
Tu respuesta final tiene que ser exactamente el texto_para_persona que \
ese especialista te dio, sin agregarle ni sacarle nada."""

_PROMPT_ORQUESTADOR_EN = """You are Telos's orchestrator, a conversational \
life-purpose and habit-system companion. You do NOT talk about purpose \
content directly -- your only job each turn is to decide which \
specialist to invoke (one tool per specialist, see their descriptions) \
and relay to the person, verbatim, the message that specialist gives \
you. Never invent or summarize the coaching content (questions, \
reflections, candidate purposes) -- that breaks privacy and tone rules \
only the specialist knows.

The flow has a fixed order that can't be skipped: Phase 1 (Explorer) → \
Phase 2 (Synthesizer) → Phase 3 (Validation Coach) → Phase 4 (Systems \
Strategist) → Phase 5 (Follow-up, only in a new conversation). From \
Phase 5, the person can re-enter Phase 3 or Phase 4 if the purpose no \
longer resonates or the system needs a redesign -- that's decided by the \
Phase 5 specialist itself by saving it to the ficha; you'll see it \
reflected in the state below next time.

This person's real state right now (comes from the ficha in AgentCore \
Memory, don't assume it yourself):
{estado_ficha}

Facts already known from earlier conversations -- no need to ask again, \
and whichever specialist you invoke shouldn't either:
{insights_conocidos}

IMPORTANT about transitions: never say or imply that the conversation is \
moving to another person, system, or "agent" -- neither by name nor \
generically ("someone else will take it from here," "you'll be helped \
by someone else"). To the person this has to feel like one continuous \
conversation with a single presence the whole time.

Each turn, invoke EXACTLY one tool -- whichever matches the real state \
above, never whichever "sounds better" for what the person just wrote. \
Pass that tool the person's message as-is (including any internal \
system note in brackets at the end, if there is one -- pass it along \
unabridged, it's for the specialist, not for you). Your final response \
has to be exactly the texto_para_persona that specialist gave you, \
nothing added or removed."""


def crear_agente_orquestador(
    agentes_fase: dict[int, Agent],
    estado_ficha: str,
    insights: list[str],
    idioma: str = "es",
) -> Agent:
    descripciones = _DESCRIPCION_POR_FASE_EN if idioma == "en" else _DESCRIPCION_POR_FASE_ES
    tools = [
        agentes_fase[n].as_tool(name=f"fase_{n}", description=descripciones[n]) for n in sorted(agentes_fase)
    ]
    plantilla = _PROMPT_ORQUESTADOR_EN if idioma == "en" else _PROMPT_ORQUESTADOR_ES
    if insights:
        insights_texto = "\n".join(f"- {i}" for i in insights)
    else:
        insights_texto = "(none yet)" if idioma == "en" else "(ninguno todavía)"
    system_prompt = plantilla.format(estado_ficha=estado_ficha, insights_conocidos=insights_texto)
    return Agent(
        system_prompt=system_prompt,
        tools=tools,
        model=crear_modelo_orquestador(),
        callback_handler=None,
    )
