"""Adaptador genérico: traduce un generador Python de eventos
`(nombre_evento, datos)` a Server-Sent Events, sin acumular nada en
memoria y preservando el orden de llegada (una cascada de cambio de
fase entrega más de un mensaje por turno; el frontend tiene que verlos
en el mismo orden en que se generaron, no todos juntos al final).

Quien arma el generador de eventos (api/main.py) decide qué eventos
produce y bajo qué lock/orquestación -- este módulo solo sabe formatear,
a propósito: así el lock por (usuario_id, idioma) puede cubrir toda la
iteración real (incluyendo las llamadas a Bedrock que pasan mientras se
consume el generador), no solo el momento en que se lo crea."""

import json
from collections.abc import Generator, Iterable


def formatear_evento(nombre: str, datos: dict) -> str:
    return f"event: {nombre}\ndata: {json.dumps(datos, ensure_ascii=False)}\n\n"


def stream_eventos(generador_eventos: Iterable[tuple[str, dict]]) -> Generator[str, None, None]:
    """Consume el generador de eventos ya armado por quien llama y lo
    traduce a SSE. Agrega un `error` si el generador levanta una
    excepción a mitad de camino, y siempre cierra con `done` -- haya
    habido error o no -- para que el frontend sepa cuándo dejar de
    esperar más frames."""
    try:
        for nombre, datos in generador_eventos:
            yield formatear_evento(nombre, datos)
    except Exception as e:  # noqa: BLE001 -- el error tiene que llegar al cliente, no tumbar la conexión en silencio
        yield formatear_evento("error", {"detalle": str(e)})
    finally:
        yield "event: done\ndata: {}\n\n"
