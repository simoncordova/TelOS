"""Selector de backend para el progreso de ejes del Explorador (Fase 1).

Guarda qué ejes de los 5 (valores, momentos_flow, haría_sin_pagar,
recordado_por, evita_o_drena) ya tienen sustancia real, con una frase
breve de evidencia cada uno -- computado por código (structured_output_model,
no una instrucción de "llevá la cuenta interna") después de cada turno del
Explorador, y releído al armar el prompt del turno siguiente para
inyectarlo como hecho explícito. Ver agents/explorador.py.

Bug real que motivó esto (12/09/2026): pedirle al modelo que lleve la
cuenta de ejes cubiertos "en su cabeza", releyendo el historial completo
cada turno, no era confiable -- Haiku repitió la misma pregunta (venta de
aplicaciones) con otra redacción varias veces en una conversación real,
pese a que el historial completo SÍ estaba disponible en cada invocación
(confirmado leyendo los turnos guardados). Mover el tracking a un dato
explícito, verificado y persistido por código saca esa carga de la
memoria del modelo.

No versiona (a diferencia de tools/ficha.py): es progreso transitorio de
UNA fase en curso, no un resultado a mostrar en "Tu evolución" -- cada
guardado sobrescribe el anterior. TELOS_FICHA_BACKEND mismo criterio que
el resto del proyecto.
"""

import os

if os.environ.get("TELOS_FICHA_BACKEND", "local") == "agentcore":
    from tools.progreso_exploracion_agentcore import (
        borrar_progreso_exploracion,
        guardar_progreso_exploracion,
        leer_progreso_exploracion,
    )
else:
    from tools.progreso_exploracion_local import (
        borrar_progreso_exploracion,
        guardar_progreso_exploracion,
        leer_progreso_exploracion,
    )

__all__ = ["borrar_progreso_exploracion", "guardar_progreso_exploracion", "leer_progreso_exploracion"]
