"""Orquestador. Ver docs/agente-proposito-de-vida-prompts.md sección 1 y
C:\\Users\\Wendy\\.claude\\plans\\cosmic-zooming-tarjan.md (orquestador
agéntico, rama gamificacion).

No conversa directamente sobre contenido de propósito: aplica el
guardrail de crisis en cada turno, antes que cualquier otra cosa, y
después arma un `Agent` orquestador (agents/orquestador_agente.py) con
los 5 agentes de fase expuestos como tools, para que decida con juicio
semántico a cuál invocar -- Fase 1→2→3→4 sigue siendo un flujo fijo (no
se saltan pasos, reforzado por la descripción de cada tool), Fase 5 es
dinámica y puede reinyectar al usuario en Fase 3 o 4.

Cada agente de fase, según el spec, guarda su ficha exactamente una vez,
al cerrar su fase (no hay saves parciales a mitad de fase). A diferencia
del diseño anterior (que inferí "¿cerró?" leyendo si el texto sonaba a
un cierre, con un regex), cada agente de fase ahora declara explícitamente
`cerrado: bool` en su tool `informar_al_orquestador` -- y ese booleano se
verifica contra AgentCore Memory (¿la ficha realmente tiene una versión
nueva?) antes de confiar en él, exactamente igual que antes se verificaba
`_contenedor_guardado`.

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

import time

from strands.agent import Agent

from agents._modelo import crear_modelo_subagente
from agents.coach_validacion import crear_agente_coach_validacion
from agents.estratega_sistemas import crear_agente_estratega_sistemas
from agents.explorador import crear_agente_explorador
from agents.orquestador_agente import crear_agente_orquestador
from agents.seguimiento import crear_agente_seguimiento
from agents.sintetizador import crear_agente_sintetizador
from tools.contexto_usuario import agregar_insight, leer_insights
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
# mismo que ejecutarla -- ver agents/_modelo.py::INSTRUCCION_INFORME_ES/EN
# (el `cerrado: bool` que declara informar_al_orquestador) para la
# instrucción equivalente en el prompt; esto es la red de seguridad por
# código si igual no alcanza.
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

    def _construir_agentes_fase(self) -> tuple[dict[int, Agent], dict[int, dict[str, list]]]:
        """Arma los 5 agentes de fase, siempre los 5 -- el orquestador
        agéntico elige con su propio juicio semántico a cuál invocar (ver
        agents/orquestador_agente.py), en vez de que el código restrinja
        el toolset a "solo la fase actual". El freno real sigue siendo
        _verificar_y_reforzar más abajo, que confirma contra AgentCore
        Memory lo que se haya declarado antes de confiar en nada.

        Cada fase tiene su propia tripleta de contenedores (opciones/
        guardado/informe) para poder distinguir cuál de las 5 respondió
        este turno -- no se puede compartir un solo contenedor entre las
        5 porque, si el orquestador llegara a invocar más de una (no
        debería, pero nada lo impide a nivel de tipos), se pisarían entre
        sí."""
        agentes: dict[int, Agent] = {}
        contenedores: dict[int, dict[str, list]] = {}
        for fase, fabrica in _FABRICAS_POR_FASE.items():
            contenedor_opciones: list = []
            contenedor_guardado: list = []
            contenedor_informe: list = []
            turnos = leer_turnos(self.usuario_id, fase)
            agente = fabrica(
                self.usuario_id,
                self.idioma,
                mensajes_previos=_turnos_a_mensajes(turnos),
                nombre=self.nombre,
                contenedor_opciones=contenedor_opciones,
                contenedor_guardado=contenedor_guardado,
                contenedor_informe=contenedor_informe,
            )
            if fase == 1:
                nudge = self._nudge_explorador()
                if nudge:
                    agente.system_prompt = agente.system_prompt + nudge
            agentes[fase] = agente
            contenedores[fase] = {
                "opciones": contenedor_opciones,
                "guardado": contenedor_guardado,
                "informe": contenedor_informe,
            }
        return agentes, contenedores

    def _nudge_explorador(self) -> str:
        """Recordatorio inyectado en el SYSTEM PROMPT del Explorador (no
        en el mensaje de la persona, como antes -- el orquestador es
        quien arma el input que ve la tool, no el código) si ya lleva
        demasiados turnos sin cerrar. Ver _UMBRAL_NUDGE_EXPLORADOR* y el
        docstring de agents/explorador.py."""
        if self.fase_actual != 1:
            return ""
        turnos_previos = len(leer_turnos(self.usuario_id, 1)) // 2
        if turnos_previos >= _UMBRAL_NUDGE_EXPLORADOR_FUERTE:
            return _NUDGE_EXPLORADOR_FUERTE[self.idioma]
        if turnos_previos >= _UMBRAL_NUDGE_EXPLORADOR:
            return _NUDGE_EXPLORADOR[self.idioma]
        return ""

    def _turno_supera_umbral_fuerte(self) -> bool:
        """True si el Explorador ya lleva turnos como para exigir el
        cierre sin ambigüedad, sin importar lo que declare -- freno de
        seguridad equivalente al `forzar_cierre_duro` de antes, ver
        _verificar_y_reforzar."""
        if self.fase_actual != 1:
            return False
        return (len(leer_turnos(self.usuario_id, 1)) // 2) >= _UMBRAL_NUDGE_EXPLORADOR_FUERTE

    def _resumir_estado_ficha(self) -> str:
        """Texto corto que el orquestador agéntico ve en su prompt --
        derivado de la ficha real (AgentCore Memory), no una suposición
        del modelo sobre en qué fase está la persona."""
        ficha = leer_ficha_usuario(self.usuario_id)
        if not ficha["existe"]:
            return "No ficha yet -- no phase has closed." if self.idioma == "en" else "Todavía no hay ficha -- ninguna fase cerró."
        actual = ficha["actual"] or {}
        fase_cerrada = actual.get("fase")
        reentrada = (actual.get("datos") or {}).get("reentrada")
        if self.idioma == "en":
            base = f"Last closed phase: {fase_cerrada}. Continuing in phase: {self.fase_actual}."
            if reentrada:
                base += f" Pending re-entry into {reentrada}."
            return base
        base = f"Última fase cerrada: {fase_cerrada}. Continúa en la fase: {self.fase_actual}."
        if reentrada:
            base += f" Reingreso pendiente a {reentrada}."
        return base

    def _invocar_una_vez(self, texto: str) -> tuple[int, str, bool]:
        """Arma el orquestador agéntico (con los 5 subagentes como tools)
        y lo invoca una vez. Devuelve (fase_que_respondió,
        texto_para_la_persona, cerrado_declarado) -- el texto sale del
        informe estructurado que el subagente le dejó al orquestador
        (`informar_al_orquestador`), nunca del propio texto del
        orquestador (ver plan de migración, sección 6: no hay garantía
        de que el `AgentResult` del orquestador conserve el texto
        completo del subagente delegado). Cualquier `dato_nuevo` del
        informe se persiste como insight de una vez."""
        agentes, contenedores = self._construir_agentes_fase()
        estado = self._resumir_estado_ficha()
        insights = leer_insights(self.usuario_id)
        orquestador = crear_agente_orquestador(agentes, estado, insights, self.idioma)

        mensajes_antes = {fase: len(agente.messages) for fase, agente in agentes.items()}
        orquestador(texto)
        registrar_invocacion(self.usuario_id)  # la llamada del orquestador

        for fase, agente in agentes.items():
            contenedor = contenedores[fase]
            fue_invocado = len(agente.messages) > mensajes_antes[fase]
            if not fue_invocado:
                continue
            if not contenedor["informe"] and not excedio_limite_diario(self.usuario_id):
                # La tool obligatoria no se llamó -- un reintento apuntado
                # sobre ESTE MISMO agente (ya invocado este turno, no se
                # pierde lo que generó) antes de resignarse. Ver
                # _FORZAR_INFORME.
                agente(_FORZAR_INFORME[self.idioma])
                registrar_invocacion(self.usuario_id)
            if not contenedor["informe"]:
                continue
            informe = contenedor["informe"][-1]
            self._contenedor_opciones = list(contenedor["opciones"])
            dato_nuevo = informe.get("dato_nuevo")
            if dato_nuevo:
                agregar_insight(self.usuario_id, dato_nuevo)
            return fase, (informe.get("texto") or "").strip(), bool(informe.get("cerrado"))

        self._contenedor_opciones = []
        return self.fase_actual, "", False

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
        límite."""
        if excedio_limite_diario(self.usuario_id):
            return self.fase_actual, mensaje_limite_alcanzado(self.idioma), False
        fase, respuesta, cerrado = self._invocar_una_vez(texto)
        if not respuesta and not excedio_limite_diario(self.usuario_id):
            fase, respuesta, cerrado = self._invocar_una_vez(_RESPUESTA_VACIA_RETRY[self.idioma])
        return fase, (respuesta or _RESPUESTA_VACIA_FALLBACK[self.idioma]), cerrado

    def _invocar_fase_directo(self, fase: int, texto: str) -> tuple[str, bool]:
        """Invoca UNA fase puntual directo, sin pasar por el orquestador
        -- usado solo por los frenos de seguridad de _verificar_y_reforzar
        (forzar cierre, completar campos faltantes) y por los mensajes de
        arranque (abrir_conversacion, cascada de cambio de fase), donde
        ya se sabe con certeza a qué fase invocar y no tiene sentido
        gastar otra decisión del orquestador. Devuelve (texto, cerrado)."""
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
        )
        agente(texto)
        registrar_invocacion(self.usuario_id)
        if not contenedor_informe and not excedio_limite_diario(self.usuario_id):
            # Misma red de seguridad que _invocar_una_vez -- ver
            # _FORZAR_INFORME.
            agente(_FORZAR_INFORME[self.idioma])
            registrar_invocacion(self.usuario_id)
        self._contenedor_opciones = list(contenedor_opciones)
        if not contenedor_informe:
            return "", False
        informe = contenedor_informe[-1]
        dato_nuevo = informe.get("dato_nuevo")
        if dato_nuevo:
            agregar_insight(self.usuario_id, dato_nuevo)
        return (informe.get("texto") or "").strip(), bool(informe.get("cerrado"))

    def _verificar_y_reforzar(
        self, fase: int, respuesta: str, cerrado_declarado: bool, total_versiones_antes: int, forzar: bool = False
    ) -> str:
        """Después de invocar `fase` (por el orquestador o directo),
        confirma contra AgentCore Memory -- no contra lo que el modelo
        declaró de sí mismo -- que lo que pasó es consistente, y fuerza
        como mucho un reintento por cada chequeo, directo a esa misma
        fase (no vuelve a pasar por el orquestador, ya no hay ninguna
        decisión de ruteo pendiente):

        1. Si se declaró `cerrado=True` (o `forzar=True`, freno de
           turnos del Explorador) pero AgentCore Memory no tiene una
           versión nueva, reintenta con _FORZAR_CIERRE.
        2. Si sí hay una versión nueva de esta fase, pero le falta alguna
           clave obligatoria (_CAMPOS_REQUERIDOS_AL_CERRAR), reintenta
           con _FALTAN_CAMPOS."""
        if (cerrado_declarado or forzar) and self._contar_versiones() <= total_versiones_antes:
            respuesta, _ = self._invocar_fase_directo(fase, _FORZAR_CIERRE[self.idioma])

        ficha = self._leer_ficha_con_reintento(total_versiones_antes)
        hubo_guardado = (len(ficha["historial"]) + (1 if ficha["existe"] else 0)) > total_versiones_antes
        if hubo_guardado and ficha["actual"]["fase"] == fase:
            datos = ficha["actual"]["datos"] or {}
            requeridos = _CAMPOS_REQUERIDOS_AL_CERRAR.get(fase, ())
            # "is None" y no una verificación de verdad -- un campo
            # booleano como "cumplido" (rama gamificacion) es
            # legítimamente `False` cuando la persona no sostuvo el
            # hábito, y eso NO es lo mismo que faltar.
            faltantes = tuple(c for c in requeridos if datos.get(c) is None)
            if faltantes:
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
        respuesta, cerrado = self._invocar_fase_directo(self.fase_actual, kickoff)
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
        respuesta, cerrado = self._invocar_fase_directo(self.fase_actual, kickoff)
        respuesta = self._verificar_y_reforzar(self.fase_actual, respuesta, cerrado, total_versiones_antes)
        guardar_intercambio(self.usuario_id, self.fase_actual, kickoff, respuesta)
        yield self.fase_actual, respuesta, list(self._contenedor_opciones)

    def enviar_mensaje(self, texto: str):
        """Generador: entrega (fase, texto, opciones) por cada mensaje, en
        el orden en que se van generando -- no un solo string con todo
        junto. `opciones` es la lista (posiblemente vacía) que haya
        dejado la tool `presentar_opciones` en esta invocación -- ver
        docstring del módulo.

        El mensaje de la persona pasa por el orquestador agéntico
        (agents/orquestador_agente.py), que decide a qué fase invocar --
        a diferencia de los mensajes de arranque (abrir_conversacion,
        cascada de cambio de fase más abajo), donde ya se sabe con
        certeza cuál es y se invoca directo."""
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
        forzar_cierre_duro = self._turno_supera_umbral_fuerte()
        fase_respondio, respuesta, cerrado = self._invocar(texto)
        # Público, de solo lectura, para diagnóstico (scripts/
        # simular_conversacion.py): qué fase respondió y qué declaró
        # ANTES del reintento forzado de _verificar_y_reforzar -- así se
        # puede ver si el freno tuvo que intervenir, no solo el resultado
        # final ya corregido.
        self.ultima_fase_respondio = fase_respondio
        self.ultimo_cerrado_declarado = cerrado
        respuesta = self._verificar_y_reforzar(
            fase_respondio, respuesta, cerrado, total_versiones_antes, forzar=forzar_cierre_duro
        )

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
            continuacion, cerrado_cascada = self._invocar_fase_directo(self.fase_actual, kickoff)
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
        """`fase_que_respondio` es la fase que el orquestador agéntico
        realmente invocó este turno (no necesariamente `self.fase_actual`
        de antes del turno -- en el caso normal coinciden, ver
        agents/orquestador_agente.py, pero el avance se calcula sobre lo
        que de verdad pasó, no sobre lo que se esperaba que pasara)."""
        ficha = self._leer_ficha_con_reintento(total_versiones_antes)
        if not ficha["existe"]:
            return

        total_versiones = len(ficha["historial"]) + 1
        if total_versiones <= total_versiones_antes:
            return  # no se guardó nada nuevo en este turno, seguimos en la misma fase

        actual = ficha["actual"]
        if actual["fase"] != fase_que_respondio:
            return  # la versión nueva no corresponde a la fase que respondió

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
