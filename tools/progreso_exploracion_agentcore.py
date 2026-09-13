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
    # max_results alto a propósito -- MemoryClient.list_events() devuelve
    # los eventos en orden cronológico y corta con `all_events[:max_results]`
    # (ver .venv .../bedrock_agentcore/memory/client.py), o sea que un
    # max_results chico te da los eventos MÁS VIEJOS, no los más
    # recientes. Bug real (12/09/2026): esto tenía max_results=10 copiado
    # de perfil_agentcore.py (que guarda el nombre una sola vez, ahí nunca
    # se notaba); acá se guarda un evento por cada turno de Fase 1
    # (orquestador.py::_invocar_explorador), así que pasados 10 turnos la
    # lectura quedaba congelada en un progreso viejo -- un eje marcado
    # "answered" después del evento #10 volvía a verse "pending" y el
    # Explorador repetía la pregunta ya contestada.
    eventos = _obtener_cliente().list_events(
        memory_id=_obtener_memory_id(),
        actor_id=id_seguro(usuario_id),
        session_id=id_seguro(usuario_id) + _SUFIJO_SESION,
        max_results=100,
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
