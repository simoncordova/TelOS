"""Prueba que agents/_modelo.py::crear_modelo arme el BedrockModel con o
sin guardrail según GUARDRAIL_ID -- sin llamar a Bedrock de verdad
(construir un BedrockModel no hace ninguna llamada de red, solo arma la
config). Monkeypatchea los atributos del módulo, no la variable de
entorno directamente: GUARDRAIL_ID/GUARDRAIL_VERSION se leen una sola
vez al importar el módulo, igual que MODEL_ID/REGION."""

from agents import _modelo


def test_crear_modelo_sin_guardrail(monkeypatch):
    monkeypatch.setattr(_modelo, "GUARDRAIL_ID", "")
    modelo = _modelo.crear_modelo()
    assert "guardrail_id" not in modelo.config


def test_crear_modelo_con_guardrail(monkeypatch):
    monkeypatch.setattr(_modelo, "GUARDRAIL_ID", "gr-abc123")
    monkeypatch.setattr(_modelo, "GUARDRAIL_VERSION", "1")
    modelo = _modelo.crear_modelo()
    assert modelo.config["guardrail_id"] == "gr-abc123"
    assert modelo.config["guardrail_version"] == "1"
    assert modelo.config["guardrail_trace"] == "enabled"
