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
la misma profundidad que la exploración de propósito de Fase 1."""

PREGUNTAS_SISTEMA_IDS = ("accion", "cuando_donde", "metrica", "obstaculo")


def _nodo(id_: str, label: str, hijos: list[dict] | None = None) -> dict:
    nodo = {"id": id_, "label": label}
    if hijos:
        nodo["hijos"] = hijos
    return nodo


CATEGORIAS_SISTEMA = {
    "es": {
        "accion": [
            _nodo(
                "movimiento_salud",
                "Movimiento o salud física",
                hijos=[
                    _nodo("ejercicio_cardio", "Ejercicio cardiovascular"),
                    _nodo("fuerza_resistencia", "Fuerza o resistencia"),
                    _nodo("estiramiento_movilidad", "Estiramiento o movilidad"),
                    _nodo("alimentacion_consciente", "Alimentación consciente"),
                ],
            ),
            _nodo(
                "aprendizaje",
                "Aprendizaje",
                hijos=[
                    _nodo("leer", "Leer"),
                    _nodo("practicar_habilidad", "Practicar una habilidad"),
                    _nodo("estudiar_tema", "Estudiar un tema"),
                    _nodo("tomar_curso", "Avanzar un curso"),
                ],
            ),
            _nodo(
                "trabajo_proyecto",
                "Trabajo o proyecto propio",
                hijos=[
                    _nodo("avanzar_tarea", "Avanzar una tarea concreta"),
                    _nodo("planificar", "Planificar el día o la semana"),
                    _nodo("crear_contenido", "Crear contenido"),
                    _nodo("resolver_pendiente", "Resolver algo pendiente"),
                ],
            ),
            _nodo(
                "relaciones",
                "Relaciones",
                hijos=[
                    _nodo("contactar_alguien", "Contactar a alguien"),
                    _nodo("tiempo_de_calidad", "Pasar tiempo de calidad"),
                    _nodo("escuchar_activamente", "Escuchar activamente"),
                    _nodo("expresar_gratitud", "Expresar gratitud"),
                ],
            ),
            _nodo(
                "creatividad",
                "Creatividad",
                hijos=[
                    _nodo("escribir_algo", "Escribir"),
                    _nodo("dibujar_disenar", "Dibujar o diseñar"),
                    _nodo("tocar_instrumento", "Tocar un instrumento"),
                    _nodo("producir_algo_nuevo", "Producir algo nuevo"),
                ],
            ),
            _nodo(
                "bienestar_mental",
                "Bienestar mental",
                hijos=[
                    _nodo("meditar_respirar", "Meditar o respirar consciente"),
                    _nodo("escribir_diario", "Escribir un diario"),
                    _nodo("desconectar_pantallas", "Desconectar sin pantallas"),
                    _nodo("descansar_de_verdad", "Descansar de verdad"),
                ],
            ),
            _nodo(
                "finanzas",
                "Finanzas",
                hijos=[
                    _nodo("revisar_gastos", "Revisar gastos"),
                    _nodo("ahorrar_cantidad_fija", "Ahorrar una cantidad fija"),
                    _nodo("aprender_finanzas", "Aprender sobre finanzas"),
                    _nodo("planificar_objetivo", "Planificar un objetivo"),
                ],
            ),
            _nodo(
                "comunidad_causa",
                "Comunidad o causa",
                hijos=[
                    _nodo("voluntariado_accion", "Voluntariado"),
                    _nodo("ayudar_puntual", "Ayudar a alguien puntual"),
                    _nodo("participar_grupo", "Participar en un grupo"),
                    _nodo("compartir_conocimiento", "Compartir conocimiento"),
                ],
            ),
        ],
        "cuando_donde": [
            _nodo(
                "manana_temprano",
                "Mañana temprano",
                hijos=[
                    _nodo("manana_temprano_todos_dias_casa", "Todos los días, en casa"),
                    _nodo("manana_temprano_semana_gimnasio_trabajo", "Días de semana, camino al trabajo o gimnasio"),
                    _nodo("manana_temprano_finde", "Fines de semana"),
                ],
            ),
            _nodo(
                "media_manana",
                "Media mañana",
                hijos=[
                    _nodo("media_manana_todos_dias", "Todos los días"),
                    _nodo("media_manana_semana_trabajo", "Días de semana, en el trabajo"),
                    _nodo("media_manana_finde", "Fines de semana"),
                ],
            ),
            _nodo(
                "mediodia",
                "Mediodía",
                hijos=[
                    _nodo("mediodia_todos_dias", "Todos los días"),
                    _nodo("mediodia_semana", "Días de semana"),
                    _nodo("mediodia_finde", "Fines de semana"),
                ],
            ),
            _nodo(
                "tarde",
                "Tarde",
                hijos=[
                    _nodo("tarde_todos_dias_casa", "Todos los días, en casa"),
                    _nodo("tarde_semana_trabajo", "Días de semana, en el trabajo"),
                    _nodo("tarde_finde", "Fines de semana"),
                ],
            ),
            _nodo(
                "noche",
                "Noche",
                hijos=[
                    _nodo("noche_todos_dias_casa", "Todos los días, en casa"),
                    _nodo("noche_semana", "Días de semana"),
                    _nodo("noche_finde", "Fines de semana"),
                ],
            ),
            _nodo(
                "antes_de_dormir",
                "Antes de dormir",
                hijos=[
                    _nodo("antes_dormir_todos_dias", "Todos los días, en casa"),
                    _nodo("antes_dormir_semana", "Días de semana"),
                    _nodo("antes_dormir_finde", "Fines de semana"),
                ],
            ),
        ],
        "metrica": [
            _nodo("cantidad_concreta", "Una cantidad concreta (ej. minutos, repeticiones)"),
            _nodo("binario_si_no", "Sí o no -- lo hice o no lo hice"),
            _nodo("numero_que_sube", "Un número que va sumando (ej. páginas, kilómetros)"),
            _nodo("sensacion_registrada", "Una sensación que registro (ej. cómo me sentí después)"),
            _nodo("resultado_tangible", "Algo tangible que quedó terminado"),
            _nodo("revision_semanal", "Una revisión semanal contra lo planeado"),
        ],
        "obstaculo": [
            _nodo(
                "falta_de_tiempo",
                "Falta de tiempo",
                hijos=[
                    _nodo("agenda_se_llena", "La agenda se llena con otras cosas"),
                    _nodo("imprevistos", "Imprevistos que se comen el rato planeado"),
                ],
            ),
            _nodo(
                "cansancio_energia",
                "Cansancio o falta de energía",
                hijos=[
                    _nodo("cansancio_fisico", "Cansancio físico al final del día"),
                    _nodo("falta_motivacion_momento", "Se me va la motivación justo en el momento"),
                ],
            ),
            _nodo(
                "distracciones",
                "Distracciones",
                hijos=[
                    _nodo("celular_redes", "El celular o las redes sociales"),
                    _nodo("otras_tareas_urgentes", "Otras tareas que parecen más urgentes"),
                ],
            ),
            _nodo(
                "presion_de_otros",
                "Presión o compromisos de otros",
                hijos=[
                    _nodo("pedidos_de_terceros", "Pedidos de otras personas que se cruzan"),
                    _nodo("culpa_por_decir_no", "Culpa por decir que no a algo"),
                ],
            ),
            _nodo(
                "falta_de_claridad",
                "Falta de claridad sobre cómo empezar",
                hijos=[
                    _nodo("no_se_por_donde_arrancar", "No sé por dónde arrancar ese día"),
                    _nodo("perfeccionismo", "Quiero hacerlo perfecto y termino sin hacer nada"),
                ],
            ),
        ],
    },
    "en": {
        "accion": [
            _nodo(
                "movimiento_salud",
                "Movement or physical health",
                hijos=[
                    _nodo("ejercicio_cardio", "Cardio exercise"),
                    _nodo("fuerza_resistencia", "Strength or endurance"),
                    _nodo("estiramiento_movilidad", "Stretching or mobility"),
                    _nodo("alimentacion_consciente", "Mindful eating"),
                ],
            ),
            _nodo(
                "aprendizaje",
                "Learning",
                hijos=[
                    _nodo("leer", "Reading"),
                    _nodo("practicar_habilidad", "Practicing a skill"),
                    _nodo("estudiar_tema", "Studying a topic"),
                    _nodo("tomar_curso", "Working through a course"),
                ],
            ),
            _nodo(
                "trabajo_proyecto",
                "Work or a project of my own",
                hijos=[
                    _nodo("avanzar_tarea", "Moving a concrete task forward"),
                    _nodo("planificar", "Planning the day or week"),
                    _nodo("crear_contenido", "Creating content"),
                    _nodo("resolver_pendiente", "Handling something pending"),
                ],
            ),
            _nodo(
                "relaciones",
                "Relationships",
                hijos=[
                    _nodo("contactar_alguien", "Reaching out to someone"),
                    _nodo("tiempo_de_calidad", "Spending quality time"),
                    _nodo("escuchar_activamente", "Listening actively"),
                    _nodo("expresar_gratitud", "Expressing gratitude"),
                ],
            ),
            _nodo(
                "creatividad",
                "Creativity",
                hijos=[
                    _nodo("escribir_algo", "Writing"),
                    _nodo("dibujar_disenar", "Drawing or designing"),
                    _nodo("tocar_instrumento", "Playing an instrument"),
                    _nodo("producir_algo_nuevo", "Making something new"),
                ],
            ),
            _nodo(
                "bienestar_mental",
                "Mental wellbeing",
                hijos=[
                    _nodo("meditar_respirar", "Meditating or mindful breathing"),
                    _nodo("escribir_diario", "Journaling"),
                    _nodo("desconectar_pantallas", "Unplugging from screens"),
                    _nodo("descansar_de_verdad", "Actually resting"),
                ],
            ),
            _nodo(
                "finanzas",
                "Finances",
                hijos=[
                    _nodo("revisar_gastos", "Reviewing expenses"),
                    _nodo("ahorrar_cantidad_fija", "Saving a fixed amount"),
                    _nodo("aprender_finanzas", "Learning about finances"),
                    _nodo("planificar_objetivo", "Planning toward a goal"),
                ],
            ),
            _nodo(
                "comunidad_causa",
                "Community or a cause",
                hijos=[
                    _nodo("voluntariado_accion", "Volunteering"),
                    _nodo("ayudar_puntual", "Helping someone with something specific"),
                    _nodo("participar_grupo", "Participating in a group"),
                    _nodo("compartir_conocimiento", "Sharing knowledge"),
                ],
            ),
        ],
        "cuando_donde": [
            _nodo(
                "manana_temprano",
                "Early morning",
                hijos=[
                    _nodo("manana_temprano_todos_dias_casa", "Every day, at home"),
                    _nodo("manana_temprano_semana_gimnasio_trabajo", "Weekdays, on the way to work or the gym"),
                    _nodo("manana_temprano_finde", "Weekends"),
                ],
            ),
            _nodo(
                "media_manana",
                "Mid-morning",
                hijos=[
                    _nodo("media_manana_todos_dias", "Every day"),
                    _nodo("media_manana_semana_trabajo", "Weekdays, at work"),
                    _nodo("media_manana_finde", "Weekends"),
                ],
            ),
            _nodo(
                "mediodia",
                "Midday",
                hijos=[
                    _nodo("mediodia_todos_dias", "Every day"),
                    _nodo("mediodia_semana", "Weekdays"),
                    _nodo("mediodia_finde", "Weekends"),
                ],
            ),
            _nodo(
                "tarde",
                "Afternoon",
                hijos=[
                    _nodo("tarde_todos_dias_casa", "Every day, at home"),
                    _nodo("tarde_semana_trabajo", "Weekdays, at work"),
                    _nodo("tarde_finde", "Weekends"),
                ],
            ),
            _nodo(
                "noche",
                "Evening",
                hijos=[
                    _nodo("noche_todos_dias_casa", "Every day, at home"),
                    _nodo("noche_semana", "Weekdays"),
                    _nodo("noche_finde", "Weekends"),
                ],
            ),
            _nodo(
                "antes_de_dormir",
                "Before bed",
                hijos=[
                    _nodo("antes_dormir_todos_dias", "Every day, at home"),
                    _nodo("antes_dormir_semana", "Weekdays"),
                    _nodo("antes_dormir_finde", "Weekends"),
                ],
            ),
        ],
        "metrica": [
            _nodo("cantidad_concreta", "A concrete amount (e.g. minutes, reps)"),
            _nodo("binario_si_no", "Yes or no -- did it or didn't"),
            _nodo("numero_que_sube", "A number that adds up (e.g. pages, miles)"),
            _nodo("sensacion_registrada", "A feeling I log (e.g. how I felt after)"),
            _nodo("resultado_tangible", "Something tangible that got finished"),
            _nodo("revision_semanal", "A weekly check against the plan"),
        ],
        "obstaculo": [
            _nodo(
                "falta_de_tiempo",
                "Not enough time",
                hijos=[
                    _nodo("agenda_se_llena", "The schedule fills up with other things"),
                    _nodo("imprevistos", "Unplanned things eat the time I set aside"),
                ],
            ),
            _nodo(
                "cansancio_energia",
                "Tiredness or low energy",
                hijos=[
                    _nodo("cansancio_fisico", "Physical tiredness by end of day"),
                    _nodo("falta_motivacion_momento", "Motivation disappears right when it's time"),
                ],
            ),
            _nodo(
                "distracciones",
                "Distractions",
                hijos=[
                    _nodo("celular_redes", "Phone or social media"),
                    _nodo("otras_tareas_urgentes", "Other tasks that feel more urgent"),
                ],
            ),
            _nodo(
                "presion_de_otros",
                "Pressure or commitments to others",
                hijos=[
                    _nodo("pedidos_de_terceros", "Other people's requests get in the way"),
                    _nodo("culpa_por_decir_no", "Guilt over saying no to something"),
                ],
            ),
            _nodo(
                "falta_de_claridad",
                "Not being clear on how to start",
                hijos=[
                    _nodo("no_se_por_donde_arrancar", "Not knowing where to start that day"),
                    _nodo("perfeccionismo", "Wanting it perfect and ending up doing nothing"),
                ],
            ),
        ],
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
