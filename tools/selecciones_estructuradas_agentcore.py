"""Backend de AgentCore Memory para las selecciones del árbol Ikigai. Ver
tools/selecciones_estructuradas.py para el selector de backend.

Reutiliza el mismo recurso de Memory que tools/ficha_agentcore.py (mismo
cliente, mismo memory_id) -- un `session_id` propio
("<usuario>__selecciones_estructuradas") alcanza para aislar este hilo de
eventos, sin gastar otro recurso de AWS.

No versiona: cada guardado agrega un evento nuevo, pero solo se lee el
último -- mismo patrón que tools/perfil_agentcore.py para el nombre.
en_orden_cronologico() es obligatorio acá, no cosmético -- ver la nota en
tools/ficha_agentcore.py sobre por qué list_events() no devuelve los
eventos en orden ascendente por default."""

import json

from tools._agentcore_ids import id_seguro
from tools.ficha_agentcore import _obtener_cliente, _obtener_memory_id, en_orden_cronologico
from tools.ficha_agentcore import borrar_eventos as _borrar_eventos

_SUFIJO_SESION = "__selecciones_estructuradas"


def guardar_selecciones_estructuradas(usuario_id: str, progreso: dict) -> None:
    _obtener_cliente().create_blob_event(
        memory_id=_obtener_memory_id(),
        actor_id=id_seguro(usuario_id),
        session_id=id_seguro(usuario_id) + _SUFIJO_SESION,
        blob_data=json.dumps(progreso, ensure_ascii=False),
    )


def leer_selecciones_estructuradas(usuario_id: str) -> dict:
    eventos = en_orden_cronologico(
        _obtener_cliente().list_events(
            memory_id=_obtener_memory_id(),
            actor_id=id_seguro(usuario_id),
            session_id=id_seguro(usuario_id) + _SUFIJO_SESION,
            max_results=100,
            include_payload=True,
        )
    )
    for evento in reversed(eventos):
        if not evento.get("payload") or "blob" not in evento["payload"][0]:
            continue
        blob = evento["payload"][0]["blob"]
        try:
            return json.loads(blob) if isinstance(blob, str) else blob
        except (json.JSONDecodeError, AttributeError):
            continue
    return {}


def borrar_selecciones_estructuradas(usuario_id: str) -> int:
    """Borra el progreso guardado -- ver docstring de la variante local.
    Irreversible."""
    return _borrar_eventos(id_seguro(usuario_id), id_seguro(usuario_id) + _SUFIJO_SESION)
