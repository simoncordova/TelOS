"""Selector de backend para el historial de turnos de la fase en curso.

Distinto de tools/ficha.py: la ficha guarda el resultado FINAL de cada
fase (una sola vez, al cerrarla). Esto guarda la conversación turno por
turno MIENTRAS la fase todavía está en curso, para poder reconstruirla
si el proceso se corta a mitad de camino (el proceso se cae, CloudShell
recicla la sesión, se cierra el navegador) — sin esto, todo lo hablado
en una fase que no llegó a cerrarse se pierde para siempre, aunque la
ficha esté guardada en AgentCore Memory.

Mismo TELOS_FICHA_BACKEND que tools/ficha.py: no tiene sentido elegir
backends distintos para las dos cosas.
"""

import os

if os.environ.get("TELOS_FICHA_BACKEND", "local") == "agentcore":
    from tools.conversacion_agentcore import guardar_intercambio, leer_turnos
else:
    from tools.conversacion_local import guardar_intercambio, leer_turnos

__all__ = ["guardar_intercambio", "leer_turnos"]
