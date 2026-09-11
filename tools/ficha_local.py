"""Backend local (JSON) para la ficha del usuario. Ver
docs/agente-proposito-de-vida-prompts.md secciones 7 y 9.

Uso: desarrollo sin AWS y pruebas. En producción se usa
tools/ficha_agentcore.py — ver tools/ficha.py para el selector de backend.

Cada llamada a guardar_ficha_usuario agrega una versión nueva; nunca
sobrescribe el historial (ver reglas de privacidad/versionado del spec).
"""

import json
import os
from datetime import datetime, timezone

_RUTA_DATOS = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "fichas.json")


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


def guardar_ficha_usuario(usuario_id: str, datos: dict, fase: int, motivo_version: str) -> None:
    """Agrega una nueva versión de la ficha del usuario. No sobrescribe el historial."""
    todo = _cargar_todo()
    versiones = todo.setdefault(usuario_id, [])
    versiones.append(
        {
            "fase": fase,
            "datos": datos,
            "motivo_version": motivo_version,
            "fecha": datetime.now(timezone.utc).isoformat(),
        }
    )
    _guardar_todo(todo)


def leer_ficha_usuario(usuario_id: str) -> dict:
    """Devuelve la última versión de la ficha y un resumen del historial.

    Returns:
        {
            "existe": bool,
            "actual": {"fase": int, "datos": dict, "motivo_version": str, "fecha": str} | None,
            "historial": [{"fase": int, "datos": dict, "motivo_version": str, "fecha": str}, ...],
        }

    Nota: `historial` incluye `datos` completo de cada versión vieja (no
    solo metadata) desde que se agregó la vista "Tu evolución" de la
    interfaz -- el backend ya tenía el dato completo en memoria antes de
    filtrarlo, así que esto no cuesta una lectura extra.
    """
    todo = _cargar_todo()
    versiones = todo.get(usuario_id, [])
    if not versiones:
        return {"existe": False, "actual": None, "historial": []}

    return {
        "existe": True,
        "actual": versiones[-1],
        "historial": versiones[:-1],
    }
