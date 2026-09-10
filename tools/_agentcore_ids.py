"""Sanitiza usuario_id (el email real de Cognito) a un identificador que
cumpla las reglas de AgentCore Memory para actorId/sessionId -- ninguno
de los dos acepta "@" ni ".", que un email siempre tiene. Confirmado con
un ValidationException real contra AWS:
"Value at 'actorId' failed to satisfy constraint: Member must satisfy
regular expression pattern: [a-zA-Z0-9][a-zA-Z0-9-_/]*(?::[a-zA-Z0-9-_/]+)*[a-zA-Z0-9-_/]*"
(sessionId es más restrictivo todavía: sin "/" ni ":").

Usado por tools/ficha_agentcore.py y tools/conversacion_agentcore.py --
mismo esquema de sanitización en los dos para que, con el mismo
usuario_id de entrada, ambos lleguen al mismo actor_id; si no
coincidieran, AgentCore Memory los trataría como usuarios distintos.

No es a prueba de colisiones (dos emails reales que solo difieran en
caracteres que se sanitizan igual terminarían con el mismo id) -- riesgo
aceptado para el MVP, con 3 usuarios de prueba elegidos a mano.
"""

import re

_CARACTER_INVALIDO = re.compile(r"[^a-zA-Z0-9_-]")


def id_seguro(usuario_id: str) -> str:
    seguro = _CARACTER_INVALIDO.sub("_", usuario_id)
    if not seguro or not seguro[0].isalnum():
        seguro = f"u_{seguro}"
    return seguro
