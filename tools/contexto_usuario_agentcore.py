"""Backend de AgentCore Memory para los insights de contexto de la
persona. Ver tools/contexto_usuario.py para el selector de backend.

Reutiliza el mismo recurso de Memory que tools/ficha_agentcore.py (mismo
cliente, mismo memory_id) en vez de aprovisionar uno nuevo -- un
`session_id` distinto ("<usuario>__contexto") alcanza para aislar este
hilo de eventos del de la ficha y del perfil, sin gastar otro recurso de
AWS para un MVP de hackathon.

No versiona por separado cada insight: cada guardado sube la lista
COMPLETA como un blob nuevo (mismo patrón "agregar una versión nueva, leer
la última" que ya usa tools/ficha_agentcore.py::guardar_ficha_usuario),
así que leer_insights solo necesita el evento más reciente del hilo.
"""

import json
import logging

from tools._agentcore_ids import id_seguro
from tools.ficha_agentcore import _obtener_cliente, _obtener_memory_id
from tools.ficha_agentcore import borrar_eventos as _borrar_eventos

logger = logging.getLogger(__name__)

_SUFIJO_SESION = "__contexto"


def _leer_lista(usuario_id: str) -> list[str]:
    eventos = _obtener_cliente().list_events(
        memory_id=_obtener_memory_id(),
        actor_id=id_seguro(usuario_id),
        session_id=id_seguro(usuario_id) + _SUFIJO_SESION,
        max_results=1,
        include_payload=True,
    )
    if not eventos or not eventos[-1].get("payload"):
        return []
    blob = eventos[-1]["payload"][0].get("blob", "[]")
    try:
        return json.loads(blob) if isinstance(blob, str) else (blob or [])
    except json.JSONDecodeError:
        logger.warning("No se pudo decodificar los insights de contexto, se asume lista vacía.")
        return []


def agregar_insight(usuario_id: str, insight: str) -> None:
    """Agrega un hecho puntual a la lista de insights conocidos de esta
    persona -- no reemplaza los anteriores, los acumula."""
    insights = _leer_lista(usuario_id)
    insights.append(insight)
    _obtener_cliente().create_blob_event(
        memory_id=_obtener_memory_id(),
        actor_id=id_seguro(usuario_id),
        session_id=id_seguro(usuario_id) + _SUFIJO_SESION,
        blob_data=json.dumps(insights, ensure_ascii=False),
    )


def leer_insights(usuario_id: str) -> list[str]:
    """Devuelve todos los insights conocidos de esta persona, en el orden
    en que se agregaron. Lista vacía si todavía no hay ninguno."""
    return _leer_lista(usuario_id)


def borrar_insights(usuario_id: str) -> int:
    """Borra todos los insights guardados -- para resetear cuentas de
    prueba contaminadas (ver scripts/borrar_usuario.py). Irreversible."""
    return _borrar_eventos(id_seguro(usuario_id), id_seguro(usuario_id) + _SUFIJO_SESION)
