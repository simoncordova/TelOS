"""Auth por request para la API -- cada request llega a un worker
distinto en principio, así que la sesión vive en una cookie con el
id_token crudo de Cognito y se revalida (firma + exp + aud + iss) en
cada request. Ver ui/auth.py -- ese módulo hace el trabajo real
(intercambio de code, validación de JWT); este módulo solo lo envuelve
para el ciclo request/response de FastAPI, sin reimplementar nada."""

import hmac
import os

from fastapi import HTTPException, Request

from ui import auth as cognito

NOMBRE_COOKIE = "telos_session"

_REQUIERE_LOGIN = os.environ.get("TELOS_REQUIRE_LOGIN", "1") != "0"
_USUARIO_DEV = "prueba-local"
_SECRETO_SCHEDULER = os.environ.get("PUSH_SCHEDULER_SECRET", "")


def requiere_login() -> bool:
    return _REQUIERE_LOGIN


def obtener_usuario_actual(request: Request) -> str:
    """Dependencia de FastAPI: devuelve el usuario_id (= email) de la
    persona autenticada, o lanza 401. Con TELOS_REQUIRE_LOGIN=0 se salta
    Cognito -- solo para desarrollo local."""
    if not _REQUIERE_LOGIN:
        return request.headers.get("X-Telos-Usuario-Dev", _USUARIO_DEV)

    id_token = request.cookies.get(NOMBRE_COOKIE)
    if not id_token:
        raise HTTPException(status_code=401, detail="No hay sesión activa.")
    try:
        identidad = cognito.validar_id_token(id_token)
    except Exception as e:  # noqa: BLE001 -- cualquier falla de validación es "no autenticado", no un 500
        raise HTTPException(status_code=401, detail=f"Sesión inválida: {e}") from e
    if not cognito.sesion_vigente(identidad):
        raise HTTPException(status_code=401, detail="Sesión vencida.")
    return identidad["email"]


def verificar_secreto_scheduler(request: Request) -> None:
    """Dependencia para /api/push/enviar-recordatorios (Fase 4): ese
    endpoint no lo llama una persona con sesión, lo llama el Scheduler de
    EventBridge (ver infra/stacks/telos_stack.py) -- se protege con un
    secreto compartido en vez de Cognito. Falla cerrado si el secreto no
    está configurado (nunca "sin secreto = permitido"): un recordatorio
    real manda notificaciones a TODAS las personas suscriptas, no es un
    endpoint que deba quedar abierto por accidente."""
    si_configurado = _SECRETO_SCHEDULER and hmac.compare_digest(
        request.headers.get("X-Telos-Scheduler-Secret", ""), _SECRETO_SCHEDULER
    )
    if not si_configurado:
        raise HTTPException(status_code=403, detail="Secreto de scheduler inválido o no configurado.")
