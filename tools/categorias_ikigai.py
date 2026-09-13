"""Taxonomía del selector visual Ikigai (Fase 1) -- ver
C:\\Users\\Wendy\\.claude\\plans\\quirky-launching-swing.md ("Formato de la
taxonomía -- Fase 1: UN grafo/árbol, no 4-5 árboles paralelos").

Reemplaza la generación libre de preguntas del Explorador conversacional
(Explorer v2, sacado el 13/09/2026): en vez de que un modelo pregunte y
otro evalúe si la respuesta "ya alcanza", la persona elige de este árbol
-- la elección ES el dato, válida por construcción, sin nada que un LLM
tenga que juzgar.

UN solo árbol de categorías de interés/actividad, no un árbol por
dimensión: una misma categoría puede aportar a varias dimensiones del
Ikigai a la vez (`dimensiones`), que es literalmente el punto del
framework (la zona de superposición de los círculos). Etiquetas
booleanas por dimensión, no pesos numéricos -- más fácil de autorar de
forma consistente a mano sobre muchos nodos, y sigue capturando la
convergencia con precisión: un nodo etiquetado en 3-4 dimensiones a la
vez ES un punto de intersección real.

3 niveles (amplio → intermedio → específico/hoja). Los nodos de
organización (niveles 1-2, en general) no etiquetan dimensión propia --
`dimensiones: []` -- son solo agrupadores; las hojas son las que
etiquetan con precisión.

Contenido: semilla inicial (32 hojas, ES/EN), pensada para dar cobertura
real a las 5 dimensiones y validar el mecanismo -- no es exhaustiva
("miles de combinaciones" es una autoría de contenido considerable
aparte, ver el plan). Puramente datos -- sin I/O, sin lógica de
navegación ni de convergencia (eso vive en agents/orquestador.py, que sí
conoce el progreso de la persona)."""

DIMENSIONES_IKIGAI = ("amas", "sos_bueno", "mundo_necesita", "pueden_pagar", "valores")


def _nodo(id_: str, label: str, dimensiones: list[str] | None = None, hijos: list[dict] | None = None) -> dict:
    nodo = {"id": id_, "label": label, "dimensiones": dimensiones or []}
    if hijos:
        nodo["hijos"] = hijos
    return nodo


CATEGORIAS_IKIGAI = {
    "es": [
        _nodo(
            "crear_construir",
            "Crear o construir cosas",
            hijos=[
                _nodo(
                    "software_tecnologia",
                    "Software y tecnología",
                    hijos=[
                        _nodo("crear_apps", "Aplicaciones o productos digitales", ["amas", "sos_bueno", "pueden_pagar"]),
                        _nodo("automatizar_tedioso", "Automatizar algo tedioso", ["sos_bueno", "mundo_necesita"]),
                    ],
                ),
                _nodo(
                    "con_las_manos",
                    "Con las manos",
                    hijos=[
                        _nodo("carpinteria_reparaciones", "Carpintería, reparaciones, manualidades", ["amas", "pueden_pagar"]),
                        _nodo("cocinar_recetas", "Cocinar o crear recetas propias", ["amas", "mundo_necesita"]),
                    ],
                ),
                _nodo(
                    "contenido_ideas",
                    "Contenido e ideas",
                    hijos=[
                        _nodo("escribir", "Escribir (historias, ensayos, guiones)", ["amas", "valores"]),
                        _nodo("musica_audiovisual", "Música o producción audiovisual", ["amas", "sos_bueno"]),
                    ],
                ),
            ],
        ),
        _nodo(
            "ayudar_cuidar",
            "Ayudar o cuidar a otros",
            hijos=[
                _nodo(
                    "uno_a_uno",
                    "Uno a uno",
                    hijos=[
                        _nodo("mentorear", "Enseñar o mentorear a una persona", ["sos_bueno", "mundo_necesita", "valores"]),
                        _nodo("acompañar_dificil", "Acompañar en un momento difícil", ["mundo_necesita", "valores"]),
                    ],
                ),
                _nodo(
                    "grupo_comunidad",
                    "A un grupo o comunidad",
                    hijos=[
                        _nodo("liderar_grupo", "Organizar o liderar un grupo", ["sos_bueno", "pueden_pagar"]),
                        _nodo("voluntariado", "Voluntariado o causa social", ["mundo_necesita", "valores"]),
                    ],
                ),
                _nodo(
                    "cuidado_cercano",
                    "Cuidado cercano",
                    hijos=[
                        _nodo("cuidar_familia", "Cuidar a la familia", ["mundo_necesita", "valores"]),
                        _nodo("presente_amigos", "Estar presente para amigos", ["mundo_necesita", "valores"]),
                    ],
                ),
            ],
        ),
        _nodo(
            "resolver_entender",
            "Resolver problemas / entender cómo funcionan las cosas",
            hijos=[
                _nodo(
                    "problemas_tecnicos",
                    "Problemas técnicos o lógicos",
                    hijos=[
                        _nodo("depurar_diagnosticar", "Depurar o diagnosticar qué está fallando", ["sos_bueno", "pueden_pagar"]),
                        _nodo("optimizar", "Optimizar algo que ya funciona pero mal", ["sos_bueno", "mundo_necesita"]),
                    ],
                ),
                _nodo(
                    "problemas_personas",
                    "Problemas de personas o de organización",
                    hijos=[
                        _nodo("mediar_conflicto", "Mediar un conflicto", ["sos_bueno", "valores"]),
                        _nodo("ordenar_caos", "Ordenar el caos (procesos, planificación)", ["sos_bueno", "pueden_pagar"]),
                    ],
                ),
                _nodo(
                    "curiosidad_pura",
                    "Curiosidad pura",
                    hijos=[
                        _nodo("investigar_a_fondo", "Investigar un tema a fondo", ["amas", "sos_bueno"]),
                        _nodo("aprender_de_punta_a_punta", "Aprender algo nuevo de punta a punta", ["amas"]),
                    ],
                ),
            ],
        ),
        _nodo(
            "enseñar_transmitir",
            "Enseñar o transmitir conocimiento",
            hijos=[
                _nodo(
                    "frente_a_grupo",
                    "Frente a un grupo",
                    hijos=[
                        _nodo("dar_clases_talleres", "Dar clases o talleres", ["sos_bueno", "mundo_necesita", "pueden_pagar"]),
                        _nodo("hablar_publico", "Hablar en público sobre un tema que domino", ["sos_bueno", "pueden_pagar"]),
                    ],
                ),
                _nodo(
                    "contenido_que_queda",
                    "Contenido que queda",
                    hijos=[
                        _nodo("escribir_guias", "Escribir guías o tutoriales", ["sos_bueno", "mundo_necesita"]),
                        _nodo("grabar_contenido_educativo", "Grabar contenido educativo", ["sos_bueno", "pueden_pagar"]),
                    ],
                ),
            ],
        ),
        _nodo(
            "liderar_organizar",
            "Liderar u organizar",
            hijos=[
                _nodo(
                    "equipo_proyecto",
                    "Un equipo o proyecto",
                    hijos=[
                        _nodo("coordinar_personas", "Coordinar personas hacia un objetivo común", ["sos_bueno", "pueden_pagar"]),
                        _nodo("decisiones_dificiles", "Tomar decisiones difíciles por el grupo", ["sos_bueno", "valores"]),
                    ],
                ),
                _nodo(
                    "causa_propia",
                    "Una causa o iniciativa propia",
                    hijos=[
                        _nodo("emprender", "Emprender algo desde cero", ["amas", "pueden_pagar"]),
                        _nodo("impulsar_cambio", "Impulsar un cambio en mi entorno", ["mundo_necesita", "valores"]),
                    ],
                ),
            ],
        ),
        _nodo(
            "investigar_aprender",
            "Investigar o aprender continuamente",
            hijos=[
                _nodo(
                    "ciencia_tecnologia",
                    "Ciencia o tecnología",
                    hijos=[
                        _nodo("seguir_avances", "Seguir de cerca avances de un campo", ["amas", "sos_bueno"]),
                        _nodo("experimentar", "Experimentar y probar cosas nuevas", ["amas", "sos_bueno"]),
                    ],
                ),
                _nodo(
                    "personas_cultura",
                    "Personas o cultura",
                    hijos=[
                        _nodo("entender_gente", "Entender por qué la gente hace lo que hace", ["amas", "sos_bueno"]),
                        _nodo("explorar_formas_de_vivir", "Explorar otras formas de pensar o vivir", ["amas", "valores"]),
                    ],
                ),
            ],
        ),
        _nodo(
            "expresarme",
            "Expresarme o mostrar algo mío",
            hijos=[
                _nodo(
                    "performance_en_vivo",
                    "Performance en vivo",
                    hijos=[
                        _nodo("actuar_tocar_en_vivo", "Hablar en público, actuar, tocar en vivo", ["amas", "sos_bueno"]),
                        _nodo("enseñar_con_estilo", "Enseñar frente a un grupo con estilo propio", ["amas", "sos_bueno"]),
                    ],
                ),
                _nodo(
                    "obra_que_queda",
                    "Obra que queda",
                    hijos=[
                        _nodo("publicar_algo", "Publicar algo (escrito, código, arte)", ["amas", "valores"]),
                        _nodo("diseñar_para_otros", "Diseñar algo que otros van a usar o ver", ["amas", "sos_bueno", "pueden_pagar"]),
                    ],
                ),
            ],
        ),
        _nodo(
            "cuidar_entorno",
            "Cuidar mi entorno o causas sociales",
            hijos=[
                _nodo(
                    "medio_ambiente",
                    "Medio ambiente",
                    hijos=[
                        _nodo("reducir_impacto", "Reducir el impacto ambiental en lo que hago", ["mundo_necesita", "valores"]),
                        _nodo("soluciones_ambientales", "Trabajar en soluciones ambientales", ["mundo_necesita", "pueden_pagar"]),
                    ],
                ),
                _nodo(
                    "justicia_equidad",
                    "Justicia o equidad",
                    hijos=[
                        _nodo("defender_a_quien_no_puede", "Defender a quien no puede defenderse solo", ["mundo_necesita", "valores"]),
                        _nodo("igualdad_de_oportunidades", "Trabajar por más igualdad de oportunidades", ["mundo_necesita", "valores"]),
                    ],
                ),
            ],
        ),
    ],
    "en": [
        _nodo(
            "crear_construir",
            "Create or build things",
            hijos=[
                _nodo(
                    "software_tecnologia",
                    "Software and technology",
                    hijos=[
                        _nodo("crear_apps", "Apps or digital products", ["amas", "sos_bueno", "pueden_pagar"]),
                        _nodo("automatizar_tedioso", "Automating something tedious", ["sos_bueno", "mundo_necesita"]),
                    ],
                ),
                _nodo(
                    "con_las_manos",
                    "With my hands",
                    hijos=[
                        _nodo("carpinteria_reparaciones", "Carpentry, repairs, crafts", ["amas", "pueden_pagar"]),
                        _nodo("cocinar_recetas", "Cooking or creating my own recipes", ["amas", "mundo_necesita"]),
                    ],
                ),
                _nodo(
                    "contenido_ideas",
                    "Content and ideas",
                    hijos=[
                        _nodo("escribir", "Writing (stories, essays, scripts)", ["amas", "valores"]),
                        _nodo("musica_audiovisual", "Music or audiovisual production", ["amas", "sos_bueno"]),
                    ],
                ),
            ],
        ),
        _nodo(
            "ayudar_cuidar",
            "Help or take care of others",
            hijos=[
                _nodo(
                    "uno_a_uno",
                    "One on one",
                    hijos=[
                        _nodo("mentorear", "Teaching or mentoring one person", ["sos_bueno", "mundo_necesita", "valores"]),
                        _nodo("acompañar_dificil", "Being there for someone in a hard moment", ["mundo_necesita", "valores"]),
                    ],
                ),
                _nodo(
                    "grupo_comunidad",
                    "A group or community",
                    hijos=[
                        _nodo("liderar_grupo", "Organizing or leading a group", ["sos_bueno", "pueden_pagar"]),
                        _nodo("voluntariado", "Volunteering or a social cause", ["mundo_necesita", "valores"]),
                    ],
                ),
                _nodo(
                    "cuidado_cercano",
                    "Close care",
                    hijos=[
                        _nodo("cuidar_familia", "Taking care of family", ["mundo_necesita", "valores"]),
                        _nodo("presente_amigos", "Being present for friends", ["mundo_necesita", "valores"]),
                    ],
                ),
            ],
        ),
        _nodo(
            "resolver_entender",
            "Solve problems / understand how things work",
            hijos=[
                _nodo(
                    "problemas_tecnicos",
                    "Technical or logical problems",
                    hijos=[
                        _nodo("depurar_diagnosticar", "Debugging or diagnosing what's failing", ["sos_bueno", "pueden_pagar"]),
                        _nodo("optimizar", "Optimizing something that works, poorly", ["sos_bueno", "mundo_necesita"]),
                    ],
                ),
                _nodo(
                    "problemas_personas",
                    "People or organizational problems",
                    hijos=[
                        _nodo("mediar_conflicto", "Mediating a conflict", ["sos_bueno", "valores"]),
                        _nodo("ordenar_caos", "Bringing order to chaos (process, planning)", ["sos_bueno", "pueden_pagar"]),
                    ],
                ),
                _nodo(
                    "curiosidad_pura",
                    "Pure curiosity",
                    hijos=[
                        _nodo("investigar_a_fondo", "Researching a topic in depth", ["amas", "sos_bueno"]),
                        _nodo("aprender_de_punta_a_punta", "Learning something new end to end", ["amas"]),
                    ],
                ),
            ],
        ),
        _nodo(
            "enseñar_transmitir",
            "Teach or pass on knowledge",
            hijos=[
                _nodo(
                    "frente_a_grupo",
                    "In front of a group",
                    hijos=[
                        _nodo("dar_clases_talleres", "Teaching classes or workshops", ["sos_bueno", "mundo_necesita", "pueden_pagar"]),
                        _nodo("hablar_publico", "Public speaking on something I know well", ["sos_bueno", "pueden_pagar"]),
                    ],
                ),
                _nodo(
                    "contenido_que_queda",
                    "Content that lasts",
                    hijos=[
                        _nodo("escribir_guias", "Writing guides or tutorials", ["sos_bueno", "mundo_necesita"]),
                        _nodo("grabar_contenido_educativo", "Recording educational content", ["sos_bueno", "pueden_pagar"]),
                    ],
                ),
            ],
        ),
        _nodo(
            "liderar_organizar",
            "Lead or organize",
            hijos=[
                _nodo(
                    "equipo_proyecto",
                    "A team or project",
                    hijos=[
                        _nodo("coordinar_personas", "Coordinating people toward a shared goal", ["sos_bueno", "pueden_pagar"]),
                        _nodo("decisiones_dificiles", "Making hard calls for the group", ["sos_bueno", "valores"]),
                    ],
                ),
                _nodo(
                    "causa_propia",
                    "My own cause or initiative",
                    hijos=[
                        _nodo("emprender", "Starting something from scratch", ["amas", "pueden_pagar"]),
                        _nodo("impulsar_cambio", "Driving change in my environment", ["mundo_necesita", "valores"]),
                    ],
                ),
            ],
        ),
        _nodo(
            "investigar_aprender",
            "Research or keep learning",
            hijos=[
                _nodo(
                    "ciencia_tecnologia",
                    "Science or technology",
                    hijos=[
                        _nodo("seguir_avances", "Following advances in a field closely", ["amas", "sos_bueno"]),
                        _nodo("experimentar", "Experimenting and trying new things", ["amas", "sos_bueno"]),
                    ],
                ),
                _nodo(
                    "personas_cultura",
                    "People or culture",
                    hijos=[
                        _nodo("entender_gente", "Understanding why people do what they do", ["amas", "sos_bueno"]),
                        _nodo("explorar_formas_de_vivir", "Exploring other ways of thinking or living", ["amas", "valores"]),
                    ],
                ),
            ],
        ),
        _nodo(
            "expresarme",
            "Express myself / show something of my own",
            hijos=[
                _nodo(
                    "performance_en_vivo",
                    "Live performance",
                    hijos=[
                        _nodo("actuar_tocar_en_vivo", "Public speaking, acting, performing live", ["amas", "sos_bueno"]),
                        _nodo("enseñar_con_estilo", "Teaching a group with my own style", ["amas", "sos_bueno"]),
                    ],
                ),
                _nodo(
                    "obra_que_queda",
                    "Work that lasts",
                    hijos=[
                        _nodo("publicar_algo", "Publishing something (writing, code, art)", ["amas", "valores"]),
                        _nodo("diseñar_para_otros", "Designing something others will use or see", ["amas", "sos_bueno", "pueden_pagar"]),
                    ],
                ),
            ],
        ),
        _nodo(
            "cuidar_entorno",
            "Care for my environment or social causes",
            hijos=[
                _nodo(
                    "medio_ambiente",
                    "Environment",
                    hijos=[
                        _nodo("reducir_impacto", "Reducing my own environmental impact", ["mundo_necesita", "valores"]),
                        _nodo("soluciones_ambientales", "Working on environmental solutions", ["mundo_necesita", "pueden_pagar"]),
                    ],
                ),
                _nodo(
                    "justicia_equidad",
                    "Justice or equity",
                    hijos=[
                        _nodo("defender_a_quien_no_puede", "Standing up for someone who can't do it alone", ["mundo_necesita", "valores"]),
                        _nodo("igualdad_de_oportunidades", "Working toward more equal opportunity", ["mundo_necesita", "valores"]),
                    ],
                ),
            ],
        ),
    ],
}


def buscar_nodo_con_ruta(idioma: str, nodo_id: str) -> tuple[dict, list[str]] | None:
    """Busca `nodo_id` en el árbol del idioma dado (DFS) y devuelve
    (nodo, ruta_de_ids_desde_la_raiz) -- o None si no existe. El backend
    deriva la ruta y las `dimensiones` de acá en vez de confiar en lo que
    mande el cliente, mismo criterio de "código decide, no el cliente ni
    el modelo" que el resto del proyecto."""
    arbol = CATEGORIAS_IKIGAI.get(idioma, CATEGORIAS_IKIGAI["es"])

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
