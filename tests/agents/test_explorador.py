"""Cobertura de agents/explorador.py::_formatear_estado_ejes -- el bloque
de texto que se inyecta en el prompt para que el Explorador vea qué ejes
ya están cubiertos como un hecho explícito, en vez de tener que llevar
la cuenta él solo releyendo todo el historial (ver
tools/progreso_exploracion.py)."""

import os

os.environ.setdefault("TELOS_FICHA_BACKEND", "local")

from agents.explorador import _formatear_estado_ejes


def test_sin_ejes_previos_es():
    assert "ninguno todavía" in _formatear_estado_ejes(None, "es")
    assert "ninguno todavía" in _formatear_estado_ejes({}, "es")


def test_sin_ejes_previos_en():
    assert "none yet" in _formatear_estado_ejes(None, "en")


def test_eje_cubierto_muestra_evidencia():
    texto = _formatear_estado_ejes({"valores": "honestidad y lealtad"}, "es")
    assert "CUBIERTO" in texto
    assert "honestidad y lealtad" in texto


def test_eje_vacio_queda_pendiente():
    texto = _formatear_estado_ejes({"valores": ""}, "es")
    assert "pendiente" in texto
    assert "CUBIERTO" not in texto


def test_incluye_los_5_ejes_aunque_falten_en_el_dict():
    # Un dict parcial (solo 1 de 5 ejes) igual tiene que listar los 5 --
    # si no, el modelo no sabe que los otros 4 siguen pendientes.
    texto = _formatear_estado_ejes({"valores": "algo"}, "es")
    for etiqueta in ("valores", "flow", "recordada", "evita"):
        assert etiqueta in texto
