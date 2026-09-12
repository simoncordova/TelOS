"""Backend local (JSON) para los insights de contexto de la persona. Ver
tools/contexto_usuario.py para el selector de backend.

Uso: desarrollo sin AWS y pruebas. En producción se usa
tools/contexto_usuario_agentcore.py.
"""

import json
import os

_RUTA_DATOS = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "contexto_usuario.json")


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


def agregar_insight(usuario_id: str, insight: str) -> None:
    """Agrega un hecho puntual a la lista de insights conocidos de esta
    persona -- no reemplaza los anteriores, los acumula."""
    todo = _cargar_todo()
    insights = todo.setdefault(usuario_id, [])
    insights.append(insight)
    _guardar_todo(todo)


def leer_insights(usuario_id: str) -> list[str]:
    """Devuelve todos los insights conocidos de esta persona, en el orden
    en que se agregaron. Lista vacía si todavía no hay ninguno."""
    return _cargar_todo().get(usuario_id, [])


def borrar_insights(usuario_id: str) -> None:
    """Borra todos los insights guardados -- para resetear cuentas de
    prueba contaminadas (ver scripts/borrar_usuario.py). Irreversible."""
    todo = _cargar_todo()
    if usuario_id in todo:
        del todo[usuario_id]
        _guardar_todo(todo)
