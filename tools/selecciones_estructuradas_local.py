"""Backend local (JSON) para las selecciones del árbol Ikigai. Ver
tools/selecciones_estructuradas.py para el selector de backend y el
porqué.

Uso: desarrollo sin AWS y pruebas. En producción se usa
tools/selecciones_estructuradas_agentcore.py.
"""

import json
import os

_RUTA_DATOS = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "selecciones_estructuradas.json")


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


def guardar_selecciones_estructuradas(usuario_id: str, progreso: dict) -> None:
    """Sobrescribe el progreso de selecciones vigente -- no versiona, es
    estado transitorio de la fase en curso."""
    todo = _cargar_todo()
    todo[usuario_id] = progreso
    _guardar_todo(todo)


def leer_selecciones_estructuradas(usuario_id: str) -> dict:
    """Devuelve el progreso guardado, o {} si todavía no hay ninguno
    (fase recién arrancada)."""
    return _cargar_todo().get(usuario_id, {})


def borrar_selecciones_estructuradas(usuario_id: str) -> None:
    """Borra el progreso guardado -- para resetear cuentas de prueba
    contaminadas (ver scripts/borrar_usuario.py) y para limpiar después
    de que la fase cierra de verdad. Irreversible."""
    todo = _cargar_todo()
    if usuario_id in todo:
        del todo[usuario_id]
        _guardar_todo(todo)
