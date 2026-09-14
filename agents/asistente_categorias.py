"""Asistente de categorías -- chat de apoyo real de Fase 1 (ver
web/src/components/Seleccion/ArbolSelector.tsx). Reemplaza las
respuestas fijas por palabra clave: dado lo que la persona describe en
texto libre, busca ENTRE LAS CATEGORÍAS QUE YA EXISTEN en
tools/categorias_ikigai.py cuál encaja mejor -- nunca inventa una
categoría nueva.

Decisión explícita del dueño del producto (13/09/2026): dejar que el
modelo agregue estructura de producto en caliente (una categoría/hoja
nueva) es el mismo patrón que causó los bugs de repetición de Explorer
v1/v2 -- juicio del modelo sobre algo que debería ser fijo y curado. Acá
el modelo solo elige entre lo que ya existe, y ese resultado se vuelve a
validar contra la taxonomía real antes de confiar en él (mismo criterio
"código decide, nunca confía ciegamente en lo que devuelve el modelo"
que el resto del proyecto) -- si sugiere una combinación que no existe,
se descarta como si no hubiera encontrado nada. Si de verdad no hay una
categoría que encaje, el asistente sugiere la más cercana en su propia
explicación para que la persona use el campo de detalle libre que ya
existe en cada selección -- no se agrega ningún mecanismo nuevo de
"crear categoría", el que ya hay (detalle_libre) alcanza."""

from pydantic import BaseModel
from strands import Agent

from agents._modelo import crear_modelo_subagente
from tools.categorias_ikigai import DOMINIOS, HOJAS, VERBOS, buscar_hoja

_PROMPT_ES = """Una persona está explorando su propósito de vida \
eligiendo categorías de un árbol fijo. Te va a describir, con sus \
propias palabras, algo que quiere expresar -- tu ÚNICO trabajo es \
buscar, ENTRE LAS CATEGORÍAS QUE YA EXISTEN abajo, cuál encaja mejor. \
Nunca inventes una categoría que no esté en la lista, y nunca devuelvas \
un id que no aparezca tal cual entre comillas.

{tabla}

Descripción de la persona: "{descripcion}"

Si alguna combinación verbo + dominio + hoja de la lista de arriba \
encaja razonablemente, devolvé encontrada=true con esos tres ids \
EXACTOS (el id entre comillas, no el nombre visible) y una explicación \
breve y cálida, hablándole directo a la persona, de por qué encaja. Si \
ninguna combinación encaja bien, devolvé encontrada=false, y en la \
explicación mencioná -- con tus propias palabras, hablándole a la \
persona -- la categoría más parecida que sí existe, sugiriéndole que la \
elija y agregue su matiz específico en el campo de detalle libre. Nunca \
le prometas una categoría que no está en la lista."""

_PROMPT_EN = """A person is exploring their life purpose by choosing \
categories from a fixed tree. They're about to describe, in their own \
words, something they want to express -- your ONLY job is to search, \
AMONG THE CATEGORIES THAT ALREADY EXIST below, for the best match. \
Never invent a category that isn't in the list, and never return an id \
that doesn't appear verbatim in quotes.

{tabla}

Person's description: "{descripcion}"

If some verb + domain + leaf combination from the list above fits \
reasonably, return encontrada=true with those exact three ids (the id \
in quotes, not the display name) and a short, warm explanation, \
speaking directly to the person, of why it fits. If nothing fits well, \
return encontrada=false, and in the explanation mention -- in your own \
words, speaking to the person -- the closest existing category, \
suggesting they pick it and add their specific nuance in the free-text \
detail field. Never promise a category that isn't in the list."""


class SugerenciaCategoria(BaseModel):
    """Contrato forzado (structured_output_model). `verbo_id`/
    `dominio_id`/`hoja_id` solo tienen sentido cuando `encontrada=True` --
    se vuelven a validar contra tools/categorias_ikigai.py::buscar_hoja
    antes de confiar en ellos, nunca se aceptan tal cual."""

    encontrada: bool
    verbo_id: str | None = None
    dominio_id: str | None = None
    hoja_id: str | None = None
    explicacion: str


def _tabla_categorias(idioma: str) -> str:
    """Arma la tabla de referencia (verbo -> dominios disponibles;
    dominio -> hojas) que se le pasa al modelo -- pura, sin llamar a
    Bedrock, separada a propósito para poder probarla sin AWS."""
    verbos = VERBOS.get(idioma, VERBOS["es"])
    dominios = DOMINIOS.get(idioma, DOMINIOS["es"])
    hojas = HOJAS.get(idioma, HOJAS["es"])

    lineas: list[str] = []
    for v in verbos:
        doms = ", ".join(f'"{d}" ({dominios[d]["label"]})' for d in v["dominios"])
        lineas.append(f'Verbo "{v["id"]}" ({v["label"]}) -- dominios disponibles: {doms}')
    lineas.append("")
    for dom_id, lista in hojas.items():
        hojas_texto = ", ".join(f'"{h["id"]}" ({h["label"]})' for h in lista)
        lineas.append(f'Dominio "{dom_id}" ({dominios[dom_id]["label"]}) -- hojas: {hojas_texto}')
    return "\n".join(lineas)


def sugerir_categoria(descripcion_persona: str, idioma: str = "es") -> SugerenciaCategoria:
    """Busca, entre las categorías existentes, cuál encaja mejor con lo
    que la persona describió -- ver docstring del módulo. Nunca lanza:
    si la llamada al modelo falla, o si sugiere una combinación que no
    existe en la taxonomía real, devuelve `encontrada=False` con una
    explicación genérica en vez de propagar el error."""
    idioma_arbol = "en" if idioma == "en" else "es"
    _explicacion_generica = (
        "No pude buscar una sugerencia justo ahora -- elegí la categoría que te resulte más cercana y agregá el detalle."
        if idioma_arbol == "es"
        else "I couldn't look up a suggestion right now -- pick whichever category feels closest and add the detail."
    )

    plantilla = _PROMPT_EN if idioma_arbol == "en" else _PROMPT_ES
    prompt = plantilla.format(tabla=_tabla_categorias(idioma_arbol), descripcion=descripcion_persona)
    agente = Agent(model=crear_modelo_subagente(), callback_handler=None)
    try:
        resultado = agente(prompt, structured_output_model=SugerenciaCategoria)
        sugerencia = resultado.structured_output
    except Exception:  # noqa: BLE001 -- fallo real forzando la forma, no un caso esperado
        return SugerenciaCategoria(encontrada=False, explicacion=_explicacion_generica)

    if sugerencia is None:
        return SugerenciaCategoria(encontrada=False, explicacion=_explicacion_generica)
    if not sugerencia.encontrada:
        return sugerencia
    if not (sugerencia.verbo_id and sugerencia.dominio_id and sugerencia.hoja_id):
        return SugerenciaCategoria(encontrada=False, explicacion=sugerencia.explicacion)
    if buscar_hoja(idioma_arbol, sugerencia.verbo_id, sugerencia.dominio_id, sugerencia.hoja_id) is None:
        # El modelo sugirió una combinación que no existe -- no se
        # confía, se descarta como si no hubiera encontrado nada.
        return SugerenciaCategoria(encontrada=False, explicacion=sugerencia.explicacion)
    return sugerencia
