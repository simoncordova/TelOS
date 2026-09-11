"""Auth por request para la API (rama gamificacion) -- a diferencia de
Streamlit (ui/app.py), que guarda la identidad ya validada en
st.session_state del mismo proceso, acá cada request llega a un worker
distinto en principio, así que la sesión vive en una cookie con el
id_token crudo de Cognito y se revalida (firma + exp + aud + iss) en
cada request. Ver ui/auth.py -- ese módulo hace el trabajo real
(intercambio de code, validación de JWT); este módulo solo lo envuelve
para el ciclo request/response de FastAPI, sin reimplementar nada."""

import os

from fastapi import HTTPException, Request

from ui import auth as cognito

NOMBRE_COOKIE = "telos_session"

_REQUIERE_LOGIN = os.environ.get("TELOS_REQUIRE_LOGIN", "1") != "0"
_USUARIO_DEV = "prueba-local"


def requiere_login() -> bool:
    return _REQUIERE_LOGIN


def obtener_usuario_actual(request: Request) -> str:
    """Dependencia de FastAPI: devuelve el usuario_id (= email) de la
    persona autenticada, o lanza 401. Con TELOS_REQUIRE_LOGIN=0 (mismo
    mecanismo que ui/app.py) se salta Cognito -- solo para desarrollo
    local, igual que hoy."""
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
