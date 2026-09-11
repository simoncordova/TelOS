"""Selector de backend para las suscripciones de push del navegador
(Fase 3 del plan de migración -- rama gamificacion). Mismo patrón que
tools/ficha.py: los agentes/la API nunca importan directo de
push_suscripcion_local o push_suscripcion_agentcore.

TELOS_FICHA_BACKEND=local (default) usa JSON local, TELOS_FICHA_BACKEND=
agentcore usa AgentCore Memory real -- reutiliza la MISMA variable de
entorno que ya selecciona el backend de la ficha (no tiene sentido un
backend de persistencia distinto solo para esto).

No expuesto como tool de ningún agente: suscribirse/desuscribirse es una
acción de la interfaz (un botón, un permiso de navegador), no una
decisión conversacional del modelo -- por eso vive en api/main.py, no en
agents/*.py.
"""

import os

if os.environ.get("TELOS_FICHA_BACKEND", "local") == "agentcore":
    from tools.push_suscripcion_agentcore import (
        eliminar_suscripcion_push,
        guardar_suscripcion_push,
        listar_suscripciones_push,
        listar_todas_las_suscripciones,
    )
else:
    from tools.push_suscripcion_local import (
        eliminar_suscripcion_push,
        guardar_suscripcion_push,
        listar_suscripciones_push,
        listar_todas_las_suscripciones,
    )

__all__ = [
    "eliminar_suscripcion_push",
    "guardar_suscripcion_push",
    "listar_suscripciones_push",
    "listar_todas_las_suscripciones",
]
