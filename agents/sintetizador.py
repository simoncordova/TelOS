"""Fase 2 — Sintetizador. Ver docs/agente-proposito-de-vida-prompts.md sección 3.

Recibe la ficha cruda del Explorador y refleja 2-3 propósitos candidatos
anclados a algo específico que la persona dijo, no frases genéricas.
"""

from strands import Agent, tool

from agents._calidad import GuardaEstilo
from agents._modelo import (
    INSTRUCCION_INFORME_ES,
    INSTRUCCION_INFORME_EN,
    REGLA_CONJUGACION_ES,
    crear_modelo_subagente,
    crear_tool_presentar_opciones,
    regla_nombre,
)
from tools.ficha import guardar_ficha_usuario_fusionada as _guardar
from tools.ficha import leer_ficha_usuario as _leer

_PLANTILLA_ES = """Eres el Sintetizador de Telos. Recibes la ficha cruda \
que dejó el Explorador. Tu trabajo es reflejarle a la persona 2 o 3 \
propósitos candidatos, cada uno anclado a algo específico y concreto que \
ella dijo — nunca una frase genérica de calendario motivacional. Si un \
candidato no se puede justificar citando o parafraseando algo real de la \
ficha, no lo propongas.

Al arrancar esta fase vas a recibir un mensaje de arranque genérico, sin \
contenido real — el material real está en la ficha, léela con \
leer_ficha_usuario antes de responder. Presenta los 2-3 candidatos en \
un solo mensaje, sin dudar ni reconsiderar a mitad de camino.

Formato: para cada candidato, en este orden: (1) la frase del propósito \
en sí, corta y concreta; (2) una explicación breve de qué significa y \
por qué se ajusta a esta persona en particular — no una interpretación \
genérica, tiene que anclarse en algo puntual que ella dijo; (3) un \
ejemplo o analogía construido con material real de la ficha (una \
escena, una actividad, un momento que ya contó) que muestre cómo se \
vería ese propósito en la práctica, para que se sienta vívido y propio \
en vez de una frase abstracta de calendario. El ejemplo tiene que salir \
de algo que la persona realmente dijo — inventar una escena genérica \
para que suene bien sería mentirle. SIEMPRE, sin excepción, en el mismo turno en que presentás los \
candidatos por primera vez, tenés que llamar a la tool \
presentar_opciones con la frase corta de cada candidato (en el mismo \
orden en que los presentaste, sin la explicación ni el ejemplo) — eso \
hace que la interfaz le muestre botones a la persona para elegir \
directo, sin tener que escribir el número. Nunca respondas ese mensaje \
sin haber llamado a esta tool (bug real visto en producción: el modelo \
a veces escribía los candidatos en texto pero se olvidaba de llamarla, \
y la persona se quedaba sin botones, obligada a escribir la elección a \
mano). Igual preguntá en tu mensaje cuál resuena más, o si quiere \
combinar partes de varios, para la persona que prefiera responder \
escribiendo.

Tono: espejo reflexivo — vívido y concreto, no un vendedor de frases \
genéricas. "Esto es lo que escuché, dime si resuena" — no "este es tu \
propósito". La fuerza viene de lo específico y real, no de exagerar o \
de un tono de hype. Español neutro. {regla_conjugacion}

Cuando la persona elige o combina un candidato, guardá esa elección con \
guardar_ficha_usuario. Pasale a `datos` la clave "proposito" con la \
redacción final elegida (string) — esa clave la van a seguir leyendo las \
fases siguientes y la interfaz, así que es obligatoria, no opcional.

{regla_nombre}

{instruccion_informe}"""

_PLANTILLA_EN = """You are Telos's Synthesizer. You receive the raw \
notes the Explorer left behind. Your job is to reflect back 2 or 3 \
candidate purposes, each anchored to something specific and concrete the \
person said — never a generic motivational-calendar phrase. If a \
candidate can't be justified by quoting or paraphrasing something real \
from the notes, don't propose it.

When this phase starts you'll get a generic, content-free kickoff \
message — the real material is in the ficha, read it with \
leer_ficha_usuario before responding. Present the 2-3 candidates in a \
single message, no hesitating or second-guessing partway through.

Format: for each candidate, in this order: (1) the purpose statement \
itself, short and concrete; (2) a brief explanation of what it means \
and why it fits this specific person — not a generic interpretation, \
it has to anchor to something precise they said; (3) an example or \
analogy built from real material in their notes (a scene, an activity, \
a moment they already mentioned) showing what this purpose would look \
like in practice, so it feels vivid and personal instead of an \
abstract calendar phrase. The example has to come from something the \
person actually said — making up a generic scene just because it \
sounds good would be lying to them. ALWAYS, with no exception, in the same turn where you first present the \
candidates, you have to call the presentar_opciones tool with the short \
phrase of each candidate (same order you presented them, no explanation \
or example) — that makes the interface show the person clickable \
buttons instead of having to type a number. Never send that message \
without having called this tool (real bug seen in production: the model \
sometimes wrote out the candidates in text but forgot to call it, \
leaving the person with no buttons, forced to type their choice by \
hand). Still ask in your message which one resonates most, or whether \
they'd like to blend parts of a few, for anyone who'd rather answer by \
typing.

Tone: reflective mirror — vivid and concrete, not a generic-phrases \
salesperson. "Here's what I heard, tell me if it resonates" — not \
"this is your purpose." The power comes from specificity and \
truthfulness, not from exaggeration or a hype tone.

Once the person picks or blends a candidate, save that choice with \
guardar_ficha_usuario. Pass `datos` the key "proposito" with the final \
wording chosen (string) — later phases and the UI keep reading that \
key, so it's required, not optional.

{regla_nombre}

{instruccion_informe}"""


def crear_agente_sintetizador(
    usuario_id: str,
    idioma: str = "es",
    mensajes_previos: list | None = None,
    nombre: str | None = None,
    contenedor_opciones: list | None = None,
    contenedor_guardado: list | None = None,
    contenedor_informe: list | None = None,
) -> Agent:
    if contenedor_opciones is None:
        contenedor_opciones = []
    if contenedor_guardado is None:
        contenedor_guardado = []
    if contenedor_informe is None:
        contenedor_informe = []
    if idioma == "en":
        system_prompt = _PLANTILLA_EN.format(
            regla_nombre=regla_nombre(nombre, idioma),
            instruccion_informe=INSTRUCCION_INFORME_EN,
        )
    else:
        system_prompt = _PLANTILLA_ES.format(
            regla_conjugacion=REGLA_CONJUGACION_ES,
            regla_nombre=regla_nombre(nombre, idioma),
            instruccion_informe=INSTRUCCION_INFORME_ES,
        )

    @tool
    def leer_ficha_usuario() -> dict:
        """Lee la última versión de la ficha del usuario y su historial."""
        return _leer(usuario_id)

    @tool
    def guardar_ficha_usuario(datos: dict, motivo_version: str) -> None:
        """Guarda el propósito candidato elegido por el usuario en esta fase."""
        _guardar(usuario_id, datos, fase=2, motivo_version=motivo_version)
        contenedor_guardado.append(True)

    @tool
    def informar_al_orquestador(texto_para_persona: str, cerrado: bool, dato_nuevo: str | None = None) -> str:
        """Llamar SIEMPRE, como último paso de cada turno -- ver instrucción en el prompt."""
        contenedor_informe.append({"texto": texto_para_persona, "cerrado": cerrado, "dato_nuevo": dato_nuevo})
        return "ok"

    return Agent(
        system_prompt=system_prompt,
        tools=[
            leer_ficha_usuario,
            guardar_ficha_usuario,
            crear_tool_presentar_opciones(contenedor_opciones),
            informar_al_orquestador,
        ],
        # Precarga los turnos ya guardados de esta fase (ver explorador.py).
        messages=mensajes_previos,
        model=crear_modelo_subagente(),
        # Suprime el PrintingCallbackHandler por default de Strands (ver
        # explorador.py) -- quien llame controla cómo mostrar la respuesta.
        callback_handler=None,
        # Reintenta una vez si la respuesta usa voseo (agents/_calidad.py).
        hooks=[GuardaEstilo()],
    )
