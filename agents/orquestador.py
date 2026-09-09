"""Orquestador. Ver docs/agente-proposito-de-vida-prompts.md sección 1.

No conversa directamente sobre contenido de propósito: rutea entre los
agentes de fase y aplica el guardrail de crisis en cada turno, antes que
cualquier otra cosa. Fase 1→2→3→4 es un flujo fijo (no se saltan pasos);
Fase 5 es dinámica y puede reinyectar al usuario en Fase 3 o 4.

Cada agente de fase, según el spec, guarda su ficha exactamente una vez,
al cerrar su fase (no hay saves parciales a mitad de fase) — por eso
"¿se guardó una versión nueva de la fase actual en este turno?" alcanza
como señal de "esta fase terminó, avanza a la siguiente".
"""

from strands.agent import Agent

from agents.coach_validacion import crear_agente_coach_validacion
from agents.estratega_sistemas import crear_agente_estratega_sistemas
from agents.explorador import crear_agente_explorador
from agents.seguimiento import crear_agente_seguimiento
from agents.sintetizador import crear_agente_sintetizador
from tools.crisis import detectar_señal_crisis, mensaje_crisis, registrar_evento_crisis
from tools.ficha import leer_ficha_usuario

_FABRICAS_POR_FASE = {
    1: crear_agente_explorador,
    2: crear_agente_sintetizador,
    3: crear_agente_coach_validacion,
    4: crear_agente_estratega_sistemas,
    5: crear_agente_seguimiento,
}


class SesionTelos:
    """Sesión en memoria de proceso: mantiene el agente Strands activo para
    la fase actual de un usuario. La persistencia real vive en la ficha
    (tools/ficha.py), no aquí — esta clase se puede recrear en cualquier
    momento a partir de la ficha guardada.
    """

    def __init__(self, usuario_id: str, idioma: str = "es"):
        self.usuario_id = usuario_id
        self.idioma = idioma
        self.fase_actual = self._determinar_fase_inicial()
        self._agente: Agent = _FABRICAS_POR_FASE[self.fase_actual](usuario_id, idioma)

    def _determinar_fase_inicial(self) -> int:
        ficha = leer_ficha_usuario(self.usuario_id)
        if not ficha["existe"]:
            return 1
        fase_guardada = ficha["actual"]["fase"]
        # Una ficha cerrada (fase 4 ya completa) significa que cualquier
        # sesión nueva entra directo a seguimiento, no retoma la fase 4.
        return 5 if fase_guardada >= 4 else fase_guardada

    def enviar_mensaje(self, texto: str) -> str:
        resultado_crisis = detectar_señal_crisis(texto)
        if resultado_crisis["disparado"]:
            registrar_evento_crisis(self.usuario_id, resultado_crisis["categoria"])
            return mensaje_crisis(self.idioma)

        total_versiones_antes = self._contar_versiones()
        respuesta = self._agente(texto)
        self._avanzar_fase_si_corresponde(total_versiones_antes)

        return str(respuesta)

    def _contar_versiones(self) -> int:
        ficha = leer_ficha_usuario(self.usuario_id)
        return len(ficha["historial"]) + (1 if ficha["existe"] else 0)

    def _avanzar_fase_si_corresponde(self, total_versiones_antes: int) -> None:
        ficha = leer_ficha_usuario(self.usuario_id)
        if not ficha["existe"]:
            return

        total_versiones = len(ficha["historial"]) + 1
        if total_versiones <= total_versiones_antes:
            return  # no se guardó nada nuevo en este turno, seguimos en la misma fase

        actual = ficha["actual"]
        if actual["fase"] != self.fase_actual:
            return  # la versión nueva no corresponde a la fase en curso

        if self.fase_actual in (1, 2, 3):
            self._pasar_a_fase(self.fase_actual + 1)
        elif self.fase_actual == 4:
            self._pasar_a_fase(5)
        elif self.fase_actual == 5:
            reentrada = (actual["datos"] or {}).get("reentrada")
            if reentrada == "fase3":
                self._pasar_a_fase(3)
            elif reentrada == "fase4":
                self._pasar_a_fase(4)
            # sin reentrada: se queda en Fase 5 hasta la próxima sesión

    def _pasar_a_fase(self, fase: int) -> None:
        self.fase_actual = fase
        self._agente = _FABRICAS_POR_FASE[fase](self.usuario_id, self.idioma)
