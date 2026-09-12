"""Cobertura de tools/calendario_agentcore.py sin credenciales de AWS ni de
Google -- se mockea en el límite documentado por el propio módulo: la
respuesta de AgentCore Identity (`_pedir_token`/`_cliente`) y la del
cliente de Google (`googleapiclient.discovery.build`), nunca la lógica de
Telos que corre alrededor.

El módulo bajo prueba deja escrito que fue validado contra el código
fuente instalado de bedrock_agentcore pero "sin poder ejercitar el flujo
de consentimiento real" -- este archivo cubre lo que sí se puede probar
sin esa cuenta real: el timeout que no debe bloquear un turno de chat, y
las tres ramas de salida de crear_evento_calendario.
"""

import time

from tools import calendario_agentcore as ca


def test_obtener_token_no_bloquea_mas_alla_del_timeout(monkeypatch):
    # Regresión del bug real documentado en el módulo: si el
    # ThreadPoolExecutor se usara como context manager, __exit__ esperaría
    # a que el polling interno del SDK (hasta 600s reales) termine antes
    # de devolver, aunque ya haya timeouteado.
    monkeypatch.setattr(ca, "_ESPERA_MAXIMA_SEGUNDOS", 0.2)

    def _pedir_token_lento(usuario_id, contenedor_url):
        contenedor_url.append("https://accounts.google.com/o/oauth2/fake")
        time.sleep(5)
        return "token-nunca-usado"

    monkeypatch.setattr(ca, "_pedir_token", _pedir_token_lento)

    inicio = time.monotonic()
    token, url = ca._obtener_token("usuario-1")
    transcurrido = time.monotonic() - inicio

    assert token is None
    assert url == "https://accounts.google.com/o/oauth2/fake"
    assert transcurrido < 1.0


def test_obtener_token_falla_real_no_url(monkeypatch):
    def _pedir_token_falla(usuario_id, contenedor_url):
        raise RuntimeError("AgentCore/Google no disponible")

    monkeypatch.setattr(ca, "_pedir_token", _pedir_token_falla)

    token, url = ca._obtener_token("usuario-1")

    assert token is None
    assert url is None


def test_crear_evento_calendario_pendiente_de_autorizacion(monkeypatch):
    monkeypatch.setattr(ca, "_obtener_token", lambda usuario_id: (None, "https://consent.example/abc"))

    resultado = ca.crear_evento_calendario("u1", {"accion": "meditar", "cuando": "8am"})

    assert resultado["confirmado"] is False
    assert "https://consent.example/abc" in resultado["mensaje"]


def test_crear_evento_calendario_fallo_sin_url(monkeypatch):
    monkeypatch.setattr(ca, "_obtener_token", lambda usuario_id: (None, None))

    resultado = ca.crear_evento_calendario("u1", {"accion": "meditar"})

    assert resultado["confirmado"] is False
    assert "http" not in resultado["mensaje"]


def test_crear_evento_calendario_exitoso(monkeypatch):
    monkeypatch.setattr(ca, "_obtener_token", lambda usuario_id: ("token-valido", None))

    class _Ejecutable:
        def execute(self):
            return {"id": "evt-123"}

    class _EventosFake:
        def insert(self, calendarId, body):
            return _Ejecutable()

    class _ServicioFake:
        def events(self):
            return _EventosFake()

    monkeypatch.setattr("googleapiclient.discovery.build", lambda *a, **k: _ServicioFake())

    resultado = ca.crear_evento_calendario("u1", {"accion": "meditar", "cuando": "8am"})

    assert resultado == {
        "confirmado": True,
        "mensaje": 'Listo, lo agendé de verdad en tu Google Calendar: "meditar" — 8am.',
        "eventoId": "evt-123",
    }


def test_crear_evento_calendario_rechazado_por_google(monkeypatch):
    from googleapiclient.errors import HttpError

    monkeypatch.setattr(ca, "_obtener_token", lambda usuario_id: ("token-valido", None))

    class _RespuestaFalsa:
        status = 403
        reason = "Forbidden"

    def _insert_que_falla(**kwargs):
        raise HttpError(_RespuestaFalsa(), b'{"error": {"message": "denied"}}')

    class _EventosFake:
        def insert(self, calendarId, body):
            class _Ejecutable:
                def execute(self_inner):
                    return _insert_que_falla()

            return _Ejecutable()

    class _ServicioFake:
        def events(self):
            return _EventosFake()

    monkeypatch.setattr("googleapiclient.discovery.build", lambda *a, **k: _ServicioFake())

    resultado = ca.crear_evento_calendario("u1", {"accion": "meditar", "cuando": "8am"})

    assert resultado["confirmado"] is False
    assert "http" not in resultado["mensaje"]


def test_completar_autorizacion_delega_en_identity_client(monkeypatch):
    llamadas = {}

    class _ClienteFake:
        def complete_resource_token_auth(self, session_uri, user_identifier):
            llamadas["session_uri"] = session_uri
            llamadas["user_id"] = user_identifier.user_id

    monkeypatch.setattr(ca, "_cliente", lambda: _ClienteFake())

    ca.completar_autorizacion("session-abc", "usuario-1")

    assert llamadas == {"session_uri": "session-abc", "user_id": "usuario-1"}
