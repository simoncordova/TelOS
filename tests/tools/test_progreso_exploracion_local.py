"""Cobertura de tools/progreso_exploracion_local.py -- el tracking de
ejes del Explorador agregado a raíz de un bug real (12/09/2026): el
modelo repetía preguntas sobre ejes ya cubiertos porque llevar la cuenta
"en su cabeza" no era confiable, incluso con el historial completo
disponible en cada turno."""

import tools.progreso_exploracion_local as progreso


def _usar_archivo_temporal(monkeypatch, tmp_path):
    ruta = tmp_path / "progreso_exploracion.json"
    monkeypatch.setattr(progreso, "_RUTA_DATOS", str(ruta))


def test_sin_progreso_devuelve_vacio(monkeypatch, tmp_path):
    _usar_archivo_temporal(monkeypatch, tmp_path)
    assert progreso.leer_progreso_exploracion("u1") == {}


def test_guarda_y_relee(monkeypatch, tmp_path):
    _usar_archivo_temporal(monkeypatch, tmp_path)
    ejes = {"valores": "honestidad y lealtad", "momentos_flow": ""}
    progreso.guardar_progreso_exploracion("u1", ejes)
    assert progreso.leer_progreso_exploracion("u1") == ejes


def test_guardado_nuevo_sobrescribe_no_versiona(monkeypatch, tmp_path):
    _usar_archivo_temporal(monkeypatch, tmp_path)
    progreso.guardar_progreso_exploracion("u1", {"valores": "algo"})
    progreso.guardar_progreso_exploracion("u1", {"valores": "algo", "momentos_flow": "otra cosa"})
    actual = progreso.leer_progreso_exploracion("u1")
    assert actual == {"valores": "algo", "momentos_flow": "otra cosa"}


def test_borrar_limpia_solo_ese_usuario(monkeypatch, tmp_path):
    _usar_archivo_temporal(monkeypatch, tmp_path)
    progreso.guardar_progreso_exploracion("u1", {"valores": "algo"})
    progreso.guardar_progreso_exploracion("u2", {"valores": "otra cosa"})
    progreso.borrar_progreso_exploracion("u1")
    assert progreso.leer_progreso_exploracion("u1") == {}
    assert progreso.leer_progreso_exploracion("u2") == {"valores": "otra cosa"}
