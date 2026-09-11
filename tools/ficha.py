"""Selector de backend de persistencia de la ficha del usuario.

Los agentes siempre importan `guardar_ficha_usuario` / `leer_ficha_usuario`
desde este módulo, nunca directamente desde ficha_local o ficha_agentcore
— eso es lo que permite hacer el swap de backend sin tocar agents/*.py.

TELOS_FICHA_BACKEND=local (default) usa JSON local, para desarrollo sin
AWS. TELOS_FICHA_BACKEND=agentcore usa AgentCore Memory real — ver
tools/ficha_agentcore.py.

Estas funciones se exponen sin decorador @tool a propósito: usuario_id y
fase no deben quedar a criterio del modelo (es contexto determinístico de
la sesión, no una decisión conversacional). Cada agents/*.py construye su
propio tool con @tool envolviendo estas funciones, fijando usuario_id y
fase por closure y dejando que el modelo solo decida `datos` y
`motivo_version`.
"""

import os

if os.environ.get("TELOS_FICHA_BACKEND", "local") == "agentcore":
    from tools.ficha_agentcore import borrar_ficha_usuario, guardar_ficha_usuario, leer_ficha_usuario
else:
    from tools.ficha_local import borrar_ficha_usuario, guardar_ficha_usuario, leer_ficha_usuario


def guardar_ficha_usuario_fusionada(usuario_id: str, datos: dict, fase: int, motivo_version: str) -> None:
    """Envoltorio de `guardar_ficha_usuario` que fusiona `datos` sobre la
    última versión guardada (las claves nuevas ganan si hay conflicto) en
    vez de reemplazarla entera. Usado por los 5 `agents/*.py` en vez de
    la función base -- ver docs/agente-proposito-de-vida-prompts.md
    sección 0.7 y la fila de `guardar_ficha_usuario` en la sección 7.

    El spec le pide a cada fase >= 2 que re-incluya "proposito" (y desde
    Fase 4, "sistema") en `datos` aunque no los haya cambiado, para que
    la versión más reciente de la ficha siempre tenga lo necesario --
    confiar en que el modelo se acuerde de hacerlo cada vez resultó NO
    ser confiable (bug real: el propósito ya guardado en una fase
    desaparecía del panel de la interfaz y de la Vista de resumen de
    Fase 5 apenas una fase posterior guardaba sin re-incluirlo). Esta
    fusión lo garantiza por código: si el modelo omite una clave que ya
    tenía valor, el valor anterior sobrevive; si la incluye (por ejemplo,
    al redefinir el sistema en una re-entrada desde Fase 5), la nueva
    gana, como corresponde."""
    ficha = leer_ficha_usuario(usuario_id)
    datos_previos = (ficha["actual"] or {}).get("datos", {}) if ficha["existe"] else {}
    fusionado = {**(datos_previos or {}), **datos}
    guardar_ficha_usuario(usuario_id, fusionado, fase, motivo_version)


__all__ = ["borrar_ficha_usuario", "guardar_ficha_usuario", "guardar_ficha_usuario_fusionada", "leer_ficha_usuario"]
