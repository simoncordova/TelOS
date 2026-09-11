"""Selector de backend para el nombre de pila de la persona. Ver
docs/agente-proposito-de-vida-prompts.md sección 1 ("Paso 0: nombre").

Distinto de tools/ficha.py: la ficha versiona el resultado de cada fase;
el nombre es un dato de perfil que no cambia con las fases y tiene que
sobrevivir aunque la ficha avance de fase (por eso vive aparte, no como
una clave más dentro de `datos`). Mismo TELOS_FICHA_BACKEND que el resto
del proyecto -- no tiene sentido elegir un backend distinto para esto.

Se llama desde agents/orquestador.py (código determinístico), nunca
desde un agente de fase como tool: el nombre se pide una sola vez, antes
de que exista ninguna fase, así que no es una decisión conversacional
del modelo.
"""

import os

if os.environ.get("TELOS_FICHA_BACKEND", "local") == "agentcore":
    from tools.perfil_agentcore import guardar_nombre_usuario, leer_nombre_usuario
else:
    from tools.perfil_local import guardar_nombre_usuario, leer_nombre_usuario

__all__ = ["guardar_nombre_usuario", "leer_nombre_usuario"]
