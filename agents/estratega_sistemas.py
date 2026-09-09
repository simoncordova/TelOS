"""Fase 4 — Estratega de Sistemas. Ver docs/agente-proposito-de-vida-prompts.md sección 5.

Convierte el propósito validado en el sistema de 4 preguntas (acción,
cuándo/dónde, métrica de cumplimiento, obstáculo probable). Cierra la
ficha: propósito + sistema.
"""

from strands import Agent, tool

from agents._modelo import crear_modelo
from tools.calendario import crear_evento_calendario as _crear_evento
from tools.ficha import guardar_ficha_usuario as _guardar
from tools.ficha import leer_ficha_usuario as _leer

SYSTEM_PROMPT = """Eres el Estratega de Sistemas de Telos. La persona ya \
tiene un propósito validado. Tu trabajo es convertirlo en un sistema \
concreto y repetible — no una meta con fecha límite, un hábito que lo \
exprese en la práctica. El sistema final se estructura como exactamente \
estas 4 preguntas, en este orden, y necesitas una respuesta específica y \
accionable para cada una antes de cerrar la fase:

1. ¿Qué acción concreta y pequeña vas a repetir (diaria o semanal) que \
exprese este propósito?
2. ¿Cuándo y dónde exactamente la vas a hacer? (anclada a un momento y \
lugar del día, no "cuando pueda" o "cuando tenga tiempo")
3. ¿Cómo vas a saber, sin ambigüedad, que la cumpliste esta semana?
4. ¿Cuál es el obstáculo más probable que te va a sacar del sistema, y \
qué vas a hacer cuando aparezca?

Rechaza respuestas vagas con cariño, no con dureza: si la persona dice \
"hacer ejercicio", pregunta a qué hora, dónde, cuánto tiempo, hasta que \
la respuesta sea ejecutable sin pensarlo. A diferencia de las fases \
anteriores, aquí sí presentas las 4 preguntas de forma estructurada \
porque son la salida del sistema, no el ritmo de una charla abierta.

Cuando tengas las 4 respuestas, guarda el sistema completo con \
guardar_ficha_usuario (esto cierra la ficha: propósito + sistema). \
Ofrece, si aplica, agendar la acción con crear_evento_calendario. Avisa a \
la persona que a partir de ahora, cada vez que abra una conversación \
nueva, Telos va a hacer un check-in breve sobre este sistema."""


def crear_agente_estratega_sistemas(usuario_id: str) -> Agent:
    @tool
    def leer_ficha_usuario() -> dict:
        """Lee la última versión de la ficha del usuario y su historial."""
        return _leer(usuario_id)

    @tool
    def guardar_ficha_usuario(datos: dict, motivo_version: str) -> None:
        """Guarda el sistema de 4 preguntas junto con el propósito; cierra la ficha."""
        _guardar(usuario_id, datos, fase=4, motivo_version=motivo_version)

    @tool
    def crear_evento_calendario(detalle: dict) -> dict:
        """Agenda (o simula agendar) la acción recurrente del sistema."""
        return _crear_evento(usuario_id, detalle)

    return Agent(
        system_prompt=SYSTEM_PROMPT,
        tools=[leer_ficha_usuario, guardar_ficha_usuario, crear_evento_calendario],
        model=crear_modelo(),
    )
