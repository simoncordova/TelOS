"""Fase 3 — Coach de Validación. Ver docs/agente-proposito-de-vida-prompts.md sección 4.

Pone a prueba el propósito candidato contra evidencia real (pasada y
futura) y afina la redacción hasta que la persona la sienta propia.
"""

from strands import Agent, tool

from agents._modelo import crear_modelo
from tools.ficha import guardar_ficha_usuario as _guardar
from tools.ficha import leer_ficha_usuario as _leer

SYSTEM_PROMPT = """Eres el Coach de Validación de Telos. La persona ya \
eligió un propósito candidato. Tu trabajo es ponerlo a prueba contra la \
realidad, no aplaudirlo sin más.

Pregunta por evidencia pasada: momentos concretos donde ya vivió ese \
propósito, aunque fuera en pequeño. Después pregunta por fricción futura: \
situaciones donde sería tentador abandonarlo o donde chocaría con otras \
prioridades de su vida. Usa lo que responda para afinar la redacción del \
propósito junto con la persona hasta que quede en una frase que la \
persona sienta como propia, no como eslogan.

Tono: cálido pero riguroso. Preguntas socráticas. Nunca porrismo vacío \
tipo "¡qué bonito objetivo!" sin sustancia detrás.

Cuando la persona confirma la redacción final, guárdala con \
guardar_ficha_usuario junto con la evidencia que la respalda, y pasa el \
control al diseño del sistema."""


def crear_agente_coach_validacion(usuario_id: str) -> Agent:
    @tool
    def leer_ficha_usuario() -> dict:
        """Lee la última versión de la ficha del usuario y su historial."""
        return _leer(usuario_id)

    @tool
    def guardar_ficha_usuario(datos: dict, motivo_version: str) -> None:
        """Guarda el propósito validado y su evidencia de respaldo."""
        _guardar(usuario_id, datos, fase=3, motivo_version=motivo_version)

    return Agent(
        system_prompt=SYSTEM_PROMPT,
        tools=[leer_ficha_usuario, guardar_ficha_usuario],
        model=crear_modelo(),
    )
