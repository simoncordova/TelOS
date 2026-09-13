"""Taxonomía del selector visual Ikigai (Fase 1) -- ver el plan
"quirky-launching-swing" (directorio de planes de Claude Code).

Reemplaza la generación libre de preguntas del Explorador conversacional
(Explorer v2, sacado el 13/09/2026): en vez de que un modelo pregunte y
otro evalúe si la respuesta "ya alcanza", la persona elige de este árbol
-- la elección ES el dato, válida por construcción, sin nada que un LLM
tenga que juzgar.

**Contenido y mecánica portados del prototipo interactivo real hecho en
Claude Design (13/09/2026)** -- no la semilla original que se había
inventado acá antes de tener el diseño. Diferencias respecto a esa
primera versión, todas deliberadas para que backend y frontend coincidan
exacto:

- **4 dimensiones, no 5** -- L (lo que amás), G (en lo que destacás),
  V (lo que aporta valor), N (lo que el mundo necesita). "Valores" no es
  una dimensión de cobertura acá: es un paso aparte, una sola vez, ver
  VALORES_DISPONIBLES y agents/orquestador.py::SesionTelos.confirmar_valores.
- **3 niveles con IDs compuestos, no un solo árbol plano**: VERBOS
  (nivel 1, ej. "crear") -> DOMINIOS (nivel 2, ej. "tech", reutilizado
  por varios verbos) -> HOJAS (nivel 3, específico, ej. "IA"). El mismo
  dominio+hoja alcanzado desde un verbo distinto es una selección
  distinta -- el verbo también aporta sus propias dimensiones. El
  `nodo_id` que manda el cliente es la ruta completa unida con "/"
  (`"crear/tech/IA"`), igual que en el prototipo.
- **Convergencia por unión, no por hoja sola**: las dimensiones finales
  de una selección son la unión de las del verbo y las de la hoja
  (`unir_dimensiones`) -- ej. "crear" (LG) + "IA" (LG) = LG; "crear" (LG)
  + "Apps" (LV) = LGV. Autoría más eficiente que etiquetar cada hoja
  desde cero.
"""

DIMENSIONES_IKIGAI = ("L", "G", "V", "N")

ETIQUETAS_DIMENSION = {
    "es": {"L": "Lo que amas", "G": "En lo que destacas", "V": "Lo que aporta valor", "N": "Lo que el mundo necesita"},
    "en": {"L": "What you love", "G": "What you're good at", "V": "What creates value", "N": "What the world needs"},
}


def _verbo(id_: str, label: str, desc: str, dims: str, dominios: list[str]) -> dict:
    return {"id": id_, "label": label, "desc": desc, "dims": dims, "dominios": dominios}


VERBOS = {
    "es": [
        _verbo("crear", "Crear", "Dar forma a algo que antes no existía.", "LG", ["tech", "arte", "producto", "palabra", "sistemas", "naturaleza"]),
        _verbo("ayudar", "Ayudar", "Estar del lado de alguien que lo necesita.", "LN", ["personas", "salud", "comunidad", "aprendizaje", "palabra", "naturaleza"]),
        _verbo("resolver", "Resolver", "Desarmar un problema hasta que ceda.", "GV", ["sistemas", "tech", "datos", "producto", "naturaleza", "salud"]),
        _verbo("ensenar", "Enseñar", "Que otro pueda hacer lo que tú sabes.", "LN", ["aprendizaje", "tech", "arte", "palabra", "personas", "ciencia"]),
        _verbo("liderar", "Liderar", "Llevar a un grupo a un lugar mejor.", "GV", ["producto", "personas", "comunidad", "sistemas", "tech", "aprendizaje"]),
        _verbo("investigar", "Investigar", "Perseguir una pregunta hasta el fondo.", "LG", ["ciencia", "datos", "naturaleza", "personas", "tech", "palabra"]),
        _verbo("construir", "Construir", "Hacer que algo se sostenga en el tiempo.", "GV", ["tech", "sistemas", "producto", "naturaleza", "arte", "comunidad"]),
        _verbo("transformar", "Transformar", "Cambiar cómo funcionan las cosas.", "NV", ["sistemas", "comunidad", "personas", "naturaleza", "producto", "aprendizaje"]),
    ],
    "en": [
        _verbo("crear", "Create", "Give shape to something that didn't exist before.", "LG", ["tech", "arte", "producto", "palabra", "sistemas", "naturaleza"]),
        _verbo("ayudar", "Help", "Stand by someone who needs it.", "LN", ["personas", "salud", "comunidad", "aprendizaje", "palabra", "naturaleza"]),
        _verbo("resolver", "Solve", "Take a problem apart until it gives.", "GV", ["sistemas", "tech", "datos", "producto", "naturaleza", "salud"]),
        _verbo("ensenar", "Teach", "Make it so someone else can do what you know.", "LN", ["aprendizaje", "tech", "arte", "palabra", "personas", "ciencia"]),
        _verbo("liderar", "Lead", "Take a group somewhere better.", "GV", ["producto", "personas", "comunidad", "sistemas", "tech", "aprendizaje"]),
        _verbo("investigar", "Investigate", "Chase a question all the way down.", "LG", ["ciencia", "datos", "naturaleza", "personas", "tech", "palabra"]),
        _verbo("construir", "Build", "Make something hold up over time.", "GV", ["tech", "sistemas", "producto", "naturaleza", "arte", "comunidad"]),
        _verbo("transformar", "Transform", "Change how things work.", "NV", ["sistemas", "comunidad", "personas", "naturaleza", "producto", "aprendizaje"]),
    ],
}

DOMINIOS = {
    "es": {
        "tech": {"label": "Tecnología", "desc": "Software, IA, datos y herramientas."},
        "arte": {"label": "Arte y estética", "desc": "Forma, imagen, sonido, materia."},
        "producto": {"label": "Productos y negocios", "desc": "Soluciones que alguien usa de verdad."},
        "palabra": {"label": "Palabra e historias", "desc": "Escribir, narrar, comunicar."},
        "personas": {"label": "Personas", "desc": "Vínculos, acompañamiento, desarrollo."},
        "comunidad": {"label": "Comunidad", "desc": "Grupos, territorio, lo colectivo."},
        "salud": {"label": "Cuerpo y salud", "desc": "Bienestar físico y mental."},
        "aprendizaje": {"label": "Aprendizaje", "desc": "Cómo aprendemos y enseñamos."},
        "sistemas": {"label": "Sistemas y procesos", "desc": "Cómo funcionan las cosas por dentro."},
        "datos": {"label": "Datos y evidencia", "desc": "Medir, entender, anticipar."},
        "naturaleza": {"label": "Naturaleza y entorno", "desc": "Territorio, clima, ciudad."},
        "ciencia": {"label": "Ciencia", "desc": "Preguntas, método, descubrimiento."},
    },
    "en": {
        "tech": {"label": "Technology", "desc": "Software, AI, data and tools."},
        "arte": {"label": "Art and aesthetics", "desc": "Form, image, sound, material."},
        "producto": {"label": "Products and business", "desc": "Solutions someone actually uses."},
        "palabra": {"label": "Words and stories", "desc": "Writing, storytelling, communicating."},
        "personas": {"label": "People", "desc": "Bonds, support, growth."},
        "comunidad": {"label": "Community", "desc": "Groups, place, the collective."},
        "salud": {"label": "Body and health", "desc": "Physical and mental wellbeing."},
        "aprendizaje": {"label": "Learning", "desc": "How we learn and teach."},
        "sistemas": {"label": "Systems and processes", "desc": "How things work underneath."},
        "datos": {"label": "Data and evidence", "desc": "Measuring, understanding, anticipating."},
        "naturaleza": {"label": "Nature and environment", "desc": "Land, climate, the city."},
        "ciencia": {"label": "Science", "desc": "Questions, method, discovery."},
    },
}


def _hoja(id_: str, desc: str, dims: str) -> dict:
    return {"id": id_, "label": id_, "desc": desc, "dims": dims}


HOJAS = {
    "es": {
        "tech": [_hoja("IA", "Tecnología que aprende y crea.", "LG"), _hoja("Apps", "Productos digitales cotidianos.", "LV"), _hoja("Software", "Sistemas que otros usan a diario.", "GV"), _hoja("Automatización", "Quitar del medio el trabajo repetitivo.", "GV"), _hoja("Hardware", "Objetos que piensan.", "GL"), _hoja("Infraestructura", "Lo invisible que sostiene todo.", "GN")],
        "arte": [_hoja("Imagen", "Fotografía, ilustración, visual.", "L"), _hoja("Sonido", "Música y paisaje sonoro.", "L"), _hoja("Espacio", "Objetos, interiores, materia.", "LG"), _hoja("Movimiento", "Video, animación, cuerpo.", "LG"), _hoja("Dirección", "Dar coherencia estética a algo.", "GV"), _hoja("Artesanía", "Hacer con las manos.", "LN")],
        "producto": [_hoja("Producto digital", "Construir soluciones útiles para otros.", "LV"), _hoja("Emprender", "Llevar una idea al mundo real.", "LV"), _hoja("Estrategia", "Decidir dónde jugar.", "GV"), _hoja("Ventas", "Conectar valor con quien lo necesita.", "VN"), _hoja("Operaciones", "Que funcione todos los días.", "GV"), _hoja("Impacto social", "Negocio con propósito.", "NV")],
        "palabra": [_hoja("Escritura", "Ordenar ideas en palabras.", "LG"), _hoja("Narrativa", "Contar lo que importa.", "LN"), _hoja("Divulgación", "Hacer entendible lo complejo.", "GN"), _hoja("Marca", "Dar voz a algo.", "GV"), _hoja("Periodismo", "Sacar cosas a la luz.", "NV"), _hoja("Conversación", "Facilitar el diálogo.", "LN")],
        "personas": [_hoja("Mentoría", "Ayudar a otros a crecer.", "LN"), _hoja("Acompañar", "Estar al lado en lo difícil.", "LN"), _hoja("Equipos", "Que trabajar juntos funcione.", "GV"), _hoja("Talento", "Encontrar a la persona correcta.", "GV"), _hoja("Mundo interior", "Trabajar lo que no se ve.", "LN"), _hoja("Cuidado", "Sostener a quien no puede solo.", "LN")],
        "comunidad": [_hoja("Territorio", "Lo que pasa cerca.", "LN"), _hoja("Organizar", "Mover a un grupo hacia algo.", "GN"), _hoja("Cultura local", "Lo que nos identifica.", "LN"), _hoja("Inclusión", "Que nadie quede afuera.", "NV"), _hoja("Redes", "Conectar personas entre sí.", "GV"), _hoja("Voluntariado", "Entregar tiempo propio.", "LN")],
        "salud": [_hoja("Movimiento", "Entrenar el cuerpo.", "LG"), _hoja("Salud mental", "Sostener la mente.", "LN"), _hoja("Nutrición", "Lo que comemos.", "GN"), _hoja("Prevención", "Actuar antes de que duela.", "GN"), _hoja("Rehabilitación", "Volver a funcionar.", "GN"), _hoja("Longevidad", "Vivir mejor más tiempo.", "LN")],
        "aprendizaje": [_hoja("Diseño de aprendizaje", "Cómo se enseña algo.", "GV"), _hoja("Contenido educativo", "Ayudar a otros a desarrollar conocimiento.", "LV"), _hoja("Aula", "Enseñar cara a cara.", "LN"), _hoja("Habilidades", "Entrenar para hacer.", "GV"), _hoja("Infancia", "Los primeros años.", "LN"), _hoja("Reconversión", "Aprender otro oficio.", "NV")],
        "sistemas": [_hoja("Procesos", "Ordenar cómo se hace.", "GV"), _hoja("Diagnóstico", "Encontrar la falla.", "GN"), _hoja("Rediseño", "Cambiar la forma del sistema.", "GV"), _hoja("Política pública", "Reglas que afectan a muchos.", "NV"), _hoja("Logística", "Mover cosas y tiempo.", "GV"), _hoja("Calidad", "Que salga bien siempre.", "GV")],
        "datos": [_hoja("Análisis", "Entender lo que pasó.", "GV"), _hoja("Predicción", "Anticipar lo que viene.", "LG"), _hoja("Visualización", "Hacer ver el patrón.", "LG"), _hoja("Medición de impacto", "Saber si sirvió.", "NV"), _hoja("Investigación", "Preguntar con números.", "GN"), _hoja("Modelos", "Simular la realidad.", "LG")],
        "naturaleza": [_hoja("Clima", "El problema grande.", "NV"), _hoja("Paisaje", "Habitar el lugar.", "LN"), _hoja("Alimentos", "De dónde viene la comida.", "GN"), _hoja("Energía", "Cómo movemos el mundo.", "NV"), _hoja("Conservación", "Proteger lo que queda.", "LN"), _hoja("Ciudad", "Vivir juntos mejor.", "GN")],
        "ciencia": [_hoja("Preguntas abiertas", "Lo que nadie sabe aún.", "LG"), _hoja("Método", "Cómo se prueba una idea.", "GV"), _hoja("Biología", "La vida por dentro.", "GN"), _hoja("Materia", "Las reglas del mundo.", "LG"), _hoja("Cognición", "Cómo pensamos.", "LN"), _hoja("Transferencia", "Del laboratorio a la calle.", "VN")],
    },
    "en": {
        "tech": [_hoja("AI", "Technology that learns and creates.", "LG"), _hoja("Apps", "Everyday digital products.", "LV"), _hoja("Software", "Systems others use daily.", "GV"), _hoja("Automation", "Taking repetitive work out of the way.", "GV"), _hoja("Hardware", "Objects that think.", "GL"), _hoja("Infrastructure", "The invisible thing holding it all up.", "GN")],
        "arte": [_hoja("Image", "Photography, illustration, visuals.", "L"), _hoja("Sound", "Music and soundscape.", "L"), _hoja("Space", "Objects, interiors, material.", "LG"), _hoja("Motion", "Video, animation, the body.", "LG"), _hoja("Direction", "Giving something aesthetic coherence.", "GV"), _hoja("Craft", "Making with your hands.", "LN")],
        "producto": [_hoja("Digital product", "Building useful solutions for others.", "LV"), _hoja("Entrepreneurship", "Bringing an idea into the real world.", "LV"), _hoja("Strategy", "Deciding where to play.", "GV"), _hoja("Sales", "Connecting value with who needs it.", "VN"), _hoja("Operations", "Making it work every day.", "GV"), _hoja("Social impact", "Business with purpose.", "NV")],
        "palabra": [_hoja("Writing", "Putting ideas into words.", "LG"), _hoja("Narrative", "Telling what matters.", "LN"), _hoja("Explaining", "Making the complex understandable.", "GN"), _hoja("Brand", "Giving something a voice.", "GV"), _hoja("Journalism", "Bringing things to light.", "NV"), _hoja("Conversation", "Facilitating dialogue.", "LN")],
        "personas": [_hoja("Mentorship", "Helping others grow.", "LN"), _hoja("Being there", "Standing by someone through something hard.", "LN"), _hoja("Teams", "Making working together work.", "GV"), _hoja("Talent", "Finding the right person.", "GV"), _hoja("Inner world", "Working on what doesn't show.", "LN"), _hoja("Care", "Holding up someone who can't alone.", "LN")],
        "comunidad": [_hoja("Place", "What happens close by.", "LN"), _hoja("Organizing", "Moving a group toward something.", "GN"), _hoja("Local culture", "What makes us who we are.", "LN"), _hoja("Inclusion", "Making sure no one is left out.", "NV"), _hoja("Networks", "Connecting people to each other.", "GV"), _hoja("Volunteering", "Giving your own time.", "LN")],
        "salud": [_hoja("Movement", "Training the body.", "LG"), _hoja("Mental health", "Holding up the mind.", "LN"), _hoja("Nutrition", "What we eat.", "GN"), _hoja("Prevention", "Acting before it hurts.", "GN"), _hoja("Rehabilitation", "Getting back to function.", "GN"), _hoja("Longevity", "Living better, longer.", "LN")],
        "aprendizaje": [_hoja("Learning design", "How something gets taught.", "GV"), _hoja("Educational content", "Helping others build knowledge.", "LV"), _hoja("Classroom", "Teaching face to face.", "LN"), _hoja("Skills", "Training people to do.", "GV"), _hoja("Early childhood", "The first years.", "LN"), _hoja("Reskilling", "Learning another trade.", "NV")],
        "sistemas": [_hoja("Processes", "Putting order into how it's done.", "GV"), _hoja("Diagnosis", "Finding the failure.", "GN"), _hoja("Redesign", "Changing the system's shape.", "GV"), _hoja("Public policy", "Rules that affect many.", "NV"), _hoja("Logistics", "Moving things and time.", "GV"), _hoja("Quality", "Making it come out right, always.", "GV")],
        "datos": [_hoja("Analysis", "Understanding what happened.", "GV"), _hoja("Prediction", "Anticipating what's coming.", "LG"), _hoja("Visualization", "Making the pattern visible.", "LG"), _hoja("Impact measurement", "Knowing if it worked.", "NV"), _hoja("Research", "Asking with numbers.", "GN"), _hoja("Models", "Simulating reality.", "LG")],
        "naturaleza": [_hoja("Climate", "The big problem.", "NV"), _hoja("Landscape", "Inhabiting a place.", "LN"), _hoja("Food", "Where food comes from.", "GN"), _hoja("Energy", "How we move the world.", "NV"), _hoja("Conservation", "Protecting what's left.", "LN"), _hoja("City", "Living together better.", "GN")],
        "ciencia": [_hoja("Open questions", "What no one knows yet.", "LG"), _hoja("Method", "How an idea gets tested.", "GV"), _hoja("Biology", "Life from the inside.", "GN"), _hoja("Matter", "The rules of the world.", "LG"), _hoja("Cognition", "How we think.", "LN"), _hoja("Transfer", "From the lab to the street.", "VN")],
    },
}

VALORES_DISPONIBLES = {
    "es": ["Autonomía", "Honestidad", "Tiempo con los míos", "Aprender siempre", "Justicia", "Calma", "Excelencia", "Libertad creativa", "Pertenencia", "Coherencia"],
    "en": ["Autonomy", "Honesty", "Time with my people", "Always learning", "Justice", "Calm", "Excellence", "Creative freedom", "Belonging", "Coherence"],
}
MAX_VALORES = 3


def unir_dimensiones(dims_a: str, dims_b: str) -> list[str]:
    """Une dos strings de letras de dimensión (ej. "LG" + "LV" -> ["L","G","V"]),
    sin duplicados, preservando el orden de aparición -- mismo criterio
    que `union()` en el prototipo de Claude Design."""
    vistas: list[str] = []
    for letra in dims_a + dims_b:
        if letra not in vistas:
            vistas.append(letra)
    return vistas


def buscar_hoja(idioma: str, verbo_id: str, dominio_id: str, hoja_id: str) -> tuple[dict, dict, list[str]] | None:
    """Busca la combinación (verbo, dominio, hoja) y devuelve
    (verbo, hoja, dimensiones_unidas) -- o None si no existe esa
    combinación exacta (ej. un dominio que no está en `verbo["dominios"]`,
    o una hoja que no está definida para ese dominio). El backend
    calcula acá las dimensiones finales, nunca confía en lo que mande el
    cliente."""
    idioma = idioma if idioma in VERBOS else "es"
    verbo = next((v for v in VERBOS[idioma] if v["id"] == verbo_id), None)
    if verbo is None or dominio_id not in verbo["dominios"]:
        return None
    hoja = next((h for h in HOJAS[idioma].get(dominio_id, []) if h["id"] == hoja_id), None)
    if hoja is None:
        return None
    return verbo, hoja, unir_dimensiones(verbo["dims"], hoja["dims"])
