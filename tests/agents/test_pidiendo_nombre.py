"""Regresión de un bug real (13/09/2026): `SesionTelos._pidiendo_nombre`
volvía a activarse para cualquier persona que ya había avanzado de Fase 1
usando SOLO los selectores visuales (ArbolSelector/SistemaSelector), que
nunca pasan por `enviar_mensaje` y por lo tanto nunca capturan el nombre.

Sin este fix, cada vez que la sesión en memoria expiraba (TTL de 10 min
en api/main.py::_obtener_sesion) y se reconstruía, `abrir_conversacion`
reportaba fase=0 ("Bienvenida") sin importar la fase real -- la persona
volvía a ver el selector de Fase 1 desde cero, con su progreso real
intacto pero invisible, y cualquier intento de confirmar una selección
ahí fallaba con 400 ("confirmar_seleccion solo aplica en Fase 1") porque
el fase_actual real ya era otro. Ver agents/orquestador.py::
SesionTelos._pidiendo_nombre para el detalle completo."""

import os

os.environ.setdefault("TELOS_FICHA_BACKEND", "local")

from agents.orquestador import SesionTelos
from tools.ficha import borrar_ficha_usuario, guardar_ficha_usuario_fusionada
from tools.perfil import borrar_nombre_usuario


def _usuario_sin_nombre_con_ficha_en_fase(usuario_id: str, fase_guardada: int) -> None:
    borrar_ficha_usuario(usuario_id)
    borrar_nombre_usuario(usuario_id)
    guardar_ficha_usuario_fusionada(
        usuario_id,
        {"materia_prima": "lo que sea que haya sintetizado Fase 1"},
        fase=fase_guardada,
        motivo_version="setup de test",
    )


def test_persona_sin_nombre_recien_llegada_si_pide_nombre():
    usuario_id = "test_pidiendo_nombre_u1"
    borrar_ficha_usuario(usuario_id)
    borrar_nombre_usuario(usuario_id)
    sesion = SesionTelos(usuario_id, idioma="es")
    assert sesion.fase_actual == 1
    assert sesion._pidiendo_nombre is True


def test_persona_sin_nombre_pero_ya_en_fase_2_no_vuelve_a_pedirlo():
    usuario_id = "test_pidiendo_nombre_u2"
    _usuario_sin_nombre_con_ficha_en_fase(usuario_id, fase_guardada=1)
    sesion = SesionTelos(usuario_id, idioma="es")
    assert sesion.fase_actual == 2  # avanzó de verdad, ver _determinar_fase_inicial
    assert sesion._pidiendo_nombre is False  # y por eso ya no hay que pedirle el nombre


def test_abrir_conversacion_no_atajaria_con_fase_0(monkeypatch):
    """No se ejercita el camino real de abrir_conversacion cuando
    _pidiendo_nombre es False (invoca al modelo de la fase, requiere
    Bedrock -- fuera de alcance de este test) -- alcanza con confirmar
    que el atajo `if self._pidiendo_nombre: yield 0, ...` no se toma,
    dejando pasar la ejecución hacia _invocar_fase_directo (acá
    reemplazado por un doble sin red)."""
    usuario_id = "test_pidiendo_nombre_u3"
    _usuario_sin_nombre_con_ficha_en_fase(usuario_id, fase_guardada=1)
    sesion = SesionTelos(usuario_id, idioma="es")
    monkeypatch.setattr(sesion, "_invocar_fase_directo", lambda *a, **k: ("respuesta de prueba", False))
    monkeypatch.setattr(sesion, "_verificar_y_reforzar", lambda fase, respuesta, cerrado, total: respuesta)
    fase, texto, _opciones = next(sesion.abrir_conversacion())
    assert fase == 2  # nunca 0 -- ese era justo el bug
    assert texto == "respuesta de prueba"
