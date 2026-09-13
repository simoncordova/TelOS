"""Cobertura de tools/selecciones_estructuradas_local.py -- mismo patrón
que tests/tools/test_ficha_local.py. Reemplaza a
tests/tools/test_progreso_exploracion_local.py (Explorer v2, sacado el
13/09/2026 en favor del selector visual Ikigai)."""

import tools.selecciones_estructuradas_local as selecciones_local


def _usar_archivo_temporal(monkeypatch, tmp_path):
    ruta = tmp_path / "selecciones_estructuradas.json"
    monkeypatch.setattr(selecciones_local, "_RUTA_DATOS", str(ruta))


def test_sin_selecciones_devuelve_vacio(monkeypatch, tmp_path):
    _usar_archivo_temporal(monkeypatch, tmp_path)
    assert selecciones_local.leer_selecciones_estructuradas("u1") == {}


def test_guardar_y_leer(monkeypatch, tmp_path):
    _usar_archivo_temporal(monkeypatch, tmp_path)
    progreso = {"selecciones": [{"nodo_id": "crear_apps"}], "cobertura": {"amas": 1}}
    selecciones_local.guardar_selecciones_estructuradas("u1", progreso)
    assert selecciones_local.leer_selecciones_estructuradas("u1") == progreso


def test_guardar_sobrescribe_no_versiona(monkeypatch, tmp_path):
    _usar_archivo_temporal(monkeypatch, tmp_path)
    selecciones_local.guardar_selecciones_estructuradas("u1", {"cobertura": {"amas": 1}})
    selecciones_local.guardar_selecciones_estructuradas("u1", {"cobertura": {"amas": 2}})
    assert selecciones_local.leer_selecciones_estructuradas("u1") == {"cobertura": {"amas": 2}}


def test_borrar(monkeypatch, tmp_path):
    _usar_archivo_temporal(monkeypatch, tmp_path)
    selecciones_local.guardar_selecciones_estructuradas("u1", {"cobertura": {"amas": 1}})
    selecciones_local.borrar_selecciones_estructuradas("u1")
    assert selecciones_local.leer_selecciones_estructuradas("u1") == {}


def test_borrar_usuario_ajeno_no_afecta(monkeypatch, tmp_path):
    _usar_archivo_temporal(monkeypatch, tmp_path)
    selecciones_local.guardar_selecciones_estructuradas("u1", {"cobertura": {"amas": 1}})
    selecciones_local.borrar_selecciones_estructuradas("u2")  # nunca existió, no debe fallar
    assert selecciones_local.leer_selecciones_estructuradas("u1") == {"cobertura": {"amas": 1}}
