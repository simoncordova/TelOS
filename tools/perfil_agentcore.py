"""Backend de AgentCore Memory para el nombre de pila de la persona. Ver
tools/perfil.py para el selector de backend.

Reutiliza el mismo recurso de Memory que tools/ficha_agentcore.py (mismo
cliente, mismo memory_id) en vez de aprovisionar uno nuevo solo para un
string -- un `session_id` distinto ("<usuario>__perfil") alcanza para
aislar este hilo de eventos del de la ficha versionada, sin gastar otro
recurso de AWS para un MVP de hackathon.

No versiona: cada guardado sobrescribe el nombre vigente, tomando el
último evento del hilo -- a diferencia de la ficha, el nombre no tiene
historial que preservar.
"""

import json

from tools._agentcore_ids import id_seguro
from tools.ficha_agentcore import _obtener_cliente, _obtener_memory_id
from tools.ficha_agentcore import borrar_eventos as _borrar_eventos

_SUFIJO_SESION = "__perfil"


def guardar_nombre_usuario(usuario_id: str, nombre: str) -> None:
    _obtener_cliente().create_blob_event(
        memory_id=_obtener_memory_id(),
        actor_id=id_seguro(usuario_id),
        session_id=id_seguro(usuario_id) + _SUFIJO_SESION,
        blob_data=json.dumps({"nombre": nombre}, ensure_ascii=False),
    )


def leer_nombre_usuario(usuario_id: str) -> str | None:
    # max_results alto a propósito -- ver el comentario equivalente en
    # tools/progreso_exploracion_agentcore.py::leer_progreso_exploracion,
    # que sí llegó a fallar en producción con este mismo max_results=10
    # copiado de acá: list_events() corta con `all_events[:max_results]`
    # sobre una lista en orden cronológico, así que un valor chico te da
    # los eventos más VIEJOS, no los recientes. Acá nunca se notó porque
    # el nombre se guarda una sola vez, pero es el mismo riesgo si algún
    # día se re-guarda más de 10 veces (ej. corrección de nombre).
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
            datos = json.loads(blob) if isinstance(blob, str) else blob
            return datos.get("nombre")
        except (json.JSONDecodeError, AttributeError):
            continue
    return None


def borrar_nombre_usuario(usuario_id: str) -> int:
    """Borra el evento con el nombre guardado -- para resetear cuentas
    de prueba contaminadas (ver scripts/borrar_usuario.py). Irreversible."""
    return _borrar_eventos(id_seguro(usuario_id), id_seguro(usuario_id) + _SUFIJO_SESION)
