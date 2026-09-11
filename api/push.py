"""Envío de Web Push real (Fase 3/4 del plan de migración, rama
gamificacion) -- capa delgada sobre pywebpush, sin lógica de negocio acá
más que construir el texto del recordatorio (determinístico, en código,
nunca generado por el modelo: mismo criterio que el resto del proyecto
para todo lo que tiene que respetar una regla de tono exacta -- ver
agents/seguimiento.py y sección 8 de
docs/agente-proposito-de-vida-prompts.md, "sin rachas-shaming, sin
repetir check-ins").

Formato de claves: ver scripts/generar_claves_vapid.py.
"""

import json
import os

from pywebpush import WebPushException, webpush

_VAPID_PUBLIC_KEY = os.environ.get("VAPID_PUBLIC_KEY", "")
_VAPID_PRIVATE_KEY = os.environ.get("VAPID_PRIVATE_KEY", "")
_VAPID_SUBJECT = os.environ.get("VAPID_SUBJECT", "mailto:telos@example.com")

_TEXTO_RECORDATORIO = {
    "es": {"titulo": "Telos", "cuerpo": "Un momento para tu sistema, cuando puedas 🌱"},
    "en": {"titulo": "Telos", "cuerpo": "A moment for your system, whenever you're ready 🌱"},
}

_TEXTO_PRUEBA = {
    "es": {"titulo": "Telos", "cuerpo": "Notificación de prueba -- si ves esto, el push real funciona 🎉"},
    "en": {"titulo": "Telos", "cuerpo": "Test notification -- if you see this, real push works 🎉"},
}


def configurado() -> bool:
    return bool(_VAPID_PRIVATE_KEY and _VAPID_SUBJECT)


def clave_publica() -> str:
    return _VAPID_PUBLIC_KEY


def construir_recordatorio(idioma: str) -> dict:
    """Texto fijo, no generado por el modelo -- una notificación push no
    pasa por ningún agente ni guardrail, así que el tono tiene que estar
    garantizado por código, igual que la Vista de resumen de Fase 5
    (agents/seguimiento.py::construir_vista_resumen). Sin mención de
    racha ni de "hace X días que no volvés" a propósito -- el spec
    prohíbe el tono de hábito-shaming en el Agente 5, y un push es
    exactamente ese mismo canal, solo que fuera de la app."""
    return _TEXTO_RECORDATORIO.get(idioma, _TEXTO_RECORDATORIO["es"])


def construir_prueba(idioma: str) -> dict:
    return _TEXTO_PRUEBA.get(idioma, _TEXTO_PRUEBA["es"])


class SuscripcionInvalida(Exception):
    """La suscripción ya no es válida del lado del navegador/proveedor
    (desinstalada, permiso revocado, endpoint vencido) -- quien llama
    debe borrarla (tools/push_suscripcion.py) en vez de reintentar."""


def enviar_push(suscripcion: dict, mensaje: dict) -> None:
    """Manda una notificación real. Lanza SuscripcionInvalida si el
    proveedor de push contesta que el endpoint ya no sirve (404/410 --
    códigos estándar del protocolo Web Push para "esta suscripción
    murió"), o WebPushException para cualquier otro fallo (red, VAPID
    mal configurado, etc.) que sí vale la pena loguear como error real
    en vez de silenciar."""
    try:
        webpush(
            subscription_info=suscripcion,
            data=json.dumps(mensaje, ensure_ascii=False),
            vapid_private_key=_VAPID_PRIVATE_KEY,
            vapid_claims={"sub": _VAPID_SUBJECT},
        )
    except WebPushException as e:
        codigo = getattr(e.response, "status_code", None)
        if codigo in (404, 410):
            raise SuscripcionInvalida(str(e)) from e
        raise
