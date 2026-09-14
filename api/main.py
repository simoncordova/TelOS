"""API HTTP para el frontend Next.js -- capa delgada sobre
`agents.orquestador.SesionTelos`: NO reimplementa lógica de agentes,
solo la expone por HTTP/SSE.

Corre desde la raíz del repo (mismo patrón que scripts/chat_terminal.py
-- imports absolutos `agents.*`/`tools.*` sin paquete instalado):
`uvicorn api.main:app`.
"""

import os
import threading
import time

from fastapi import Depends, FastAPI, HTTPException, Response
from fastapi.responses import HTMLResponse, PlainTextResponse, RedirectResponse, StreamingResponse

from agents.asistente_categorias import sugerir_categoria
from agents.orquestador import SesionTelos
from agents.seguimiento import calcular_racha, construir_vista_resumen
from api import push
from api.auth import NOMBRE_COOKIE, obtener_usuario_actual, requiere_login, verificar_secreto_scheduler
from api.esquemas import (
    AbrirSesionRequest,
    CerrarFase1Request,
    ConfirmarSeleccionRequest,
    ConfirmarValoresRequest,
    EliminarSuscripcionPushRequest,
    EnviarMensajeRequest,
    EnviarPruebaPushRequest,
    SeleccionConfirmadaResponse,
    SugerenciaCategoriaResponse,
    SugerirCategoriaRequest,
    SuscripcionPushRequest,
)
from api.sse import stream_eventos
from tools.categorias_ikigai import DIMENSIONES_IKIGAI, DOMINIOS, ETIQUETAS_DIMENSION, HOJAS, MAX_VALORES, VALORES_DISPONIBLES, VERBOS
from tools.categorias_sistema import CATEGORIAS_SISTEMA, PREGUNTAS_SISTEMA_IDS
from tools.categorias_validacion import AREAS_VIDA
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
#
# Bug real (12/09/2026): "no es fuente de verdad" quedaba solo en el
# comentario -- nada invalidaba esta entrada nunca, así que cuando
# scripts/borrar_usuario.py corría por fuera de este proceso (contra el
# mismo AgentCore Memory, pero sin pasar por la API), el SesionTelos ya
# cacheado seguía con `fase_actual`/`nombre` viejos en memoria
# indefinidamente -- una cuenta recién borrada seguía viéndose como si
# tuviera fase 2 (o la que fuera) hasta reiniciar el proceso a mano. El
# TTL de abajo la hace autocurarse sola: una sesión vieja se descarta y
# se reconstruye leyendo la ficha real de nuevo, sin necesitar ningún
# mecanismo de invalidación explícita entre procesos.
_TTL_SESION_SEGUNDOS = 10 * 60
_sesiones: dict[tuple[str, str], tuple[SesionTelos, float]] = {}
_locks: dict[tuple[str, str], threading.Lock] = {}
_locks_guard = threading.Lock()


def _obtener_sesion(usuario_id: str, idioma: str) -> SesionTelos:
    clave = (usuario_id, idioma)
    entrada = _sesiones.get(clave)
    if entrada is not None:
        sesion, creada_en = entrada
        if time.monotonic() - creada_en < _TTL_SESION_SEGUNDOS:
            return sesion
    sesion = SesionTelos(usuario_id, idioma=idioma)
    _sesiones[clave] = (sesion, time.monotonic())
    return sesion


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
            # candidatos_pendientes: propósitos candidatos estructurados
            # de Fase 2 (ver SesionTelos.candidatos_pendientes) -- leído
            # de la sesión, no del tuple que arma correr_generador,
            # porque solo el Sintetizador lo usa y extender ese tuple a
            # un 4to elemento en cada lugar que lo genera/consume
            # (scripts/chat_terminal.py, scripts/simular_conversacion.py,
            # tests/) no valía la pena para un campo que casi siempre
            # viaja vacío. Seguro contra datos de una fase anterior
            # porque SesionTelos siempre sobreescribe este contenedor en
            # la misma invocación que produce cada `texto` (ver
            # _invocar_fase_directo) -- para cuando este for pide el
            # próximo valor, ya corresponde a la fase que generó ESE
            # `texto`, nunca a la anterior.
            yield "mensaje", {"fase": fase, "texto": texto, "opciones": opciones, "candidatos": sesion.candidatos_pendientes}
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


@app.post("/api/sesion/continuar")
def continuar_sesion(body: AbrirSesionRequest, usuario_id: str = Depends(obtener_usuario_actual)) -> StreamingResponse:
    """Fases 1 y 4 pueden cerrar por selección visual
    (`POST /api/seleccion/confirmar`), fuera del pipeline de texto de
    `POST /api/sesion/mensaje` -- así que la cascada que arranca a la
    fase siguiente en el mismo turno nunca se dispara sola ahí. El
    frontend llama a esto una vez, justo después de que una selección
    devuelva `cerrado=True`, para arrancar de verdad al agente de la
    fase nueva si es conversacional (ver
    agents/orquestador.py::SesionTelos.continuar_tras_seleccion) -- no
    hace nada si la fase nueva también resuelve su arranque por
    selección, o es Fase 5."""
    eventos = _eventos_turno(usuario_id, body.idioma, lambda sesion: sesion.continuar_tras_seleccion())
    return StreamingResponse(stream_eventos(eventos), media_type="text/event-stream")


@app.get("/api/categorias/{fase}")
def obtener_categorias(fase: int, idioma: str = "en") -> dict:
    """Sirve el árbol/selector de categorías completo de una sola vez --
    el frontend lo cachea y navega client-side, sin otra llamada de red
    por click (ver el plan del selector visual Ikigai). Fase 1: verbo
    (nivel 1) -> dominio (nivel 2) -> hoja (nivel 3), tal como en el
    prototipo real de Claude Design (tools/categorias_ikigai.py). Fase 3:
    un selector plano de áreas de vida, reutilizado para evidencia pasada
    y fricción futura (tools/categorias_validacion.py). Fase 4: 4 árboles
    independientes, uno por pregunta (tools/categorias_sistema.py)."""
    idioma_arbol = "es" if idioma == "es" else "en"
    if fase == 1:
        return {
            "dimensiones": list(DIMENSIONES_IKIGAI),
            "etiquetasDimension": ETIQUETAS_DIMENSION[idioma_arbol],
            "verbos": VERBOS[idioma_arbol],
            "dominios": DOMINIOS[idioma_arbol],
            "hojas": HOJAS[idioma_arbol],
            "valoresDisponibles": VALORES_DISPONIBLES[idioma_arbol],
            "maxValores": MAX_VALORES,
        }
    if fase == 3:
        return {"areas": AREAS_VIDA[idioma_arbol]}
    if fase == 4:
        return {"preguntas": list(PREGUNTAS_SISTEMA_IDS), "categorias": CATEGORIAS_SISTEMA[idioma_arbol]}
    raise HTTPException(status_code=404, detail=f"No hay taxonomía para la fase {fase} todavía.")


@app.post("/api/categorias/sugerir")
def sugerir_categoria_endpoint(
    body: SugerirCategoriaRequest, usuario_id: str = Depends(obtener_usuario_actual)
) -> SugerenciaCategoriaResponse:
    """Chat de apoyo de Fase 1 (ArbolSelector.tsx): busca, entre las
    categorías fijas que ya existen, la que mejor encaje con lo que la
    persona describió en texto libre -- nunca crea categorías nuevas (ver
    agents/asistente_categorias.py, decisión explícita del dueño del
    producto). Requiere login como el resto de la API porque dispara una
    invocación real a Bedrock."""
    resultado = sugerir_categoria(body.descripcion, body.idioma)
    return SugerenciaCategoriaResponse(
        encontrada=resultado.encontrada,
        verbo_id=resultado.verbo_id,
        dominio_id=resultado.dominio_id,
        hoja_id=resultado.hoja_id,
        explicacion=resultado.explicacion,
    )


@app.post("/api/seleccion/confirmar")
def confirmar_seleccion(
    body: ConfirmarSeleccionRequest, usuario_id: str = Depends(obtener_usuario_actual)
) -> SeleccionConfirmadaResponse:
    """Fases 1, 3 y 4: confirma una opción de un árbol o selector de
    categorías -- nunca pasa por el camino de texto libre (ver
    agents/orquestador.py::SesionTelos.confirmar_seleccion/
    confirmar_seleccion_validacion/confirmar_seleccion_sistema, que
    derivan `ruta`/`dimensiones` de la taxonomía, nunca del cliente).
    Fase 3 nunca cierra acá -- ver docstring de
    SeleccionConfirmadaResponse; su cierre real pasa por
    `POST /api/sesion/mensaje` una vez en etapa "refinando". Mismo lock
    por (usuario_id, idioma) que _eventos_turno, para serializar
    selecciones concurrentes del mismo usuario contra la misma
    SesionTelos en memoria."""
    lock = _obtener_lock(usuario_id, body.idioma)
    with lock:
        sesion = _obtener_sesion(usuario_id, body.idioma)
        try:
            if body.fase == 4:
                if not body.pregunta_id:
                    raise HTTPException(status_code=400, detail="pregunta_id es obligatorio cuando fase=4.")
                resultado = sesion.confirmar_seleccion_sistema(body.pregunta_id, body.nodo_id, body.detalle_libre)
            elif body.fase == 3:
                resultado = sesion.confirmar_seleccion_validacion(body.nodo_id, body.detalle_libre)
            else:
                resultado = sesion.confirmar_seleccion(body.nodo_id, body.detalle_libre)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e)) from e
        fase_actual = sesion.fase_actual
    return SeleccionConfirmadaResponse(
        cobertura=resultado.get("cobertura"),
        respuestas=resultado.get("respuestas"),
        etapa=resultado.get("etapa"),
        mensaje_apertura_refinado=resultado.get("mensaje_apertura_refinado"),
        mostrar_valores=resultado.get("mostrar_valores", False),
        puede_cerrar=resultado.get("puede_cerrar", False),
        cerrado=resultado.get("cerrado", False),
        mensaje_cierre=resultado.get("mensaje_cierre"),
        fase_actual=fase_actual,
    )


@app.post("/api/seleccion/cerrar-fase1")
def cerrar_fase1(
    body: CerrarFase1Request, usuario_id: str = Depends(obtener_usuario_actual)
) -> SeleccionConfirmadaResponse:
    """Fase 1: cierre explícito, disparado por la persona (botón "Ver mi
    propósito", habilitado cuando `POST /api/seleccion/confirmar` devolvió
    `puede_cerrar=True`) -- ver agents/orquestador.py::SesionTelos.
    cerrar_fase_1_manual. El frontend debe llamar a
    `POST /api/sesion/continuar` inmediatamente después para arrancar al
    Sintetizador (Fase 2)."""
    lock = _obtener_lock(usuario_id, body.idioma)
    with lock:
        sesion = _obtener_sesion(usuario_id, body.idioma)
        try:
            resultado = sesion.cerrar_fase_1_manual()
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e)) from e
        fase_actual = sesion.fase_actual
    return SeleccionConfirmadaResponse(
        cerrado=resultado["cerrado"],
        mensaje_cierre=resultado["mensaje_cierre"],
        fase_actual=fase_actual,
    )


@app.post("/api/seleccion/valores")
def confirmar_valores(
    body: ConfirmarValoresRequest, usuario_id: str = Depends(obtener_usuario_actual)
) -> dict:
    """Fase 1: confirma hasta MAX_VALORES valores elegidos -- paso único,
    no una dimensión de cobertura más (ver agents/orquestador.py::
    SesionTelos.confirmar_valores y tools/categorias_ikigai.py)."""
    lock = _obtener_lock(usuario_id, body.idioma)
    with lock:
        sesion = _obtener_sesion(usuario_id, body.idioma)
        try:
            resultado = sesion.confirmar_valores(body.valores)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e)) from e
    return resultado


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
