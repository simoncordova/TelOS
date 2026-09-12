"""Backend real de calendario: agenda directo en el Google Calendar de la
persona, vía Amazon Bedrock AgentCore Identity (OAuth2 de 3 patas) --
ver tools/calendario.py para el selector de backend.

No usa AgentCore Runtime -- corre sobre la misma API FastAPI que ya
tenemos. La pieza clave es `BedrockAgentCoreContext.set_workload_access_token`
(pública en el SDK instalado, ver .venv/Lib/site-packages/bedrock_agentcore/
runtime/context.py): sin Runtime, `@requires_access_token` cae por default
a una identidad local aleatoria persistida en un archivo (.agentcore.json,
pensada para un script de desarrollo, no para una app multiusuario) --
fijando el contexto nosotros mismos con el `usuario_id` real (ya
autenticado por Cognito antes de llegar acá, ver
api/auth.py::obtener_usuario_actual), AgentCore Identity guarda y busca
el token de Google atado a esa persona real, no a una identidad
compartida por accidente entre todos los usuarios.

Requiere setup externo, hecho una sola vez, que este código no puede
hacer por sí solo (sin credenciales de AWS ni cuenta de Google en este
entorno de desarrollo):

1. Google Cloud Console: crear un proyecto, habilitar la API de Google
   Calendar, configurar la pantalla de consentimiento OAuth (modo
   "Testing" alcanza para el demo, evita la revisión larga de Google),
   y crear credenciales OAuth 2.0 tipo "Web application". Guardar el
   client ID y el client secret.
2. AWS (CloudShell, con credenciales reales) -- crear el credential
   provider con esas credenciales:
       aws bedrock-agentcore-control create-oauth2-credential-provider \\
         --region <region> \\
         --name "telos-google-calendar" \\
         --credential-provider-vendor "GoogleOauth2" \\
         --oauth2-provider-config-input '{"googleOauth2ProviderConfig":
           {"clientId": "<client-id>", "clientSecret": "<client-secret>"}}'
   La respuesta trae un `callbackUrl` (algo como
   https://bedrock-agentcore.<region>.amazonaws.com/identities/oauth2/callback/<id>)
   -- ESE es el que hay que cargar como "Authorized redirect URI" en las
   credenciales OAuth de Google Cloud Console. No confundir con
   TELOS_CALENDARIO_CALLBACK_URL de abajo: son dos callbacks distintos en
   dos saltos del mismo flujo (ver docstring de completar_autorizacion).
3. Crear (una sola vez) la workload identity del agente, con la URL de
   ESTE repo como return URL permitida:
       aws bedrock-agentcore-control create-workload-identity \\
         --region <region> \\
         --name "telos-agent" \\
         --allowed-resource-oauth2-return-urls '["https://<tu-dominio>/api/calendario/oauth2/callback"]'

Variables de entorno:
    TELOS_GOOGLE_CREDENTIAL_PROVIDER    nombre del provider (default: "telos-google-calendar")
    TELOS_AGENTCORE_WORKLOAD_IDENTITY   nombre de la workload identity (default: "telos-agent")
    TELOS_CALENDARIO_CALLBACK_URL       URL pública de la ruta de callback de este repo
                                        (api/main.py::calendario_oauth2_callback) --
                                        obligatoria para que el consentimiento pueda volver acá
    TELOS_GOOGLE_CALENDAR_ID            calendario a usar (default: "primary")

Todo lo de acá está escrito contra el código fuente instalado de
bedrock_agentcore (no de memoria ni asumido de la documentación) pero sin
poder ejercitar el flujo de consentimiento real contra Google ni AWS
real desde este entorno de desarrollo -- validar con una cuenta de
prueba antes de confiar en esto para el demo.
"""

import concurrent.futures
import logging
import os

from bedrock_agentcore.identity.auth import requires_access_token
from bedrock_agentcore.runtime import BedrockAgentCoreContext
from bedrock_agentcore.services.identity import IdentityClient, UserIdIdentifier

logger = logging.getLogger(__name__)

_REGION = os.environ.get("TELOS_AWS_REGION", "us-east-1")
_WORKLOAD_IDENTITY = os.environ.get("TELOS_AGENTCORE_WORKLOAD_IDENTITY", "telos-agent")
_PROVIDER_NAME = os.environ.get("TELOS_GOOGLE_CREDENTIAL_PROVIDER", "telos-google-calendar")
_CALLBACK_URL = os.environ.get("TELOS_CALENDARIO_CALLBACK_URL", "")
_CALENDAR_ID = os.environ.get("TELOS_GOOGLE_CALENDAR_ID", "primary")

# Acotado a crear/editar eventos, no acceso total de lectura/escritura al
# calendario -- mínimo privilegio, todo lo que Fase 4 necesita es poder
# crear el evento recurrente del sistema.
_SCOPES = ["https://www.googleapis.com/auth/calendar.events"]

# El SDK por default espera (polling) hasta 600s a que la persona
# autorice -- pensado para un script de terminal donde alguien lo sigue
# activamente. Acá corre dentro de un turno de chat: no tiene sentido
# bloquear la respuesta varios minutos. Si no está listo en este ratito,
# se le devuelve el link a la persona y se reintenta en el próximo turno
# -- una relectura del vault no reinicia el consentimiento ya en curso.
_ESPERA_MAXIMA_SEGUNDOS = 8


def _cliente() -> IdentityClient:
    return IdentityClient(_REGION)


def _pedir_token(usuario_id: str, contenedor_url: list) -> str:
    """Corre en un thread aparte (ver _obtener_token). Fija el contexto de
    AgentCore Identity para ESTE usuario_id real y pide el access token de
    Google. Si hace falta consentimiento nuevo, `on_auth_url` dispara y
    deja la URL en `contenedor_url` apenas AgentCore la genera -- mucho
    antes de que el polling interno del SDK (o, acá, el timeout del
    future en _obtener_token) termine."""
    wat = _cliente().get_workload_access_token(_WORKLOAD_IDENTITY, user_id=usuario_id)["workloadAccessToken"]
    # ContextVar: tiene que fijarse en ESTE thread, el mismo que ejecuta
    # la función decorada -- concurrent.futures no copia el contexto del
    # thread que llamó a submit().
    BedrockAgentCoreContext.set_workload_access_token(wat)

    @requires_access_token(
        provider_name=_PROVIDER_NAME,
        scopes=_SCOPES,
        auth_flow="USER_FEDERATION",
        on_auth_url=contenedor_url.append,
        callback_url=_CALLBACK_URL,
        force_authentication=False,
    )
    def _obtener(*, access_token: str) -> str:
        return access_token

    return _obtener()


def _obtener_token(usuario_id: str) -> tuple[str | None, str | None]:
    """(access_token, None) si ya había un token vigente en el vault, o
    (None, url_autorizacion) si hace falta que la persona autorice
    primero. Nunca bloquea más de _ESPERA_MAXIMA_SEGUNDOS, aunque el
    pedido siga esperando en segundo plano más allá de eso.

    OJO: el `executor` se crea SIN `with` a propósito -- `ThreadPoolExecutor.
    __exit__` llama `shutdown(wait=True)`, que hubiera esperado a que el
    thread en segundo plano termine (hasta 600s del polling interno del
    SDK) antes de dejar salir esta función, exactamente lo que
    _ESPERA_MAXIMA_SEGUNDOS quiere evitar. Sin `with`, el work item
    sigue corriendo solo (el registro interno de concurrent.futures lo
    mantiene vivo aunque el objeto Executor salga de scope) y esta
    función devuelve apenas se cumple el timeout, no cuando termina el
    thread. Bug real: encontrado corriendo el caso de prueba de
    "consentimiento pendiente" contra un mock -- con `with`, tardaba los
    600s completos en vez de los ~8 esperados."""
    contenedor_url: list[str] = []
    executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
    future = executor.submit(_pedir_token, usuario_id, contenedor_url)
    try:
        return future.result(timeout=_ESPERA_MAXIMA_SEGUNDOS), None
    except concurrent.futures.TimeoutError:
        # El thread sigue corriendo en segundo plano -- si la persona
        # autoriza en los próximos minutos, el próximo llamado a esta
        # función va a encontrar el token ya guardado en el vault sin
        # pedir consentimiento de nuevo.
        url = contenedor_url[0] if contenedor_url else None
        return None, url
    except Exception:  # noqa: BLE001 -- falla real de AgentCore/Google, no un timeout esperado
        logger.exception("Fallo real pidiendo el token de Google Calendar para %s", usuario_id)
        return None, None


def completar_autorizacion(session_id: str, usuario_id: str) -> None:
    """Llamado por api/main.py::calendario_oauth2_callback cuando el
    navegador de la persona vuelve del consentimiento de Google. Cierra
    el "session binding": ata esa sesión de autorización (`session_id`,
    que AgentCore agrega como query param al volver) al usuario_id real
    -- sin este paso, el token queda en el vault sin asociar a nadie.

    Dos callbacks distintos en este flujo entero, no confundir (ver
    docstring del módulo): el que se registra en Google Cloud Console es
    el que genera `create-oauth2-credential-provider` (AWS lo atiende
    directo, nunca pasa por este repo); este de acá es al que AgentCore
    redirige a la persona DESPUÉS de completar el intercambio con
    Google, para terminar de atar la sesión a nuestro usuario_id."""
    _cliente().complete_resource_token_auth(
        session_uri=session_id,
        user_identifier=UserIdIdentifier(user_id=usuario_id),
    )


def crear_evento_calendario(usuario_id: str, detalle: dict) -> dict:
    """Agenda el evento recurrente del sistema en el Google Calendar real
    de la persona. Misma firma/forma de retorno que
    tools/calendario_local.py -- ver tools/calendario.py para el selector.

    Si todavía no autorizó (o hace falta reconsentir), `mensaje` incluye
    el link de autorización en vez de crear el evento -- el agente de
    fase (Estratega de Sistemas) lo relaya tal cual en su
    texto_para_persona, y reintenta en un turno posterior si la persona
    confirma que ya autorizó."""
    access_token, url_autorizacion = _obtener_token(usuario_id)

    if access_token is None:
        if url_autorizacion:
            return {
                "confirmado": False,
                "mensaje": (
                    "Antes de agendarlo necesito que autorices el acceso a tu "
                    f"Google Calendar: {url_autorizacion}\n\nAvisame apenas lo "
                    "hayas hecho y lo agendo."
                ),
            }
        return {
            "confirmado": False,
            "mensaje": (
                "No pude conectar con Google Calendar ahora mismo. Probemos "
                "de nuevo en un momento, o seguimos sin agendarlo por hoy."
            ),
        }

    return _crear_evento_real(access_token, detalle)


def _crear_evento_real(access_token: str, detalle: dict) -> dict:
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError

    accion = detalle.get("accion", "tu sistema")
    cuando = detalle.get("cuando", "")

    credenciales = Credentials(token=access_token, scopes=_SCOPES)
    try:
        servicio = build("calendar", "v3", credentials=credenciales)
        evento = {
            "summary": accion,
            "description": f"Sistema de hábito creado con Telos. Cuándo/dónde: {cuando}",
            # MVP: un evento simple, no una regla RRULE de recurrencia
            # real -- suficiente para demostrar la integración; una
            # recurrencia real es la siguiente iteración si el tiempo
            # alcanza (ver PLAN.md).
        }
        creado = servicio.events().insert(calendarId=_CALENDAR_ID, body=evento).execute()
        return {
            "confirmado": True,
            "mensaje": f"Listo, lo agendé de verdad en tu Google Calendar: \"{accion}\" — {cuando}.",
            "eventoId": creado.get("id"),
        }
    except HttpError:
        logger.exception("Google Calendar API rechazó el evento")
        return {
            "confirmado": False,
            "mensaje": (
                "Google Calendar rechazó el pedido de agendar esto. Podemos "
                "seguir sin el calendario por ahora y retomarlo después."
            ),
        }
