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

Sin probar contra un recurso real de AgentCore Memory: este entorno de
desarrollo no tiene credenciales de AWS. Validar en CloudShell (con
`TELOS_FICHA_BACKEND=agentcore`) antes del demo — en particular, que el
nombre del campo de memoria (`memoryId` vs `id`) y la forma del payload
de vuelta en list_events coincidan con lo que retorna el SDK instalado
en ese entorno (bedrock-agentcore==1.22.0 al momento de escribir esto).
"""

import os
from datetime import datetime, timezone

from bedrock_agentcore.memory import MemoryClient

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
        actor_id=usuario_id,
        session_id=usuario_id,
        blob_data=version,
    )


def leer_ficha_usuario(usuario_id: str) -> dict:
    """Devuelve la última versión de la ficha y un resumen del historial.

    Misma forma de retorno que tools/ficha_local.py — ver ese módulo.
    """
    eventos = _obtener_cliente().list_events(
        memory_id=_obtener_memory_id(),
        actor_id=usuario_id,
        session_id=usuario_id,
        max_results=100,
        include_payload=True,
    )
    versiones = [
        evento["payload"][0]["blob"]
        for evento in eventos
        if evento.get("payload") and "blob" in evento["payload"][0]
    ]
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
