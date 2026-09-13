"""Biblioteca de preguntas del Explorador (Fase 1) -- Explorer v2, ver
revisión de arquitectura externa (12/09/2026, "no implementar
generate_question(), implementar select_next_question()").

Reemplaza la generación libre de preguntas del modelo: el código elige
cuál preguntar de acá, nunca el LLM. Cada eje tiene una pregunta
principal y una de profundización (para el caso "partial" -- ver
agents/orquestador.py::_seleccionar_siguiente_pregunta), preescritas y
revisables como producto, independientes del comportamiento del LLM.

Puramente datos -- sin I/O, sin lógica de selección (eso vive en
agents/orquestador.py, que sí conoce el progreso de la persona).
"""

PREGUNTAS_EXPLORACION = {
    "es": {
        "valores": [
            {"id": "valores_01", "text": "¿Qué cosas son realmente importantes para ti, de esas que no negociarías aunque fuera más fácil hacerlo?"},
            {"id": "valores_02", "text": "Pensando en la gente con la que más te identificás, ¿qué tienen en común que vos también valorás?"},
        ],
        "momentos_flow": [
            {"id": "flow_01", "text": "¿Hay algo que hayas hecho donde perdiste completamente la noción del tiempo, donde todo simplemente fluyó?"},
            {"id": "flow_02", "text": "De ese momento, ¿qué fue específicamente lo que te enganchó -- el desafío en sí, ver que funcionaba, algo más?"},
        ],
        "haria_sin_pagar": [
            {"id": "gratis_01", "text": "¿Hay algo que harías incluso si nadie te pagara por hacerlo? Algo que harías de todas formas."},
            {"id": "gratis_02", "text": "¿Qué es lo que te haría volver a esa actividad una y otra vez, sin que nadie te lo pida?"},
        ],
        "recordado_por": [
            {"id": "recordado_01", "text": "¿Con qué te gustaría ser recordado? Si alguien hablara de vos años adelante, ¿qué esperás que diga?"},
            {"id": "recordado_02", "text": "De lo que acabás de decir, ¿qué es específicamente lo que te gustaría que la gente sintiera o pudiera hacer gracias a eso?"},
        ],
        "evita_o_drena": [
            {"id": "evita_01", "text": "¿Hay algo que evitás hacer aunque sientas que \"deberías\"? ¿Qué tipo de cosas preferís no enfrentar?"},
            {"id": "evita_02", "text": "¿Qué es lo que específicamente te agota o te frena de eso que evitás?"},
        ],
    },
    "en": {
        "valores": [
            {"id": "valores_01", "text": "What things really matter to you -- the ones you wouldn't compromise on even if it'd be easier to?"},
            {"id": "valores_02", "text": "Thinking about the people you admire most, what do they have in common that you value too?"},
        ],
        "momentos_flow": [
            {"id": "flow_01", "text": "Is there something you've done where you completely lost track of time, where it just flowed?"},
            {"id": "flow_02", "text": "From that moment, what specifically hooked you -- the challenge itself, seeing it work, something else?"},
        ],
        "haria_sin_pagar": [
            {"id": "gratis_01", "text": "Is there something you'd do even if nobody paid you for it? Something you'd do anyway."},
            {"id": "gratis_02", "text": "What would make you keep coming back to that activity, without anyone asking you to?"},
        ],
        "recordado_por": [
            {"id": "recordado_01", "text": "How would you like to be remembered? If someone talked about you years from now, what would you want them to say?"},
            {"id": "recordado_02", "text": "From what you just said, what specifically would you want people to feel or be able to do because of that?"},
        ],
        "evita_o_drena": [
            {"id": "evita_01", "text": "Is there something you avoid doing even though you feel you \"should\"? What kind of things do you prefer not to face?"},
            {"id": "evita_02", "text": "What specifically drains you or holds you back about the thing you avoid?"},
        ],
    },
}

EJES = ("valores", "momentos_flow", "haria_sin_pagar", "recordado_por", "evita_o_drena")
