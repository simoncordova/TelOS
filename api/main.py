"""API HTTP para el frontend Next.js -- capa delgada sobre
`agents.orquestador.SesionTelos`: NO reimplementa lógica de agentes,
solo la expone por HTTP/SSE. Ver
C:\\Users\\Wendy\\.claude\\plans\\cosmic-zooming-tarjan.md sección A para
el diseño completo.

Corre desde la raíz del repo (mismo patrón que scripts/chat_terminal.py
-- imports absolutos `agents.*`/`tools.*` sin paquete instalado):
`uvicorn api.main:app`.
"""

import os
import threading

from fastapi import Depends, FastAPI, Response
from fastapi.responses import HTMLResponse, PlainTextResponse, RedirectResponse, StreamingResponse

from agents.orquestador import SesionTelos
from agents.seguimiento import calcular_racha, construir_vista_resumen
from api import push
from api.auth import NOMBRE_COOKIE, obtener_usuario_actual, requiere_login, verificar_secreto_scheduler
from api.esquemas import (
    AbrirSesionRequest,
    EliminarSuscripcionPushRequest,
    EnviarMensajeRequest,
    EnviarPruebaPushRequest,
    SuscripcionPushRequest,
)
from api.sse import stream_eventos
from tools.ficha import leer_ficha_usuario
from tools.perfil import leer_nombre_usuario
from tools.push_suscripcion import (
    eliminar_suscripcion_push,
    guardar_suscripcion_push,
    listar_suscripciones_push,
    listar_todas_las_suscripciones,
)
from ui import auth as cognito

app = FastAPI(title="Telos API")

# Una sesión en memoria de proceso por (usuario_id, idioma) --
# SesionTelos ya está diseñada para poder recrearse sin perder contexto
# (relee ficha/turnos guardados), así
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


def _ficha_snapshot(usuario_id: str, idioma: str, nombre: str | None, ficha: dict | None = None) -> dict:
    if ficha is None:
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
def login(idioma: str = "en") -> RedirectResponse:
    return RedirectResponse(cognito.url_login(idioma))


@app.get("/api/auth/callback")
def callback(code: str, state: str = "en") -> Response:
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
    aplicado, para no atarse a cuál de las dos es.

    El snapshot final relee la ficha con el mismo reintento por
    consistencia eventual que ya usa el avance de fase
    (SesionTelos.ficha_actualizada) -- sin esto, justo después de que un
    agente guardara propósito/sistema, el evento "ficha" podía viajar con
    la versión ANTERIOR (AgentCore Memory tarda un instante en reflejar
    un guardado reciente), y el panel "Tus resultados" del frontend se
    veía vacío un turno entero aunque el guardado real ya hubiera
    pasado -- bug real reportado por el dueño del producto probando la
    app desplegada."""
    lock = _obtener_lock(usuario_id, idioma)
    with lock:
        sesion = _obtener_sesion(usuario_id, idioma)
        total_antes = sesion.contar_versiones_ficha()
        for fase, texto, opciones in correr_generador(sesion):
            yield "mensaje", {"fase": fase, "texto": texto, "opciones": opciones}
        ficha = sesion.ficha_actualizada(total_antes)
        yield "ficha", _ficha_snapshot(usuario_id, idioma, sesion.nombre, ficha=ficha)


@app.post("/api/sesion/abrir")
def abrir_sesion(body: AbrirSesionRequest, usuario_id: str = Depends(obtener_usuario_actual)) -> StreamingResponse:
    eventos = _eventos_turno(usuario_id, body.idioma, lambda sesion: sesion.abrir_conversacion())
    return StreamingResponse(stream_eventos(eventos), media_type="text/event-stream")


@app.post("/api/sesion/mensaje")
def enviar_mensaje(body: EnviarMensajeRequest, usuario_id: str = Depends(obtener_usuario_actual)) -> StreamingResponse:
    eventos = _eventos_turno(usuario_id, body.idioma, lambda sesion: sesion.enviar_mensaje(body.texto))
    return StreamingResponse(stream_eventos(eventos), media_type="text/event-stream")


@app.get("/api/ficha")
def obtener_ficha(idioma: str = "en", usuario_id: str = Depends(obtener_usuario_actual)) -> dict:
    nombre = leer_nombre_usuario(usuario_id)
    return _ficha_snapshot(usuario_id, idioma, nombre)


@app.get("/api/ficha/exportar")
def exportar_ficha(idioma: str = "en", usuario_id: str = Depends(obtener_usuario_actual)) -> PlainTextResponse:
    nombre = leer_nombre_usuario(usuario_id)
    ficha = leer_ficha_usuario(usuario_id)
    resumen = construir_vista_resumen(ficha["actual"], idioma, nombre, ficha["historial"])
    return PlainTextResponse(resumen, headers={"Content-Disposition": "attachment; filename=telos.txt"})


# --- Push (Fase 3/4 del plan): suscripción desde el navegador, envío
# manual de prueba, y el envío masivo que dispara el Scheduler de
# EventBridge. Ver api/push.py y tools/push_suscripcion.py. ---


@app.get("/api/push/config")
def push_config() -> dict:
    """El frontend pide la clave pública acá (en vez de necesitarla
    horneada en el build de Next.js) para no tener que pasar
    NEXT_PUBLIC_VAPID_PUBLIC_KEY como build arg de Docker -- ver
    infra/stacks/telos_stack.py."""
    return {"configurado": push.configurado(), "clavePublica": push.clave_publica()}


@app.post("/api/push/suscripcion", status_code=204)
def guardar_suscripcion(body: SuscripcionPushRequest, usuario_id: str = Depends(obtener_usuario_actual)) -> None:
    guardar_suscripcion_push(usuario_id, body.model_dump())


@app.delete("/api/push/suscripcion", status_code=204)
def eliminar_suscripcion(body: EliminarSuscripcionPushRequest, usuario_id: str = Depends(obtener_usuario_actual)) -> None:
    eliminar_suscripcion_push(usuario_id, body.endpoint)


@app.post("/api/push/enviar-prueba")
def enviar_prueba(body: EnviarPruebaPushRequest, usuario_id: str = Depends(obtener_usuario_actual)) -> dict:
    """Manda una notificación de prueba a TODAS las suscripciones de la
    persona logueada (puede tener más de un dispositivo/navegador) --
    para validar la tubería completa (Service Worker, VAPID, proveedor
    de push real) antes de depender del scheduler de Fase 4."""
    suscripciones = listar_suscripciones_push(usuario_id)
    enviados, invalidas = _enviar_a_suscripciones(usuario_id, suscripciones, push.construir_prueba(body.idioma))
    return {"enviados": enviados, "invalidasEliminadas": invalidas}


@app.post("/api/push/enviar-recordatorios", dependencies=[Depends(verificar_secreto_scheduler)])
def enviar_recordatorios() -> dict:
    """Único llamado por el Scheduler de EventBridge (ver
    infra/stacks/telos_stack.py) -- nunca por una persona ni por el
    frontend. Recorre a todas las personas suscriptas y les manda el
    mismo recordatorio fijo, respetando el mismo tono que el resto del
    proyecto (sin racha, sin "hace X días") -- ver
    push.construir_recordatorio."""
    # El idioma elegido no se persiste en ningún lado hoy (es estado
    # efímero del navegador, se pierde al cerrar la pestaña) -- un
    # recordatorio async no tiene de dónde leerlo, así que usa "en" para
    # todos, el mismo default del resto de la app. Si hace falta un
    # recordatorio en el idioma real de cada persona, hay que agregar ese
    # campo al perfil primero (tools/perfil.py) -- no inventado acá sin
    # que el spec lo pida.
    total_enviados = 0
    total_invalidas = 0
    for usuario_id, suscripciones in listar_todas_las_suscripciones().items():
        enviados, invalidas = _enviar_a_suscripciones(usuario_id, suscripciones, push.construir_recordatorio("en"))
        total_enviados += enviados
        total_invalidas += invalidas
    return {"enviados": total_enviados, "invalidasEliminadas": total_invalidas}


# --- Calendario (P2 del plan): callback de OAuth2 de AgentCore Identity
# para Google Calendar. Ver tools/calendario_agentcore.py para el resto
# del flujo y el setup externo que necesita. ---


@app.get("/api/calendario/oauth2/callback")
def calendario_oauth2_callback(session_id: str, usuario_id: str = Depends(obtener_usuario_actual)) -> HTMLResponse:
    """A esta ruta vuelve el navegador de la persona después de aprobar
    el consentimiento en Google -- Cognito ya la autenticó antes (cookie
    `samesite=lax`, sobrevive la navegación completa de ida y vuelta a
    Google), así que `obtener_usuario_actual` alcanza para saber a quién
    atar esta autorización, sin necesitar un mapeo de sesiones aparte.
    `session_id` lo agrega AgentCore como query param al redirigir acá
    -- ver tools.calendario_agentcore.completar_autorizacion para qué
    hace con los dos."""
    from tools.calendario_agentcore import completar_autorizacion

    try:
        completar_autorizacion(session_id, usuario_id)
    except Exception as e:  # noqa: BLE001 -- cualquier falla acá se le muestra a la persona, no un 500 pelado
        return HTMLResponse(f"<p>No se pudo completar la autorización: {e}</p>", status_code=400)
    return HTMLResponse(
        "<p>Listo, tu Google Calendar quedó conectado. Podés cerrar esta pestaña "
        "y volver a la conversación.</p>"
    )


def _enviar_a_suscripciones(usuario_id: str, suscripciones: list[dict], mensaje: dict) -> tuple[int, int]:
    enviados = 0
    invalidas = 0
    for suscripcion in suscripciones:
        try:
            push.enviar_push(suscripcion, mensaje)
            enviados += 1
        except push.SuscripcionInvalida:
            eliminar_suscripcion_push(usuario_id, suscripcion.get("endpoint", ""))
            invalidas += 1
    return enviados, invalidas
