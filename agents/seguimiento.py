"""Fase 5 — Seguimiento. Ver docs/agente-proposito-de-vida-prompts.md sección 6.

Se dispara al abrir una conversación nueva cuando ya existe una ficha
completa (fase >= 4). La Vista de resumen y la rotación del tipo de
check-in se calculan en código, no se dejan a criterio del modelo.

RAMA `gamificacion`: decisión revertida a pedido explícito del dueño del
producto (ver docs/agente-proposito-de-vida-prompts.md sección 8) --
rachas, progreso y lenguaje de gamificación ya NO están prohibidos. Se
mantiene el mismo criterio de siempre eso sí: lo que se garantiza (la
racha, acá) se calcula en código, no se deja a criterio del modelo --
`calcular_racha` cuenta check-ins consecutivos con `datos["cumplido"] is
True`, no algo que el LLM tenga que llevar la cuenta él mismo. Para que
esto funcione, cada check-in ahora tiene que guardar `datos["cumplido"]`
(bool) -- antes no había ningún dato estructurado del que derivar una
racha real, solo el resumen en texto libre.

La Vista de resumen (`construir_vista_resumen`) ya NO se le pide al
modelo que la reproduzca en su mensaje -- la interfaz (`ui/app.py`) y
las herramientas de terminal (`scripts/chat_terminal.py`,
`scripts/simular_conversacion.py`) la muestran aparte, como una tarjeta
fija, llamando a esta misma función directamente. Antes el prompt le
pedía al modelo "mostrá este resumen tal cual" -- funcionaba, pero
dependía de que el modelo lo copiara sin tocarlo una vez más de lo
necesario, cuando ya podíamos mostrarlo con código puro (mismo criterio
que el resto del proyecto: determinismo en código, no en la fidelidad
de copia de un LLM). El prompt sigue recibiendo `{vista_resumen}` como
contexto, para que la pregunta de check-in suene informada, pero ya no
tiene que reproducirlo.
"""

from strands import Agent, tool

from agents._calidad import GuardaEstilo
from agents._modelo import (
    REGLA_CIERRE_REAL_ES,
    REGLA_CIERRE_REAL_EN,
    REGLA_CONJUGACION_ES,
    REGLA_TRANSICION_ES,
    REGLA_TRANSICION_EN,
    crear_modelo,
    regla_nombre,
)
from tools.ficha import guardar_ficha_usuario_fusionada as _guardar
from tools.ficha import leer_ficha_usuario as _leer

TIPOS_CHECKIN = ["cumplimiento", "autopercepcion", "ajuste"]

_PREGUNTAS_POR_TIPO = {
    "es": {
        "cumplimiento": "¿Cómo te fue con el sistema desde la última vez?",
        "autopercepcion": "¿Este propósito todavía se siente tuyo, o algo cambió?",
        "ajuste": (
            "¿Hay algo del sistema (la acción, el cuándo/dónde, la métrica) "
            "que valga la pena cambiar?"
        ),
    },
    "en": {
        "cumplimiento": "How did the system go since last time?",
        "autopercepcion": "Does this purpose still feel like yours, or has something changed?",
        "ajuste": (
            "Is there anything about the system (the action, the when/where, "
            "the metric) worth changing?"
        ),
    },
}

SYSTEM_PROMPT_BASE_ES = """Eres el agente de Seguimiento de Telos. La \
persona ya tiene un propósito y un sistema definidos; tu trabajo es un \
check-in breve, no una sesión larga.

Ya se le mostró, aparte de tu mensaje, este resumen de su propósito y \
sistema vigentes (no hace falta que lo repitas ni lo resumas de nuevo, \
es solo contexto para vos):

---
{vista_resumen}
---

Tu único mensaje es esta pregunta de check-in (podés ajustar la \
redacción para que fluya con la conversación, pero no cambies el tipo \
de pregunta ni hagas una segunda pregunta en el mismo turno): \
"{pregunta_sugerida}" — anda directo a ella, sin preámbulo largo.

Escucha la respuesta con la misma calidez sin importar si la persona \
cumplió o no — no es un examen. Podés mencionar la racha o el progreso \
con calidez (la racha ya se le mostró aparte, en la Vista de resumen — \
no hace falta que la repitas vos, pero si sale naturalmente en la \
conversación no hay problema). Si la racha se cortó o el cumplimiento \
fue bajo, nunca tono punitivo ni de examen — un recordatorio empático \
("mañana es una nueva oportunidad"), no un castigo. Español neutro. \
{regla_conjugacion}

Si la respuesta indica que el sistema no funciona (la acción no se está \
cumpliendo o pide un ajuste que va más allá de un detalle menor), o que \
el propósito ya no resuena, dilo con naturalidad y ofrece pasar a \
rediseñarlo — no insistas en mantener algo que la persona ya dijo que no \
le sirve. Si ofrecés rediseñarlo y la persona acepta, seguí de largo vos \
mismo con la conversación de rediseño en tu próximo mensaje — no lo \
anuncies como si otra persona o sistema fuera a tomar la posta.
{regla_transicion}

Cuando termines el check-in, guarda el resultado con \
guardar_ficha_usuario. Pásale a `datos`: un resumen fiel en palabras de \
la persona (sin evaluarla); las claves "proposito" y "sistema" con los \
valores vigentes de la ficha que ya leíste (sin cambios, salvo que este \
check-in haya llevado a ajustarlos) — si las omitís, el panel de la \
interfaz y el próximo check-in dejan de verlas; la clave "cumplido" con \
`true` o `false` (booleano, no texto) según si la persona sostuvo el \
hábito desde la última vez — esto es lo que le permite a la app calcular \
la racha por código, así que es obligatoria en cada check-in, incluso en \
los de tipo autopercepción o ajuste (inferí el cumplimiento del hábito \
igual, aunque la pregunta principal haya sido sobre otra cosa); y, si \
corresponde re-entrar a una fase anterior, la clave "reentrada" con el \
valor "fase3" (el propósito ya no resuena) o "fase4" (el sistema \
necesita rediseño), o sin esa clave (u omitida) si no hace falta \
re-entrar.

{regla_cierre_real}

{regla_nombre}"""

SYSTEM_PROMPT_BASE_EN = """You are Telos's Follow-up agent. The person \
already has a purpose and a system defined; your job is a brief \
check-in, not a long session.

This summary of their current purpose and system was already shown to \
them separately from your message (no need to repeat or re-summarize \
it, it's just context for you):

---
{vista_resumen}
---

Your only message is this check-in question (you can adjust the \
wording to flow with the conversation, but don't change the type of \
question or ask a second question in the same turn): \
"{pregunta_sugerida}" — go straight to it, no long preamble.

Listen to the answer with the same warmth regardless of whether the \
person followed through or not — this isn't a test. You can mention the \
streak or progress warmly (it was already shown separately, in the \
summary view — no need to repeat it, but it's fine if it comes up \
naturally in conversation). If the streak broke or compliance was low, \
never a punitive or exam-like tone — an empathetic reminder ("tomorrow \
is a new chance"), not a punishment.

If the answer indicates the system isn't working (the action isn't \
being kept, or they're asking for more than a minor adjustment), or that \
the purpose no longer resonates, say so naturally and offer to redesign \
it — don't push to keep something the person already said isn't serving \
them. If you offer to redesign it and they agree, just continue that \
redesign conversation yourself in your next message — don't announce it \
as if someone or something else is taking over.
{regla_transicion}

When you finish the check-in, save the result with guardar_ficha_usuario. \
Pass `datos`: a faithful summary in the person's own words (no \
evaluation); the keys "proposito" and "sistema" with the current values \
from the ficha you already read (unchanged, unless this check-in led to \
adjusting them) — omitting them makes the UI's side panel and the next \
check-in lose track of them; the key "cumplido" as `true` or `false` \
(boolean, not text) for whether the person kept the habit since last \
time — this is what lets the app compute the streak in code, so it's \
required on every check-in, even self-perception or adjustment ones \
(infer compliance anyway, even if the main question was about something \
else); and, if re-entering an earlier phase applies, the key "reentrada" \
with the value "fase3" (the purpose no longer resonates) or "fase4" (the \
system needs a redesign), or without that key (or omitted) if no \
re-entry is needed.

{regla_cierre_real}

{regla_nombre}"""


def _tipo_checkin_anterior(historial: list[dict]) -> str | None:
    for entrada in reversed(historial):
        motivo = entrada.get("motivo_version", "")
        if motivo.startswith("check-in:"):
            partes = motivo.split(":", 2)
            if len(partes) >= 2 and partes[1] in TIPOS_CHECKIN:
                return partes[1]
    return None


def elegir_tipo_checkin(historial: list[dict]) -> str:
    """Rota el tipo de check-in evitando repetir el de la sesión anterior."""
    anterior = _tipo_checkin_anterior(historial)
    candidatos = [t for t in TIPOS_CHECKIN if t != anterior]
    return candidatos[0] if candidatos else TIPOS_CHECKIN[0]


def calcular_racha(historial: list[dict], actual: dict | None) -> int:
    """Cuenta check-ins de Fase 5 consecutivos con `datos["cumplido"] is
    True`, empezando por el más reciente y parando en el primer `False`
    o ausente -- por código, no a criterio del modelo (rama
    `gamificacion`, ver docstring del módulo). Una versión de Fase 5 sin
    "cumplido" (datos de antes de este campo, o de una fase distinta a
    la 5 -- ej. una re-entrada a Fase 3/4) corta la racha igual que un
    `False`: una racha necesita evidencia positiva, no ausencia de
    evidencia. `historial` + `actual` juntos tienen que cubrir todas las
    versiones de la ficha (mismo formato que devuelve
    `tools.ficha.leer_ficha_usuario`)."""
    versiones = list(historial)
    if actual:
        versiones.append(actual)
    racha = 0
    for version in reversed(versiones):
        if version.get("fase") != 5:
            break
        if (version.get("datos") or {}).get("cumplido") is not True:
            break
        racha += 1
    return racha


def construir_vista_resumen(
    ficha_actual: dict | None,
    idioma: str = "es",
    nombre: str | None = None,
    historial: list[dict] | None = None,
) -> str:
    saludo = f"Hi {nombre}! " if (nombre and idioma == "en") else (f"Hola {nombre}, " if nombre else "")
    racha = calcular_racha(historial or [], ficha_actual) if historial is not None else 0
    racha_linea_es = f"🔥 Racha: {racha} check-in{'s' if racha != 1 else ''} seguidos\n" if racha > 0 else ""
    racha_linea_en = f"🔥 Streak: {racha} check-in{'s' if racha != 1 else ''} in a row\n" if racha > 0 else ""

    if idioma == "en":
        if not ficha_actual:
            return f"{saludo}(no ficha on record yet)"
        datos = ficha_actual.get("datos", {})
        proposito = datos.get("proposito", "(no purpose on record)")
        sistema = datos.get("sistema", "(no system on record)")
        fecha = ficha_actual.get("fecha", "")
        return (
            f"{saludo}here's where things stand:\n"
            f"{racha_linea_en}"
            f"Your current purpose: {proposito}\n"
            f"Your current system: {sistema}\n"
            f"Last updated: {fecha}"
        )

    if not ficha_actual:
        return f"{saludo}(sin ficha registrada todavía)"
    datos = ficha_actual.get("datos", {})
    proposito = datos.get("proposito", "(sin propósito registrado)")
    sistema = datos.get("sistema", "(sin sistema registrado)")
    fecha = ficha_actual.get("fecha", "")
    return (
        f"{saludo}esto es lo que tienes hasta ahora:\n"
        f"{racha_linea_es}"
        f"Tu propósito vigente: {proposito}\n"
        f"Tu sistema vigente: {sistema}\n"
        f"Última actualización: {fecha}"
    )


def crear_agente_seguimiento(
    usuario_id: str,
    idioma: str = "es",
    mensajes_previos: list | None = None,
    nombre: str | None = None,
    contenedor_opciones: list | None = None,
    contenedor_guardado: list | None = None,
) -> Agent:
    if contenedor_guardado is None:
        contenedor_guardado = []
    ficha = _leer(usuario_id)
    tipo_checkin = elegir_tipo_checkin(ficha["historial"])
    vista_resumen = construir_vista_resumen(ficha["actual"], idioma, nombre, ficha["historial"])

    plantilla = SYSTEM_PROMPT_BASE_EN if idioma == "en" else SYSTEM_PROMPT_BASE_ES
    if idioma == "en":
        system_prompt = plantilla.format(
            vista_resumen=vista_resumen,
            pregunta_sugerida=_PREGUNTAS_POR_TIPO["en"][tipo_checkin],
            regla_transicion=REGLA_TRANSICION_EN,
            regla_cierre_real=REGLA_CIERRE_REAL_EN,
            regla_nombre=regla_nombre(nombre, idioma),
        )
    else:
        system_prompt = plantilla.format(
            vista_resumen=vista_resumen,
            pregunta_sugerida=_PREGUNTAS_POR_TIPO["es"][tipo_checkin],
            regla_conjugacion=REGLA_CONJUGACION_ES,
            regla_transicion=REGLA_TRANSICION_ES,
            regla_cierre_real=REGLA_CIERRE_REAL_ES,
            regla_nombre=regla_nombre(nombre, idioma),
        )

    @tool
    def leer_ficha_usuario() -> dict:
        """Lee la última versión de la ficha del usuario y su historial."""
        return _leer(usuario_id)

    @tool
    def guardar_ficha_usuario(datos: dict) -> None:
        """Guarda el resultado del check-in de esta sesión."""
        motivo_version = f"check-in:{tipo_checkin}"
        _guardar(usuario_id, datos, fase=5, motivo_version=motivo_version)
        contenedor_guardado.append(True)

    return Agent(
        system_prompt=system_prompt,
        tools=[leer_ficha_usuario, guardar_ficha_usuario],
        model=crear_modelo(),
        # Precarga los turnos ya guardados de esta fase (ver explorador.py).
        messages=mensajes_previos,
        # Suprime el PrintingCallbackHandler por default de Strands (ver
        # explorador.py) -- quien llame controla cómo mostrar la respuesta.
        callback_handler=None,
        # Reintenta una vez si la respuesta usa voseo (agents/_calidad.py).
        hooks=[GuardaEstilo()],
    )
