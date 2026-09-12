"""Cobertura de tools/ficha_local.py -- puntualmente el número de
versión y la idempotencia por turn_id agregados a raíz de la revisión de
arquitectura externa (12/09/2026, sección 7: "Reintento del mismo
turn_id -- las tools de persistencia deben ser idempotentes").
"""

import tools.ficha_local as ficha_local


def _usar_archivo_temporal(monkeypatch, tmp_path):
    ruta = tmp_path / "fichas.json"
    monkeypatch.setattr(ficha_local, "_RUTA_DATOS", str(ruta))


def test_primera_version_es_1(monkeypatch, tmp_path):
    _usar_archivo_temporal(monkeypatch, tmp_path)
    ficha_local.guardar_ficha_usuario("u1", {"a": 1}, fase=1, motivo_version="test")
    actual = ficha_local.leer_ficha_usuario("u1")["actual"]
    assert actual["version"] == 1


def test_versiones_incrementan(monkeypatch, tmp_path):
    _usar_archivo_temporal(monkeypatch, tmp_path)
    ficha_local.guardar_ficha_usuario("u1", {"a": 1}, fase=1, motivo_version="v1")
    ficha_local.guardar_ficha_usuario("u1", {"a": 2}, fase=1, motivo_version="v2")
    ficha = ficha_local.leer_ficha_usuario("u1")
    assert ficha["actual"]["version"] == 2
    assert ficha["historial"][0]["version"] == 1


def test_mismo_turn_id_no_duplica(monkeypatch, tmp_path):
    _usar_archivo_temporal(monkeypatch, tmp_path)
    ficha_local.guardar_ficha_usuario("u1", {"a": 1}, fase=1, motivo_version="v1", turn_id="turno-abc")
    # Reintento del mismo turno -- no debería agregar una versión nueva.
    ficha_local.guardar_ficha_usuario("u1", {"a": 1}, fase=1, motivo_version="v1", turn_id="turno-abc")
    ficha = ficha_local.leer_ficha_usuario("u1")
    assert ficha["actual"]["version"] == 1
    assert ficha["historial"] == []


def test_turn_id_distinto_si_guarda(monkeypatch, tmp_path):
    _usar_archivo_temporal(monkeypatch, tmp_path)
    ficha_local.guardar_ficha_usuario("u1", {"a": 1}, fase=1, motivo_version="v1", turn_id="turno-1")
    ficha_local.guardar_ficha_usuario("u1", {"a": 2}, fase=1, motivo_version="v2", turn_id="turno-2")
    ficha = ficha_local.leer_ficha_usuario("u1")
    assert ficha["actual"]["version"] == 2


def test_sin_turn_id_nunca_deduplica(monkeypatch, tmp_path):
    # None (default) es para callers fuera de un turno real (scripts,
    # tests) -- nunca debe activar la protección de idempotencia.
    _usar_archivo_temporal(monkeypatch, tmp_path)
    ficha_local.guardar_ficha_usuario("u1", {"a": 1}, fase=1, motivo_version="v1")
    ficha_local.guardar_ficha_usuario("u1", {"a": 1}, fase=1, motivo_version="v1")
    ficha = ficha_local.leer_ficha_usuario("u1")
    assert ficha["actual"]["version"] == 2
