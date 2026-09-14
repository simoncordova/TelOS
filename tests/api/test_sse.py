"""Regresión de un bug real visto en logs de producción (14/09/2026):
`api.sse.stream_eventos` mandaba el evento "done" desde un `finally`,
sin distinguir "el generador terminó" de "el cliente se desconectó
(GeneratorExit)". Python prohíbe yield mientras se propaga un
GeneratorExit -- intentarlo producía `RuntimeError: generator ignored
GeneratorExit` en los logs, y como el generador de adentro (que sostiene
el lock por usuario+idioma en api/main.py::_eventos_turno) no se cerraba
a mano, el lock podía quedar tomado hasta que el recolector de basura
lo alcanzara, bloqueando en cascada el resto de los requests de esa
misma persona. Estos tests ejercitan api.sse.stream_eventos en aislado,
sin HTTP real ni AWS."""

from api.sse import stream_eventos


def test_yields_cada_evento_y_termina_en_done():
    def generador():
        yield "mensaje", {"fase": 1, "texto": "hola", "opciones": []}
        yield "ficha", {"existe": False}

    eventos = list(stream_eventos(generador()))
    assert len(eventos) == 3
    assert eventos[0].startswith("event: mensaje\n")
    assert eventos[1].startswith("event: ficha\n")
    assert eventos[2] == "event: done\ndata: {}\n\n"


def test_excepcion_a_mitad_de_camino_manda_error_y_done():
    def generador():
        yield "mensaje", {"fase": 1, "texto": "hola", "opciones": []}
        raise ValueError("Bedrock no disponible")

    eventos = list(stream_eventos(generador()))
    assert len(eventos) == 3
    assert eventos[0].startswith("event: mensaje\n")
    assert eventos[1].startswith("event: error\n")
    assert "Bedrock no disponible" in eventos[1]
    assert eventos[2] == "event: done\ndata: {}\n\n"


def test_cierre_temprano_cierra_el_generador_de_adentro_sin_runtime_error():
    """Simula un cliente que se desconecta a mitad de un turno (cerró la
    pestaña, cambió de fase, o el proxy cortó la conexión) -- Starlette
    llama a `.close()` sobre el generador que devuelve `stream_eventos`.
    Antes del fix esto disparaba `RuntimeError: generator ignored
    GeneratorExit` (por el `finally: yield` viejo) y nunca cerraba el
    generador de adentro, que es quien sostiene el lock real."""
    cerrado_de_adentro = False

    def generador_de_adentro():
        nonlocal cerrado_de_adentro
        try:
            yield "mensaje", {"fase": 1, "texto": "hola", "opciones": []}
            yield "mensaje", {"fase": 1, "texto": "no debería llegar", "opciones": []}
        finally:
            # Mismo lugar donde _eventos_turno soltaría el lock real
            # (el `with lock:` de api/main.py) -- acá solo confirmamos
            # que efectivamente se cierra, sin lock real de por medio.
            cerrado_de_adentro = True

    externo = stream_eventos(generador_de_adentro())
    primero = next(externo)
    assert primero.startswith("event: mensaje\n")

    # No debe lanzar RuntimeError (antes: "generator ignored GeneratorExit").
    externo.close()

    assert cerrado_de_adentro is True
