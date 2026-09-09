"""Selector de backend de persistencia de la ficha del usuario.

Los agentes siempre importan `guardar_ficha_usuario` / `leer_ficha_usuario`
desde este módulo, nunca directamente desde ficha_local o ficha_agentcore
— eso es lo que permite hacer el swap de backend sin tocar agents/*.py.

TELOS_FICHA_BACKEND=local (default) usa JSON local, para desarrollo sin
AWS. TELOS_FICHA_BACKEND=agentcore usa AgentCore Memory real — ver
tools/ficha_agentcore.py.

Estas funciones se exponen sin decorador @tool a propósito: usuario_id y
fase no deben quedar a criterio del modelo (es contexto determinístico de
la sesión, no una decisión conversacional). Cada agents/*.py construye su
propio tool con @tool envolviendo estas funciones, fijando usuario_id y
fase por closure y dejando que el modelo solo decida `datos` y
`motivo_version`.
"""

import os

if os.environ.get("TELOS_FICHA_BACKEND", "local") == "agentcore":
    from tools.ficha_agentcore import guardar_ficha_usuario, leer_ficha_usuario
else:
    from tools.ficha_local import guardar_ficha_usuario, leer_ficha_usuario

__all__ = ["guardar_ficha_usuario", "leer_ficha_usuario"]
