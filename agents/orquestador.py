"""Orquestador. Ver docs/agente-proposito-de-vida-prompts.md sección 1.

No conversa directamente sobre contenido de propósito: rutea entre los
agentes de fase y aplica el guardrail de crisis en cada turno, antes que
cualquier otra cosa. Fase 1→2→3→4 es un flujo fijo (no se saltan pasos);
Fase 5 es dinámica y puede reinyectar al usuario en Fase 3 o 4.

Cada agente de fase, según el spec, guarda su ficha exactamente una vez,
al cerrar su fase (no hay saves parciales a mitad de fase) — por eso
"¿se guardó una versión nueva de la fase actual en este turno?" alcanza
como señal de "esta fase terminó, avanza a la siguiente".

Cuando la fase cambia a 2, 3 o 4 (flujo fijo o re-entrada desde Fase 5),
el agente nuevo se invoca en el mismo turno con un mensaje de arranque
neutro — si no, la persona se queda mirando un chat "colgado" después
del cierre de una fase, sin señal de que tiene que escribir algo para
que continúe. La única excepción es al llegar a Fase 5: ese cierre es
el fin natural de la sesión (el spec dice que Fase 5 se dispara "al
abrir una conversación nueva", no en el mismo turno que cierra Fase 4).
Este encadenado -- y no un prompt que le pida al modelo "avisale a la
persona que sigue otro agente" -- es la máquina de estados real del
producto: vive en código Python plano, se puede leer de punta a punta
en este archivo, y no depende de que un LLM decida correctamente cuándo
rutear. Los agentes de fase, en paralelo, tienen instrucciones explícitas
de no narrar el mecanismo (agents/_modelo.py::REGLA_TRANSICION_ES/EN) —
la persona nunca debería enterarse de que hay más de un agente.


Paso 0, antes de la Fase 1: si todavía no se guardó un nombre de pila
para este usuario_id (tools/perfil.py), la sesión completa arranca
pidiéndolo -- sin invocar ningún agente de fase todavía, sin costo de
Bedrock salvo la extracción del nombre en sí (ver `_extraer_nombre`).
Esto es intencionalmente código, no un tool de ningún agente: el nombre
no es una decisión conversacional de un agente de fase, es un dato de
sesión que después se inyecta en los 5 prompts (`nombre=` en cada
fábrica de agents/*.py) para que se dirijan a la persona por su nombre.
Una vez capturado, la sesión sigue exactamente por la fase en la que ya
estaba (no reinicia a Fase 1) -- esto cubre tanto a alguien nuevo como a
una ficha vieja de antes de que existiera esta función.

`enviar_mensaje` es un generador, no devuelve un string: cuando hay
cascada, entrega el mensaje de la fase que cierra y el de la fase
siguiente por separado, apenas cada uno está listo, en vez de esperar a
tener los dos para mostrar todo junto de una — con el Sintetizador
generando más contenido ahora (propósito + explicación + ejemplo por
candidato), esperar a los dos combinados se sentía como que la app se
había colgado. Quien llama (`api/main.py`, `scripts/chat_terminal.py`)
itera y muestra cada parte a medida que llega. Cada elemento entregado es
una tupla (fase, texto, opciones): `opciones` es una lista de strings (a
veces vacía) que un agente de fase puede ofrecer vía la tool
`presentar_opciones` (agents/_modelo.py) para que la interfaz la muestre
como botones en vez de obligar a la persona a escribir la elección --
por ahora solo la usa el Sintetizador, para elegir el propósito
candidato.
"""

import re
import time

from strands.agent import Agent

from agents._modelo import crear_modelo
from agents.coach_validacion import crear_agente_coach_validacion
from agents.estratega_sistemas import crear_agente_estratega_sistemas
from agents.explorador import crear_agente_explorador
from agents.seguimiento import crear_agente_seguimiento
from agents.sintetizador import crear_agente_sintetizador
from tools.conversacion import guardar_intercambio, leer_turnos
from tools.crisis import detectar_señal_crisis, mensaje_crisis, registrar_evento_crisis
from tools.ficha import leer_ficha_usuario
from tools.limite_uso import excedio_limite_diario, mensaje_limite_alcanzado, registrar_invocacion
from tools.perfil import guardar_nombre_usuario, leer_nombre_usuario

_FABRICAS_POR_FASE = {
    1: crear_agente_explorador,
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

# Tope de preguntas del Explorador (Fase 1) antes de que el Orquestador
# empiece a insistir por código en que cierre -- ver agents/explorador.py
# para la instrucción equivalente en el prompt. Los dos frenos conviven a
# propósito (ver docstring de ese archivo): el del prompt es el criterio
# normal, este es la red de seguridad cuando el modelo no lo aplica solo
# (bug real visto en producción: una conversación real pasó de 25
# preguntas sin cerrar, hasta que la persona tuvo que pedirlo ella misma).
_UMBRAL_NUDGE_EXPLORADOR = 8
_UMBRAL_NUDGE_EXPLORADOR_FUERTE = 12
_NUDGE_EXPLORADOR = {
    "es": (
        "\n\n[Nota interna del sistema, no se la muestres a la persona: ya "
        "van bastantes preguntas en esta fase. Si ya tenés sustancia en 4 "
        "de los 5 ejes, cerrá la fase en tu respuesta a este mismo mensaje "
        "con guardar_ficha_usuario, en vez de seguir preguntando.]"
    ),
    "en": (
        "\n\n[Internal system note, don't show this to the person: this "
        "phase has had quite a few questions already. If you have "
        "substance in 4 of the 5 areas, close the phase in your reply to "
        "this very message with guardar_ficha_usuario instead of asking "
        "more.]"
    ),
}
_NUDGE_EXPLORADOR_FUERTE = {
    "es": (
        "\n\n[Nota interna del sistema, no se la muestres a la persona: "
        "esta fase ya se extendió demasiado -- cerrala en tu respuesta a "
        "este mismo mensaje con guardar_ficha_usuario, aunque algún eje "
        "haya quedado con menos detalle del ideal. No hagas más preguntas "
        "nuevas.]"
    ),
    "en": (
        "\n\n[Internal system note, don't show this to the person: this "
        "phase has run too long -- close it in your reply to this very "
        "message with guardar_ficha_usuario, even if some area ended up "
        "with less detail than ideal. Don't ask any more new questions.]"
    ),
}

# Freno de seguridad para un bug real visto en producción, distinto del
# de arriba: con el aviso fuerte ya en el texto, el Explorador escribió
# que había guardado todo y que la conversación seguía de largo, pero
# nunca LLAMÓ a guardar_ficha_usuario -- el Orquestador nunca vio una
# versión nueva, nunca cascadeó, y el mismo agente terminó improvisando
# él solo el trabajo de las fases siguientes (eligió un patrón de
# propósito, lo dio por validado, empezó a diseñar un sistema de hábito)
# sin salir nunca de Fase 1. Describir una acción en el texto no es lo
# mismo que ejecutarla -- ver agents/_modelo.py::REGLA_CIERRE_REAL_ES/EN
# para la instrucción equivalente en el prompt; esto es la red de
# seguridad por código si igual no alcanza.
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

# El mismo bug de "dijo que guardó pero no llamó a la tool" apareció
# después en el Sintetizador (Fase 2), no solo en el Explorador -- así
# que el freno de _FORZAR_CIERRE no puede depender del contador de
# turnos de Fase 1 (_UMBRAL_NUDGE_EXPLORADOR* arriba), que no tiene
# sentido para las otras fases. Esta versión general aplica en
# CUALQUIER fase, en cualquier turno: no adivina "¿ya deberían haber
# cerrado?" por cantidad de turnos, sino que verifica dos señales
# concretas después de cada invocación -- (1) ¿el texto de la respuesta
# suena a que ya guardó? (regex, ver _FRASE_CIERRE_FALSO) y (2) ¿la tool
# guardar_ficha_usuario se ejecutó de verdad en esa invocación? (el flag
# `_contenedor_guardado`, que cada agents/*.py llena desde el cuerpo real
# de su tool -- no una relectura de la ficha con reintentos, así no hay
# falso negativo por consistencia eventual de AgentCore Memory). Si (1)
# es cierto y (2) es falso, se fuerza un reintento; si (2) ya es cierto,
# no hace falta insistir aunque el texto también lo mencione.
_FRASE_CIERRE_FALSO = {
    "es": re.compile(
        r"ya\s+(lo\s+|los\s+|la\s+|las\s+)?(guard[eé]|guardamos)\b"
        r"|guard[eé]\s+(todo|el\s+avance|tu\s+elecci[oó]n|la\s+redacci[oó]n|el\s+sistema|tu\s+prop[oó]sito)"
        r"|(ya\s+)?est[aá]\s+(?:\w+\s+)?guardad[oa]"
        r"|qued[oó]\s+(?:\w+\s+)?guardad[oa]"
        r"|ha\s+sido\s+guardad[oa]",
        re.IGNORECASE,
    ),
    "en": re.compile(
        # Bug real (rama gamificacion): "the purpose is now properly
        # saved" no matcheaba nada de lo de abajo -- tercera persona/voz
        # pasiva con un adverbio en el medio ("now properly"), en vez de
        # la primera persona o "it's saved" que ya cubríamos. Los dos
        # alternativos nuevos (`is ... saved` / `has been saved`)
        # permiten como mucho una palabra de relleno entre el verbo y
        # "saved" para cubrir esa forma sin volverse tan laxos que
        # empiecen a matchear frases sin relación.
        r"\b(already\s+saved|i(?:'ve| have)?\s+saved|it'?s\s+(?:already\s+)?saved|saved\s+(?:it|that|everything|your)"
        r"|is\s+(?:now\s+)?(?:\w+\s+)?saved\b|has\s+been\s+saved)\b",
        re.IGNORECASE,
    ),
}

# Claves de `datos` que cada fase, al cerrar, tiene que garantizar que
# existan en la ficha (ver tools/ficha.py::guardar_ficha_usuario_fusionada
# y docs/agente-proposito-de-vida-prompts.md sección 7). La fusión ya
# resuelve el caso de "el modelo se olvidó de re-incluir una clave que
# una fase anterior ya había puesto" -- lo que NO resuelve es que una
# clave nunca se haya puesto NINGUNA vez (ej. el Estratega cierra la
# ficha sin incluir "sistema" -- no hay ningún valor previo del que
# heredarlo). Esto se chequea después de cualquier guardado real
# (`_contenedor_guardado`), releyendo la ficha ya fusionada.
_CAMPOS_REQUERIDOS_AL_CERRAR = {
    2: ("proposito",),
    3: ("proposito",),
    4: ("proposito", "sistema"),
    # "cumplido" (booleano) es de la rama `gamificacion` -- sin él,
    # agents/seguimiento.py::calcular_racha no tiene de qué derivar la
    # racha, así que es tan obligatorio como "proposito"/"sistema".
    5: ("proposito", "sistema", "cumplido"),
}

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


def _turnos_a_mensajes(turnos: list[dict]) -> list[dict]:
    """Convierte los turnos guardados (tools/conversacion.py) al formato
    de `Message` que espera Strands (`Agent(messages=...)`)."""
    return [{"role": t["rol"], "content": [{"text": t["texto"]}]} for t in turnos]


def _texto_completo_del_turno(mensajes_nuevos: list[dict]) -> str:
    """Concatena el texto de TODOS los mensajes de assistant generados en
    una invocación, no solo el último -- causa raíz real (no una
    casualidad de Bedrock) de buena parte de las "respuestas vacías" que
    venían apareciendo: cada prompt de fase le pide al modelo "escribí tu
    mensaje, DESPUÉS llamá a la tool" (guardar_ficha_usuario,
    presentar_opciones). Cuando el modelo hace exactamente eso, Strands
    arma DOS mensajes de assistant en la misma invocación: uno con el
    texto real + la tool call, y otro después del resultado de la tool
    que suele quedar vacío (el modelo ya dijo todo lo que tenía que
    decir). `str(self._agente(texto))` usa `AgentResult.__str__`, que
    según su propio docstring solo devuelve "the last message generated
    by the agent" -- si ese último mensaje es el vacío, el texto real del
    mensaje anterior se perdía en el camino, aunque el modelo lo hubiera
    generado perfectamente bien. Por eso acá se reconstruye a mano desde
    `Agent.messages` (la conversación completa, donde Strands va
    agregando cada mensaje del loop) en vez de confiar en el resultado
    final."""
    partes = []
    for mensaje in mensajes_nuevos:
        if mensaje.get("role") != "assistant":
            continue
        for bloque in mensaje.get("content", []):
            if isinstance(bloque, dict) and bloque.get("text"):
                partes.append(bloque["text"])
    return "\n\n".join(partes)


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
            model=crear_modelo(),
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
        # Contenedor mutable compartido con el agente de fase actual (ver
        # agents._modelo.crear_tool_presentar_opciones): la tool de un
        # agente lo llena durante self._agente(texto); _invocar lo limpia
        # antes de cada invocación y quien llama a enviar_mensaje/
        # abrir_conversacion lee la instantánea apenas termina esa
        # invocación puntual.
        self._contenedor_opciones: list = []
        # Mismo patrón, para saber con certeza (no por relectura de la
        # ficha, que puede tardar en reflejar un guardado por consistencia
        # eventual) si guardar_ficha_usuario se ejecutó de verdad en la
        # última invocación -- cada agents/*.py lo llena desde el cuerpo
        # real de esa tool. Ver _FRASE_CIERRE_FALSO.
        self._contenedor_guardado: list = []
        self.fase_actual = self._determinar_fase_inicial()
        self._agente: Agent | None = None if self._pidiendo_nombre else self._crear_agente_fase(self.fase_actual)

    def _crear_agente_fase(self, fase: int) -> Agent:
        turnos = leer_turnos(self.usuario_id, fase)
        return _FABRICAS_POR_FASE[fase](
            self.usuario_id,
            self.idioma,
            mensajes_previos=_turnos_a_mensajes(turnos),
            nombre=self.nombre,
            contenedor_opciones=self._contenedor_opciones,
            contenedor_guardado=self._contenedor_guardado,
        )

    def _invocar_una_vez(self, texto: str) -> str:
        self._contenedor_opciones.clear()
        self._contenedor_guardado.clear()
        indice_previo = len(self._agente.messages)
        self._agente(texto)
        registrar_invocacion(self.usuario_id)
        # Reconstruye el texto desde Agent.messages en vez de confiar en
        # str(resultado) -- ver docstring de _texto_completo_del_turno.
        return _texto_completo_del_turno(self._agente.messages[indice_previo:]).strip()

    def _invocar(self, texto: str) -> str:
        """Invoca al agente de la fase actual, salvo que esta cuenta ya
        haya llegado al límite diario de invocaciones reales
        (tools/limite_uso.py) -- en ese caso corta antes de tocar Bedrock
        y devuelve el aviso fijo, sin generar costo. Cuenta cada
        invocación real, no cada mensaje de la persona: una cascada de
        cambio de fase dispara más de una por mensaje, y cada una cuesta
        igual, así que cada una cuenta para el límite.

        Nunca devuelve un string vacío: AgentCore Memory rechaza guardar
        un turno con texto de largo 0 (`ParamValidationError`, bug real
        visto en producción que tumbaba toda la app) y una burbuja en
        blanco tampoco le sirve a la persona. Si la respuesta viene
        vacía, reintenta una vez con un empujón explícito antes de
        resignarse a un aviso fijo -- mismo criterio que el resto de los
        reintentos acotados del proyecto (GuardaEstilo, la relectura de
        la ficha): como mucho un reintento, nunca un loop sin límite."""
        if excedio_limite_diario(self.usuario_id):
            return mensaje_limite_alcanzado(self.idioma)
        respuesta = self._invocar_una_vez(texto)
        if not respuesta and not excedio_limite_diario(self.usuario_id):
            respuesta = self._invocar_una_vez(_RESPUESTA_VACIA_RETRY[self.idioma])
        return respuesta or _RESPUESTA_VACIA_FALLBACK[self.idioma]

    def _preparar_texto_y_forzado(self, texto: str) -> tuple[str, bool]:
        """Le agrega al texto que ve el modelo (nunca a lo que se guarda
        en tools/conversacion.py) un recordatorio interno de cerrar la
        fase si el Explorador ya lleva demasiados turnos -- ver
        _UMBRAL_NUDGE_EXPLORADOR arriba. El segundo valor de la tupla
        indica si se aplicó el aviso fuerte: en ese caso, `enviar_mensaje`
        exige que la tool se haya ejecutado de verdad (no alcanza con que
        el texto *suene* a un cierre) y fuerza un reintento si no."""
        if self.fase_actual != 1:
            return texto, False
        turnos_previos = len(leer_turnos(self.usuario_id, 1)) // 2
        if turnos_previos >= _UMBRAL_NUDGE_EXPLORADOR_FUERTE:
            return texto + _NUDGE_EXPLORADOR_FUERTE[self.idioma], True
        if turnos_previos >= _UMBRAL_NUDGE_EXPLORADOR:
            return texto + _NUDGE_EXPLORADOR[self.idioma], False
        return texto, False

    def _dice_que_guardo_sin_guardar(self, respuesta: str) -> bool:
        """True si el texto de la respuesta suena a que ya guardó el
        avance (regex _FRASE_CIERRE_FALSO) pero guardar_ficha_usuario NO
        se ejecutó de verdad en la última invocación (`_contenedor_guardado`
        vacío). Bug real visto primero en el Explorador y después en el
        Sintetizador -- no es privativo de una fase, así que este chequeo
        se aplica parejo en cualquiera (ver `_invocar_verificado`)."""
        if self._contenedor_guardado:
            return False
        patron = _FRASE_CIERRE_FALSO.get(self.idioma, _FRASE_CIERRE_FALSO["es"])
        return bool(patron.search(respuesta))

    def _campos_faltantes(self, fase: int) -> tuple[str, ...]:
        """Si guardar_ficha_usuario se ejecutó de verdad en la última
        invocación (`_contenedor_guardado`) para `fase`, pero a la ficha
        ya fusionada (`tools.ficha.guardar_ficha_usuario_fusionada`)
        todavía le falta alguna clave que esa fase tiene que garantizar
        (`_CAMPOS_REQUERIDOS_AL_CERRAR`), las devuelve. La fusión ya
        resuelve "se olvidó de re-incluir una clave que una fase anterior
        ya había puesto" -- esto detecta el caso que la fusión no puede
        arreglar sola: que nunca se haya puesto, ni siquiera esta vez
        (ej. el Estratega cierra la ficha sin incluir "sistema", que es
        nuevo en esta fase, no hay ningún valor previo del que
        heredarlo)."""
        if not self._contenedor_guardado:
            return ()
        requeridos = _CAMPOS_REQUERIDOS_AL_CERRAR.get(fase, ())
        if not requeridos:
            return ()
        ficha = leer_ficha_usuario(self.usuario_id)
        datos = (ficha["actual"] or {}).get("datos", {}) if ficha["existe"] else {}
        # "is None" y no una verificación de verdad -- un campo booleano
        # como "cumplido" (rama gamificacion) es legítimamente `False`
        # cuando la persona no sostuvo el hábito, y eso NO es lo mismo
        # que faltar. Solo la ausencia real de la clave (o un `None`
        # explícito) cuenta como faltante.
        return tuple(campo for campo in requeridos if (datos or {}).get(campo) is None)

    def _invocar_verificado(self, texto: str) -> str:
        """Invoca y, si la respuesta suena a que ya guardó pero la tool
        no se ejecutó de verdad, o si guardó mas le faltó alguna clave
        obligatoria de esta fase, fuerza un reintento sin ambigüedad
        antes de devolverla -- envoltorio de `_invocar` que se usa en
        todos los puntos donde se invoca a un agente de fase, para que
        estas verificaciones no dependan de acordarse de aplicarlas cada
        vez."""
        respuesta = self._invocar(texto)
        if self._dice_que_guardo_sin_guardar(respuesta):
            respuesta = self._invocar(_FORZAR_CIERRE[self.idioma])
        faltantes = self._campos_faltantes(self.fase_actual)
        if faltantes:
            campos = ", ".join(f'"{campo}"' for campo in faltantes)
            respuesta = self._invocar(_FALTAN_CAMPOS[self.idioma].format(campos=campos))
        return respuesta

    def abrir_conversacion(self):
        """Generador: el agente de la fase actual habla primero, sin
        esperar texto de la persona -- se llama una sola vez, al abrir
        la sesión (nueva o retomada). Sin esto, el sistema siempre se
        queda esperando a que la persona adivine qué escribir primero,
        incluso en Fase 5, que según el spec tiene que mostrar la Vista
        de resumen apenas se abre la conversación, no después.

        Si todavía no se capturó el nombre de la persona (Paso 0), lo
        pide directo en código, sin invocar ningún agente.

        No revisa el guardrail de crisis (no hay texto de la persona
        que revisar) ni avanza de fase (abrir no cierra nada)."""
        if self._pidiendo_nombre:
            yield 0, _PEDIR_NOMBRE[self.idioma], []
            return

        kickoff = _KICKOFF[self.idioma]
        respuesta = self._invocar_verificado(kickoff)
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
        """Cierra el Paso 0: guarda el nombre, arma recién ahora el
        agente de la fase en la que ya estaba esta persona (nueva o
        retomada) y lo hace hablar primero en el mismo turno, con el
        mismo mecanismo de arranque que una cascada de cambio de fase --
        así la persona nunca ve un chat esperando en silencio después de
        contestar."""
        nombre = _extraer_nombre(texto, self.idioma, self.usuario_id)
        guardar_nombre_usuario(self.usuario_id, nombre)
        self.nombre = nombre
        self._pidiendo_nombre = False
        self._agente = self._crear_agente_fase(self.fase_actual)

        kickoff = _KICKOFF[self.idioma]
        respuesta = self._invocar_verificado(kickoff)
        guardar_intercambio(self.usuario_id, self.fase_actual, kickoff, respuesta)
        yield self.fase_actual, respuesta, list(self._contenedor_opciones)

    def enviar_mensaje(self, texto: str):
        """Generador: entrega (fase, texto, opciones) por cada mensaje, en
        el orden en que se van generando -- no un solo string con todo
        junto. `opciones` es la lista (posiblemente vacía) que haya
        dejado la tool `presentar_opciones` en esta invocación -- ver
        docstring del módulo."""
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
        texto_efectivo, forzar_cierre_duro = self._preparar_texto_y_forzado(texto)
        respuesta = self._invocar(texto_efectivo)

        if forzar_cierre_duro and not self._contenedor_guardado:
            # Freno de seguridad: el aviso fuerte ya le pedía cerrar en
            # este mismo turno, pero la tool guardar_ficha_usuario no se
            # ejecutó -- sin importar si el texto sonaba a que sí cerró.
            # Un reintento más, sin ambigüedad, antes de dejarlo pasar.
            respuesta = self._invocar(_FORZAR_CIERRE[self.idioma])
        elif self._dice_que_guardo_sin_guardar(respuesta):
            # Mismo bug, en cualquier otra fase (no depende del contador
            # de turnos de Fase 1): el texto suena a que ya guardó pero
            # la tool no se ejecutó -- bug real visto en el Sintetizador.
            respuesta = self._invocar(_FORZAR_CIERRE[self.idioma])

        faltantes = self._campos_faltantes(fase_antes)
        if faltantes:
            # Guardó de verdad, pero le faltó una clave que esta fase
            # tiene que garantizar (ej. "sistema" en el cierre de Fase 4)
            # y que ninguna versión anterior tiene para heredar por
            # fusión -- ver tools.ficha.guardar_ficha_usuario_fusionada.
            campos = ", ".join(f'"{campo}"' for campo in faltantes)
            respuesta = self._invocar(_FALTAN_CAMPOS[self.idioma].format(campos=campos))

        guardar_intercambio(self.usuario_id, fase_antes, texto, respuesta)
        yield fase_antes, respuesta, list(self._contenedor_opciones)

        self._avanzar_fase_si_corresponde(total_versiones_antes)

        # La fase cambió en este mismo turno: si el destino no es Fase 5
        # (que espera a una conversación nueva, no continúa en caliente),
        # arrancamos al agente siguiente ya mismo para no dejar a la
        # persona esperando sin saber que le toca escribir algo. Se
        # entrega como un mensaje aparte, no concatenado al anterior --
        # así quien llama puede mostrar el primero apenas está listo, sin
        # esperar a que este segundo termine de generarse.
        if self.fase_actual != fase_antes and self.fase_actual != 5:
            kickoff = _KICKOFF[self.idioma]
            continuacion = self._invocar_verificado(kickoff)
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

    def _avanzar_fase_si_corresponde(self, total_versiones_antes: int) -> None:
        ficha = self._leer_ficha_con_reintento(total_versiones_antes)
        if not ficha["existe"]:
            return

        total_versiones = len(ficha["historial"]) + 1
        if total_versiones <= total_versiones_antes:
            return  # no se guardó nada nuevo en este turno, seguimos en la misma fase

        actual = ficha["actual"]
        if actual["fase"] != self.fase_actual:
            return  # la versión nueva no corresponde a la fase en curso

        if self.fase_actual in (1, 2, 3):
            self._pasar_a_fase(self.fase_actual + 1)
        elif self.fase_actual == 4:
            self._pasar_a_fase(5)
        elif self.fase_actual == 5:
            reentrada = (actual["datos"] or {}).get("reentrada")
            if reentrada == "fase3":
                self._pasar_a_fase(3)
            elif reentrada == "fase4":
                self._pasar_a_fase(4)
            # sin reentrada: se queda en Fase 5 hasta la próxima sesión

    def _pasar_a_fase(self, fase: int) -> None:
        self.fase_actual = fase
        # Precarga los turnos que puedan existir de un paso anterior por
        # esta misma fase (p. ej. Fase 5 reentra a Fase 3): limitación
        # conocida, no distingue el primer intento del segundo -- ver
        # tools/conversacion_agentcore.py.
        self._agente = self._crear_agente_fase(fase)
