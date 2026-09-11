"""API HTTP para el frontend Node.js (rama gamificacion) -- capa delgada
sobre `agents.orquestador.SesionTelos`: NO reimplementa lógica de
agentes, solo la expone por HTTP/SSE. Ver
C:\\Users\\Wendy\\.claude\\plans\\cosmic-zooming-tarjan.md sección A para
el diseño completo.

Corre desde la raíz del repo (mismo patrón que `streamlit run ui/app.py`
y scripts/chat_terminal.py -- imports absolutos `agents.*`/`tools.*` sin
paquete instalado): `uvicorn api.main:app`.
"""

import os
import threading

from fastapi import Depends, FastAPI, Response
from fastapi.responses import PlainTextResponse, RedirectResponse, StreamingResponse

from agents.orquestador import SesionTelos
from agents.seguimiento import calcular_racha, construir_vista_resumen
from api.auth import NOMBRE_COOKIE, obtener_usuario_actual, requiere_login
from api.esquemas import AbrirSesionRequest, EnviarMensajeRequest
from api.sse import stream_eventos
from tools.ficha import leer_ficha_usuario
from tools.perfil import leer_nombre_usuario
from ui import auth as cognito

app = FastAPI(title="Telos API")

# Una sesión en memoria de proceso por (usuario_id, idioma), igual patrón
# que `clave_sesion` en ui/app.py -- SesionTelos ya está diseñada para
# poder recrearse sin perder contexto (relee ficha/turnos guardados), así
# que este cache es solo una optimización de latencia, no una fuente de
# verdad. Un Lock por clave serializa turnos concurrentes del mismo
# usuario: el Agent de Strands no es seguro para invocación concurrente.
# threading.Lock (no asyncio.Lock) a propósito: los endpoints son `def`
# sync -- FastAPI los corre en threadpool porque hacen I/O bloqueante
# real (boto3/Bedrock) -- y StreamingResponse itera un generador sync
# también en threadpool, así que todo el trabajo pasa en threads, nunca
# en el event loop.
_sesiones: dict[tuple[str, str], SesionTelos] = {}
_locks: dict[tuple[str, str], threading.Lock] = {}
_locks_guard = threading.Lock()


def _obtener_sesion(usuario_id: str, idioma: str) -> SesionTelos:
    clave = (usuario_id, idioma)
    if clave not in _sesiones:
        _sesiones[clave] = SesionTelos(usuario_id, idioma=idioma)
    return _sesiones[clave]


def _obtener_lock(usuario_id: str, idioma: str) -> threading.Lock:
    clave = (usuario_id, idioma)
    with _locks_guard:
        if clave not in _locks:
            _locks[clave] = threading.Lock()
        return _locks[clave]


def _ficha_snapshot(usuario_id: str, idioma: str, nombre: str | None) -> dict:
    ficha = leer_ficha_usuario(usuario_id)
    racha = calcular_racha(ficha["historial"], ficha["actual"])
    resumen = construir_vista_resumen(ficha["actual"], idioma, nombre, ficha["historial"])
    return {
        "existe": ficha["existe"],
        "actual": ficha["actual"],
        "historial": ficha["historial"],
        "racha": racha,
        "vista_resumen": resumen,
        "nombre": nombre,
    }


@app.get("/api/salud")
def salud() -> dict:
    return {"estado": "ok"}


# --- Auth: FastAPI es dueño del redirect_uri de Cognito (ver plan,
# sección A) -- Next.js solo linkea acá y recibe la cookie de sesión. ---


@app.get("/api/auth/login")
def login(idioma: str = "es") -> RedirectResponse:
    return RedirectResponse(cognito.url_login(idioma))


@app.get("/api/auth/callback")
def callback(code: str, state: str = "es") -> Response:
    try:
        id_token = cognito.intercambiar_codigo_por_id_token(code)
    except ValueError as e:
        return PlainTextResponse(f"Login fallido: {e}", status_code=401)

    destino = os.environ.get("WEB_APP_URL", "/")
    respuesta = RedirectResponse(f"{destino}?idioma={state}")
    respuesta.set_cookie(
        NOMBRE_COOKIE,
        id_token,
        httponly=True,
        secure=True,
        samesite="lax",
    )
    return respuesta


@app.get("/api/auth/logout")
def logout() -> Response:
    respuesta = RedirectResponse(cognito.url_logout())
    respuesta.delete_cookie(NOMBRE_COOKIE)
    return respuesta


@app.get("/api/auth/config")
def auth_config() -> dict:
    return {"requiereLogin": requiere_login()}


@app.get("/api/auth/me")
def auth_me(usuario_id: str = Depends(obtener_usuario_actual)) -> dict:
    """Único propósito: que web/ (Server Component, no puede leer una
    cookie HttpOnly) sepa si hay sesión activa sin tener que arriesgar un
    401 en una llamada que además le importa el resultado de negocio."""
    return {"usuarioId": usuario_id, "nombre": leer_nombre_usuario(usuario_id)}


# --- Conversación ---


def _eventos_turno(usuario_id: str, idioma: str, correr_generador):
    """Produce eventos (nombre, datos) bajo el lock de (usuario_id,
    idioma) durante TODA la iteración -- creación de la sesión, cada
    invocación real al modelo, y el snapshot final de la ficha -- no
    solo al arrancar. `correr_generador(sesion)` es
    `SesionTelos.abrir_conversacion` o `.enviar_mensaje(texto)` ya
    aplicado, para no atarse a cuál de las dos es."""
    lock = _obtener_lock(usuario_id, idioma)
    with lock:
        sesion = _obtener_sesion(usuario_id, idioma)
        for fase, texto, opciones in correr_generador(sesion):
            yield "mensaje", {"fase": fase, "texto": texto, "opciones": opciones}
        yield "ficha", _ficha_snapshot(usuario_id, idioma, sesion.nombre)


@app.post("/api/sesion/abrir")
def abrir_sesion(body: AbrirSesionRequest, usuario_id: str = Depends(obtener_usuario_actual)) -> StreamingResponse:
    eventos = _eventos_turno(usuario_id, body.idioma, lambda sesion: sesion.abrir_conversacion())
    return StreamingResponse(stream_eventos(eventos), media_type="text/event-stream")


@app.post("/api/sesion/mensaje")
def enviar_mensaje(body: EnviarMensajeRequest, usuario_id: str = Depends(obtener_usuario_actual)) -> StreamingResponse:
    eventos = _eventos_turno(usuario_id, body.idioma, lambda sesion: sesion.enviar_mensaje(body.texto))
    return StreamingResponse(stream_eventos(eventos), media_type="text/event-stream")


@app.get("/api/ficha")
def obtener_ficha(idioma: str = "es", usuario_id: str = Depends(obtener_usuario_actual)) -> dict:
    nombre = leer_nombre_usuario(usuario_id)
    return _ficha_snapshot(usuario_id, idioma, nombre)


@app.get("/api/ficha/exportar")
def exportar_ficha(idioma: str = "es", usuario_id: str = Depends(obtener_usuario_actual)) -> PlainTextResponse:
    nombre = leer_nombre_usuario(usuario_id)
    ficha = leer_ficha_usuario(usuario_id)
    resumen = construir_vista_resumen(ficha["actual"], idioma, nombre, ficha["historial"])
    return PlainTextResponse(resumen, headers={"Content-Disposition": "attachment; filename=telos.txt"})
