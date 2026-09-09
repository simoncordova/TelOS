"""Interfaz Streamlit de Telos — 100% Python, sin HTML/JS/CSS.

Envoltorio delgado sobre agents.orquestador.SesionTelos: la lógica de
fases, guardrail y persistencia vive ahí, no acá.
"""

import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agents.orquestador import SesionTelos  # noqa: E402

st.set_page_config(page_title="Telos", page_icon="🧭")

_NOMBRES_FASE = {
    1: "Explorador",
    2: "Sintetizador",
    3: "Coach de Validación",
    4: "Estratega de Sistemas",
    5: "Seguimiento",
}

with st.sidebar:
    st.title("Telos")
    st.caption("El propósito no es una meta, es un horizonte.")
    usuario_id = st.text_input(
        "Tu identificador",
        value=st.session_state.get("usuario_id", ""),
        help="Usa el mismo identificador para retomar tu ficha entre sesiones.",
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
