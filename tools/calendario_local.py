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
        detalle: dict con al menos "accion", "cuando" (día/hora
            recurrente) -- "proposito" es opcional, se agrega a la
            descripción del evento si se pasa (pedido explícito del
            dueño del producto, 14/09/2026: el cuerpo del evento debe
            mostrar el propósito, no solo la acción).

    Returns:
        {"confirmado": bool, "mensaje": str, "url_autorizacion": None}
        -- el mock nunca necesita autorización, url_autorizacion
        siempre None; mismo shape que calendario_agentcore.py para que
        quien llama (api/main.py) no tenga que distinguir el backend.
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
        "url_autorizacion": None,
    }
