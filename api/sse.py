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
    excepción a mitad de camino, y cierra con `done` -- haya habido
    error o no -- para que el frontend sepa cuándo dejar de esperar más
    frames.

    Bug real (14/09/2026, visto en logs de producción): la versión
    anterior mandaba el evento `done` desde un `finally`, sin distinguir
    "el generador terminó" de "alguien llamó a `.close()` porque la
    persona cerró la pestaña, navegó a otra fase, o CloudFront cortó la
    conexión". Python prohíbe expresamente hacer `yield` mientras se
    propaga un `GeneratorExit` -- intentarlo no manda nada, solo genera
    `RuntimeError: generator ignored GeneratorExit` (visible en los logs
    del contenedor como "Exception ignored in: <generator object
    stream_eventos>"). Peor todavía: como acá se itera `generador_eventos`
    con un `for` común (no `yield from`), cerrar ESTE generador no cierra
    automáticamente al de adentro (api/main.py::_eventos_turno, que es
    quien mantiene tomado el lock por usuario+idioma durante toda la
    iteración) -- sin cerrarlo a mano, ese lock podía quedar tomado hasta
    que el recolector de basura llegara a destruirlo por su cuenta, en
    vez de liberarse apenas la persona se va. Eso explica el patrón real
    reportado: después de que una conexión se cortaba a medio turno,
    cualquier request siguiente de esa misma persona (otro `abrir` o un
    `confirmar`) se quedaba esperando el lock hasta tocar el timeout del
    proxy (504 / net::ERR_HTTP2_PROTOCOL_ERROR)."""
    try:
        for nombre, datos in generador_eventos:
            yield formatear_evento(nombre, datos)
    except GeneratorExit:
        # No hay nadie del otro lado esperando un "done" -- y ya no se
        # puede mandar nada de todos modos (ver docstring). Cerrar el
        # generador de adentro a mano, porque el `for` de arriba no lo
        # hace solo, para soltar YA el lock que sigue sosteniendo.
        generador_eventos.close()
        raise
    except Exception as e:  # noqa: BLE001 -- el error tiene que llegar al cliente, no tumbar la conexión en silencio
        yield formatear_evento("error", {"detalle": str(e)})
        yield "event: done\ndata: {}\n\n"
    else:
        yield "event: done\ndata: {}\n\n"
