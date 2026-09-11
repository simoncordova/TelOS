"""Interfaz Streamlit de Telos — 100% Python, sin HTML/JS/CSS.

Envoltorio delgado sobre agents.orquestador.SesionTelos: la lógica de
fases, guardrail y persistencia vive ahí, no acá. Login con Google vía
Cognito (ui/auth.py) — ver ese módulo para la config necesaria.

Idioma: selector explícito ES/EN (no autodetección) — ver sección 0.5 de
docs/agente-proposito-de-vida-prompts.md. El guardrail de crisis revisa
ambos idiomas siempre, sin importar lo que esté seleccionado acá.

Layout: no es un chat lineal a secas. De arriba a abajo en el área
principal: una tarjeta de bienvenida (solo la primera vez, antes de que
la persona diga su nombre -- explica de qué va la app y el camino de 5
pasos, sin ser un wizard largo), un mapa del camino (las 5 fases como
paradas, con un popover por parada para espiar lo que ya se definió
ahí), la tarjeta de la Vista de resumen cuando estás en Fase 5 (código,
no el texto del agente — ver agents/seguimiento.py), y recién después el
chat. En la barra lateral:
"Tus resultados" (propósito + sistema, el sistema como checklist si el
modelo siguió el formato de líneas etiquetadas), "Tu evolución"
(historial de versiones) y exportar la ficha. La barra lateral se
desplaza aparte del área principal en Streamlit -- por eso "Tus
resultados" vive ahí y no en una columna junto al chat, que en charlas
largas terminaba perdiéndose scroll abajo (bug real reportado). Se relee
la ficha en cada rerun, así que todo esto se actualiza solo apenas un
agente guarda una versión nueva.
"""

import os
import sys
from datetime import datetime
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import ui.auth as auth  # noqa: E402
from agents.orquestador import SesionTelos  # noqa: E402
from agents.seguimiento import construir_vista_resumen  # noqa: E402
from tools.ficha import leer_ficha_usuario  # noqa: E402

st.set_page_config(page_title="Telos", page_icon="🧭")

_NOMBRES_FASE = {
    "es": {0: "Bienvenida", 1: "Explorador", 2: "Sintetizador", 3: "Coach de Validación", 4: "Estratega de Sistemas", 5: "Seguimiento"},
    "en": {0: "Welcome", 1: "Explorer", 2: "Synthesizer", 3: "Validation Coach", 4: "Systems Strategist", 5: "Follow-up"},
}

# Iconos cortos para el mapa del camino (columna angosta) -- nombres
# completos quedan en el popover, no en la etiqueta del botón.
_ICONOS_FASE = {
    1: "🔎",
    2: "🪞",
    3: "🧭",
    4: "🛠️",
    5: "🔁",
}

_TEXTOS = {
    "es": {
        "caption": "El propósito no es una meta, es un horizonte.",
        "login_button": "Iniciar sesión",
        "logout_button": "Cerrar sesión",
        "connected_as": "Conectado como {usuario_id}",
        "saludo_nombre": "Hola, {nombre}",
        "cognito_missing": (
            "Falta configurar Cognito (COGNITO_DOMAIN / COGNITO_USER_POOL_ID / "
            "COGNITO_CLIENT_ID / COGNITO_CLIENT_SECRET / APP_URL). Si estás "
            "corriendo localmente sin login, poné TELOS_REQUIRE_LOGIN=0."
        ),
        "login_failed": "No se pudo completar el login: {error}",
        "id_label": "Tu identificador (login deshabilitado, TELOS_REQUIRE_LOGIN=0)",
        "id_missing": "Escribe un identificador en la barra lateral para empezar.",
        "fase_label": "Fase actual",
        "chat_placeholder": "Escribe aquí...",
        "spinner": "...",
        "idioma_label": "Idioma / Language",
        "panel_titulo": "Tus resultados",
        "panel_proposito": "Propósito",
        "panel_sistema": "Sistema",
        "panel_vacio_proposito": "Todavía no lo definiste.",
        "panel_vacio_sistema": "Todavía no lo definiste.",
        "opciones_titulo": "Elegí una opción, o escribí tu respuesta abajo:",
        "opciones_submit": "Elegir",
        "resumen_titulo": "Tu resumen",
        "camino_peek_vacio": "Todavía no hay nada guardado acá.",
        "camino_peek_fase1": "Acá arrancó todo: valores, momentos de flow, qué harías sin que te paguen, tu legado, qué evitás aunque \"deberías\".",
        "evolucion_titulo": "Tu evolución",
        "evolucion_vacio": "Todavía no hay versiones guardadas.",
        "exportar_boton": "⬇️ Descargar tu ficha",
        "exportar_nombre_archivo": "telos_ficha.txt",
        "exportar_contenido": (
            "Telos — tu ficha\n"
            "Nombre: {nombre}\n\n"
            "Propósito:\n{proposito}\n\n"
            "Sistema:\n{sistema}\n\n"
            "Última actualización: {fecha}\n"
        ),
        "exportar_sin_dato": "(sin definir)",
        "bienvenida_titulo": "👋 Bienvenido a Telos",
        "bienvenida_texto": (
            "Vamos a explorar tu propósito de vida en una conversación corta, "
            "en 5 pasos:\n\n"
            "1. 🔎 **Explorador** — ponés en palabras lo que te mueve\n"
            "2. 🪞 **Sintetizador** — te reflejamos 2 o 3 propósitos posibles\n"
            "3. 🧭 **Coach de Validación** — lo ponemos a prueba con tu propia experiencia\n"
            "4. 🛠️ **Estratega de Sistemas** — lo convertimos en un hábito concreto\n"
            "5. 🔁 **Seguimiento** — check-ins breves cada vez que vuelvas\n\n"
            "No es una meta con fecha límite — es un horizonte. Para arrancar, "
            "contame cómo te llamas 👇"
        ),
    },
    "en": {
        "caption": "Purpose isn't a goal to reach, it's a horizon.",
        "login_button": "Sign in",
        "logout_button": "Sign out",
        "connected_as": "Signed in as {usuario_id}",
        "saludo_nombre": "Hi, {nombre}",
        "cognito_missing": (
            "Cognito isn't configured (COGNITO_DOMAIN / COGNITO_USER_POOL_ID / "
            "COGNITO_CLIENT_ID / COGNITO_CLIENT_SECRET / APP_URL). If you're "
            "running locally without login, set TELOS_REQUIRE_LOGIN=0."
        ),
        "login_failed": "Login could not be completed: {error}",
        "id_label": "Your identifier (login disabled, TELOS_REQUIRE_LOGIN=0)",
        "id_missing": "Type an identifier in the sidebar to get started.",
        "fase_label": "Current phase",
        "chat_placeholder": "Type here...",
        "spinner": "...",
        "idioma_label": "Idioma / Language",
        "panel_titulo": "Your results",
        "panel_proposito": "Purpose",
        "panel_sistema": "System",
        "panel_vacio_proposito": "Not defined yet.",
        "panel_vacio_sistema": "Not defined yet.",
        "opciones_titulo": "Pick one, or type your own answer below:",
        "opciones_submit": "Choose",
        "resumen_titulo": "Your summary",
        "camino_peek_vacio": "Nothing saved here yet.",
        "camino_peek_fase1": "This is where it all started: values, flow moments, what you'd do for free, your legacy, what you avoid even though you \"should.\"",
        "evolucion_titulo": "Your evolution",
        "evolucion_vacio": "No saved versions yet.",
        "exportar_boton": "⬇️ Download your ficha",
        "exportar_nombre_archivo": "telos_ficha.txt",
        "exportar_contenido": (
            "Telos — your ficha\n"
            "Name: {nombre}\n\n"
            "Purpose:\n{proposito}\n\n"
            "System:\n{sistema}\n\n"
            "Last updated: {fecha}\n"
        ),
        "exportar_sin_dato": "(not defined)",
        "bienvenida_titulo": "👋 Welcome to Telos",
        "bienvenida_texto": (
            "We're going to explore your life purpose in a short "
            "conversation, in 5 steps:\n\n"
            "1. 🔎 **Explorer** — put into words what moves you\n"
            "2. 🪞 **Synthesizer** — we reflect back 2 or 3 possible purposes\n"
            "3. 🧭 **Validation Coach** — we stress-test it against your own experience\n"
            "4. 🛠️ **Systems Strategist** — we turn it into a concrete habit\n"
            "5. 🔁 **Follow-up** — brief check-ins every time you come back\n\n"
            "It's not a goal with a deadline — it's a horizon. To get "
            "started, tell me your name 👇"
        ),
    },
}

_REQUIERE_LOGIN = os.environ.get("TELOS_REQUIRE_LOGIN", "1") != "0"


def _fecha_corta(fecha_iso: str) -> str:
    try:
        return datetime.fromisoformat(fecha_iso).strftime("%Y-%m-%d %H:%M")
    except (ValueError, TypeError):
        return fecha_iso or ""


def _parsear_sistema(sistema_texto: str) -> list[tuple[str, str]]:
    """Separa el string de "sistema" (formato libre de líneas
    "Etiqueta: valor", ver agents/estratega_sistemas.py) en filas para
    mostrarlas como checklist en vez de un bloque de texto plano. Si el
    modelo no siguió ese formato, devuelve una sola fila con todo el
    texto tal cual -- nunca falla, solo se degrada a texto plano."""
    if not sistema_texto:
        return []
    filas = []
    for linea in sistema_texto.splitlines():
        linea = linea.strip()
        if not linea or ":" not in linea:
            continue
        etiqueta, _, valor = linea.partition(":")
        if valor.strip():
            filas.append((etiqueta.strip(), valor.strip()))
    return filas if filas else [("", sistema_texto)]


# Restaura el idioma elegido antes de loguearse: el link de login manda
# a la persona a otro dominio (Cognito) y de vuelta -- una navegación de
# página completa, no una interacción dentro de la misma sesión de
# Streamlit -- así que st.session_state["idioma"] se pierde con la
# sesión vieja. Cognito devuelve `state` intacto en el callback
# (ver ui/auth.py::url_login), así que lo usamos para restaurarlo antes
# de que el radio de idioma se dibuje con su default.
_estado_idioma = st.query_params.get("state")
if _estado_idioma in ("es", "en") and st.session_state.get("idioma") != _estado_idioma:
    st.session_state["idioma"] = _estado_idioma

with st.sidebar:
    st.title("Telos")
    idioma = st.radio(
        _TEXTOS["es"]["idioma_label"],
        options=["es", "en"],
        format_func=lambda i: "Español" if i == "es" else "English",
        horizontal=True,
        key="idioma",
    )
    t = _TEXTOS[idioma]
    st.caption(t["caption"])

if _REQUIERE_LOGIN:
    if not auth.configurado():
        st.error(t["cognito_missing"])
        st.stop()

    identidad = st.session_state.get("identidad")

    if not auth.sesion_vigente(identidad):
        codigo = st.query_params.get("code")
        if codigo:
            try:
                identidad = auth.intercambiar_codigo_por_identidad(codigo)
                st.session_state["identidad"] = identidad
                st.query_params.clear()
                st.rerun()
            except ValueError as e:
                st.query_params.clear()
                st.error(t["login_failed"].format(error=e))
                st.stop()
        else:
            st.link_button(t["login_button"], auth.url_login(idioma))
            st.stop()

    usuario_id = identidad["email"]
    with st.sidebar:
        st.caption(t["connected_as"].format(usuario_id=usuario_id))
        st.link_button(t["logout_button"], auth.url_logout())
else:
    with st.sidebar:
        usuario_id = st.text_input(
            t["id_label"],
            value=st.session_state.get("usuario_id", ""),
        )
    if not usuario_id:
        st.info(t["id_missing"])
        st.stop()

clave_sesion = (usuario_id, idioma)
if st.session_state.get("clave_sesion") != clave_sesion:
    # Cambió el usuario o el idioma (o es la primera carga): arrancar una
    # sesión nueva que lea la ficha existente de ese usuario_id, si la
    # hay — el progreso guardado no se pierde, solo se reinicia el
    # agente de la fase en curso en el idioma elegido.
    st.session_state["clave_sesion"] = clave_sesion
    st.session_state["usuario_id"] = usuario_id
    nueva_sesion = SesionTelos(usuario_id, idioma=idioma)
    st.session_state["sesion"] = nueva_sesion
    st.session_state["mensajes"] = []
    st.session_state["opciones_pendientes"] = []
    # El agente habla primero, siempre -- nueva conversación o retomada
    # (Fase 5 en particular tiene que mostrar la Vista de resumen apenas
    # se abre, no después de que la persona adivine qué escribir -- esa
    # vista ahora se dibuja aparte como tarjeta, ver más abajo). Si
    # todavía no se sabe el nombre de la persona, esto es el Paso 0
    # (agents/orquestador.py) pidiéndolo, sin invocar ningún agente.
    with st.spinner(t["spinner"]):
        for _fase, parte, opciones in nueva_sesion.abrir_conversacion():
            st.session_state["mensajes"].append({"rol": "assistant", "texto": parte})
            st.session_state["opciones_pendientes"] = opciones

sesion: SesionTelos = st.session_state["sesion"]


def _procesar_turno(texto: str) -> None:
    """Consume el generador de la sesión, mostrando cada parte apenas
    está lista (ver docstring de agents.orquestador.SesionTelos) y
    dejando registradas las últimas opciones ofrecidas, si las hay."""
    st.session_state["mensajes"].append({"rol": "user", "texto": texto})
    with st.chat_message("user"):
        st.markdown(texto)

    generador = sesion.enviar_mensaje(texto)
    opciones_finales: list[str] = []
    while True:
        with st.spinner(t["spinner"]):
            try:
                _fase, parte, opciones = next(generador)
            except StopIteration:
                break
        with st.chat_message("assistant"):
            st.markdown(parte)
        st.session_state["mensajes"].append({"rol": "assistant", "texto": parte})
        opciones_finales = opciones
    st.session_state["opciones_pendientes"] = opciones_finales


ficha = leer_ficha_usuario(usuario_id)
datos = ficha["actual"]["datos"] if ficha["existe"] and ficha["actual"] else {}
proposito = (datos or {}).get("proposito")
sistema = (datos or {}).get("sistema")

with st.sidebar:
    st.metric(t["fase_label"], _NOMBRES_FASE[idioma].get(sesion.fase_actual, sesion.fase_actual))

    # "Tus resultados" vive acá, no en una columna junto al chat -- ver
    # docstring del módulo (bug real: se perdía de vista en charlas
    # largas). Se relee la ficha en cada rerun, así que se actualiza
    # sola apenas un agente guarda una versión nueva.
    st.divider()
    st.subheader(t["panel_titulo"])

    st.markdown(f"**{t['panel_proposito']}**")
    st.text_area(
        t["panel_proposito"],
        value=proposito or t["panel_vacio_proposito"],
        disabled=True,
        label_visibility="collapsed",
        height=100,
        key="panel_proposito",
    )

    st.markdown(f"**{t['panel_sistema']}**")
    filas_sistema = _parsear_sistema(sistema) if sistema else []
    if len(filas_sistema) > 1:
        # El modelo siguió el formato de líneas etiquetadas (ver
        # agents/estratega_sistemas.py) -- se puede mostrar como
        # checklist en vez de un bloque de texto plano.
        for etiqueta, valor in filas_sistema:
            st.markdown(f"✅ **{etiqueta}:** {valor}" if etiqueta else f"✅ {valor}")
    else:
        st.text_area(
            t["panel_sistema"],
            value=sistema or t["panel_vacio_sistema"],
            disabled=True,
            label_visibility="collapsed",
            height=160,
            key="panel_sistema",
        )

    # "Tu evolución": el historial de versiones nunca se sobrescribe
    # (ver sección 9 del spec, privacidad/versionado) -- esto lo hace
    # visible, no solo un dato interno.
    st.divider()
    with st.expander(t["evolucion_titulo"]):
        versiones = list(ficha["historial"])
        if ficha["existe"] and ficha["actual"]:
            versiones.append(ficha["actual"])
        versiones.sort(key=lambda v: v.get("fecha", ""))
        if not versiones:
            st.caption(t["evolucion_vacio"])
        else:
            for version in reversed(versiones):
                nombre_fase_v = _NOMBRES_FASE[idioma].get(version.get("fase"), version.get("fase"))
                st.markdown(f"**{_fecha_corta(version.get('fecha', ''))}** — {nombre_fase_v}  \n{version.get('motivo_version', '')}")

    # Exportar: P2 del PLAN.md, la parte simple (sin eliminar datos).
    st.download_button(
        t["exportar_boton"],
        data=t["exportar_contenido"].format(
            nombre=sesion.nombre or "",
            proposito=proposito or t["exportar_sin_dato"],
            sistema=sistema or t["exportar_sin_dato"],
            fecha=_fecha_corta((ficha["actual"] or {}).get("fecha", "")) if ficha["existe"] else "",
        ),
        file_name=t["exportar_nombre_archivo"],
        mime="text/plain",
        disabled=not proposito,
        use_container_width=True,
    )

# Pantalla de bienvenida: solo para quien todavía no tiene nombre
# guardado (Paso 0, agents/orquestador.py) -- una señal simple y
# pública de "primera vez", sin necesitar un flag nuevo. Explica de qué
# va la app y el camino de 5 pasos antes de que conteste "¿cómo te
# llamas?" -- breve a propósito, no un wizard de onboarding: el
# Explorador mismo tiene la regla de sentirse "ágil y alcanzable, no
# como el inicio de un proceso largo" (sección 2 del spec), y esta
# pantalla tiene que sostener ese mismo tono.
if not sesion.nombre:
    with st.container(border=True):
        st.subheader(t["bienvenida_titulo"])
        st.markdown(t["bienvenida_texto"])

# Mapa del camino: las 5 fases como paradas, no una barra de "% completado"
# (el spec prohíbe ese lenguaje -- el propósito es un horizonte, no una
# meta). Cada parada es un popover: clickeable para espiar lo que ya se
# definió ahí, sin salir del chat.
columnas_camino = st.columns(5)
for numero_fase, columna in zip(range(1, 6), columnas_camino):
    with columna:
        if numero_fase < sesion.fase_actual:
            icono_estado = "✅"
        elif numero_fase == sesion.fase_actual:
            icono_estado = "🔵"
        else:
            icono_estado = "⚪"
        etiqueta = f"{icono_estado} {_ICONOS_FASE[numero_fase]}"
        with st.popover(etiqueta, use_container_width=True):
            st.markdown(f"**{_NOMBRES_FASE[idioma][numero_fase]}**")
            if numero_fase == 1:
                st.caption(t["camino_peek_fase1"])
            elif numero_fase in (2, 3):
                st.write(proposito or t["camino_peek_vacio"])
            else:
                st.write(sistema or t["camino_peek_vacio"])

# La Vista de resumen de Fase 5 ya no viene en el texto del agente (ver
# agents/seguimiento.py) -- se dibuja acá, como tarjeta fija, con código
# puro (mismo criterio que el resto del proyecto: determinismo en
# código, no en que el modelo copie un bloque de texto sin tocarlo).
if sesion.fase_actual == 5:
    with st.container(border=True):
        st.subheader(t["resumen_titulo"])
        st.markdown(construir_vista_resumen(ficha["actual"], idioma, sesion.nombre, ficha["historial"]).replace("\n", "  \n"))

if sesion.nombre:
    st.caption(t["saludo_nombre"].format(nombre=sesion.nombre))

for mensaje in st.session_state["mensajes"]:
    with st.chat_message(mensaje["rol"]):
        st.markdown(mensaje["texto"])

# Formulario: cuando el agente de la fase actual ofreció opciones
# cerradas (por ahora, el candidato de propósito en el Sintetizador —
# ver agents/_modelo.py::crear_tool_presentar_opciones), se muestran
# como botones de radio en vez de obligar a escribir la elección. Igual
# queda disponible el chat_input de abajo para quien prefiera escribir
# su propia respuesta.
opciones_pendientes = st.session_state.get("opciones_pendientes") or []
if opciones_pendientes:
    with st.form(key=f"opciones_{len(st.session_state['mensajes'])}"):
        st.caption(t["opciones_titulo"])
        eleccion = st.radio(
            t["opciones_titulo"],
            options=opciones_pendientes,
            label_visibility="collapsed",
        )
        enviado = st.form_submit_button(t["opciones_submit"])
    if enviado:
        st.session_state["opciones_pendientes"] = []
        _procesar_turno(eleccion)
        st.rerun()

texto_usuario = st.chat_input(t["chat_placeholder"])
if texto_usuario:
    st.session_state["opciones_pendientes"] = []
    _procesar_turno(texto_usuario)
    st.rerun()
