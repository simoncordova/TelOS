"""Selector de backend para los insights de contexto de la persona --
hechos puntuales que reveló en cualquier fase, pensados para que
agents/orquestador.py los inyecte al invocar cualquier subagente y así
nadie vuelva a preguntar algo que la persona ya contó, sin importar en
qué fase lo haya dicho (diseño original en
C:\\Users\\Wendy\\.claude\\plans\\cosmic-zooming-tarjan.md, sección 4,
escrito para el orquestador agéntico que después se revirtió -- ver
docstring de agents/_modelo.py).

OJO -- estado real (14/09/2026): `agregar_insight` sí se llama (ver
SesionTelos._verificar_y_reforzar) así que los insights se escriben,
pero `leer_insights` no tiene ningún caller en agents/*.py todavía --
nada los vuelve a inyectar en el prompt de un subagente. No es código
muerto (el backend funciona y tiene tests), pero la funcionalidad que
motivó este módulo -- "no volver a preguntar algo ya contado" -- no está
completa mientras ese lado de lectura no se conecte.

Distinto de tools/ficha.py (que versiona el resultado estructurado de
cada fase) y de tools/perfil.py (un solo string, el nombre): esto es una
lista de hechos que crece con el tiempo, escrita por los subagentes vía
su tool `informar_al_orquestador` (campo `dato_nuevo`), nunca por la
persona ni por ningún agente directamente. Respeta la misma regla de
privacidad de la sección 9 del spec: paráfrasis fiel de hechos puntuales,
nunca juicios de carácter ni clasificaciones -- si un subagente manda un
`dato_nuevo` que suena a eso, es un bug del prompt de ese subagente, no
algo que este módulo deba filtrar.

Mismo TELOS_FICHA_BACKEND que el resto del proyecto -- no tiene sentido
elegir un backend distinto para esto.
"""

import os

if os.environ.get("TELOS_FICHA_BACKEND", "local") == "agentcore":
    from tools.contexto_usuario_agentcore import agregar_insight, borrar_insights, leer_insights
else:
    from tools.contexto_usuario_local import agregar_insight, borrar_insights, leer_insights

__all__ = ["agregar_insight", "borrar_insights", "leer_insights"]
