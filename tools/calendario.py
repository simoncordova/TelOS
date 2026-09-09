"""crear_evento_calendario — P2 según PLAN.md.

Mock por defecto: devuelve una confirmación fija sin llamar a ninguna API
externa. Cuando se implemente la integración real vía AgentCore Gateway
(Google Calendar), solo cambia el cuerpo de esta función — el prompt del
Agente 4 y su firma no cambian.
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
