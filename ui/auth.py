"""Login vía Cognito Hosted UI (Authorization Code flow), usuarios
propios del User Pool — sin proveedores externos (nada de Google/etc.),
para no depender de ninguna cuenta de terceros. El dueño de la cuenta
crea los usuarios de prueba a mano (`aws cognito-idp admin-create-user`,
ver README); no hay auto-registro público.

No es un tool de agente ni un agente — es plumbing específico de la UI,
por eso vive en ui/ y no en agents/ ni tools/.

Config vía variables de entorno (las inyecta infra/stacks/telos_stack.py
como runtime env vars de App Runner; en local hay que exportarlas a mano
o dejar TELOS_REQUIRE_LOGIN=0 para saltarse el login):
    COGNITO_DOMAIN          https://<prefix>.auth.<region>.amazoncognito.com
    COGNITO_USER_POOL_ID    us-east-1_XXXXXXXXX
    COGNITO_CLIENT_ID
    COGNITO_CLIENT_SECRET
    COGNITO_REGION          (default: TELOS_AWS_REGION o us-east-1)
    APP_URL                 URL pública de la UI (= redirect_uri registrado en Cognito)
"""

import os
import time

import jwt
import requests
from jwt import PyJWKClient

_DOMAIN = os.environ.get("COGNITO_DOMAIN", "")
_USER_POOL_ID = os.environ.get("COGNITO_USER_POOL_ID", "")
_CLIENT_ID = os.environ.get("COGNITO_CLIENT_ID", "")
_CLIENT_SECRET = os.environ.get("COGNITO_CLIENT_SECRET", "")
_REGION = os.environ.get("COGNITO_REGION", os.environ.get("TELOS_AWS_REGION", "us-east-1"))
_APP_URL = os.environ.get("APP_URL", "http://localhost:8501")

_ISSUER = f"https://cognito-idp.{_REGION}.amazonaws.com/{_USER_POOL_ID}"
_JWKS_URL = f"{_ISSUER}/.well-known/jwks.json"

_jwk_client: PyJWKClient | None = None


def configurado() -> bool:
    """True si hay suficiente config de Cognito para intentar el login."""
    return bool(_DOMAIN and _USER_POOL_ID and _CLIENT_ID and _CLIENT_SECRET)


def url_login() -> str:
    return (
        f"{_DOMAIN}/oauth2/authorize"
        f"?client_id={_CLIENT_ID}"
        f"&response_type=code"
        f"&scope=openid+email+profile"
        f"&redirect_uri={_APP_URL}"
    )


def url_logout() -> str:
    return (
        f"{_DOMAIN}/logout"
        f"?client_id={_CLIENT_ID}"
        f"&logout_uri={_APP_URL}"
    )


def intercambiar_codigo_por_identidad(code: str) -> dict:
    """Canjea el authorization code por tokens y devuelve la identidad ya
    validada: {"email": str, "nombre": str, "sub": str}.

    Lanza ValueError si el intercambio o la validación del ID token
    fallan (código vencido/reusado, firma inválida, etc.) — quien llama
    debe tratarlo como "login fallido", no dejar pasar al usuario.
    """
    respuesta = requests.post(
        f"{_DOMAIN}/oauth2/token",
        data={
            "grant_type": "authorization_code",
            "client_id": _CLIENT_ID,
            "code": code,
            "redirect_uri": _APP_URL,
        },
        auth=(_CLIENT_ID, _CLIENT_SECRET),
        timeout=10,
    )
    if not respuesta.ok:
        raise ValueError(f"No se pudo canjear el código de login: {respuesta.status_code} {respuesta.text}")

    id_token = respuesta.json().get("id_token")
    if not id_token:
        raise ValueError("La respuesta de Cognito no incluyó id_token.")

    return _validar_id_token(id_token)


def _obtener_jwk_client() -> PyJWKClient:
    global _jwk_client
    if _jwk_client is None:
        _jwk_client = PyJWKClient(_JWKS_URL)
    return _jwk_client


def _validar_id_token(id_token: str) -> dict:
    clave_firmante = _obtener_jwk_client().get_signing_key_from_jwt(id_token)
    claims = jwt.decode(
        id_token,
        clave_firmante.key,
        algorithms=["RS256"],
        audience=_CLIENT_ID,
        issuer=_ISSUER,
        options={"require": ["exp", "iat", "aud", "iss"]},
    )
    return {
        "email": claims.get("email", claims.get("sub")),
        "nombre": claims.get("name", ""),
        "sub": claims["sub"],
        "expira": claims["exp"],
    }


def sesion_vigente(identidad: dict | None) -> bool:
    return bool(identidad) and identidad.get("expira", 0) > time.time()
