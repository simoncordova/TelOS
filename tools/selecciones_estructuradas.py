"""Selector de backend para las selecciones del árbol Ikigai (Fase 1).
Ver C:\\Users\\Wendy\\.claude\\plans\\quirky-launching-swing.md.

Reemplaza a tools/progreso_exploracion.py (Explorer v2, sacado el
13/09/2026): ya no hay texto libre que evaluar turno a turno -- la
persona elige de tools/categorias_ikigai.py, cada elección aporta sus
`dimensiones` a una cobertura que se calcula por código
(agents/orquestador.py::SesionTelos.confirmar_seleccion). No versiona
(a diferencia de tools/ficha.py): es progreso transitorio de UNA fase en
curso, cada guardado sobrescribe el anterior.

TELOS_FICHA_BACKEND mismo criterio que el resto del proyecto.
"""

import os

if os.environ.get("TELOS_FICHA_BACKEND", "local") == "agentcore":
    from tools.selecciones_estructuradas_agentcore import (
        borrar_selecciones_estructuradas,
        guardar_selecciones_estructuradas,
        leer_selecciones_estructuradas,
    )
else:
    from tools.selecciones_estructuradas_local import (
        borrar_selecciones_estructuradas,
        guardar_selecciones_estructuradas,
        leer_selecciones_estructuradas,
    )

__all__ = [
    "borrar_selecciones_estructuradas",
    "guardar_selecciones_estructuradas",
    "leer_selecciones_estructuradas",
]
