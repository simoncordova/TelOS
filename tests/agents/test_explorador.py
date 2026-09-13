"""Cobertura de agents/explorador.py::_formatear_ejes_cubiertos --
Explorer v2 (revisión de arquitectura externa, 12/09/2026): el
Explorador ya no decide qué preguntar ni si un eje está cubierto, solo
conversa con lo que el código ya decidió. Esto testea el bloque de
evidencia que se le inyecta en el prompt."""

import os

os.environ.setdefault("TELOS_FICHA_BACKEND", "local")

from agents.explorador import _formatear_ejes_cubiertos


def test_sin_evidencia_es():
    assert "ninguno todavía" in _formatear_ejes_cubiertos({}, "es")


def test_sin_evidencia_en():
    assert "none yet" in _formatear_ejes_cubiertos({}, "en")


def test_incluye_la_evidencia_real():
    texto = _formatear_ejes_cubiertos({"valores": "honestidad y lealtad"}, "es")
    assert "valores" in texto
    assert "honestidad y lealtad" in texto


def test_solo_lista_ejes_con_evidencia():
    # A diferencia del diseño anterior, acá no hace falta listar los 5 --
    # el código ya sabe cuáles están pendientes por el progreso guardado.
    texto = _formatear_ejes_cubiertos({"valores": "algo"}, "es")
    assert "momentos_flow" not in texto
