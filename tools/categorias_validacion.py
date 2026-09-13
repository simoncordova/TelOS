"""Taxonomía del selector visual de Fase 3 (Coach de Validación) -- ver
el plan "quirky-launching-swing" (directorio de planes de Claude Code),
sección "Adaptación por fase" -- Fase 3.

Diseño híbrido, distinto de Fase 1/4: acá NO hay un árbol de categorías
profundo posible, porque lo que se busca (un momento concreto que la
persona ya vivió, una situación futura de fricción) es evidencia
personal y vivida -- enumerarla de antemano en un árbol de 3 niveles
sonaría falso, sería mentirle a la persona que su situación específica
"ya estaba prevista". Lo que SÍ se puede fijar por código es el ORDEN
(evidencia pasada antes que fricción futura -- ver
agents/orquestador.py::SesionTelos.confirmar_seleccion_validacion) y un
punto de partida: un selector corto de "¿en qué área de tu vida?" (un
solo nivel, sin hijos), seguido de un campo de texto libre y opcional
donde la persona cuenta el detalle real. Reutilizado para las dos etapas
(evidencia pasada y fricción futura) -- las mismas áreas de vida sirven
para las dos preguntas, ver `ETIQUETA_ETAPA` en agents/orquestador.py
para cómo se le da un enunciado distinto a cada una."""

AREAS_VIDA = {
    "es": [
        {"id": "trabajo_carrera", "label": "Trabajo o carrera"},
        {"id": "relaciones_cercanas", "label": "Relaciones cercanas (familia, pareja, amigos)"},
        {"id": "hobby_proyecto_personal", "label": "Un hobby o proyecto personal"},
        {"id": "comunidad_grupo", "label": "Comunidad o un grupo al que pertenezco"},
        {"id": "momento_dificil", "label": "Un momento difícil que atravesé"},
        {"id": "decision_que_tome", "label": "Una decisión que tomé"},
        {"id": "tiempo_libre", "label": "Cómo uso mi tiempo libre"},
        {"id": "algo_sin_que_pidieran", "label": "Algo que hice sin que nadie me lo pidiera"},
    ],
    "en": [
        {"id": "trabajo_carrera", "label": "Work or career"},
        {"id": "relaciones_cercanas", "label": "Close relationships (family, partner, friends)"},
        {"id": "hobby_proyecto_personal", "label": "A hobby or personal project"},
        {"id": "comunidad_grupo", "label": "A community or group I belong to"},
        {"id": "momento_dificil", "label": "A hard time I went through"},
        {"id": "decision_que_tome", "label": "A decision I made"},
        {"id": "tiempo_libre", "label": "How I spend my free time"},
        {"id": "algo_sin_que_pidieran", "label": "Something I did without anyone asking me to"},
    ],
}


def buscar_area_vida(idioma: str, area_id: str) -> dict | None:
    """Mismo criterio que tools/categorias_ikigai.py::buscar_hoja
    -- el backend valida contra la taxonomía, nunca confía en lo que
    mande el cliente. Sin `ruta` (un solo nivel, no hace falta)."""
    for area in AREAS_VIDA.get(idioma, AREAS_VIDA["es"]):
        if area["id"] == area_id:
            return area
    return None
