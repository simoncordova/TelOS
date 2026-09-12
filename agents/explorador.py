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
vez de recitar una lista fija de preguntas. Llevá la cuenta interna (no \
en voz alta) de qué ejes ya cubriste, para no volver a preguntar por el \
mismo eje con otras palabras — son exactamente estos 5, cada uno se \
cubre una sola vez: valores, momentos de flow/energía, qué haría sin \
que le paguen, con qué le gustaría ser recordada, qué evita hacer aunque \
"debería".

Tono: curioso, cercano, español neutro. {regla_conjugacion} Nada de \
jerga de self-help ni de "coach motivacional" genérico.

Cierre — esto no es opcional ni "a criterio": en cuanto tengas algo de \
sustancia (más de una palabra) en 4 de los 5 ejes, o como mucho después \
de 8 preguntas tuyas en total (lo que llegue primero), cerrá la fase en \
ESE MISMO turno: guarda el avance con guardar_ficha_usuario. No seas \
exhaustivo ni busques pulir cada eje al detalle — material suficiente es \
mejor que material perfecto.

{regla_nombre}

{instruccion_informe}"""

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
instead of reciting a fixed list of questions. Keep an internal (not \
spoken) tally of which areas you've already covered, so you never ask \
about the same one again in different words — there are exactly 5, each \
covered once: values, flow/energy moments, what they'd do without \
getting paid, how they'd like to be remembered, what they avoid doing \
even though they "should."

Tone: curious, warm, casual, plain English. No self-help jargon, no \
generic "motivational coach" voice.

Closing — this isn't optional or "your call": as soon as you have real \
substance (more than one word) in 4 of the 5 areas, or after 8 of your \
own questions total at the very most (whichever comes first), close the \
phase in THAT SAME turn: save the progress with guardar_ficha_usuario. \
Don't be exhaustive or try to polish every area — good-enough material \
beats perfect material.

{regla_nombre}

{instruccion_informe}"""


def crear_agente_explorador(
    usuario_id: str,
    idioma: str = "es",
    mensajes_previos: list | None = None,
    nombre: str | None = None,
    contenedor_opciones: list | None = None,
    contenedor_guardado: list | None = None,
    contenedor_informe: list | None = None,
) -> Agent:
    if contenedor_guardado is None:
        contenedor_guardado = []
    if contenedor_informe is None:
        contenedor_informe = []
    if idioma == "en":
        plantilla = _PLANTILLA_EN
        instruccion_saludo = f' (use their first name, "{nombre}")' if nombre else ""
        system_prompt = plantilla.format(
            instruccion_saludo=instruccion_saludo,
            regla_nombre=regla_nombre(nombre, idioma),
            instruccion_informe=INSTRUCCION_INFORME_EN,
        )
    else:
        plantilla = _PLANTILLA_ES
        instruccion_saludo = f' (usa su primer nombre, "{nombre}")' if nombre else ""
        system_prompt = plantilla.format(
            instruccion_saludo=instruccion_saludo,
            regla_conjugacion=REGLA_CONJUGACION_ES,
            regla_nombre=regla_nombre(nombre, idioma),
            instruccion_informe=INSTRUCCION_INFORME_ES,
        )

    @tool
    def guardar_ficha_usuario(datos: dict, motivo_version: str) -> None:
        """Guarda el avance de la ficha del usuario en esta fase (Explorador)."""
        _guardar(usuario_id, datos, fase=1, motivo_version=motivo_version)
        contenedor_guardado.append(True)

    @tool
    def informar_al_orquestador(texto_para_persona: str, cerrado: bool, dato_nuevo: str | None = None) -> str:
        """Llamar SIEMPRE, como último paso de cada turno -- ver instrucción en el prompt."""
        contenedor_informe.append({"texto": texto_para_persona, "cerrado": cerrado, "dato_nuevo": dato_nuevo})
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
