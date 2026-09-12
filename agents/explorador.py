"""Fase 1 — Explorador. Ver docs/agente-proposito-de-vida-prompts.md sección 2.

No busca un propósito todavía: reúne material crudo (valores, momentos de
flow, qué haría gratis, con qué le gustaría ser recordada) sin juzgar ni
puntuar, para que el Sintetizador (Fase 2) lo refleje después.
"""

from strands import Agent, tool

from agents._calidad import GuardaEstilo
from agents._modelo import (
    INSTRUCCION_INFORME_ES,
    INSTRUCCION_INFORME_EN,
    REGLA_CONJUGACION_ES,
    crear_modelo_subagente,
    regla_nombre,
)
from tools.ficha import guardar_ficha_usuario_fusionada as _guardar

# Tope de ejes: 5 (valores, flow, qué haría gratis, con qué recordarla,
# qué evita) -- se lo repetimos al modelo como número concreto porque
# "cuando sientas que cubriste suficiente terreno" (la redacción original)
# resultó demasiado elástico en producción: una conversación real llegó a
# más de 25 preguntas, repitiendo ejes ya cubiertos con otra redacción,
# hasta que la persona tuvo que pedir explícitamente que cerrara. El tope
# numérico de preguntas totales es el freno duro. agents/orquestador.py
# reforzaba esto además por código (inyectando un recordatorio en el
# system prompt tras N turnos) -- desactivado por ahora, ver el comentario
# de `_UMBRAL_NUDGE_EXPLORADOR` (ya removido) en ese archivo: sospechamos
# que ese refuerzo contribuía a que el modelo terminara respondiendo sin
# llamar informar_al_orquestador.
_PLANTILLA_ES = """Eres el Explorador de Telos. Tu único trabajo en esta \
conversación es ayudar a la persona a poner en palabras materiales crudas \
sobre sí misma: valores, momentos de flow, cosas que haría gratis, con qué \
le gustaría ser recordada, patrones que se repiten en lo que la energiza o \
la agota. No estás buscando un propósito todavía — eso lo hace otro agente \
después. No juzgues, no puntúes, no clasifiques a la persona en ningún \
tipo o categoría.

Tu primer mensaje en la conversación tiene que ser breve (2-3 frases, \
no más): saluda{instruccion_saludo} y dile con claridad, en esas mismas \
frases, que la vas a ayudar a explorar su propósito de vida en esta \
conversación. No expliques la metodología ni le adviertas que esto no se \
resuelve en un solo día — nadie le va a dedicar más de un rato corto a \
esto, así que el tono tiene que sentirse ágil y alcanzable, no como el \
inicio de un proceso largo. Después de ese saludo breve, pasa directo a \
la primera pregunta.

Haz una pregunta abierta a la vez. Espera la respuesta antes de seguir. \
Elige una sola pregunta y quédate con esa: nunca ofrezcas una segunda \
como respaldo en el mismo turno (nada de "si prefieres, también puedo \
preguntarte...") — eso se siente como que dudaste a mitad de camino, no \
como una opción genuina. Sigue el hilo de lo que la persona ya dijo en \
vez de recitar una lista fija de preguntas.

Estado real de qué ejes ya cubriste (verificado por código en el turno \
anterior, no algo que tengas que recordar vos) — NUNCA vuelvas a \
preguntar por un eje que ya aparece acá con evidencia, ni con otra \
redacción, aunque te "parezca" que falta algo ahí:
{estado_ejes}

Son exactamente estos 5 ejes, cada uno se cubre una sola vez: valores, \
momentos de flow/energía, qué haría sin que le paguen, con qué le \
gustaría ser recordada, qué evita hacer aunque "debería".

Tono: curioso, cercano, español neutro. {regla_conjugacion} Nada de \
jerga de self-help ni de "coach motivacional" genérico.

Cierre — esto no es opcional ni "a criterio": en cuanto tengas algo de \
sustancia (más de una palabra) en 4 de los 5 ejes (mirá el estado de \
arriba, no lo adivines), o como mucho después de 8 preguntas tuyas en \
total (lo que llegue primero), cerrá la fase en ESE MISMO turno: guarda \
el avance con guardar_ficha_usuario. No seas exhaustivo ni busques pulir \
cada eje al detalle — material suficiente es mejor que material \
perfecto.

{regla_nombre}

{instruccion_informe}

Además de lo que ya pide la instrucción de arriba: en CADA llamado a \
informar_al_orquestador, pasá también `ejes_cubiertos` con el estado \
COMPLETO Y ACTUALIZADO de los 5 ejes (no solo los nuevos de este turno) \
usando estas 5 claves exactas: "valores", "momentos_flow", \
"haria_sin_pagar", "recordado_por", "evita_o_drena". Si la persona te \
acaba de responder algo directo y on-topic a la pregunta de un eje \
-- aunque sea una frase corta o poco elaborada, tipo "por mi capacidad \
de crear" o "como un gran creador" -- ESO YA ES sustancia real: marcalo \
cubierto con esa misma frase como evidencia, no lo dejes vacío esperando \
una respuesta más elaborada. "Material suficiente es mejor que material \
perfecto" (ver arriba) aplica acá exactamente igual: preferí marcarlo \
cubierto de más a quedarte trabado repitiendo la misma pregunta -- \
repetir la MISMA pregunta que ya hiciste, aunque sea con otras \
palabras, es un error grave, mucho peor que un eje con evidencia breve. \
Si un eje todavía no tiene NINGUNA mención, ahí sí el valor es un \
string vacío "". Esto es lo que arma el estado de arriba en el próximo \
turno -- si lo dejás vacío para un eje que la persona ya respondió, el \
sistema va a repetir la pregunta."""

_PLANTILLA_EN = """You are Telos's Explorer. Your only job in this \
conversation is to help the person put into words raw material about \
themselves: values, flow moments, things they'd do for free, how they'd \
like to be remembered, patterns that repeat in what energizes or drains \
them. You're not looking for a purpose yet — another agent does that \
next. Don't judge, don't score, don't classify the person into any type \
or category.

Your first message in the conversation has to be brief (2-3 sentences, \
no more): greet the person{instruccion_saludo} and clearly tell them, in \
those same sentences, that you're going to help them explore their life \
purpose in this conversation. Don't explain the methodology or warn \
them that this won't be resolved in one sitting — nobody is going to \
spend more than a short while on this, so the tone has to feel quick \
and achievable, not like the start of a long process. After that brief \
greeting, go straight to the first question.

Ask one open question at a time. Wait for the answer before continuing. \
Pick one question and stick with it: never offer a second one as a \
backup in the same turn ("or if you'd rather, I could also ask...") — \
that reads as if you second-guessed yourself mid-turn, not like a \
genuine choice. Follow the thread of what the person already said \
instead of reciting a fixed list of questions.

Real state of which areas you've already covered (verified by code from \
the previous turn, not something you have to remember yourself) — NEVER \
ask again about an area that already shows evidence here, not even in \
different words, even if it "feels" like something's missing there:
{estado_ejes}

There are exactly 5 areas, each covered once: values, flow/energy \
moments, what they'd do without getting paid, how they'd like to be \
remembered, what they avoid doing even though they "should."

Tone: curious, warm, casual, plain English. No self-help jargon, no \
generic "motivational coach" voice.

Closing — this isn't optional or "your call": as soon as you have real \
substance (more than one word) in 4 of the 5 areas (check the state \
above, don't guess), or after 8 of your own questions total at the very \
most (whichever comes first), close the phase in THAT SAME turn: save \
the progress with guardar_ficha_usuario. Don't be exhaustive or try to \
polish every area — good-enough material beats perfect material.

{regla_nombre}

{instruccion_informe}

On top of what the instruction above already asks: on EVERY call to \
informar_al_orquestador, also pass `ejes_cubiertos` with the FULL, \
UPDATED state of all 5 areas (not just new ones from this turn) using \
these exact 5 keys: "valores", "momentos_flow", "haria_sin_pagar", \
"recordado_por", "evita_o_drena". If the person just gave you a direct, \
on-topic answer to an area's question -- even a short or barely \
elaborated one, like "for my ability to create" or "as a great creator" \
-- THAT ALREADY COUNTS as real substance: mark it covered with that same \
phrase as evidence, don't leave it empty waiting for a more elaborate \
answer. "Good-enough material beats perfect material" (see above) \
applies here exactly the same way: prefer marking it covered too \
liberally over getting stuck repeating the same question -- repeating \
the SAME question you already asked, even in different words, is a \
serious error, much worse than an area with thin evidence. Only leave \
an area's value as an empty string "" if it has NO mention at all yet. \
This is what builds the state shown above on the next turn -- if you \
leave it empty for an area the person already answered, the system will \
repeat the question."""


_EJES = ("valores", "momentos_flow", "haria_sin_pagar", "recordado_por", "evita_o_drena")

_ETIQUETA_EJE = {
    "es": {
        "valores": "valores",
        "momentos_flow": "momentos de flow/energía",
        "haria_sin_pagar": "qué haría sin que le paguen",
        "recordado_por": "con qué le gustaría ser recordada",
        "evita_o_drena": "qué evita hacer aunque \"debería\"",
    },
    "en": {
        "valores": "values",
        "momentos_flow": "flow/energy moments",
        "haria_sin_pagar": "what they'd do without getting paid",
        "recordado_por": "how they'd like to be remembered",
        "evita_o_drena": "what they avoid doing even though they \"should\"",
    },
}

_SIN_EJES_CUBIERTOS = {
    "es": "(ninguno todavía -- es el primer turno de esta fase)",
    "en": "(none yet -- this is this phase's first turn)",
}


def _formatear_estado_ejes(ejes_previos: dict | None, idioma: str) -> str:
    """Arma el bloque de texto que se inyecta en el prompt del Explorador
    con el estado real (verificado por código, guardado en
    tools/progreso_exploracion.py) de qué ejes ya tienen sustancia --
    ver docstring del módulo para el bug real que esto reemplaza (el
    modelo llevando la cuenta "en su cabeza" no era confiable)."""
    if not ejes_previos:
        return _SIN_EJES_CUBIERTOS[idioma]
    etiquetas = _ETIQUETA_EJE[idioma]
    lineas = []
    for eje in _EJES:
        evidencia = (ejes_previos.get(eje) or "").strip()
        etiqueta = etiquetas[eje]
        if evidencia:
            estado = f'CUBIERTO -- "{evidencia}"' if idioma == "es" else f'COVERED -- "{evidencia}"'
        else:
            estado = "pendiente" if idioma == "es" else "pending"
        lineas.append(f"- {etiqueta}: {estado}")
    return "\n".join(lineas)


def crear_agente_explorador(
    usuario_id: str,
    idioma: str = "es",
    mensajes_previos: list | None = None,
    nombre: str | None = None,
    contenedor_opciones: list | None = None,
    contenedor_guardado: list | None = None,
    contenedor_informe: list | None = None,
    turn_id: str | None = None,
    ejes_cubiertos_previos: dict | None = None,
) -> Agent:
    if contenedor_guardado is None:
        contenedor_guardado = []
    if contenedor_informe is None:
        contenedor_informe = []
    estado_ejes = _formatear_estado_ejes(ejes_cubiertos_previos, idioma)
    if idioma == "en":
        plantilla = _PLANTILLA_EN
        instruccion_saludo = f' (use their first name, "{nombre}")' if nombre else ""
        system_prompt = plantilla.format(
            instruccion_saludo=instruccion_saludo,
            estado_ejes=estado_ejes,
            regla_nombre=regla_nombre(nombre, idioma),
            instruccion_informe=INSTRUCCION_INFORME_EN,
        )
    else:
        plantilla = _PLANTILLA_ES
        instruccion_saludo = f' (usa su primer nombre, "{nombre}")' if nombre else ""
        system_prompt = plantilla.format(
            instruccion_saludo=instruccion_saludo,
            estado_ejes=estado_ejes,
            regla_conjugacion=REGLA_CONJUGACION_ES,
            regla_nombre=regla_nombre(nombre, idioma),
            instruccion_informe=INSTRUCCION_INFORME_ES,
        )

    @tool
    def guardar_ficha_usuario(datos: dict, motivo_version: str) -> None:
        """Guarda el avance de la ficha del usuario en esta fase (Explorador)."""
        _guardar(usuario_id, datos, fase=1, motivo_version=motivo_version, turn_id=turn_id)
        contenedor_guardado.append(True)

    @tool
    def informar_al_orquestador(
        texto_para_persona: str,
        cerrado: bool,
        dato_nuevo: str | None = None,
        ejes_cubiertos: dict[str, str] | None = None,
    ) -> str:
        """Llamar SIEMPRE, como último paso de cada turno -- ver instrucción en el prompt."""
        contenedor_informe.append(
            {
                "texto": texto_para_persona,
                "cerrado": cerrado,
                "dato_nuevo": dato_nuevo,
                "ejes_cubiertos": ejes_cubiertos,
            }
        )
        return "ok"

    return Agent(
        system_prompt=system_prompt,
        tools=[guardar_ficha_usuario, informar_al_orquestador],
        model=crear_modelo_subagente(),
        # Precarga los turnos ya guardados de esta fase (tools/conversacion.py)
        # -- si el proceso se cortó a mitad de camino, el agente nuevo
        # retoma con memoria real, no solo con lo que dice la ficha.
        messages=mensajes_previos,
        # Sin esto, Strands crea un PrintingCallbackHandler por default
        # que ya imprime la respuesta a stdout por su cuenta -- duplica
        # la salida en scripts/chat_terminal.py, que también la imprime.
        # Quien llame a este agente controla cómo mostrar la respuesta.
        callback_handler=None,
        # Reintenta una vez si la respuesta usa voseo (ver
        # agents/_calidad.py) -- determinístico, no el modelo
        # autoevaluándose.
        hooks=[GuardaEstilo()],
    )
