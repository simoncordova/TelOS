"""Backend de AgentCore Memory para el historial de turnos de la fase en
curso. Ver tools/conversacion.py para el contrato y el selector de
backend.

Usa `create_event`/`list_events` (turnos conversacionales reales, con
role USER/ASSISTANT) — distinto de tools/ficha_agentcore.py, que usa
`create_blob_event` para guardar el resultado estructurado de cada fase.
Mismo recurso de Memory (mismo nombre/memory_id), pero un `session_id`
distinto por fase para no mezclar las dos cosas ni los turnos de fases
distintas entre sí.

Limitación conocida: si una fase se re-entra (ej. Fase 5 manda de vuelta
a Fase 3), esta implementación no distingue "primera vez por Fase 3" de
"segunda vez" — leer_turnos devolvería también los turnos de la primera
pasada. Aceptable para el MVP; si hace falta separarlos, agregar un
sufijo de intento al session_id.

Sin probar contra un recurso real de AgentCore Memory (este entorno de
desarrollo no tiene credenciales de AWS) — validar en CloudShell antes
del demo, igual que tools/ficha_agentcore.py.
"""

import os

from bedrock_agentcore.memory import MemoryClient

from tools._agentcore_ids import id_seguro

_NOMBRE_MEMORIA = os.environ.get("TELOS_MEMORY_NAME", "telos_fichas_usuario")
_REGION = os.environ.get("TELOS_AWS_REGION", "us-east-1")

_cliente: MemoryClient | None = None
_memory_id: str | None = None


def _obtener_cliente() -> MemoryClient:
    global _cliente
    if _cliente is None:
        _cliente = MemoryClient(region_name=_REGION)
    return _cliente


def _obtener_memory_id() -> str:
    global _memory_id
    if _memory_id is None:
        memoria = _obtener_cliente().create_or_get_memory(
            name=_NOMBRE_MEMORIA,
            description="Ficha y conversación en curso de cada usuario de Telos.",
            event_expiry_days=365,
        )
        _memory_id = memoria.get("memoryId", memoria.get("id"))
    return _memory_id


def _sesion_id(fase: int) -> str:
    return f"conversacion-fase{fase}"


def guardar_intercambio(usuario_id: str, fase: int, texto_usuario: str, texto_asistente: str) -> None:
    """Agrega un par (usuario, asistente) al historial de turnos de esta fase."""
    _obtener_cliente().create_event(
        memory_id=_obtener_memory_id(),
        # usuario_id es el email real de Cognito -- sanitizar antes de
        # usarlo como actorId (ver tools/_agentcore_ids.py).
        actor_id=id_seguro(usuario_id),
        session_id=_sesion_id(fase),
        messages=[(texto_usuario, "USER"), (texto_asistente, "ASSISTANT")],
    )


def leer_turnos(usuario_id: str, fase: int) -> list[dict]:
    """Devuelve los turnos guardados de esta fase, en orden cronológico."""
    eventos = _obtener_cliente().list_events(
        memory_id=_obtener_memory_id(),
        actor_id=id_seguro(usuario_id),
        session_id=_sesion_id(fase),
        max_results=200,
        include_payload=True,
    )
    turnos = []
    for evento in eventos:
        for bloque in evento.get("payload") or []:
            conversacional = bloque.get("conversational")
            if not conversacional:
                continue
            rol = "user" if conversacional.get("role") == "USER" else "assistant"
            texto = conversacional.get("content", {}).get("text", "")
            turnos.append({"rol": rol, "texto": texto})
    return turnos


def borrar_turnos_usuario(usuario_id: str) -> int:
    """Borra los turnos guardados de las 5 fases para este usuario --
    para resetear cuentas de prueba contaminadas (ver
    scripts/borrar_usuario.py). Devuelve cuántos eventos borró en total.
    Irreversible.

    AgentCore Memory no tiene un "borrar todo el hilo" de un solo
    llamado -- hay que listar y borrar evento por evento (`DeleteEvent`,
    que pide memoryId+actorId+sessionId+eventId, los cuatro
    obligatorios, sin wrapper de alto nivel en el SDK a diferencia de
    create_event/list_events). Sin probar contra un recurso real (este
    entorno de desarrollo no tiene credenciales de AWS) -- validar con
    una cuenta de prueba antes de confiar en esto para una cuenta real.
    """
    cliente = _obtener_cliente()
    memory_id = _obtener_memory_id()
    actor_id = id_seguro(usuario_id)
    borrados = 0
    for fase in range(1, 6):
        session_id = _sesion_id(fase)
        eventos = cliente.list_events(
            memory_id=memory_id,
            actor_id=actor_id,
            session_id=session_id,
            max_results=200,
            include_payload=False,
        )
        for evento in eventos:
            event_id = evento.get("eventId")
            if not event_id:
                continue
            cliente.delete_event(memoryId=memory_id, sessionId=session_id, eventId=event_id, actorId=actor_id)
            borrados += 1
    return borrados
