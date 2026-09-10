"""Hook de reflexión compartido por los 5 agentes de fase. No es un
agente en sí — como agents/_modelo.py, es infraestructura común.

Usa el mecanismo nativo de Strands (AfterModelCallEvent.retry) en vez de
armar un loop de reintento a mano. Determinístico, no el modelo
juzgándose a sí mismo — mismo criterio que el guardrail de crisis
(tools/crisis.py): una verificación por regex es la que decide, no una
instrucción de "revisate a vos mismo" en el prompt.

Por ahora solo revisa voseo (tools/estilo.py) porque es el único
problema de estilo que se confirmó en producción — el mismo patrón
sirve para agregar más chequeos determinísticos más adelante si hace
falta (ej. que el ejemplo del Sintetizador cite algo real de la ficha).

Como mucho una regeneración por turno: si el reintento también falla el
chequeo, se deja pasar tal cual en vez de reintentar sin límite — un
guardrail de estilo no debería poder dejar a la persona sin respuesta.
"""

from strands.hooks import AfterModelCallEvent, BeforeInvocationEvent, HookProvider, HookRegistry

from tools.estilo import detectar_voseo


def _texto_del_mensaje(mensaje) -> str:
    if not mensaje:
        return ""
    return "".join(bloque.get("text", "") for bloque in mensaje.get("content", []))


class GuardaEstilo(HookProvider):
    """Fuerza como mucho una regeneración si la respuesta usa voseo."""

    def __init__(self) -> None:
        self._reintentado = False

    def register_hooks(self, registry: HookRegistry, **kwargs) -> None:
        registry.add_callback(BeforeInvocationEvent, self._reiniciar)
        registry.add_callback(AfterModelCallEvent, self._revisar)

    def _reiniciar(self, event: BeforeInvocationEvent) -> None:
        self._reintentado = False

    def _revisar(self, event: AfterModelCallEvent) -> None:
        if self._reintentado or event.stop_response is None:
            return

        texto = _texto_del_mensaje(event.stop_response.message)
        if detectar_voseo(texto):
            self._reintentado = True
            event.retry = True
