"""Interfaz Streamlit de Telos — 100% Python, sin HTML/JS/CSS.

Envoltorio delgado sobre agents.orquestador.SesionTelos: la lógica de
fases, guardrail y persistencia vive ahí, no acá. Login con Google vía
Cognito (ui/auth.py) — ver ese módulo para la config necesaria.

Idioma: selector explícito ES/EN (no autodetección) — ver sección 0.5 de
docs/agente-proposito-de-vida-prompts.md. El guardrail de crisis revisa
ambos idiomas siempre, sin importar lo que esté seleccionado acá.
"""

import os
import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import ui.auth as auth  # noqa: E402
from agents.orquestador import SesionTelos  # noqa: E402

st.set_page_config(page_title="Telos", page_icon="🧭")

_NOMBRES_FASE = {
    "es": {1: "Explorador", 2: "Sintetizador", 3: "Coach de Validación", 4: "Estratega de Sistemas", 5: "Seguimiento"},
    "en": {1: "Explorer", 2: "Synthesizer", 3: "Validation Coach", 4: "Systems Strategist", 5: "Follow-up"},
}

_TEXTOS = {
    "es": {
        "caption": "El propósito no es una meta, es un horizonte.",
        "login_button": "Iniciar sesión con Google",
        "logout_button": "Cerrar sesión",
        "connected_as": "Conectado como {usuario_id}",
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
    },
    "en": {
        "caption": "Purpose isn't a goal to reach, it's a horizon.",
        "login_button": "Sign in with Google",
        "logout_button": "Sign out",
        "connected_as": "Signed in as {usuario_id}",
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
    },
}

_REQUIERE_LOGIN = os.environ.get("TELOS_REQUIRE_LOGIN", "1") != "0"

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
            st.link_button(t["login_button"], auth.url_login())
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
    st.session_state["sesion"] = SesionTelos(usuario_id, idioma=idioma)
    st.session_state["mensajes"] = []

sesion: SesionTelos = st.session_state["sesion"]

with st.sidebar:
    st.metric(t["fase_label"], _NOMBRES_FASE[idioma].get(sesion.fase_actual, sesion.fase_actual))

for mensaje in st.session_state["mensajes"]:
    with st.chat_message(mensaje["rol"]):
        st.markdown(mensaje["texto"])

texto_usuario = st.chat_input(t["chat_placeholder"])
if texto_usuario:
    st.session_state["mensajes"].append({"rol": "user", "texto": texto_usuario})
    with st.chat_message("user"):
        st.markdown(texto_usuario)

    with st.chat_message("assistant"):
        with st.spinner(t["spinner"]):
            respuesta = sesion.enviar_mensaje(texto_usuario)
        st.markdown(respuesta)
    st.session_state["mensajes"].append({"rol": "assistant", "texto": respuesta})
