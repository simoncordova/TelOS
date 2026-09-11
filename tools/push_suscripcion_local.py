"""Backend local (JSON) para las suscripciones de push. Mismo patrón que
tools/ficha_local.py: un solo archivo en data/, para desarrollo sin AWS
y para tests (ver tools/push_suscripcion.py para el selector).

Forma de una suscripción (la misma que entrega
PushSubscription.toJSON() en el navegador, ver web/src/lib/push.ts):
    {"endpoint": str, "keys": {"p256dh": str, "auth": str}}
"""

import json
import os

_RUTA_DATOS = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "push_suscripciones.json")


def _cargar_todo() -> dict:
    if not os.path.exists(_RUTA_DATOS):
        return {}
    with open(_RUTA_DATOS, "r", encoding="utf-8") as f:
        contenido = f.read().strip()
        return json.loads(contenido) if contenido else {}


def _guardar_todo(datos_completos: dict) -> None:
    os.makedirs(os.path.dirname(_RUTA_DATOS), exist_ok=True)
    with open(_RUTA_DATOS, "w", encoding="utf-8") as f:
        json.dump(datos_completos, f, ensure_ascii=False, indent=2)


def guardar_suscripcion_push(usuario_id: str, suscripcion: dict) -> None:
    """Agrega la suscripción si es nueva (mismo endpoint = mismo
    dispositivo/navegador, se reemplaza en vez de duplicar -- puede
    traer keys nuevas si el navegador rotó las claves)."""
    todo = _cargar_todo()
    suscripciones = todo.setdefault(usuario_id, [])
    suscripciones[:] = [s for s in suscripciones if s.get("endpoint") != suscripcion.get("endpoint")]
    suscripciones.append(suscripcion)
    _guardar_todo(todo)


def eliminar_suscripcion_push(usuario_id: str, endpoint: str) -> None:
    todo = _cargar_todo()
    if usuario_id not in todo:
        return
    todo[usuario_id] = [s for s in todo[usuario_id] if s.get("endpoint") != endpoint]
    if not todo[usuario_id]:
        del todo[usuario_id]
    _guardar_todo(todo)


def listar_suscripciones_push(usuario_id: str) -> list[dict]:
    return _cargar_todo().get(usuario_id, [])


def listar_todas_las_suscripciones() -> dict[str, list[dict]]:
    """Usado por api/main.py::enviar_recordatorios (Fase 4) para
    recorrer a todas las personas con al menos una suscripción activa."""
    return _cargar_todo()
