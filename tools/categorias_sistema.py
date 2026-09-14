"""Taxonomía del selector visual de Fase 4 (Estratega de Sistemas) -- ver
C:\\Users\\Wendy\\.claude\\plans\\quirky-launching-swing.md ("Adaptación por
fase" -- Fase 4).

A diferencia de tools/categorias_ikigai.py (un grafo único con
convergencia entre dimensiones), acá son 4 árboles INDEPENDIENTES, uno
por cada pregunta fija del sistema (spec: docs/agente-proposito-de-vida-prompts.md
sección 5) -- no hay convergencia que calcular entre "acción" y
"obstáculo", cada pregunta se responde una sola vez con una elección
propia. Nodos sin `dimensiones` a propósito (ese concepto es específico
del Ikigai de Fase 1).

2 niveles por árbol (más `detalle_libre` opcional en la hoja para el
matiz final) -- alcanza para estas 4 preguntas operativas, no hace falta
la misma profundidad que la exploración de propósito de Fase 1.

Contenido y `desc` por nodo portados fielmente del prototipo real de
Claude Design de Fase 4 (13/09/2026) -- mismo criterio que
tools/categorias_ikigai.py con el prototipo de Fase 1: cuando el diseño
trae su propia versión de contenido/mecánica, se adopta tal cual en vez
de mantener la inventada antes. Dos mecánicas nuevas que trajo ese
diseño y no existían acá: (1) cada nodo (categoría Y hoja) lleva un
`desc` corto para la tarjeta, no solo un `label`; (2) la pregunta
"obstaculo" tiene un plan de contingencia con un valor por defecto por
categoría (FALLBACK_PLAN_OBSTACULO) para cuando la persona deja el campo
de texto libre vacío -- ver agents/orquestador.py::_formatear_sistema."""

PREGUNTAS_SISTEMA_IDS = ("accion", "cuando_donde", "metrica", "obstaculo")


def _nodo(id_: str, label: str, desc: str = "", hijos: list[dict] | None = None) -> dict:
    nodo: dict = {"id": id_, "label": label}
    if desc:
        nodo["desc"] = desc
    if hijos:
        nodo["hijos"] = hijos
    return nodo


CATEGORIAS_SISTEMA = {
    "es": {
        "accion": [
            _nodo(
                "movimiento_salud",
                "Movimiento o salud física",
                "El cuerpo como base de todo lo demás.",
                hijos=[
                    _nodo("ejercicio_cardio", "Ejercicio cardiovascular", "Correr, caminar fuerte, bicicleta, nadar."),
                    _nodo("fuerza_resistencia", "Fuerza o resistencia", "Entrenar con carga, progresivamente."),
                    _nodo("estiramiento_movilidad", "Estiramiento o movilidad", "Soltar el cuerpo y ganar rango."),
                    _nodo("alimentacion_consciente", "Alimentación consciente", "Decidir qué comes antes de tener hambre."),
                ],
            ),
            _nodo(
                "aprendizaje",
                "Aprendizaje",
                "Construir capacidad nueva de forma sostenida.",
                hijos=[
                    _nodo("leer_con_constancia", "Leer con constancia", "Un libro avanzando siempre."),
                    _nodo("curso_certificacion", "Un curso o certificación", "Un objetivo formal con fecha."),
                    _nodo("practicar_idioma", "Practicar un idioma", "Poco tiempo, todos los días."),
                    _nodo("oficio_tecnico", "Estudiar un oficio técnico", "Aprender haciendo, con herramientas reales."),
                ],
            ),
            _nodo(
                "trabajo_proyecto",
                "Trabajo o proyecto propio",
                "Mover lo que solo avanza si tú lo mueves.",
                hijos=[
                    _nodo("avanzar_proyecto", "Avanzar mi proyecto", "Bloques de trabajo profundo."),
                    _nodo("prospectar_clientes", "Prospectar clientes", "Conversaciones nuevas cada semana."),
                    _nodo("escribir_publicar", "Escribir o publicar", "Sacar tu criterio al mundo."),
                    _nodo("mejorar_proceso", "Mejorar un proceso", "Dejar el trabajo más fácil que ayer."),
                ],
            ),
            _nodo(
                "relaciones",
                "Relaciones",
                "La gente que quieres tener cerca en diez años.",
                hijos=[
                    _nodo("tiempo_con_familia", "Tiempo con mi familia", "Presencia sin pantallas de por medio."),
                    _nodo("reconectar_alguien", "Reconectar con alguien", "Retomar un vínculo que valoras."),
                    _nodo("conversaciones_profundas", "Conversaciones profundas", "Salir de la conversación de superficie."),
                    _nodo("cultivar_red", "Cultivar mi red", "Aportar antes de necesitar."),
                ],
            ),
            _nodo(
                "creatividad",
                "Creatividad",
                "Hacer algo que antes no existía.",
                hijos=[
                    _nodo("escribir", "Escribir", "Ordenar lo que piensas en palabras."),
                    _nodo("musica_sonido", "Música o sonido", "Practicar, componer, grabar."),
                    _nodo("imagen_video", "Imagen o video", "Foto, ilustración, edición."),
                    _nodo("construir_manos", "Construir con las manos", "Materia, objetos, prototipos."),
                ],
            ),
            _nodo(
                "bienestar_mental",
                "Bienestar mental",
                "Sostener la cabeza para sostener el resto.",
                hijos=[
                    _nodo("meditar_respirar", "Meditar o respirar", "Diez minutos de silencio deliberado."),
                    _nodo("escribir_diario", "Escribir un diario", "Descargar y entender el día."),
                    _nodo("dormir_mejor", "Dormir mejor", "Una hora de cierre siempre igual."),
                    _nodo("desconectar_pantallas", "Desconectar de pantallas", "Ventanas del día sin dispositivos."),
                ],
            ),
            _nodo(
                "finanzas",
                "Finanzas",
                "Que el dinero deje de ser una sorpresa.",
                hijos=[
                    _nodo("ahorrar_con_metodo", "Ahorrar con método", "Automático, antes de gastar."),
                    _nodo("revisar_numeros", "Revisar mis números", "Saber dónde estás, sin drama."),
                    _nodo("invertir_con_criterio", "Invertir con criterio", "Reglas propias, no impulsos."),
                    _nodo("reducir_deuda", "Reducir una deuda", "Un objetivo, un orden claro."),
                ],
            ),
            _nodo(
                "comunidad_causa",
                "Comunidad o causa",
                "Aportar donde tu presencia cambia algo.",
                hijos=[
                    _nodo("voluntariado", "Voluntariado", "Tiempo entregado con regularidad."),
                    _nodo("mentorear_alguien", "Mentorear a alguien", "Prestar tu experiencia a quien empieza."),
                    _nodo("organizar_gente", "Organizar a mi gente", "Convocar y sostener un grupo."),
                    _nodo("aportar_causa", "Aportar a una causa", "Trabajo concreto, no solo opinión."),
                ],
            ),
        ],
        "cuando_donde": [
            _nodo(
                "manana_temprano",
                "Mañana temprano",
                "Antes de que el día reclame tu atención.",
                hijos=[
                    _nodo("manana_temprano_ctx1", "Todos los días, en casa"),
                    _nodo("manana_temprano_ctx2", "Tres veces por semana, en el gimnasio"),
                    _nodo("manana_temprano_ctx3", "Días de semana, antes del trabajo"),
                ],
            ),
            _nodo(
                "media_manana",
                "Media mañana",
                "Cuando la energía está en su punto alto.",
                hijos=[
                    _nodo("media_manana_ctx1", "Días de semana, en el trabajo"),
                    _nodo("media_manana_ctx2", "Tres veces por semana, en casa"),
                    _nodo("media_manana_ctx3", "Lunes, miércoles y viernes"),
                ],
            ),
            _nodo(
                "mediodia",
                "Mediodía",
                "En el corte natural de la jornada.",
                hijos=[
                    _nodo("mediodia_ctx1", "Días de semana, en el trabajo"),
                    _nodo("mediodia_ctx2", "Todos los días, fuera de la oficina"),
                    _nodo("mediodia_ctx3", "Tres veces por semana, cerca de casa"),
                ],
            ),
            _nodo(
                "tarde",
                "Tarde",
                "Al cerrar la parte más exigente del día.",
                hijos=[
                    _nodo("tarde_ctx1", "Días de semana, en casa"),
                    _nodo("tarde_ctx2", "Tres veces por semana, en el gimnasio"),
                    _nodo("tarde_ctx3", "Fines de semana, sin horario fijo"),
                ],
            ),
            _nodo(
                "noche",
                "Noche",
                "Cuando ya no le debes tiempo a nadie más.",
                hijos=[
                    _nodo("noche_ctx1", "Todos los días, en casa"),
                    _nodo("noche_ctx2", "Días de semana, en casa"),
                    _nodo("noche_ctx3", "Tres veces por semana, en casa"),
                ],
            ),
            _nodo(
                "antes_de_dormir",
                "Antes de dormir",
                "El último bloque, siempre igual.",
                hijos=[
                    _nodo("antes_dormir_ctx1", "Todos los días, en casa"),
                    _nodo("antes_dormir_ctx2", "Días de semana, en casa"),
                    _nodo("antes_dormir_ctx3", "Fines de semana, sin apuro"),
                ],
            ),
        ],
        "metrica": [
            _nodo("cantidad_concreta", "Una cantidad concreta", "Minutos, repeticiones, páginas, llamadas."),
            _nodo("binario_si_no", "Sí o no", "Lo hice o no lo hice. Nada más."),
            _nodo("numero_que_suma", "Un número que va sumando", "Un total que crece semana a semana."),
            _nodo("sensacion_registrada", "Una sensación que registro", "Cómo quedaste después, en una línea."),
            _nodo("resultado_tangible", "Algo tangible que quedó terminado", "Una pieza, un entregable, un avance visible."),
            _nodo("revision_semanal", "Una revisión semanal", "Comparar lo hecho con lo planeado."),
        ],
        "obstaculo": [
            _nodo(
                "falta_de_tiempo",
                "Falta de tiempo",
                "El día se llena antes de llegar a esto.",
                hijos=[
                    _nodo("agenda_se_desborda", "La agenda se desborda", "Otras cosas ocupan el bloque."),
                    _nodo("imprevistos_frecuentes", "Imprevistos frecuentes", "Aparece algo urgente casi siempre."),
                ],
            ),
            _nodo(
                "cansancio_energia",
                "Cansancio o falta de energía",
                "El cuerpo o la cabeza no dan.",
                hijos=[
                    _nodo("llego_sin_energia", "Llego sin energía", "Al momento elegido ya estás vacío."),
                    _nodo("duermo_poco", "Duermo poco", "La base del día viene corta."),
                ],
            ),
            _nodo(
                "distracciones",
                "Distracciones",
                "Empiezas y algo te saca.",
                hijos=[
                    _nodo("notificaciones_pantallas", "Notificaciones y pantallas", "El teléfono gana la atención."),
                    _nodo("entorno_ruidoso", "Entorno ruidoso", "El lugar no ayuda a concentrarte."),
                ],
            ),
            _nodo(
                "presion_de_otros",
                "Presión de otros",
                "Lo tuyo cede ante lo de los demás.",
                hijos=[
                    _nodo("pedidos_ultimo_minuto", "Pedidos de último minuto", "Alguien reclama justo tu bloque."),
                    _nodo("compromisos_sociales", "Compromisos sociales", "Los planes se cruzan siempre."),
                ],
            ),
            _nodo(
                "falta_de_claridad",
                "Falta de claridad",
                "No sabes exactamente qué hacer al empezar.",
                hijos=[
                    _nodo("no_se_por_donde_empezar", "No sé por dónde empezar", "La tarea es difusa cuando llegas."),
                    _nodo("pierdo_el_criterio", "Pierdo el criterio", "Cambias de método cada vez."),
                ],
            ),
        ],
    },
    "en": {
        "accion": [
            _nodo(
                "movimiento_salud",
                "Movement or physical health",
                "Your body as the base for everything else.",
                hijos=[
                    _nodo("ejercicio_cardio", "Cardio exercise", "Running, brisk walking, cycling, swimming."),
                    _nodo("fuerza_resistencia", "Strength or endurance", "Training with load, progressively."),
                    _nodo("estiramiento_movilidad", "Stretching or mobility", "Loosening up and gaining range."),
                    _nodo("alimentacion_consciente", "Mindful eating", "Deciding what you eat before you're hungry."),
                ],
            ),
            _nodo(
                "aprendizaje",
                "Learning",
                "Building new capacity, steadily.",
                hijos=[
                    _nodo("leer_con_constancia", "Reading consistently", "One book always moving forward."),
                    _nodo("curso_certificacion", "A course or certification", "A formal goal with a date."),
                    _nodo("practicar_idioma", "Practicing a language", "A little time, every day."),
                    _nodo("oficio_tecnico", "Studying a hands-on trade", "Learning by doing, with real tools."),
                ],
            ),
            _nodo(
                "trabajo_proyecto",
                "Work or a project of my own",
                "Moving what only moves if you move it.",
                hijos=[
                    _nodo("avanzar_proyecto", "Moving my project forward", "Blocks of deep work."),
                    _nodo("prospectar_clientes", "Prospecting clients", "New conversations every week."),
                    _nodo("escribir_publicar", "Writing or publishing", "Putting your judgment out into the world."),
                    _nodo("mejorar_proceso", "Improving a process", "Leaving the work easier than yesterday."),
                ],
            ),
            _nodo(
                "relaciones",
                "Relationships",
                "The people you want close in ten years.",
                hijos=[
                    _nodo("tiempo_con_familia", "Time with my family", "Presence, with no screens in between."),
                    _nodo("reconectar_alguien", "Reconnecting with someone", "Picking back up a bond you value."),
                    _nodo("conversaciones_profundas", "Deep conversations", "Getting past the surface-level chat."),
                    _nodo("cultivar_red", "Cultivating my network", "Giving before you need to."),
                ],
            ),
            _nodo(
                "creatividad",
                "Creativity",
                "Making something that didn't exist before.",
                hijos=[
                    _nodo("escribir", "Writing", "Putting your thoughts into words."),
                    _nodo("musica_sonido", "Music or sound", "Practicing, composing, recording."),
                    _nodo("imagen_video", "Image or video", "Photo, illustration, editing."),
                    _nodo("construir_manos", "Building with your hands", "Materials, objects, prototypes."),
                ],
            ),
            _nodo(
                "bienestar_mental",
                "Mental wellbeing",
                "Holding your head steady so the rest holds too.",
                hijos=[
                    _nodo("meditar_respirar", "Meditating or breathing", "Ten minutes of deliberate silence."),
                    _nodo("escribir_diario", "Journaling", "Unloading and making sense of the day."),
                    _nodo("dormir_mejor", "Sleeping better", "One closing hour, the same every time."),
                    _nodo("desconectar_pantallas", "Unplugging from screens", "Windows of the day with no devices."),
                ],
            ),
            _nodo(
                "finanzas",
                "Finances",
                "Money stops being a surprise.",
                hijos=[
                    _nodo("ahorrar_con_metodo", "Saving with a method", "Automatic, before you spend."),
                    _nodo("revisar_numeros", "Checking my numbers", "Knowing where you stand, no drama."),
                    _nodo("invertir_con_criterio", "Investing with judgment", "Your own rules, not impulses."),
                    _nodo("reducir_deuda", "Paying down a debt", "One goal, one clear order."),
                ],
            ),
            _nodo(
                "comunidad_causa",
                "Community or a cause",
                "Showing up where your presence changes something.",
                hijos=[
                    _nodo("voluntariado", "Volunteering", "Time given on a regular basis."),
                    _nodo("mentorear_alguien", "Mentoring someone", "Lending your experience to someone starting out."),
                    _nodo("organizar_gente", "Organizing my people", "Calling together and sustaining a group."),
                    _nodo("aportar_causa", "Contributing to a cause", "Concrete work, not just opinion."),
                ],
            ),
        ],
        "cuando_donde": [
            _nodo(
                "manana_temprano",
                "Early morning",
                "Before the day claims your attention.",
                hijos=[
                    _nodo("manana_temprano_ctx1", "Every day, at home"),
                    _nodo("manana_temprano_ctx2", "Three times a week, at the gym"),
                    _nodo("manana_temprano_ctx3", "Weekdays, before work"),
                ],
            ),
            _nodo(
                "media_manana",
                "Mid-morning",
                "When your energy is at its peak.",
                hijos=[
                    _nodo("media_manana_ctx1", "Weekdays, at work"),
                    _nodo("media_manana_ctx2", "Three times a week, at home"),
                    _nodo("media_manana_ctx3", "Monday, Wednesday and Friday"),
                ],
            ),
            _nodo(
                "mediodia",
                "Midday",
                "At the day's natural break.",
                hijos=[
                    _nodo("mediodia_ctx1", "Weekdays, at work"),
                    _nodo("mediodia_ctx2", "Every day, away from the office"),
                    _nodo("mediodia_ctx3", "Three times a week, near home"),
                ],
            ),
            _nodo(
                "tarde",
                "Afternoon",
                "Closing out the day's hardest stretch.",
                hijos=[
                    _nodo("tarde_ctx1", "Weekdays, at home"),
                    _nodo("tarde_ctx2", "Three times a week, at the gym"),
                    _nodo("tarde_ctx3", "Weekends, no fixed schedule"),
                ],
            ),
            _nodo(
                "noche",
                "Evening",
                "When you no longer owe anyone else your time.",
                hijos=[
                    _nodo("noche_ctx1", "Every day, at home"),
                    _nodo("noche_ctx2", "Weekdays, at home"),
                    _nodo("noche_ctx3", "Three times a week, at home"),
                ],
            ),
            _nodo(
                "antes_de_dormir",
                "Before bed",
                "The last block, always the same.",
                hijos=[
                    _nodo("antes_dormir_ctx1", "Every day, at home"),
                    _nodo("antes_dormir_ctx2", "Weekdays, at home"),
                    _nodo("antes_dormir_ctx3", "Weekends, no rush"),
                ],
            ),
        ],
        "metrica": [
            _nodo("cantidad_concreta", "A concrete amount", "Minutes, reps, pages, calls."),
            _nodo("binario_si_no", "Yes or no", "Did it or didn't. Nothing else."),
            _nodo("numero_que_suma", "A number that adds up", "A total that grows week by week."),
            _nodo("sensacion_registrada", "A feeling I log", "How you felt afterward, in one line."),
            _nodo("resultado_tangible", "Something tangible got finished", "A piece, a deliverable, visible progress."),
            _nodo("revision_semanal", "A weekly review", "Comparing what got done against the plan."),
        ],
        "obstaculo": [
            _nodo(
                "falta_de_tiempo",
                "Not enough time",
                "The day fills up before you get to this.",
                hijos=[
                    _nodo("agenda_se_desborda", "The schedule overflows", "Other things take up the block."),
                    _nodo("imprevistos_frecuentes", "Frequent surprises", "Something urgent shows up almost every time."),
                ],
            ),
            _nodo(
                "cansancio_energia",
                "Tiredness or low energy",
                "Your body or mind just don't have it.",
                hijos=[
                    _nodo("llego_sin_energia", "I arrive with no energy", "By the chosen moment you're already empty."),
                    _nodo("duermo_poco", "I sleep too little", "The day's base comes up short."),
                ],
            ),
            _nodo(
                "distracciones",
                "Distractions",
                "You start, and something pulls you away.",
                hijos=[
                    _nodo("notificaciones_pantallas", "Notifications and screens", "The phone wins your attention."),
                    _nodo("entorno_ruidoso", "A noisy environment", "The place doesn't help you focus."),
                ],
            ),
            _nodo(
                "presion_de_otros",
                "Pressure from others",
                "Your own thing gives way to everyone else's.",
                hijos=[
                    _nodo("pedidos_ultimo_minuto", "Last-minute requests", "Someone claims your block right then."),
                    _nodo("compromisos_sociales", "Social commitments", "Plans always end up overlapping."),
                ],
            ),
            _nodo(
                "falta_de_claridad",
                "Lack of clarity",
                "You don't know exactly what to do when you start.",
                hijos=[
                    _nodo("no_se_por_donde_empezar", "I don't know where to start", "The task feels vague when you get there."),
                    _nodo("pierdo_el_criterio", "I lose my approach", "You switch methods every time."),
                ],
            ),
        ],
    },
}

# Fase 4, pregunta "obstaculo" únicamente: si la persona deja vacío el
# campo de texto libre para "¿qué harás cuando aparezca?", el código (no
# el modelo) completa un plan mínimo por defecto según la categoría de
# obstáculo elegida -- ver agents/orquestador.py::_formatear_sistema.
# Portado del prototipo de Claude Design (FALLBACK_PLAN), keyed por el id
# de la categoría de nivel 1 de "obstaculo".
FALLBACK_PLAN_OBSTACULO = {
    "es": {
        "falta_de_tiempo": "proteger el bloque en la agenda y hacer una versión corta si se pierde",
        "cansancio_energia": "hacer solo los primeros quince minutos",
        "distracciones": "dejar el teléfono fuera del alcance antes de empezar",
        "presion_de_otros": "avisar de antemano que ese bloque no está disponible",
        "falta_de_claridad": "dejar escrito la noche anterior el primer paso exacto",
    },
    "en": {
        "falta_de_tiempo": "protect the block on the calendar and do a short version if it slips",
        "cansancio_energia": "do just the first fifteen minutes",
        "distracciones": "leave the phone out of reach before starting",
        "presion_de_otros": "give notice ahead of time that block isn't available",
        "falta_de_claridad": "write down the exact first step the night before",
    },
}


def buscar_nodo_sistema_con_ruta(idioma: str, pregunta_id: str, nodo_id: str) -> tuple[dict, list[str]] | None:
    """Mismo criterio que tools/categorias_ikigai.py::buscar_hoja
    -- el backend deriva la ruta de la taxonomía, nunca confía en lo que
    mande el cliente. Busca dentro del árbol de UNA sola pregunta (no
    hay convergencia entre preguntas en Fase 4)."""
    arbol = CATEGORIAS_SISTEMA.get(idioma, CATEGORIAS_SISTEMA["es"]).get(pregunta_id, [])

    def _buscar(nodos: list[dict], ruta: list[str]) -> tuple[dict, list[str]] | None:
        for nodo in nodos:
            ruta_actual = ruta + [nodo["id"]]
            if nodo["id"] == nodo_id:
                return nodo, ruta_actual
            hijos = nodo.get("hijos")
            if hijos:
                encontrado = _buscar(hijos, ruta_actual)
                if encontrado:
                    return encontrado
        return None

    return _buscar(arbol, [])


def plan_por_defecto_obstaculo(idioma: str, categoria_id: str) -> str | None:
    """Plan mínimo por defecto para la categoría de obstáculo elegida
    -- ver FALLBACK_PLAN_OBSTACULO arriba. `None` si `categoria_id` no es
    una categoría de nivel 1 conocida (no debería pasar si vino de
    `buscar_nodo_sistema_con_ruta`, pero no se asume)."""
    return FALLBACK_PLAN_OBSTACULO.get(idioma, FALLBACK_PLAN_OBSTACULO["es"]).get(categoria_id)
