"""Prueba el backend local de tools/contexto_usuario.py -- acumula
insights sin pisar los anteriores, y borrar_insights limpia del todo.
Mismo patrón que los tests locales de ficha/perfil (sin AWS)."""

import os

os.environ.setdefault("TELOS_FICHA_BACKEND", "local")

from tools.contexto_usuario import agregar_insight, borrar_insights, leer_insights


def test_agregar_y_leer_insights():
    uid = "test_contexto_usuario_1"
    borrar_insights(uid)
    assert leer_insights(uid) == []

    agregar_insight(uid, "canta en karaoke los martes")
    agregar_insight(uid, "vive en Bogotá")

    assert leer_insights(uid) == ["canta en karaoke los martes", "vive en Bogotá"]


def test_borrar_insights_limpia_todo():
    uid = "test_contexto_usuario_2"
    agregar_insight(uid, "algo")
    assert leer_insights(uid) != []

    borrar_insights(uid)
    assert leer_insights(uid) == []


def test_usuarios_distintos_no_se_mezclan():
    uid_a = "test_contexto_usuario_a"
    uid_b = "test_contexto_usuario_b"
    borrar_insights(uid_a)
    borrar_insights(uid_b)

    agregar_insight(uid_a, "insight de A")
    agregar_insight(uid_b, "insight de B")

    assert leer_insights(uid_a) == ["insight de A"]
    assert leer_insights(uid_b) == ["insight de B"]
