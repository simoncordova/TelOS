"""Selector de backend de calendario. Los agentes siempre importan
`crear_evento_calendario` desde este módulo, nunca directamente desde
calendario_local o calendario_agentcore -- mismo patrón que
tools/ficha.py.

Variable de entorno PROPIA (TELOS_CALENDARIO_BACKEND), a propósito
distinta de TELOS_FICHA_BACKEND que usa el resto de los tools: esta
integración depende de setup externo (Google Cloud Console + un
credential provider de AgentCore Identity, ver
tools/calendario_agentcore.py) que puede no estar listo todavía aunque
el resto del proyecto ya esté corriendo contra AgentCore Memory real --
desacoplar los dos flags evita que activar la persistencia real fuerce
también esta integración, todavía no validada contra un consentimiento
real de Google.

TELOS_CALENDARIO_BACKEND=local (default) usa la confirmación simulada.
TELOS_CALENDARIO_BACKEND=agentcore usa Google Calendar real vía
AgentCore Identity.
"""

import os

if os.environ.get("TELOS_CALENDARIO_BACKEND", "local") == "agentcore":
    from tools.calendario_agentcore import crear_evento_calendario
else:
    from tools.calendario_local import crear_evento_calendario

__all__ = ["crear_evento_calendario"]
