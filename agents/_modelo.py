"""Factory de modelo compartido por los 5 agentes de fase. No es un agente
en sí — CLAUDE.md pide un archivo por agente en /agents/, esto es
configuración común para no repetirla 5 veces.
"""

import os

from strands.models import BedrockModel

MODEL_ID = os.environ.get("TELOS_MODEL_ID", "anthropic.claude-sonnet-4-5-20250929-v1:0")
REGION = os.environ.get("TELOS_AWS_REGION", "us-east-1")


def crear_modelo() -> BedrockModel:
    return BedrockModel(model_id=MODEL_ID, region_name=REGION)
