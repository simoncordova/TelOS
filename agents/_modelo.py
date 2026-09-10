"""Factory de modelo compartido por los 5 agentes de fase. No es un agente
en sí — es configuración común a los 5, para no repetirla en cada
archivo de agents/.

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


# Compartida por los 5 prompts en español (antes estaba copiada casi
# textual en cada uno, un archivo por fix cuando se detectó el bug de
# voseo). Un solo lugar para editarla si hace falta ajustarla de nuevo.
# El chequeo real (que efectivamente se cumpla) es agents/_calidad.py —
# esto es la instrucción, no la garantía.
REGLA_CONJUGACION_ES = (
    'IMPORTANTE sobre la conjugación: usa siempre las formas de "tú" '
    '(tienes, quieres, eres, puedes, sientes) — nunca las de "vos" '
    '(tenés, querés, sos, podés, sentís). El voseo se nota en cómo se '
    'conjuga el verbo, no solo en si aparece la palabra "vos" escrita, '
    'así que evita esas conjugaciones aunque nunca escribas el pronombre.'
)
