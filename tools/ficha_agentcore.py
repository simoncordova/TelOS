"""Backend de AgentCore Memory para la ficha del usuario. Ver
docs/agente-proposito-de-vida-prompts.md secciones 7 y 9, y Paso 9 del
plan de implementación.

Mismo contrato que tools/ficha_local.py — ver tools/ficha.py para el
selector de backend (TELOS_FICHA_BACKEND=agentcore lo activa).

Cada versión de la ficha se guarda como un blob event de AgentCore Memory
(un solo hilo de eventos por usuario: actor_id=usuario_id,
session_id=usuario_id — la ficha no tiene "sesiones" múltiples, es un
único historial versionado). list_events() de AgentCore ya devuelve los
eventos en orden cronológico, así que el último elemento es la versión
vigente.

El campo `blob` no se serializa/deserializa solo: `create_blob_event`
manda lo que se le pase tal cual como payload de la API, y AgentCore
Memory lo devuelve como string (no como dict) en `list_events` --
guardar un dict de Python crudo ahí y volver a indexarlo como dict al
leerlo (`actual["fase"]`) tiraba `TypeError: string indices must be
integers, not 'str'` en un deploy real. Por eso acá se serializa a JSON
antes de guardar y se deserializa al leer (`_decodificar_blob`), en vez
de asumir que el SDK hace ese trabajo.

Las fichas guardadas ANTES de este fix quedaron en un formato que no es
ni JSON ni el repr() de Python -- parece un toString() estilo Java de
algún wrapper interno de AgentCore ("{fase=1, datos={clave=valor, ...},
...}", sin comillas en los valores). Parsearlo bien es genuinamente
ambiguo (los valores son oraciones con comas adentro, no hay forma
confiable de distinguir una coma de separación de una coma de la
oración) y no vale la pena un parser a medida para datos de prueba
previos al fix -- `_decodificar_blob` devuelve `None` si no puede
decodificar una versión, y `leer_ficha_usuario` la descarta en vez de
tumbar toda la sesión por una sola versión vieja corrupta.
"""

import ast
import json
import logging
import os
from datetime import datetime, timezone

from bedrock_agentcore.memory import MemoryClient

from tools._agentcore_ids import id_seguro

logger = logging.getLogger(__name__)

_NOMBRE_MEMORIA = os.environ.get("TELOS_MEMORY_NAME", "telos_fichas_usuario")
_REGION = os.environ.get("TELOS_AWS_REGION", "us-east-1")

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


def _decodificar_blob(blob):
    """Normaliza lo que devuelve list_events para el campo `blob` -- ver
    la nota del docstring del módulo. Devuelve None (no lanza) si la
    versión no se puede decodificar -- una versión vieja corrupta no
    tiene que tumbar la lectura de toda la ficha, quien llama la
    descarta."""
    if isinstance(blob, dict):
        return blob
    if isinstance(blob, (bytes, bytearray)):
        blob = blob.decode("utf-8")
    if isinstance(blob, str):
        try:
            return json.loads(blob)
        except json.JSONDecodeError:
            pass
        try:
            return ast.literal_eval(blob)
        except (ValueError, SyntaxError):
            logger.warning("No se pudo decodificar una versión de la ficha, se descarta: %r", blob[:200])
            return None
    raise TypeError(f"Tipo de blob inesperado de AgentCore Memory: {type(blob)!r}")


def guardar_ficha_usuario(usuario_id: str, datos: dict, fase: int, motivo_version: str) -> None:
    """Agrega una nueva versión de la ficha del usuario como blob event. No sobrescribe el historial."""
    version = {
        "fase": fase,
        "datos": datos,
        "motivo_version": motivo_version,
        "fecha": datetime.now(timezone.utc).isoformat(),
    }
    _obtener_cliente().create_blob_event(
        memory_id=_obtener_memory_id(),
        # usuario_id es el email real de Cognito (con "@" y ".") --
        # AgentCore Memory no acepta esos caracteres en actorId/
        # sessionId, hay que sanitizarlo primero (ver tools/_agentcore_ids.py).
        actor_id=id_seguro(usuario_id),
        session_id=id_seguro(usuario_id),
        blob_data=json.dumps(version, ensure_ascii=False),
    )


def leer_ficha_usuario(usuario_id: str) -> dict:
    """Devuelve la última versión de la ficha y un resumen del historial.

    Misma forma de retorno que tools/ficha_local.py — ver ese módulo.
    """
    eventos = _obtener_cliente().list_events(
        memory_id=_obtener_memory_id(),
        actor_id=id_seguro(usuario_id),
        session_id=id_seguro(usuario_id),
        max_results=100,
        include_payload=True,
    )
    versiones = []
    for evento in eventos:
        if not evento.get("payload") or "blob" not in evento["payload"][0]:
            continue
        version = _decodificar_blob(evento["payload"][0]["blob"])
        if version is not None:
            versiones.append(version)
    if not versiones:
        return {"existe": False, "actual": None, "historial": []}

    return {
        "existe": True,
        "actual": versiones[-1],
        "historial": [
            {"fase": v["fase"], "motivo_version": v["motivo_version"], "fecha": v["fecha"]}
            for v in versiones[:-1]
        ],
    }
