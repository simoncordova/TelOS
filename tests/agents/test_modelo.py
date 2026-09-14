"""Prueba que agents/_modelo.py arme el BedrockModel del orquestador y el
de los subagentes con o sin guardrail según GUARDRAIL_ID -- sin llamar a
Bedrock de verdad (construir un BedrockModel no hace ninguna llamada de
red, solo arma la config). Monkeypatchea los atributos del módulo, no la
variable de entorno directamente: GUARDRAIL_ID/GUARDRAIL_VERSION se leen
una sola vez al importar el módulo, igual que MODEL_ID_ORQUESTADOR/
MODEL_ID_SUBAGENTE/REGION."""

from agents import _modelo


def test_crear_modelo_orquestador_sin_guardrail(monkeypatch):
    monkeypatch.setattr(_modelo, "GUARDRAIL_ID", "")
    modelo = _modelo.crear_modelo_orquestador()
    assert modelo.config["model_id"] == _modelo.MODEL_ID_ORQUESTADOR
    assert "guardrail_id" not in modelo.config


def test_crear_modelo_subagente_sin_guardrail(monkeypatch):
    monkeypatch.setattr(_modelo, "GUARDRAIL_ID", "")
    modelo = _modelo.crear_modelo_subagente()
    assert modelo.config["model_id"] == _modelo.MODEL_ID_SUBAGENTE
    assert "guardrail_id" not in modelo.config


def test_crear_modelo_orquestador_con_guardrail(monkeypatch):
    monkeypatch.setattr(_modelo, "GUARDRAIL_ID", "gr-abc123")
    monkeypatch.setattr(_modelo, "GUARDRAIL_VERSION", "1")
    modelo = _modelo.crear_modelo_orquestador()
    assert modelo.config["model_id"] == _modelo.MODEL_ID_ORQUESTADOR
    assert modelo.config["guardrail_id"] == "gr-abc123"
    assert modelo.config["guardrail_version"] == "1"
    assert modelo.config["guardrail_trace"] == "enabled"


def test_crear_modelo_subagente_con_guardrail(monkeypatch):
    monkeypatch.setattr(_modelo, "GUARDRAIL_ID", "gr-abc123")
    monkeypatch.setattr(_modelo, "GUARDRAIL_VERSION", "1")
    modelo = _modelo.crear_modelo_subagente()
    assert modelo.config["model_id"] == _modelo.MODEL_ID_SUBAGENTE
    assert modelo.config["guardrail_id"] == "gr-abc123"
    assert modelo.config["guardrail_version"] == "1"
    assert modelo.config["guardrail_trace"] == "enabled"


def test_presentar_candidatos_proposito_llena_el_contenedor():
    """Cobertura directa de la tool (sin Bedrock, sin Agent real) --
    mismo criterio que el resto del proyecto para no depender de AWS.
    Invocación directa siempre por kwargs, nunca posicional (ver
    docs/lineamientos-desarrollo.md)."""
    contenedor: list = []
    tool_fn = _modelo.crear_tool_presentar_candidatos_proposito(contenedor)
    candidatos = [
        _modelo.CandidatoProposito(frase="Enseñar con el ejemplo", explicacion="...", ejemplo="..."),
        _modelo.CandidatoProposito(frase="Construir puentes", explicacion="...", ejemplo="..."),
    ]
    tool_fn(candidatos=candidatos)
    assert contenedor == [
        {"frase": "Enseñar con el ejemplo", "explicacion": "...", "ejemplo": "..."},
        {"frase": "Construir puentes", "explicacion": "...", "ejemplo": "..."},
    ]


def test_presentar_candidatos_proposito_reemplaza_no_acumula():
    """Una segunda llamada (ej. el modelo reconsiderando en el mismo
    turno) reemplaza los candidatos anteriores en vez de sumarse --
    mismo criterio que crear_tool_presentar_opciones."""
    contenedor: list = ["lo que hubiera antes"]
    tool_fn = _modelo.crear_tool_presentar_candidatos_proposito(contenedor)
    tool_fn(candidatos=[_modelo.CandidatoProposito(frase="Único candidato", explicacion="e", ejemplo="j")])
    assert contenedor == [{"frase": "Único candidato", "explicacion": "e", "ejemplo": "j"}]
