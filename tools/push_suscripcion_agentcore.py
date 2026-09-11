"""Backend de AgentCore Memory para las suscripciones de push. Mismo
contrato que tools/push_suscripcion_local.py -- ver
tools/push_suscripcion.py para el selector.

A diferencia de tools/ficha_agentcore.py (un hilo de eventos POR
usuario, actor_id=usuario_id), acá TODO el registro de suscripciones
vive en un único hilo fijo (actor_id/session_id constantes, no
derivados del usuario_id): el MemoryClient de este proyecto
(bedrock_agentcore.memory) no expone ningún "list_actors" /
"list_sessions" para recorrer todos los actores de una memoria (ver
`dir(MemoryClient)` -- solo hay list_events, list_branches, etc., todos
ya scoped a un actor/session puntual), y Fase 4 (recordatorios
automáticos) necesita justamente lo contrario: la lista completa de
quién está suscripto, no la suscripción de una persona a la vez. Guardar
el registro entero como un único blob versionado (mismo patrón
"agregar una versión nueva, leer la última" que ya usa
guardar_ficha_usuario) evita necesitar esa enumeración.

Sin probar contra un recurso real de AgentCore Memory (este entorno de
desarrollo no tiene credenciales de AWS) -- validar con una cuenta de
prueba antes de confiar en esto para producción, mismo caveat que
tools/ficha_agentcore.py::borrar_eventos.
"""

import json
import logging
import os

from bedrock_agentcore.memory import MemoryClient

logger = logging.getLogger(__name__)

_NOMBRE_MEMORIA = os.environ.get("TELOS_MEMORY_NAME", "telos_fichas_usuario")
_REGION = os.environ.get("TELOS_AWS_REGION", "us-east-1")

# Hilo fijo, no derivado de ningún usuario_id -- ver docstring del
# módulo. "_registro" no es un email real, así que no puede chocar con
# un actor_id de verdad (ver tools/_agentcore_ids.py::id_seguro, que
# nunca produce nombres con guion bajo al inicio de esta forma exacta
# para una entrada no vacía).
_ACTOR_REGISTRO = "_registro_push"
_SESSION_REGISTRO = "push_suscripciones"

_cliente: MemoryClient | None = None
_memory_id: str | None = None


def _obtener_cliente() -> MemoryClient:
    global _cliente
    if _cliente is None:
        _cliente = MemoryClient(region_name=_REGION)
    return _cliente


def _obtener_memory_id() -> str:
    global _memory_id
    if _memory_id is None:
        memoria = _obtener_cliente().create_or_get_memory(
            name=_NOMBRE_MEMORIA,
            description="Ficha de propósito + sistema de cada usuario de Telos, versionada.",
            event_expiry_days=365,
        )
        _memory_id = memoria.get("memoryId", memoria.get("id"))
    return _memory_id


def _leer_registro() -> dict[str, list[dict]]:
    eventos = _obtener_cliente().list_events(
        memory_id=_obtener_memory_id(),
        actor_id=_ACTOR_REGISTRO,
        session_id=_SESSION_REGISTRO,
        max_results=1,
        include_payload=True,
        # Solo se necesita el más reciente -- cada blob nuevo es el
        # registro COMPLETO, no un delta (ver _escribir_registro).
    )
    if not eventos or not eventos[-1].get("payload"):
        return {}
    blob = eventos[-1]["payload"][0].get("blob", "{}")
    try:
        return json.loads(blob) if isinstance(blob, str) else (blob or {})
    except json.JSONDecodeError:
        logger.warning("No se pudo decodificar el registro de suscripciones push, se asume vacío.")
        return {}


def _escribir_registro(registro: dict[str, list[dict]]) -> None:
    _obtener_cliente().create_blob_event(
        memory_id=_obtener_memory_id(),
        actor_id=_ACTOR_REGISTRO,
        session_id=_SESSION_REGISTRO,
        blob_data=json.dumps(registro, ensure_ascii=False),
    )


def guardar_suscripcion_push(usuario_id: str, suscripcion: dict) -> None:
    registro = _leer_registro()
    suscripciones = registro.setdefault(usuario_id, [])
    suscripciones[:] = [s for s in suscripciones if s.get("endpoint") != suscripcion.get("endpoint")]
    suscripciones.append(suscripcion)
    _escribir_registro(registro)


def eliminar_suscripcion_push(usuario_id: str, endpoint: str) -> None:
    registro = _leer_registro()
    if usuario_id not in registro:
        return
    registro[usuario_id] = [s for s in registro[usuario_id] if s.get("endpoint") != endpoint]
    if not registro[usuario_id]:
        del registro[usuario_id]
    _escribir_registro(registro)


def listar_suscripciones_push(usuario_id: str) -> list[dict]:
    return _leer_registro().get(usuario_id, [])


def listar_todas_las_suscripciones() -> dict[str, list[dict]]:
    return _leer_registro()
