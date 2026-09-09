"""Fase 5 — Seguimiento. Ver docs/agente-proposito-de-vida-prompts.md sección 6.

Se dispara al abrir una conversación nueva cuando ya existe una ficha
completa (fase >= 4). La Vista de resumen y la rotación del tipo de
check-in se calculan en código, no se dejan a criterio del modelo — son
justamente las reglas de tono que CLAUDE.md marca como no negociables
(sin rachas, sin repetir check-in), y un prompt no las garantiza.
"""

from strands import Agent, tool

from agents._modelo import crear_modelo
from tools.ficha import guardar_ficha_usuario as _guardar
from tools.ficha import leer_ficha_usuario as _leer

TIPOS_CHECKIN = ["cumplimiento", "autopercepcion", "ajuste"]

_PREGUNTAS_POR_TIPO = {
    "cumplimiento": "¿Cómo te fue con el sistema desde la última vez?",
    "autopercepcion": "¿Este propósito todavía se siente tuyo, o algo cambió?",
    "ajuste": (
        "¿Hay algo del sistema (la acción, el cuándo/dónde, la métrica) "
        "que valga la pena cambiar?"
    ),
}

SYSTEM_PROMPT_BASE = """Eres el agente de Seguimiento de Telos. La \
persona ya tiene un propósito y un sistema definidos; tu trabajo es un \
check-in breve, no una sesión larga.

Empieza el turno mostrando EXACTAMENTE este resumen, tal cual, antes de \
cualquier otra cosa (no lo reformules, no le agregues lenguaje de racha \
ni de progreso):

---
{vista_resumen}
---

Después haz esta única pregunta de check-in (puedes ajustar la redacción \
para que fluya con la conversación, pero no cambies el tipo de pregunta \
ni hagas una segunda pregunta en el mismo turno): "{pregunta_sugerida}"

Escucha la respuesta con la misma calidez sin importar si la persona \
cumplió o no — no es un examen. Nunca menciones rachas, días \
consecutivos, ni uses lenguaje de gamificación (puntos, niveles, \
insignias).

Si la respuesta indica que el sistema no funciona (la acción no se está \
cumpliendo o pide un ajuste que va más allá de un detalle menor), o que \
el propósito ya no resuena, dilo con naturalidad y ofrece pasar a \
rediseñarlo — no insistas en mantener algo que la persona ya dijo que no \
le sirve.

Cuando termines el check-in, guarda el resultado con \
guardar_ficha_usuario. Pásale a `datos` un resumen fiel en palabras de la \
persona (sin evaluarla) y, si corresponde re-entrar a una fase anterior, \
incluye la clave "reentrada" con el valor "fase3" (el propósito ya no \
resuena) o "fase4" (el sistema necesita rediseño); si no hace falta \
re-entrar, omite esa clave o déjala en null."""


def _tipo_checkin_anterior(historial: list[dict]) -> str | None:
    for entrada in reversed(historial):
        motivo = entrada.get("motivo_version", "")
        if motivo.startswith("check-in:"):
            partes = motivo.split(":", 2)
            if len(partes) >= 2 and partes[1] in TIPOS_CHECKIN:
                return partes[1]
    return None


def elegir_tipo_checkin(historial: list[dict]) -> str:
    """Rota el tipo de check-in evitando repetir el de la sesión anterior."""
    anterior = _tipo_checkin_anterior(historial)
    candidatos = [t for t in TIPOS_CHECKIN if t != anterior]
    return candidatos[0] if candidatos else TIPOS_CHECKIN[0]


def construir_vista_resumen(ficha_actual: dict | None) -> str:
    if not ficha_actual:
        return "(sin ficha registrada todavía)"
    datos = ficha_actual.get("datos", {})
    proposito = datos.get("proposito", "(sin propósito registrado)")
    sistema = datos.get("sistema", "(sin sistema registrado)")
    fecha = ficha_actual.get("fecha", "")
    return (
        f"Tu propósito vigente: {proposito}\n"
        f"Tu sistema vigente: {sistema}\n"
        f"Última actualización: {fecha}"
    )


def crear_agente_seguimiento(usuario_id: str) -> Agent:
    ficha = _leer(usuario_id)
    tipo_checkin = elegir_tipo_checkin(ficha["historial"])
    vista_resumen = construir_vista_resumen(ficha["actual"])

    system_prompt = SYSTEM_PROMPT_BASE.format(
        vista_resumen=vista_resumen,
        pregunta_sugerida=_PREGUNTAS_POR_TIPO[tipo_checkin],
    )

    @tool
    def leer_ficha_usuario() -> dict:
        """Lee la última versión de la ficha del usuario y su historial."""
        return _leer(usuario_id)

    @tool
    def guardar_ficha_usuario(datos: dict) -> None:
        """Guarda el resultado del check-in de esta sesión."""
        motivo_version = f"check-in:{tipo_checkin}"
        _guardar(usuario_id, datos, fase=5, motivo_version=motivo_version)

    return Agent(
        system_prompt=system_prompt,
        tools=[leer_ficha_usuario, guardar_ficha_usuario],
        model=crear_modelo(),
    )
