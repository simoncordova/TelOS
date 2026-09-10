"""Orquestador. Ver docs/agente-proposito-de-vida-prompts.md sección 1.

No conversa directamente sobre contenido de propósito: rutea entre los
agentes de fase y aplica el guardrail de crisis en cada turno, antes que
cualquier otra cosa. Fase 1→2→3→4 es un flujo fijo (no se saltan pasos);
Fase 5 es dinámica y puede reinyectar al usuario en Fase 3 o 4.

Cada agente de fase, según el spec, guarda su ficha exactamente una vez,
al cerrar su fase (no hay saves parciales a mitad de fase) — por eso
"¿se guardó una versión nueva de la fase actual en este turno?" alcanza
como señal de "esta fase terminó, avanza a la siguiente".

Cuando la fase cambia a 2, 3 o 4 (flujo fijo o re-entrada desde Fase 5),
el agente nuevo se invoca en el mismo turno con un mensaje de arranque
neutro — si no, la persona se queda mirando un chat "colgado" después
del cierre de una fase, sin señal de que tiene que escribir algo para
que continúe. La única excepción es al llegar a Fase 5: ese cierre es
el fin natural de la sesión (el spec dice que Fase 5 se dispara "al
abrir una conversación nueva", no en el mismo turno que cierra Fase 4).

`enviar_mensaje` es un generador, no devuelve un string: cuando hay
cascada, entrega el mensaje de la fase que cierra y el de la fase
siguiente por separado, apenas cada uno está listo, en vez de esperar a
tener los dos para mostrar todo junto de una — con el Sintetizador
generando más contenido ahora (propósito + explicación + ejemplo por
candidato), esperar a los dos combinados se sentía como que la app se
había colgado. Quien llama (`ui/app.py`, `scripts/chat_terminal.py`)
itera y muestra cada parte a medida que llega.
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

# Mensaje interno para arrancar al agente nuevo tras un cambio de fase en
# el mismo turno. Nunca se muestra a la persona (no se agrega al
# historial visible, solo dispara la respuesta del agente siguiente).
_KICKOFF = {
    "es": "Continuemos.",
    "en": "Let's continue.",
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

    def abrir_conversacion(self):
        """Generador: el agente de la fase actual habla primero, sin
        esperar texto de la persona -- se llama una sola vez, al abrir
        la sesión (nueva o retomada). Sin esto, el sistema siempre se
        queda esperando a que la persona adivine qué escribir primero,
        incluso en Fase 5, que según el spec tiene que mostrar la Vista
        de resumen apenas se abre la conversación, no después.

        No revisa el guardrail de crisis (no hay texto de la persona
        que revisar) ni avanza de fase (abrir no cierra nada)."""
        yield self.fase_actual, str(self._agente(_KICKOFF[self.idioma]))

    def _determinar_fase_inicial(self) -> int:
        ficha = leer_ficha_usuario(self.usuario_id)
        if not ficha["existe"]:
            return 1
        fase_guardada = ficha["actual"]["fase"]
        # Una ficha cerrada (fase 4 ya completa) significa que cualquier
        # sesión nueva entra directo a seguimiento, no retoma la fase 4.
        return 5 if fase_guardada >= 4 else fase_guardada

    def enviar_mensaje(self, texto: str):
        """Generador: entrega (fase, texto) por cada mensaje, en el orden
        en que se van generando -- no un solo string con todo junto."""
        resultado_crisis = detectar_señal_crisis(texto)
        if resultado_crisis["disparado"]:
            registrar_evento_crisis(self.usuario_id, resultado_crisis["categoria"])
            yield self.fase_actual, mensaje_crisis(self.idioma)
            return

        fase_antes = self.fase_actual
        total_versiones_antes = self._contar_versiones()
        respuesta = str(self._agente(texto))
        yield fase_antes, respuesta

        self._avanzar_fase_si_corresponde(total_versiones_antes)

        # La fase cambió en este mismo turno: si el destino no es Fase 5
        # (que espera a una conversación nueva, no continúa en caliente),
        # arrancamos al agente siguiente ya mismo para no dejar a la
        # persona esperando sin saber que le toca escribir algo. Se
        # entrega como un mensaje aparte, no concatenado al anterior --
        # así quien llama puede mostrar el primero apenas está listo, sin
        # esperar a que este segundo termine de generarse.
        if self.fase_actual != fase_antes and self.fase_actual != 5:
            continuacion = str(self._agente(_KICKOFF[self.idioma]))
            yield self.fase_actual, continuacion

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
