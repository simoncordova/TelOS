"""Orquestador. Ver docs/agente-proposito-de-vida-prompts.md sección 1.

No conversa directamente sobre contenido de propósito: aplica el
guardrail de crisis en cada turno, antes que cualquier otra cosa, y
después invoca DIRECTO al agente de la fase actual (`self.fase_actual`,
mantenido por código -- ver `_avanzar_fase_si_corresponde`). Fase 1→2→3→4
es un flujo fijo (no se saltan pasos), Fase 5 es dinámica y puede
reinyectar al usuario en Fase 3 o 4.

Hasta el 12/09/2026 (rama gamificacion) el ruteo pasaba por un `Agent`
orquestador (Sonnet, `agents/orquestador_agente.py`, borrado en este
commit) con las 5 fases expuestas como tools (`Agent.as_tool()`),
decidiendo con "juicio semántico" a cuál invocar. Se sacó (revisión de
arquitectura externa) porque ese juicio era redundante -- el propio
prompt del orquestador se armaba pasándole `self.fase_actual`, que el
código ya conocía con certeza -- y porque agregaba una clase entera de
fallo real (el orquestador respondiendo texto plano sin invocar ninguna
fase-tool) y una invocación completa de Bedrock por turno sin
necesidad. Recuperable de git history si hace falta comparar.

Cada agente de fase, según el spec, guarda su ficha exactamente una vez,
al cerrar su fase (no hay saves parciales a mitad de fase). Fases 2-5
declaran explícitamente `cerrado: bool` en su tool
`informar_al_orquestador` -- y ese booleano se verifica contra AgentCore
Memory (¿la ficha realmente tiene una versión nueva?) antes de confiar
en él.

Fase 1 (Explorador) es completamente distinta desde el 13/09/2026 -- ya
no es una conversación de texto libre en absoluto (ver el plan
"quirky-launching-swing" en el directorio de planes de Claude Code). La
persona
elige de un árbol de categorías fijo (tools/categorias_ikigai.py, un
grafo único donde cada nodo aporta a una o más de las 5 dimensiones del
Ikigai -- ver DIMENSIONES_IKIGAI) en vez de responder preguntas: la
elección ES el dato, válida por construcción, sin que ningún LLM tenga
que juzgar si "ya alcanza". `confirmar_seleccion` más abajo reemplaza a
`_invocar_explorador` (Explorer v2, el intento anterior con preguntas
fijas + evaluador acotado -- sacado en este mismo cambio, ver git
history si hace falta comparar): código calcula cobertura por dimensión
y decide el cierre, nunca el modelo. `_invocar_fase_directo`/
`enviar_mensaje` (el camino de texto libre) ya NO atienden a Fase 1 más
que con un aviso fijo -- ver `_PLACEHOLDER_FASE_1` -- hasta que la
interfaz visual (`ArbolSelector.tsx`, todavía sin construir) llame a
`confirmar_seleccion` a través de los endpoints nuevos de `api/main.py`.

El guardrail de crisis, el Paso 0 (captura de nombre) y el avance de fase
siguen siendo código plano, sin involucrar a ningún `Agent` -- son
mecanismos de seguridad/bookkeeping, no decisiones conversacionales (ver
docstrings de cada método más abajo).

`enviar_mensaje` es un generador, no devuelve un string: cuando hay
cascada, entrega el mensaje de la fase que cierra y el de la fase
siguiente por separado, apenas cada uno está listo, en vez de esperar a
tener los dos para mostrar todo junto de una. Quien llama (`api/main.py`,
`scripts/chat_terminal.py`) itera y muestra cada parte a medida que
llega. Cada elemento entregado es una tupla (fase, texto, opciones):
`opciones` es una lista de strings (a veces vacía) que un agente de fase
puede ofrecer vía la tool `presentar_opciones` (agents/_modelo.py) para
que la interfaz la muestre como botones -- por ahora solo la usa el
Sintetizador, para elegir el propósito candidato.
"""

import logging
import time
import uuid

from pydantic import BaseModel
from strands.agent import Agent

from agents._modelo import crear_modelo_subagente
from agents.coach_validacion import crear_agente_coach_validacion
from agents.estratega_sistemas import crear_agente_estratega_sistemas
from agents.seguimiento import crear_agente_seguimiento
from agents.sintetizador import crear_agente_sintetizador
from tools.categorias_ikigai import DIMENSIONES_IKIGAI, buscar_nodo_con_ruta
from tools.contexto_usuario import agregar_insight
from tools.conversacion import guardar_intercambio, leer_turnos
from tools.crisis import detectar_señal_crisis, mensaje_crisis, registrar_evento_crisis
from tools.ficha import guardar_ficha_usuario_fusionada, leer_ficha_usuario
from tools.limite_uso import excedio_limite_diario, mensaje_limite_alcanzado, registrar_invocacion
from tools.perfil import guardar_nombre_usuario, leer_nombre_usuario
from tools.selecciones_estructuradas import (
    borrar_selecciones_estructuradas,
    guardar_selecciones_estructuradas,
    leer_selecciones_estructuradas,
)

logger = logging.getLogger(__name__)

# Fase 1 (Explorador) queda AFUERA de este dict a propósito -- ya no es
# una conversación en absoluto (ver docstring del módulo y
# confirmar_seleccion más abajo). _invocar_fase_directo despacha a fase 1
# ANTES de llegar al camino genérico de abajo, con un aviso fijo -- si
# algún día fase 1 llegara acá por error, preferible un KeyError
# inmediato a un crash confuso más adelante.
_FABRICAS_POR_FASE = {
    2: crear_agente_sintetizador,
    3: crear_agente_coach_validacion,
    4: crear_agente_estratega_sistemas,
    5: crear_agente_seguimiento,
}

# Mensaje interno para arrancar al agente nuevo tras un cambio de fase en
# el mismo turno. Nunca se muestra a la persona (no se agrega al
# historial visible, solo dispara la respuesta del agente siguiente).
_KICKOFF = {
    "es": "Continuemos.",
    "en": "Let's continue.",
}

# Selector Ikigai (Fase 1, ver docstring del módulo) -- invariante
# garantizada por código, no por instrucción: la fase cierra cuando cada
# una de las 5 dimensiones (tools/categorias_ikigai.py::DIMENSIONES_IKIGAI)
# ya fue tocada por al menos este número de selecciones distintas.
# Ajustable -- un valor más alto pide más material antes de sintetizar,
# uno más bajo cierra antes.
_MIN_SELECCIONES_POR_DIMENSION = 2

_MENSAJE_CIERRE_SELECCION = {
    "es": "Con esto ya tengo material real para reflejarte algo. Vamos al siguiente paso.",
    "en": "I've got real material to reflect back to you now. Let's move to the next step.",
}

# Fase 1 ya no acepta texto libre como mecanismo principal (ver docstring
# del módulo) -- este es el único texto que puede devolver el camino de
# `enviar_mensaje`/`abrir_conversacion` mientras esa fase esté activa,
# hasta que la interfaz visual (ArbolSelector.tsx) esté conectada.
_PLACEHOLDER_FASE_1 = {
    "es": (
        "Esta fase ahora se completa eligiendo categorías en la pantalla "
        "principal, no escribiendo acá -- todavía no tengo una respuesta "
        "de texto para darte en este paso."
    ),
    "en": (
        "This phase is now completed by picking categories on the main "
        "screen, not by typing here -- I don't have a text reply for this "
        "step yet."
    ),
}

# Única invocación al modelo en el cierre de Fase 1 -- ver
# SesionTelos._sintetizar_selecciones. Sin tools: la respuesta del
# modelo ES el material crudo que va a leer Fase 2, no decide nada sobre
# validez ni cierre (eso ya lo resolvió el código antes de llegar acá).
_PROMPT_SINTESIS_SELECCION = {
    "es": (
        "Estas son las categorías que una persona eligió al explorar su "
        "Ikigai en un árbol visual, de la más reveladora (toca más "
        "dimensiones del Ikigai a la vez) a la menos. Cada una indica a "
        "qué dimensiones aporta: amas (lo que ama), sos_bueno (en lo que "
        "es bueno), mundo_necesita (lo que el mundo necesita), "
        "pueden_pagar (por lo que le pueden pagar), valores (un valor no "
        "negociable).\n\n{selecciones}\n\n"
        "Redactá un párrafo breve, en español neutro, en tercera persona "
        "(\"Esta persona...\"), que describa el material crudo que surge "
        "de estas elecciones -- sin inventar nada que no esté en la "
        "lista, sin todavía proponer un propósito (eso lo hace otro paso "
        "después). Priorizá mencionar las elecciones que tocan más "
        "dimensiones a la vez -- son la señal más fuerte."
    ),
    "en": (
        "These are the categories a person chose while exploring their "
        "Ikigai on a visual tree, from the most revealing (touches the "
        "most Ikigai dimensions at once) to the least. Each one shows "
        "which dimensions it contributes to: amas (what they love), "
        "sos_bueno (what they're good at), mundo_necesita (what the "
        "world needs), pueden_pagar (what they could be paid for), "
        "valores (a non-negotiable value).\n\n{selecciones}\n\n"
        "Write a short paragraph, in plain English, in third person "
        "(\"This person...\"), describing the raw material that comes "
        "out of these choices -- don't invent anything not in the list, "
        "don't propose a purpose yet (a later step does that). "
        "Prioritize mentioning the choices that touch the most "
        "dimensions at once -- they're the strongest signal."
    ),
}

# Paso 0: pedido de nombre, antes de que exista ninguna fase. Determinístico
# y sin costo de Bedrock -- ver docstring del módulo.
_PEDIR_NOMBRE = {
    "es": "Antes de arrancar, ¿cómo te llamas? Así puedo llamarte por tu nombre en el resto de la conversación.",
    "en": "Before we start, what's your first name? That way I can call you by it for the rest of our conversation.",
}

_EXTRAER_NOMBRE_PROMPT = {
    "es": (
        'Vas a recibir la respuesta de una persona a la pregunta "¿cómo te '
        "llamas?\". Devolvé ÚNICAMENTE su primer nombre, con mayúscula "
        "inicial, sin nada más -- ni saludo, ni puntuación, ni explicación. "
        "Si el texto realmente no contiene ningún nombre, devolvé "
        "exactamente: SIN_NOMBRE"
    ),
    "en": (
        "You'll receive a person's reply to \"what's your first name?\". "
        "Return ONLY their first name, capitalized, nothing else -- no "
        "greeting, no punctuation, no explanation. If the text truly "
        "contains no name, return exactly: NO_NAME"
    ),
}

# Freno de seguridad para un bug real visto en producción (un agente de
# fase 2-5 escribió en su texto que ya había guardado todo, pero nunca
# LLAMÓ a guardar_ficha_usuario -- el Orquestador nunca vio una versión
# nueva, nunca cascadeó). Describir una acción en el texto no es lo mismo
# que ejecutarla -- ver agents/_modelo.py::INSTRUCCION_INFORME_ES/EN (el
# `cerrado: bool` que declara informar_al_orquestador) para la
# instrucción equivalente en el prompt; esto es la red de seguridad por
# código si igual no alcanza. No aplica a Fase 1, que ya no depende de
# ninguna tool que el modelo tenga que recordar llamar (ver
# confirmar_seleccion).
_FORZAR_CIERRE = {
    "es": (
        "No llamaste a la tool guardar_ficha_usuario en tu respuesta "
        "anterior, aunque el texto sonaba a que ya habías cerrado. Si ya "
        "tenés material suficiente, llamá a esa tool AHORA en tu "
        "respuesta a este mensaje -- no lo describas en texto, ejecutá "
        "la tool de verdad. Si de verdad todavía te falta material, "
        "hacé como mucho una pregunta más, breve."
    ),
    "en": (
        "You didn't call the guardar_ficha_usuario tool in your previous "
        "reply, even though the text sounded like you'd already closed. "
        "If you already have enough material, call that tool NOW in your "
        "reply to this message -- don't describe it in text, actually "
        "call the tool. If you genuinely still need more material, ask "
        "at most one more short question."
    ),
}

_RESPUESTA_VACIA_RETRY = {
    "es": "Tu respuesta anterior llegó vacía. Respondé de nuevo, con contenido real.",
    "en": "Your previous reply came back empty. Reply again, with real content this time.",
}
_RESPUESTA_VACIA_FALLBACK = {
    "es": "Disculpá, tuve un problema para generar la respuesta. ¿Podés escribir tu último mensaje de nuevo?",
    "en": "Sorry, I had trouble generating a reply. Could you send your last message again?",
}

# Bug real (orquestador agéntico, rama gamificacion): a diferencia del
# diseño anterior -- donde el mismo Agent vivía en memoria toda la sesión
# y `informar_al_orquestador` no existía -- ahora CADA turno depende de
# que el subagente llame esa tool obligatoria, y con el modelo Haiku
# (crear_modelo_subagente) eso no siempre pasa: en pruebas reales, el
# Explorador a veces respondió texto normal sin llamarla, dejando
# `contenedor_informe` vacío -- eso se leía como "respuesta vacía", caía
# al aviso fijo de arriba, y ESE aviso fijo quedaba guardado como si
# fuera un turno real (`guardar_intercambio`), corrompiendo el historial:
# el próximo turno el Explorador veía su propio "tuve un problema" previo
# en el historial y volvía a saludar de cero. Este mensaje fuerza un
# reintento apuntado (llamá la tool, no regeneres contenido si ya lo
# tenías) ANTES de llegar a ese aviso fijo -- ver
# SesionTelos._invocar_una_vez/_invocar_fase_directo.
_FORZAR_INFORME = {
    "es": (
        "No llamaste a la tool informar_al_orquestador en tu respuesta "
        "anterior, que es obligatoria en cada turno. Llamala AHORA -- "
        "usá el mismo texto que ya tenías listo para texto_para_persona, "
        "no hace falta que generes contenido nuevo."
    ),
    "en": (
        "You didn't call the informar_al_orquestador tool in your "
        "previous reply, which is mandatory every turn. Call it NOW -- "
        "use the same text you already had ready for texto_para_persona, "
        "no need to generate new content."
    ),
}


class InformeAlOrquestador(BaseModel):
    """Mismo contrato que la tool `informar_al_orquestador` de cada
    agente de fase, pero como modelo Pydantic para el reintento forzado
    (ver `_invocar_una_vez`/`_invocar_fase_directo`). A diferencia de
    `agente(texto)` normal -- donde Strands no expone forma de forzar
    tool_choice, así que el modelo puede simplemente no llamar ninguna
    tool -- pasar esta clase como `structured_output_model` en el
    reintento SÍ fuerza tool_choice a nivel de Bedrock (confirmado
    contra el código fuente instalado de Strands 1.55.0: es el mismo
    mecanismo, ahora no-deprecado, detrás del `Agent.structured_output`
    viejo). Así el reintento deja de depender de que el modelo decida
    cooperar -- garantiza la forma de la respuesta, aunque el contenido
    siga siendo cosa del modelo. `cerrado` sigue sin ser autoridad de
    cierre por sí solo: _verificar_y_reforzar sigue siendo quien lo
    confirma contra AgentCore Memory."""

    texto_para_persona: str
    cerrado: bool
    dato_nuevo: str | None = None

# El mismo bug de "dijo que guardó pero no llamó a la tool" apareció
# primero en el Explorador y después en el Sintetizador -- por eso ahora
# cada agente de fase declara explícitamente `cerrado: bool` en su tool
# `informar_al_orquestador` (agents/sintetizador.py y hermanos) en vez de
# que el código adivine por regex si el TEXTO suena a un cierre. Ese
# booleano igual se verifica acá contra AgentCore Memory antes de
# confiarle nada (ver SesionTelos._invocar/enviar_mensaje) -- la
# autoridad sigue siendo la memoria persistente, no lo que el modelo
# declara sobre sí mismo.

# Claves de `datos` que cada fase, al cerrar, tiene que garantizar que
# existan en la ficha (ver tools/ficha.py::guardar_ficha_usuario_fusionada
# y docs/agente-proposito-de-vida-prompts.md sección 7). La fusión ya
# resuelve el caso de "el modelo se olvidó de re-incluir una clave que
# una fase anterior ya había puesto" -- lo que NO resuelve es que una
# clave nunca se haya puesto NINGUNA vez (ej. el Estratega cierra la
# ficha sin incluir "sistema" -- no hay ningún valor previo del que
# heredarlo). Esto se chequea después de cualquier guardado real
# (una versión nueva de esta fase en AgentCore Memory, ver
# SesionTelos._verificar_y_reforzar), releyendo la ficha ya fusionada.
_CAMPOS_REQUERIDOS_AL_CERRAR = {
    2: ("proposito",),
    3: ("proposito",),
    4: ("proposito", "sistema"),
    # "cumplido" (booleano) es de la rama `gamificacion` -- sin él,
    # agents/seguimiento.py::calcular_racha no tiene de qué derivar la
    # racha, así que es tan obligatorio como "proposito"/"sistema".
    5: ("proposito", "sistema", "cumplido"),
}


def exit_criteria_cumplido(fase: int, datos: dict) -> tuple[bool, tuple[str, ...]]:
    """Única autoridad real sobre si una fase está lista para dejar de
    reclamar campos faltantes -- ver revisión de arquitectura externa
    (12/09/2026), sección 6: "reemplazar cerrado por invariantes". El
    booleano `cerrado` que declara el modelo (`informar_al_orquestador`)
    es una SEÑAL, no autoridad -- nunca se usa solo para decidir nada acá;
    `_verificar_y_reforzar` es quien de verdad decide, llamando a esta
    función contra los `datos` ya persistidos (no contra lo que el modelo
    dice que guardó).

    Devuelve (cumplido, campos_faltantes). "is None" y no una
    verificación de verdad -- un campo booleano como "cumplido" (fase 5,
    rama gamificacion) es legítimamente `False` cuando la persona no
    sostuvo el hábito, y eso NO es lo mismo que faltar."""
    requeridos = _CAMPOS_REQUERIDOS_AL_CERRAR.get(fase, ())
    faltantes = tuple(c for c in requeridos if datos.get(c) is None)
    return not faltantes, faltantes

_FALTAN_CAMPOS = {
    "es": (
        "Guardaste el avance, pero a `datos` le faltó la clave {campos} "
        "-- sin eso, la persona ve esa parte vacía en la interfaz aunque "
        "ya la haya definido. Volvé a llamar a guardar_ficha_usuario en "
        "tu respuesta a este mensaje, esta vez con {campos} incluida "
        "(podés tomar el valor de lo que ya se habló en esta "
        "conversación)."
    ),
    "en": (
        "You saved the progress, but `datos` was missing the {campos} "
        "key -- without it, the person sees that part empty in the UI "
        "even though it's already been defined. Call "
        "guardar_ficha_usuario again in your reply to this message, this "
        "time including {campos} (you can take the value from what was "
        "already discussed in this conversation)."
    ),
}


def _texto_ultimo_mensaje_asistente(agente: Agent) -> str:
    """Extrae el texto plano del último turno del asistente en
    `agente.messages` -- fallback para _invocar_una_vez cuando el
    sub-agente respondió de verdad pero no llamó a
    `informar_al_orquestador` ni con el reintento forzado. Strands guarda
    cada mensaje como {"role": ..., "content": [bloques]}; un bloque de
    texto tiene la clave "text", uno de tool_use/tool_result no la tiene."""
    for mensaje in reversed(agente.messages):
        if mensaje.get("role") != "assistant":
            continue
        texto = "".join(bloque.get("text", "") for bloque in mensaje.get("content", []))
        if texto.strip():
            return texto.strip()
    return ""


def _texto_de_resultado(resultado) -> str:
    """Extrae el texto plano de un `AgentResult` puntual -- usado por la
    síntesis de cierre de Fase 1 (SesionTelos._sintetizar_selecciones),
    una llamada sin tools donde la respuesta del modelo ES el texto
    buscado, directo."""
    mensaje = resultado.message or {}
    return "".join(bloque.get("text", "") for bloque in mensaje.get("content", [])).strip()


def _turnos_a_mensajes(turnos: list[dict]) -> list[dict]:
    """Convierte los turnos guardados (tools/conversacion.py) al formato
    de `Message` que espera Strands (`Agent(messages=...)`)."""
    return [{"role": t["rol"], "content": [{"text": t["texto"]}]} for t in turnos]


def _extraer_nombre(texto: str, idioma: str, usuario_id: str) -> str:
    """Extrae el primer nombre de la respuesta libre de la persona con una
    llamada mínima al modelo (sin tools, sin historial) -- una respuesta
    real como "me llamo Simón Cordova" o "soy Ana" no se puede parsear
    con un split() confiable, así que esto es justo el tipo de tarea de
    texto libre que conviene delegarle al modelo en vez de a una regex.
    Respeta el límite diario igual que cualquier invocación real (cuenta
    para `registrar_invocacion`); si ya se alcanzó el límite, o si la
    extracción no devuelve nada usable, cae a un respaldo determinístico
    (primer token de lo que escribió la persona tal cual)."""
    marcador_vacio = "NO_NAME" if idioma == "en" else "SIN_NOMBRE"
    if not excedio_limite_diario(usuario_id):
        agente = Agent(
            system_prompt=_EXTRAER_NOMBRE_PROMPT[idioma],
            model=crear_modelo_subagente(),
            callback_handler=None,
        )
        resultado = str(agente(texto)).strip()
        registrar_invocacion(usuario_id)
        if resultado and resultado.upper() != marcador_vacio:
            return resultado.split()[0].strip(".,;:!¡?¿-").capitalize()

    token = texto.strip().split()[0] if texto.strip() else ""
    limpio = token.strip(".,;:!¡?¿-").capitalize()
    return limpio or ("Friend" if idioma == "en" else "Amigo/a")


class SesionTelos:
    """Sesión en memoria de proceso: mantiene el agente Strands activo para
    la fase actual de un usuario. La ficha (tools/ficha.py) guarda el
    resultado final de cada fase; tools/conversacion.py guarda cada turno
    mientras la fase está en curso, para que un proceso nuevo pueda
    reconstruir la conversación real (no solo la ficha) si el anterior se
    cortó a mitad de camino -- por eso esta clase se puede recrear en
    cualquier momento sin perder contexto.
    """

    def __init__(self, usuario_id: str, idioma: str = "en"):
        self.usuario_id = usuario_id
        self.idioma = idioma
        self.nombre = leer_nombre_usuario(usuario_id)
        self._pidiendo_nombre = not bool(self.nombre)
        # Instantánea de las opciones (botones) que dejó el subagente que
        # respondió el último turno -- ver agents._modelo.
        # crear_tool_presentar_opciones. Se actualiza en cada invocación
        # (_invocar_una_vez/_invocar_fase_directo); quien llama a
        # enviar_mensaje/abrir_conversacion la lee apenas termina.
        self._contenedor_opciones: list = []
        # Ver enviar_mensaje -- diagnóstico público, sin valor hasta el
        # primer mensaje real (abrir_conversacion no los toca, invoca
        # directo).
        self.ultima_fase_respondio: int | None = None
        self.ultimo_cerrado_declarado: bool | None = None
        self.fase_actual = self._determinar_fase_inicial()

    def _invocar_una_vez(self, texto: str, turn_id: str | None = None) -> tuple[int, str, bool]:
        """Invoca directo a la fase actual (`self.fase_actual`), sin pasar
        por ningún router agéntico. Devuelve (fase_que_respondió,
        texto_para_la_persona, cerrado_declarado). `turn_id` identifica el
        turno real de conversación (ver `_invocar`) para que un guardado
        de ficha durante este turno sea idempotente.

        Hasta acá (rama gamificacion) esto pasaba por un `Agent`
        orquestador (Sonnet) con las 5 fases expuestas como tools
        (`Agent.as_tool()`), que "elegía" con juicio semántico a cuál
        invocar -- ver revisión de arquitectura externa, 12/09/2026.
        Sacado: `self.fase_actual` (mantenido por código en
        `_avanzar_fase_si_corresponde`, incluida la lógica de reingreso a
        Fase 3/4 desde Fase 5) YA es la respuesta a la única pregunta que
        el orquestador resolvía -- su propio prompt se armaba pasándole
        ese mismo valor (`_resumir_estado_ficha`) para que "decidiera"
        algo que el código ya sabía. Quitarlo elimina de raíz una clase
        entera de fallo (el orquestador respondiendo texto plano sin
        invocar ninguna fase-tool, visto en producción) y saca una
        invocación real de Bedrock por turno (mejora de latencia)."""
        fase = self.fase_actual
        texto_respuesta, cerrado = self._invocar_fase_directo(fase, texto, turn_id=turn_id)
        return fase, texto_respuesta, cerrado

    def _invocar(self, texto: str) -> tuple[int, str, bool]:
        """Invoca al orquestador agéntico, salvo que esta cuenta ya haya
        llegado al límite diario de invocaciones reales
        (tools/limite_uso.py) -- en ese caso corta antes de tocar Bedrock.
        Cuenta cada invocación real (orquestador + el subagente que haya
        respondido), no cada mensaje de la persona.

        Nunca devuelve un string vacío: AgentCore Memory rechaza guardar
        un turno con texto de largo 0 (`ParamValidationError`, bug real
        visto en producción) y una burbuja en blanco tampoco le sirve a
        la persona. Si la respuesta viene vacía (el orquestador no llegó
        a invocar ninguna tool, o el subagente no llamó a
        informar_al_orquestador), reintenta una vez antes de resignarse a
        un aviso fijo -- como mucho un reintento, nunca un loop sin
        límite. El mismo `turn_id` (ver InformeAlOrquestador/
        tools/ficha.py) se usa en el reintento -- es el mismo turno real
        de la persona, solo que el primer intento no produjo nada útil."""
        if excedio_limite_diario(self.usuario_id):
            return self.fase_actual, mensaje_limite_alcanzado(self.idioma), False
        turn_id = str(uuid.uuid4())
        fase, respuesta, cerrado = self._invocar_una_vez(texto, turn_id=turn_id)
        if not respuesta and not excedio_limite_diario(self.usuario_id):
            fase, respuesta, cerrado = self._invocar_una_vez(_RESPUESTA_VACIA_RETRY[self.idioma], turn_id=turn_id)
        return fase, (respuesta or _RESPUESTA_VACIA_FALLBACK[self.idioma]), cerrado

    def _invocar_fase_directo(self, fase: int, texto: str, turn_id: str | None = None) -> tuple[str, bool]:
        """Invoca UNA fase puntual directo, sin pasar por el orquestador
        -- usado solo por los frenos de seguridad de _verificar_y_reforzar
        (forzar cierre, completar campos faltantes) y por los mensajes de
        arranque (abrir_conversacion, cascada de cambio de fase), donde
        ya se sabe con certeza a qué fase invocar y no tiene sentido
        gastar otra decisión del orquestador. Devuelve (texto, cerrado).

        Fase 1 ya no es una conversación de texto (ver docstring del
        módulo y confirmar_seleccion) -- devuelve un aviso fijo, sin
        gastar ninguna invocación real."""
        if fase == 1:
            return _PLACEHOLDER_FASE_1[self.idioma], False
        if excedio_limite_diario(self.usuario_id):
            return mensaje_limite_alcanzado(self.idioma), False
        contenedor_opciones: list = []
        contenedor_guardado: list = []
        contenedor_informe: list = []
        turnos = leer_turnos(self.usuario_id, fase)
        agente = _FABRICAS_POR_FASE[fase](
            self.usuario_id,
            self.idioma,
            mensajes_previos=_turnos_a_mensajes(turnos),
            nombre=self.nombre,
            contenedor_opciones=contenedor_opciones,
            contenedor_guardado=contenedor_guardado,
            contenedor_informe=contenedor_informe,
            turn_id=turn_id,
        )
        agente(texto)
        registrar_invocacion(self.usuario_id)
        if not contenedor_informe and not excedio_limite_diario(self.usuario_id):
            # Mismo reintento forzado que _invocar_una_vez -- ver
            # InformeAlOrquestador.
            try:
                resultado_forzado = agente(_FORZAR_INFORME[self.idioma], structured_output_model=InformeAlOrquestador)
                registrar_invocacion(self.usuario_id)
            except Exception:  # noqa: BLE001 -- fallo real forzando la forma, no un caso esperado
                logger.exception("Fase %s (invocación directa): structured_output_model del reintento falló", fase)
                resultado_forzado = None
            if resultado_forzado is not None and resultado_forzado.structured_output is not None:
                informe_forzado = resultado_forzado.structured_output
                contenedor_informe.append(
                    {
                        "texto": informe_forzado.texto_para_persona,
                        "cerrado": informe_forzado.cerrado,
                        "dato_nuevo": informe_forzado.dato_nuevo,
                    }
                )
        self._contenedor_opciones = list(contenedor_opciones)
        if not contenedor_informe:
            # Mismo fallback que _invocar_una_vez -- ver ese comentario.
            texto_fallback = _texto_ultimo_mensaje_asistente(agente)
            logger.warning(
                "Fase %s (invocación directa) no llamó informar_al_orquestador ni tras el reintento forzado. "
                "Último texto del modelo: %r",
                fase,
                texto_fallback[:500],
            )
            return texto_fallback, False
        informe = contenedor_informe[-1]
        dato_nuevo = informe.get("dato_nuevo")
        if dato_nuevo:
            agregar_insight(self.usuario_id, dato_nuevo)
        return (informe.get("texto") or "").strip(), bool(informe.get("cerrado"))

    def confirmar_seleccion(self, nodo_id: str, detalle_libre: str | None = None) -> dict:
        """Fase 1: confirma una hoja elegida en el árbol Ikigai (ver
        tools/categorias_ikigai.py). Reemplaza por completo al Explorador
        conversacional -- ya no hay texto libre que evaluar: la elección
        de la persona ES el dato, válida por construcción, así que no
        hace falta ningún evaluador acotado (a diferencia de Explorer v2,
        el intento anterior con preguntas fijas + agents/evaluador_respuesta.py,
        sacado en este mismo cambio).

        La `ruta` y las `dimensiones` se derivan acá de la taxonomía
        (tools/categorias_ikigai.py::buscar_nodo_con_ruta), nunca se
        confía en lo que mande el cliente -- mismo criterio de "código
        decide" que el resto del proyecto.

        Devuelve {"cobertura": {dimension: int, ...}, "cerrado": bool,
        "mensaje_cierre": str | None}. Levanta ValueError si la fase
        actual no es 1, o si `nodo_id` no existe en la taxonomía."""
        if self.fase_actual != 1:
            raise ValueError(f"confirmar_seleccion solo aplica en Fase 1 -- fase actual es {self.fase_actual}")
        if excedio_limite_diario(self.usuario_id):
            return {"cobertura": {}, "cerrado": False, "mensaje_cierre": None}

        idioma_arbol = "en" if self.idioma == "en" else "es"
        encontrado = buscar_nodo_con_ruta(idioma_arbol, nodo_id)
        if encontrado is None:
            raise ValueError(f"nodo_id desconocido en la taxonomía de Fase 1: {nodo_id!r}")
        nodo, ruta = encontrado

        progreso = leer_selecciones_estructuradas(self.usuario_id)
        if not progreso or "selecciones" not in progreso:
            progreso = {"selecciones": [], "cobertura": {dim: 0 for dim in DIMENSIONES_IKIGAI}}
        progreso["selecciones"].append(
            {
                "nodo_id": nodo_id,
                "label": nodo["label"],
                "ruta": ruta,
                "dimensiones": list(nodo["dimensiones"]),
                "detalle_libre": detalle_libre,
            }
        )
        for dimension in nodo["dimensiones"]:
            progreso["cobertura"][dimension] = progreso["cobertura"].get(dimension, 0) + 1
        guardar_selecciones_estructuradas(self.usuario_id, progreso)

        if not self._cobertura_suficiente(progreso["cobertura"]):
            return {"cobertura": progreso["cobertura"], "cerrado": False, "mensaje_cierre": None}

        mensaje_cierre = self._cerrar_fase_1(progreso)
        return {"cobertura": progreso["cobertura"], "cerrado": True, "mensaje_cierre": mensaje_cierre}

    def _cobertura_suficiente(self, cobertura: dict) -> bool:
        """Determinístico -- Fase 1 cierra cuando las 5 dimensiones del
        Ikigai (DIMENSIONES_IKIGAI) ya fueron tocadas por al menos
        `_MIN_SELECCIONES_POR_DIMENSION` selecciones distintas. Sin
        "intentos" ni evaluación que pueda fallar -- a diferencia de
        Explorer v2, acá no hace falta una red de seguridad de "todos los
        ejes en estado terminal": la persona simplemente sigue eligiendo
        hasta llegar al mínimo."""
        return all(cobertura.get(dim, 0) >= _MIN_SELECCIONES_POR_DIMENSION for dim in DIMENSIONES_IKIGAI)

    def _cerrar_fase_1(self, progreso: dict) -> str:
        """Cierre 100% por código: sintetiza las selecciones ya
        acumuladas en el material crudo que antes armaba el Explorador
        (una sola invocación al modelo, sin tools de datos -- ver
        _sintetizar_selecciones), lo guarda directo con
        guardar_ficha_usuario_fusionada, y avanza la fase. Nunca pasa por
        ninguna tool que el modelo tenga que acordarse de llamar."""
        selecciones_por_convergencia = sorted(
            progreso["selecciones"], key=lambda s: len(s["dimensiones"]), reverse=True
        )
        material = self._sintetizar_selecciones(selecciones_por_convergencia)
        guardar_ficha_usuario_fusionada(
            self.usuario_id,
            {"materia_prima": material},
            fase=1,
            motivo_version="Selecciones del árbol Ikigai -- cierre determinado por código",
            turn_id=str(uuid.uuid4()),
        )
        borrar_selecciones_estructuradas(self.usuario_id)
        self.fase_actual = 2
        return _MENSAJE_CIERRE_SELECCION[self.idioma]

    def _sintetizar_selecciones(self, selecciones: list[dict]) -> str:
        """Única invocación real al modelo en todo el cierre de Fase 1 --
        sin tools, transforma las selecciones (ya ordenadas por
        convergencia, las que tocan más dimensiones primero) en un
        párrafo de material crudo para que lo use Fase 2 (Sintetizador).
        No decide nada -- ni qué es válido, ni cuándo cerrar -- solo
        redacta."""
        lineas = []
        for s in selecciones:
            linea = f"- {s['label']} (dimensiones: {', '.join(s['dimensiones']) or 'ninguna'})"
            if s.get("detalle_libre"):
                linea += f" -- detalle de la persona: {s['detalle_libre']}"
            lineas.append(linea)
        texto_selecciones = "\n".join(lineas)
        agente = Agent(model=crear_modelo_subagente(), callback_handler=None)
        prompt = _PROMPT_SINTESIS_SELECCION[self.idioma].format(selecciones=texto_selecciones)
        resultado = agente(prompt)
        registrar_invocacion(self.usuario_id)
        return _texto_de_resultado(resultado)

    def _verificar_y_reforzar(
        self, fase: int, respuesta: str, cerrado_declarado: bool, total_versiones_antes: int
    ) -> str:
        """Después de invocar `fase` (por el orquestador o directo),
        confirma contra AgentCore Memory -- no contra lo que el modelo
        declaró de sí mismo -- que lo que pasó es consistente, y fuerza
        como mucho un reintento por cada chequeo, directo a esa misma
        fase (no vuelve a pasar por el orquestador, ya no hay ninguna
        decisión de ruteo pendiente):

        1. Si se declaró `cerrado=True` pero AgentCore Memory no tiene una
           versión nueva, reintenta con _FORZAR_CIERRE.
        2. Si sí hay una versión nueva de esta fase, pero exit_criteria_
           cumplido() dice que faltan campos obligatorios, reintenta con
           _FALTAN_CAMPOS. `cerrado_declarado` nunca decide esto por sí
           solo -- ver exit_criteria_cumplido."""
        if cerrado_declarado and self._contar_versiones() <= total_versiones_antes:
            respuesta, _ = self._invocar_fase_directo(fase, _FORZAR_CIERRE[self.idioma])

        ficha = self._leer_ficha_con_reintento(total_versiones_antes)
        hubo_guardado = (len(ficha["historial"]) + (1 if ficha["existe"] else 0)) > total_versiones_antes
        if hubo_guardado and ficha["actual"]["fase"] == fase:
            datos = ficha["actual"]["datos"] or {}
            cumplido, faltantes = exit_criteria_cumplido(fase, datos)
            if not cumplido:
                campos = ", ".join(f'"{c}"' for c in faltantes)
                respuesta, _ = self._invocar_fase_directo(fase, _FALTAN_CAMPOS[self.idioma].format(campos=campos))

        return respuesta or _RESPUESTA_VACIA_FALLBACK[self.idioma]

    def abrir_conversacion(self):
        """Generador: el agente de la fase actual habla primero, sin
        esperar texto de la persona -- se llama una sola vez, al abrir
        la sesión (nueva o retomada). Sin esto, el sistema siempre se
        queda esperando a que la persona adivine qué escribir primero,
        incluso en Fase 5, que según el spec tiene que mostrar la Vista
        de resumen apenas se abre la conversación, no después.

        Si todavía no se capturó el nombre de la persona (Paso 0), lo
        pide directo en código, sin invocar ningún agente. Invoca la fase
        actual directo (sin pasar por el orquestador -- ya sabemos con
        certeza cuál es) y no avanza de fase (abrir no cierra nada, mismo
        criterio que antes)."""
        if self._pidiendo_nombre:
            yield 0, _PEDIR_NOMBRE[self.idioma], []
            return

        kickoff = _KICKOFF[self.idioma]
        total_versiones_antes = self._contar_versiones()
        respuesta, cerrado = self._invocar_fase_directo(self.fase_actual, kickoff, turn_id=str(uuid.uuid4()))
        respuesta = self._verificar_y_reforzar(self.fase_actual, respuesta, cerrado, total_versiones_antes)
        guardar_intercambio(self.usuario_id, self.fase_actual, kickoff, respuesta)
        yield self.fase_actual, respuesta, list(self._contenedor_opciones)

    def _determinar_fase_inicial(self) -> int:
        """El campo "fase" de una versión de la ficha registra la fase
        QUE ACABA DE CERRAR para producirla -- no la fase en la que
        continúa la persona (ver `_avanzar_fase_si_corresponde`: guarda
        con `fase=self.fase_actual` y recién DESPUÉS avanza
        `self.fase_actual` a `fase + 1`). Una sesión nueva (reconexión,
        reinicio del proceso) tiene que retomar en `fase_guardada + 1`,
        no en `fase_guardada` -- devolver el mismo número reiniciaba de
        cero una fase que ya había cerrado (bug real: si el proceso se
        reiniciaba justo después de que el Explorador cerrara pero antes
        de que la sesión en memoria cascadeara, una sesión nueva volvía a
        correr el Explorador desde el principio en vez de retomar en el
        Sintetizador). Fase 4 es la excepción: cierra la ficha entera, así
        que cualquier sesión nueva entra directo a Fase 5 en vez de
        "Fase 5 + 1"; y una ficha ya en Fase 5 (check-ins) se queda en
        Fase 5, no avanza sola a una "Fase 6" inexistente."""
        ficha = leer_ficha_usuario(self.usuario_id)
        if not ficha["existe"]:
            return 1
        fase_guardada = ficha["actual"]["fase"]
        if fase_guardada >= 4:
            return 5
        return fase_guardada + 1

    def _capturar_nombre(self, texto: str):
        """Cierra el Paso 0: guarda el nombre y hace hablar primero, en
        el mismo turno, al agente de la fase en la que ya estaba esta
        persona (nueva o retomada) -- invocado directo (sin pasar por el
        orquestador), mismo criterio que abrir_conversacion. Así la
        persona nunca ve un chat esperando en silencio después de
        contestar."""
        nombre = _extraer_nombre(texto, self.idioma, self.usuario_id)
        guardar_nombre_usuario(self.usuario_id, nombre)
        self.nombre = nombre
        self._pidiendo_nombre = False

        kickoff = _KICKOFF[self.idioma]
        total_versiones_antes = self._contar_versiones()
        respuesta, cerrado = self._invocar_fase_directo(self.fase_actual, kickoff, turn_id=str(uuid.uuid4()))
        respuesta = self._verificar_y_reforzar(self.fase_actual, respuesta, cerrado, total_versiones_antes)
        guardar_intercambio(self.usuario_id, self.fase_actual, kickoff, respuesta)
        yield self.fase_actual, respuesta, list(self._contenedor_opciones)

    def enviar_mensaje(self, texto: str):
        """Generador: entrega (fase, texto, opciones) por cada mensaje, en
        el orden en que se van generando -- no un solo string con todo
        junto. `opciones` es la lista (posiblemente vacía) que haya
        dejado la tool `presentar_opciones` en esta invocación -- ver
        docstring del módulo.

        El mensaje de la persona se invoca directo contra `self.fase_actual`
        (ver `_invocar_una_vez`) -- igual que los mensajes de arranque
        (abrir_conversacion, cascada de cambio de fase más abajo), porque
        ya no hay ninguna decisión de ruteo que tomar en ningún caso."""
        resultado_crisis = detectar_señal_crisis(texto)
        if resultado_crisis["disparado"]:
            registrar_evento_crisis(self.usuario_id, resultado_crisis["categoria"])
            yield self.fase_actual, mensaje_crisis(self.idioma), []
            return

        if self._pidiendo_nombre:
            yield from self._capturar_nombre(texto)
            return

        fase_antes = self.fase_actual
        total_versiones_antes = self._contar_versiones()
        fase_respondio, respuesta, cerrado = self._invocar(texto)
        # Público, de solo lectura, para diagnóstico (scripts/
        # simular_conversacion.py): qué fase respondió y qué declaró
        # ANTES del reintento forzado de _verificar_y_reforzar -- así se
        # puede ver si el freno tuvo que intervenir, no solo el resultado
        # final ya corregido.
        self.ultima_fase_respondio = fase_respondio
        self.ultimo_cerrado_declarado = cerrado
        respuesta = self._verificar_y_reforzar(fase_respondio, respuesta, cerrado, total_versiones_antes)

        guardar_intercambio(self.usuario_id, fase_antes, texto, respuesta)
        yield fase_antes, respuesta, list(self._contenedor_opciones)

        self._avanzar_fase_si_corresponde(fase_respondio, total_versiones_antes)

        # La fase cambió en este mismo turno: si el destino no es Fase 5
        # (que espera a una conversación nueva, no continúa en caliente),
        # arrancamos al agente siguiente ya mismo, directo (ya sabemos
        # cuál es, no hace falta el orquestador) para no dejar a la
        # persona esperando sin saber que le toca escribir algo. Se
        # entrega como un mensaje aparte, no concatenado al anterior --
        # así quien llama puede mostrar el primero apenas está listo, sin
        # esperar a que este segundo termine de generarse.
        if self.fase_actual != fase_antes and self.fase_actual != 5:
            kickoff = _KICKOFF[self.idioma]
            total_versiones_previas_cascada = self._contar_versiones()
            continuacion, cerrado_cascada = self._invocar_fase_directo(
                self.fase_actual, kickoff, turn_id=str(uuid.uuid4())
            )
            continuacion = self._verificar_y_reforzar(
                self.fase_actual, continuacion, cerrado_cascada, total_versiones_previas_cascada
            )
            guardar_intercambio(self.usuario_id, self.fase_actual, kickoff, continuacion)
            yield self.fase_actual, continuacion, list(self._contenedor_opciones)

    def contar_versiones_ficha(self) -> int:
        """Público (a diferencia de _leer_ficha_con_reintento, que sigue
        siendo un detalle interno): api/main.py lo necesita para saber
        cuántas versiones había ANTES de un turno, y así poder pedir el
        snapshot de ficha post-turno con el mismo reintento por
        consistencia eventual que ya usa el avance de fase -- sin esto,
        el panel "Tus resultados" del frontend podía mostrar el
        propósito/sistema vacío durante uno o dos segundos justo después
        de guardarlo (bug real: el snapshot que viaja por el evento SSE
        "ficha" leía la ficha una sola vez, sin reintento)."""
        return self._contar_versiones()

    def ficha_actualizada(self, total_versiones_antes: int) -> dict:
        """Público -- ver contar_versiones_ficha. Mismo reintento que ya
        usa _avanzar_fase_si_corresponde, expuesto para que quien llama
        pueda pedir la ficha ya reflejando un guardado reciente."""
        return self._leer_ficha_con_reintento(total_versiones_antes)

    def _contar_versiones(self) -> int:
        ficha = leer_ficha_usuario(self.usuario_id)
        return len(ficha["historial"]) + (1 if ficha["existe"] else 0)

    def _leer_ficha_con_reintento(self, total_versiones_antes: int, intentos: int = 4, espera_segundos: float = 1.0) -> dict:
        """AgentCore Memory puede tardar un instante en reflejar en
        list_events un evento que se acaba de guardar (consistencia
        eventual) -- sin este reintento, un guardado real podía pasar
        desapercibido acá y la fase nunca avanzaba, aunque el agente ya
        hubiera guardado todo y se lo hubiera dicho a la persona (bug
        real visto en producción: el Explorador decía "ya guardé todo,
        te paso al Sintetizador" y la app se quedaba esperando). Con el
        backend JSON local esto siempre resuelve en el primer intento
        (escritura sincrónica a disco), así que no agrega latencia ahí."""
        ficha = leer_ficha_usuario(self.usuario_id)
        for _ in range(intentos - 1):
            total_versiones = len(ficha["historial"]) + (1 if ficha["existe"] else 0)
            if total_versiones > total_versiones_antes:
                break
            time.sleep(espera_segundos)
            ficha = leer_ficha_usuario(self.usuario_id)
        return ficha

    def _avanzar_fase_si_corresponde(self, fase_que_respondio: int, total_versiones_antes: int) -> None:
        """`fase_que_respondio` es la fase que efectivamente generó la
        respuesta de este turno (siempre `self.fase_actual` de antes del
        turno, ver `_invocar_una_vez` -- ya no hay ningún router agéntico
        que pudiera invocar una fase distinta a la esperada, pero el
        avance se sigue calculando sobre lo que de verdad se guardó, no
        sobre lo que se esperaba)."""
        ficha = self._leer_ficha_con_reintento(total_versiones_antes)
        if not ficha["existe"]:
            return

        total_versiones = len(ficha["historial"]) + 1
        if total_versiones <= total_versiones_antes:
            return  # no se guardó nada nuevo en este turno, seguimos en la misma fase

        actual = ficha["actual"]
        if actual["fase"] != fase_que_respondio:
            return  # la versión nueva no corresponde a la fase que respondió

        # fase_que_respondio == 1 no debería llegar hasta acá -- Fase 1
        # cierra y avanza self.fase_actual directo en
        # SesionTelos._cerrar_fase_1, sin pasar por enviar_mensaje. Se
        # deja el caso igual (en vez de asumir que nunca puede pasar) por
        # si algún día algo la invoca por el camino genérico de texto.
        if fase_que_respondio in (1, 2, 3):
            self.fase_actual = fase_que_respondio + 1
        elif fase_que_respondio == 4:
            self.fase_actual = 5
        elif fase_que_respondio == 5:
            reentrada = (actual["datos"] or {}).get("reentrada")
            if reentrada == "fase3":
                self.fase_actual = 3
            elif reentrada == "fase4":
                self.fase_actual = 4
            # sin reentrada: se queda en Fase 5 hasta la próxima sesión
