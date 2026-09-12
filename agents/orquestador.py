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

import logging
import time
import uuid

from pydantic import BaseModel
from strands.agent import Agent

from agents._modelo import crear_modelo_subagente
from agents.coach_validacion import crear_agente_coach_validacion
from agents.estratega_sistemas import crear_agente_estratega_sistemas
from agents.explorador import crear_agente_explorador
from agents.seguimiento import crear_agente_seguimiento
from agents.sintetizador import crear_agente_sintetizador
from tools.contexto_usuario import agregar_insight
from tools.conversacion import guardar_intercambio, leer_turnos
from tools.crisis import detectar_señal_crisis, mensaje_crisis, registrar_evento_crisis
from tools.ficha import leer_ficha_usuario
from tools.limite_uso import excedio_limite_diario, mensaje_limite_alcanzado, registrar_invocacion
from tools.perfil import guardar_nombre_usuario, leer_nombre_usuario

logger = logging.getLogger(__name__)

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

# Tope de preguntas del Explorador (Fase 1): DESACTIVADO por ahora (rama
# gamificacion). La idea era una red de seguridad por código además del
# criterio del prompt (ver agents/explorador.py) para el bug real de una
# conversación que pasó de 25 preguntas sin cerrar -- pero el mecanismo
# (`_nudge_explorador` de abajo) agregaba texto extra al system prompt del
# Explorador turno a turno, y sospechamos que ESO contribuía a que Haiku
# terminara respondiendo texto plano sin llamar a `informar_al_orquestador`
# (ver bug documentado más abajo, `_RESPUESTA_VACIA_FALLBACK`). Sacado
# mientras se confirma esa hipótesis con el logging nuevo de
# `_invocar_una_vez` -- si el freno de 25 preguntas vuelve a aparecer,
# reinstalarlo de una forma que no toque el system prompt (ej. un mensaje
# de usuario aparte, no una concatenación al prompt existente).
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
