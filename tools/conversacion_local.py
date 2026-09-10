"""Backend local (JSON) para el historial de turnos de la fase en curso.
Ver tools/conversacion.py para el selector de backend.

Uso: desarrollo sin AWS y pruebas. En producción se usa
tools/conversacion_agentcore.py.
"""

import json
import os

_RUTA_DATOS = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "conversaciones.json")


def _clave(usuario_id: str, fase: int) -> str:
    return f"{usuario_id}:{fase}"


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


def guardar_intercambio(usuario_id: str, fase: int, texto_usuario: str, texto_asistente: str) -> None:
    """Agrega un par (usuario, asistente) al historial de turnos de esta fase."""
    todo = _cargar_todo()
    clave = _clave(usuario_id, fase)
    turnos = todo.setdefault(clave, [])
    turnos.append({"rol": "user", "texto": texto_usuario})
    turnos.append({"rol": "assistant", "texto": texto_asistente})
    _guardar_todo(todo)


def leer_turnos(usuario_id: str, fase: int) -> list[dict]:
    """Devuelve los turnos guardados de esta fase, en orden cronológico."""
    todo = _cargar_todo()
    return todo.get(_clave(usuario_id, fase), [])
