"""Login vía Cognito Hosted UI (Authorization Code flow), usuarios
propios del User Pool — sin proveedores externos (nada de Google/etc.),
para no depender de ninguna cuenta de terceros. El dueño de la cuenta
crea los usuarios de prueba a mano (`aws cognito-idp admin-create-user`,
ver README); no hay auto-registro público.

No es un tool de agente ni un agente — es plumbing de autenticación
reutilizado tal cual por `api/auth.py` (ver ese módulo para el ciclo
request/response de FastAPI que envuelve esto). Vive en `ui/` por
motivos históricos (originalmente era exclusivo de la UI de Streamlit,
ya decomisionada) y no se movió para no tocar los imports de `api/`.

Config vía variables de entorno (las inyecta infra/stacks/telos_stack.py
como runtime env vars de la instancia EC2; en local hay que exportarlas
a mano o dejar TELOS_REQUIRE_LOGIN=0 para saltarse el login):
    COGNITO_DOMAIN          https://<prefix>.auth.<region>.amazoncognito.com
    COGNITO_USER_POOL_ID    us-east-1_XXXXXXXXX
    COGNITO_CLIENT_ID
    COGNITO_CLIENT_SECRET
    COGNITO_REGION          (default: TELOS_AWS_REGION o us-east-1)
    APP_URL                 URL de la ruta de callback (= redirect_uri registrado en
                            Cognito, .../api/auth/callback, donde se procesa el `code`
                            del login)
    LOGOUT_REDIRECT_URL     A dónde vuelve el navegador después de cerrar sesión en
                            Cognito (default: el mismo APP_URL). Tiene que ser distinto
                            de APP_URL en la práctica: esa ruta exige un `code` (la
                            procesa como si fuera un login), y un logout no lo manda --
                            bug real, encontrado en revisión de código antes de activar
                            el login real, nunca en producción.
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
_APP_URL = os.environ.get("APP_URL", "http://localhost:8000/api/auth/callback")
_LOGOUT_REDIRECT_URL = os.environ.get("LOGOUT_REDIRECT_URL", _APP_URL)

_ISSUER = f"https://cognito-idp.{_REGION}.amazonaws.com/{_USER_POOL_ID}"
_JWKS_URL = f"{_ISSUER}/.well-known/jwks.json"

_jwk_client: PyJWKClient | None = None


def configurado() -> bool:
    """True si hay suficiente config de Cognito para intentar el login."""
    return bool(_DOMAIN and _USER_POOL_ID and _CLIENT_ID and _CLIENT_SECRET)


def url_login(idioma: str = "en") -> str:
    # El idioma va en `state`: Cognito lo devuelve intacto en el
    # callback (?state=...), y sin esto se pierde -- el link de login es
    # una navegación de página completa hacia otro dominio (Cognito) y
    # de vuelta, así que cualquier selección que solo viva en el estado
    # del cliente se resetea a su default en la sesión nueva que arma la
    # UI al volver (bug real: se elegía inglés antes de loguearse y la
    # app saludaba en español después).
    return (
        f"{_DOMAIN}/oauth2/authorize"
        f"?client_id={_CLIENT_ID}"
        f"&response_type=code"
        f"&scope=openid+email+profile"
        f"&redirect_uri={_APP_URL}"
        f"&state={idioma}"
    )


def url_logout() -> str:
    return (
        f"{_DOMAIN}/logout"
        f"?client_id={_CLIENT_ID}"
        f"&logout_uri={_LOGOUT_REDIRECT_URL}"
    )


def intercambiar_codigo_por_id_token(code: str) -> str:
    """Canjea el authorization code por tokens y devuelve el id_token
    crudo (sin decodificar) -- separado de `intercambiar_codigo_por_identidad`
    porque api/auth.py necesita el JWT crudo para guardarlo en la cookie
    de sesión y revalidarlo en cada request (a diferencia de una sesión
    de un solo proceso, que podría quedarse solo con los claims ya
    decodificados).

    Lanza ValueError si el intercambio falla (código vencido/reusado,
    etc.) — quien llama debe tratarlo como "login fallido".
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
    return id_token


def intercambiar_codigo_por_identidad(code: str) -> dict:
    """Canjea el authorization code por tokens y devuelve la identidad ya
    validada: {"email": str, "nombre": str, "sub": str}.

    Lanza ValueError si el intercambio o la validación del ID token
    fallan (código vencido/reusado, firma inválida, etc.) — quien llama
    debe tratarlo como "login fallido", no dejar pasar al usuario.
    """
    return _validar_id_token(intercambiar_codigo_por_id_token(code))


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


def validar_id_token(id_token: str) -> dict:
    """Alias público de `_validar_id_token` -- api/auth.py revalida el
    id_token guardado en la cookie de sesión en cada request, ya que
    cada request puede llegar a un worker distinto."""
    return _validar_id_token(id_token)
