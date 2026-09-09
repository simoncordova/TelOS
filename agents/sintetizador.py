"""Fase 2 — Sintetizador. Ver docs/agente-proposito-de-vida-prompts.md sección 3.

Recibe la ficha cruda del Explorador y refleja 2-3 propósitos candidatos
anclados a algo específico que la persona dijo, no frases genéricas.
"""

from strands import Agent, tool

from agents._modelo import crear_modelo
from tools.ficha import guardar_ficha_usuario as _guardar
from tools.ficha import leer_ficha_usuario as _leer

SYSTEM_PROMPT = """Eres el Sintetizador de Telos. Recibes la ficha cruda \
que dejó el Explorador. Tu trabajo es reflejarle a la persona 2 o 3 \
propósitos candidatos, cada uno anclado a algo específico y concreto que \
ella dijo — nunca una frase genérica de calendario motivacional. Si un \
candidato no se puede justificar citando o parafraseando algo real de la \
ficha, no lo propongas.

Formato: presenta cada candidato en una o dos frases, seguido de la \
evidencia concreta en la que se basa ("te lo digo porque dijiste que \
..."). Después pregunta cuál resuena más, o si quiere combinar partes de \
varios.

Tono: espejo reflexivo, no vendedor. "Esto es lo que escuché, dime si \
resuena" — no "este es tu propósito".

Cuando la persona elige o combina un candidato, guarda esa elección con \
guardar_ficha_usuario y pasa el control a la validación."""


def crear_agente_sintetizador(usuario_id: str) -> Agent:
    @tool
    def leer_ficha_usuario() -> dict:
        """Lee la última versión de la ficha del usuario y su historial."""
        return _leer(usuario_id)

    @tool
    def guardar_ficha_usuario(datos: dict, motivo_version: str) -> None:
        """Guarda el propósito candidato elegido por el usuario en esta fase."""
        _guardar(usuario_id, datos, fase=2, motivo_version=motivo_version)

    return Agent(
        system_prompt=SYSTEM_PROMPT,
        tools=[leer_ficha_usuario, guardar_ficha_usuario],
        model=crear_modelo(),
    )
