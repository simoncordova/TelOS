"""Backend de AgentCore Memory para el progreso de ejes del Explorador.
Ver tools/progreso_exploracion.py para el selector de backend.

Reutiliza el mismo recurso de Memory que tools/ficha_agentcore.py (mismo
cliente, mismo memory_id) en vez de aprovisionar uno nuevo -- un
`session_id` propio ("<usuario>__progreso_exploracion") alcanza para
aislar este hilo de eventos del de la ficha versionada y del de perfil,
sin gastar otro recurso de AWS para un MVP de hackathon.

No versiona (a diferencia de la ficha): cada guardado agrega un evento
nuevo, pero solo se lee el último -- mismo patrón que
tools/perfil_agentcore.py para el nombre."""

import json

from tools._agentcore_ids import id_seguro
from tools.ficha_agentcore import _obtener_cliente, _obtener_memory_id
from tools.ficha_agentcore import borrar_eventos as _borrar_eventos

_SUFIJO_SESION = "__progreso_exploracion"


def guardar_progreso_exploracion(usuario_id: str, ejes: dict) -> None:
    _obtener_cliente().create_blob_event(
        memory_id=_obtener_memory_id(),
        actor_id=id_seguro(usuario_id),
        session_id=id_seguro(usuario_id) + _SUFIJO_SESION,
        blob_data=json.dumps(ejes, ensure_ascii=False),
    )


def leer_progreso_exploracion(usuario_id: str) -> dict:
    eventos = _obtener_cliente().list_events(
        memory_id=_obtener_memory_id(),
        actor_id=id_seguro(usuario_id),
        session_id=id_seguro(usuario_id) + _SUFIJO_SESION,
        max_results=10,
        include_payload=True,
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


def borrar_progreso_exploracion(usuario_id: str) -> int:
    """Borra el progreso guardado -- ver docstring de la variante local.
    Irreversible."""
    return _borrar_eventos(id_seguro(usuario_id), id_seguro(usuario_id) + _SUFIJO_SESION)
