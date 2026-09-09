"""Interfaz Streamlit de Telos — 100% Python, sin HTML/JS/CSS.

Envoltorio delgado sobre agents.orquestador.SesionTelos: la lógica de
fases, guardrail y persistencia vive ahí, no acá. Login con Google vía
Cognito (ui/auth.py) — ver ese módulo para la config necesaria.
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
    1: "Explorador",
    2: "Sintetizador",
    3: "Coach de Validación",
    4: "Estratega de Sistemas",
    5: "Seguimiento",
}

_REQUIERE_LOGIN = os.environ.get("TELOS_REQUIRE_LOGIN", "1") != "0"

with st.sidebar:
    st.title("Telos")
    st.caption("El propósito no es una meta, es un horizonte.")

if _REQUIERE_LOGIN:
    if not auth.configurado():
        st.error(
            "Falta configurar Cognito (COGNITO_DOMAIN / COGNITO_USER_POOL_ID / "
            "COGNITO_CLIENT_ID / COGNITO_CLIENT_SECRET / APP_URL). Si estás "
            "corriendo localmente sin login, poné TELOS_REQUIRE_LOGIN=0."
        )
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
                st.error(f"No se pudo completar el login: {e}")
                st.stop()
        else:
            st.link_button("Iniciar sesión con Google", auth.url_login())
            st.stop()

    usuario_id = identidad["email"]
    with st.sidebar:
        st.caption(f"Conectado como {usuario_id}")
        st.link_button("Cerrar sesión", auth.url_logout())
else:
    with st.sidebar:
        usuario_id = st.text_input(
            "Tu identificador (login deshabilitado, TELOS_REQUIRE_LOGIN=0)",
            value=st.session_state.get("usuario_id", ""),
        )
    if not usuario_id:
        st.info("Escribe un identificador en la barra lateral para empezar.")
        st.stop()

if st.session_state.get("usuario_id") != usuario_id:
    # Cambió el usuario (o es la primera carga): arrancar una sesión nueva
    # que lea la ficha existente de ese usuario_id, si la hay.
    st.session_state["usuario_id"] = usuario_id
    st.session_state["sesion"] = SesionTelos(usuario_id)
    st.session_state["mensajes"] = []

sesion: SesionTelos = st.session_state["sesion"]

with st.sidebar:
    st.metric("Fase actual", _NOMBRES_FASE.get(sesion.fase_actual, sesion.fase_actual))

for mensaje in st.session_state["mensajes"]:
    with st.chat_message(mensaje["rol"]):
        st.markdown(mensaje["texto"])

texto_usuario = st.chat_input("Escribe aquí...")
if texto_usuario:
    st.session_state["mensajes"].append({"rol": "user", "texto": texto_usuario})
    with st.chat_message("user"):
        st.markdown(texto_usuario)

    with st.chat_message("assistant"):
        with st.spinner("..."):
            respuesta = sesion.enviar_mensaje(texto_usuario)
        st.markdown(respuesta)
    st.session_state["mensajes"].append({"rol": "assistant", "texto": respuesta})
