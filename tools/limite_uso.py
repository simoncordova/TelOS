"""Límite de mensajes por usuario por día. Ver
docs/agente-proposito-de-vida-prompts.md sección 1 (Orquestador).

Tripwire de costo, no persistencia de producto: cuenta cada invocación
real al modelo (no cada mensaje que escribe la persona -- una cascada de
cambio de fase dispara más de una invocación por mensaje, y cada una
cuesta igual, así que cada una cuenta). JSON local alcanza: App Runner
corre con una sola instancia (ver infra/stacks/telos_stack.py,
MaxSize=1), así que no hace falta un backend compartido entre
instancias, y perder el contador en un redeploy es aceptable para este
propósito -- el guardrail real contra un desastre de costo es el AWS
Budget del stack, esto es la primera línea de defensa, no la única.
"""

import json
import os
from datetime import date

_RUTA_DATOS = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "uso_diario.json")

LIMITE_DIARIO = 100

_MENSAJE_LIMITE = {
    "es": (
        "Llegaste al límite de mensajes de hoy para esta cuenta de prueba "
        "(100 por día). Esto es una protección de costo del demo, no algo "
        "que dijiste vos -- probá de nuevo mañana, o avisale a quien "
        "administra Telos si necesitás seguir ahora mismo."
    ),
    "en": (
        "You've reached today's message limit for this test account (100 "
        "per day). This is a cost safeguard for the demo, not something "
        "you said -- try again tomorrow, or let whoever manages Telos "
        "know if you need to keep going right now."
    ),
}


def _cargar_todo() -> dict:
    if not os.path.exists(_RUTA_DATOS):
        return {}
    with open(_RUTA_DATOS, "r", encoding="utf-8") as f:
        contenido = f.read().strip()
        return json.loads(contenido) if contenido else {}


def _guardar_todo(datos: dict) -> None:
    os.makedirs(os.path.dirname(_RUTA_DATOS), exist_ok=True)
    with open(_RUTA_DATOS, "w", encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False, indent=2)


def _clave(usuario_id: str) -> str:
    return f"{usuario_id}:{date.today().isoformat()}"


def excedio_limite_diario(usuario_id: str) -> bool:
    """True si esta cuenta ya llegó a LIMITE_DIARIO invocaciones hoy."""
    todo = _cargar_todo()
    return todo.get(_clave(usuario_id), 0) >= LIMITE_DIARIO


def registrar_invocacion(usuario_id: str) -> int:
    """Suma una invocación real al contador del día. Devuelve el total
    acumulado (no llamar si excedio_limite_diario ya dio True)."""
    todo = _cargar_todo()
    clave = _clave(usuario_id)
    todo[clave] = todo.get(clave, 0) + 1
    _guardar_todo(todo)
    return todo[clave]


def mensaje_limite_alcanzado(idioma: str = "es") -> str:
    return _MENSAJE_LIMITE["en" if idioma == "en" else "es"]
