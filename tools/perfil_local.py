"""Backend local (JSON) para el nombre de pila de la persona. Ver
tools/perfil.py para el selector de backend y por qué esto vive separado
de tools/ficha.py.

Uso: desarrollo sin AWS y pruebas. En producción se usa
tools/perfil_agentcore.py.
"""

import json
import os

_RUTA_DATOS = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "perfiles.json")


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


def guardar_nombre_usuario(usuario_id: str, nombre: str) -> None:
    """Guarda (o reemplaza) el nombre de pila de la persona. A diferencia
    de la ficha, esto no versiona -- es un dato de perfil, no el resultado
    de una fase."""
    todo = _cargar_todo()
    todo[usuario_id] = nombre
    _guardar_todo(todo)


def leer_nombre_usuario(usuario_id: str) -> str | None:
    """Devuelve el nombre guardado, o None si todavía no se pidió."""
    return _cargar_todo().get(usuario_id)


def borrar_nombre_usuario(usuario_id: str) -> None:
    """Borra el nombre guardado -- para resetear cuentas de prueba
    contaminadas (ver scripts/borrar_usuario.py). Irreversible."""
    todo = _cargar_todo()
    if usuario_id in todo:
        del todo[usuario_id]
        _guardar_todo(todo)
