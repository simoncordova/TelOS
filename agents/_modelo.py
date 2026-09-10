"""Factory de modelo compartido por los 5 agentes de fase. No es un agente
en sí — CLAUDE.md pide un archivo por agente en /agents/, esto es
configuración común para no repetirla 5 veces.

Usa el ID de "global cross-region inference" (prefijo `global.`), no el
ID pelado del modelo: Claude Sonnet 4.5 no admite invocación on-demand
"In-Region" en la mayoría de las regiones (confirmado con un
ValidationException real en us-east-1: "Invocation of model ID ... with
on-demand throughput isn't supported"). El ID `global.` funciona desde
cualquier región del mundo (a diferencia de los `us.`/`eu.`/`au.`/`jp.`
que solo enrutan dentro de esa geografía) y además sale ~10% más barato
según la documentación de Bedrock.
"""

import os

from strands.models import BedrockModel

MODEL_ID = os.environ.get("TELOS_MODEL_ID", "global.anthropic.claude-sonnet-4-5-20250929-v1:0")
REGION = os.environ.get("TELOS_AWS_REGION", "us-east-1")


def crear_modelo() -> BedrockModel:
    return BedrockModel(model_id=MODEL_ID, region_name=REGION)
