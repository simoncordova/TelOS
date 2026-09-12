"""Backend mock de calendario -- ver tools/calendario.py para el selector.

Devuelve una confirmación fija sin llamar a ninguna API externa. Es el
default (TELOS_CALENDARIO_BACKEND sin setear o distinto de "agentcore")
para que el flujo completo de la Fase 4 se pueda demostrar y probar sin
depender de que el setup de Google/AgentCore Identity (externo a este
repo, ver tools/calendario_agentcore.py) ya esté hecho.
"""


def crear_evento_calendario(usuario_id: str, detalle: dict) -> dict:
    """Registra (mock) el evento recurrente del sistema de 4 preguntas.

    Args:
        usuario_id: identificador del usuario.
        detalle: dict con al menos "accion", "cuando" (día/hora recurrente).

    Returns:
        {"confirmado": bool, "mensaje": str}
    """
    accion = detalle.get("accion", "tu sistema")
    cuando = detalle.get("cuando", "el horario que definiste")
    return {
        "confirmado": True,
        "mensaje": (
            f"Listo, quedó anotado: \"{accion}\" — {cuando}. "
            "(Integración de calendario real pendiente; por ahora es una "
            "confirmación simulada.)"
        ),
    }
