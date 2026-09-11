"""Interfaz Streamlit de Telos — 100% Python, sin HTML/JS/CSS.

Envoltorio delgado sobre agents.orquestador.SesionTelos: la lógica de
fases, guardrail y persistencia vive ahí, no acá. Login con Google vía
Cognito (ui/auth.py) — ver ese módulo para la config necesaria.

Idioma: selector explícito ES/EN (no autodetección) — ver sección 0.5 de
docs/agente-proposito-de-vida-prompts.md. El guardrail de crisis revisa
ambos idiomas siempre, sin importar lo que esté seleccionado acá.

Layout: el chat ocupa la columna principal; al lado, un panel angosto
("Tus resultados") muestra el propósito y el sistema tal como están
guardados en la ficha en este momento -- no hay que esperar a que la
conversación termine ni desplazarse para encontrarlos (ver PLAN.md /
feedback de UX: los activos que se van logrando tienen que verse, no
vivir escondidos adentro del chat). Se relee la ficha en cada rerun de
Streamlit, así que se actualiza solo apenas un agente guarda una versión
nueva.
"""

import os
import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import ui.auth as auth  # noqa: E402
from agents.orquestador import SesionTelos  # noqa: E402
from tools.ficha import leer_ficha_usuario  # noqa: E402

st.set_page_config(page_title="Telos", page_icon="🧭")

_NOMBRES_FASE = {
    "es": {0: "Bienvenida", 1: "Explorador", 2: "Sintetizador", 3: "Coach de Validación", 4: "Estratega de Sistemas", 5: "Seguimiento"},
    "en": {0: "Welcome", 1: "Explorer", 2: "Synthesizer", 3: "Validation Coach", 4: "Systems Strategist", 5: "Follow-up"},
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
    },
}

_REQUIERE_LOGIN = os.environ.get("TELOS_REQUIRE_LOGIN", "1") != "0"

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
    # se abre, no después de que la persona adivine qué escribir). Si
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


with st.sidebar:
    st.metric(t["fase_label"], _NOMBRES_FASE[idioma].get(sesion.fase_actual, sesion.fase_actual))

col_chat, col_panel = st.columns([2, 1])

with col_chat:
    if sesion.nombre:
        st.caption(t["saludo_nombre"].format(nombre=sesion.nombre))

    for mensaje in st.session_state["mensajes"]:
        with st.chat_message(mensaje["rol"]):
            st.markdown(mensaje["texto"])

    # Formulario: cuando el agente de la fase actual ofreció opciones
    # cerradas (por ahora, el candidato de propósito en el Sintetizador —
    # ver agents/_modelo.py::crear_tool_presentar_opciones), se muestran
    # como botones de radio en vez de obligar a escribir la elección.
    # Igual queda disponible el chat_input de abajo para quien prefiera
    # escribir su propia respuesta.
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

with col_panel:
    st.subheader(t["panel_titulo"])
    ficha = leer_ficha_usuario(usuario_id)
    datos = ficha["actual"]["datos"] if ficha["existe"] and ficha["actual"] else {}
    proposito = (datos or {}).get("proposito")
    sistema = (datos or {}).get("sistema")

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
    st.text_area(
        t["panel_sistema"],
        value=sistema or t["panel_vacio_sistema"],
        disabled=True,
        label_visibility="collapsed",
        height=160,
        key="panel_sistema",
    )
