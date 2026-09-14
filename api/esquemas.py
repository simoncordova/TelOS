"""Modelos Pydantic de request/response de la API -- separados de
agents/tools a propósito: son el contrato HTTP con el frontend Node.js,
no vocabulario de dominio (ver docs/agente-proposito-de-vida-prompts.md
para el vocabulario real, que sigue viviendo solo en agents/tools)."""

from pydantic import BaseModel


class AbrirSesionRequest(BaseModel):
    idioma: str = "en"


class EnviarMensajeRequest(BaseModel):
    texto: str
    idioma: str = "en"


class ConfirmarSeleccionRequest(BaseModel):
    """Fases 1, 2 y 4: una opción confirmada en un árbol, un candidato
    de propósito o un selector de categorías (tools/categorias_ikigai.py
    o tools/categorias_sistema.py -- ver agents/orquestador.py::
    SesionTelos.confirmar_seleccion/confirmar_proposito_elegido/
    confirmar_seleccion_sistema). `ruta`/`dimensiones`/el contenido real
    del candidato NO se mandan desde acá -- el backend los deriva de la
    taxonomía o de lo que de verdad se le presentó a la persona, nunca
    confía en lo que mande el cliente. `nodo_id` sirve tanto para un id
    de nodo de árbol (Fase 1) como para la respuesta elegida de Fase 4,
    o la `frase` de un candidato de propósito de Fase 2 -- mismo campo,
    incluso el shape del origen sea distinto, porque conceptualmente es
    siempre "qué opción se eligió". `pregunta_id` es obligatorio solo
    cuando `fase=4` (cuál de las 4 preguntas fijas está respondiendo --
    ver tools/categorias_sistema.py::PREGUNTAS_SISTEMA_IDS).

    Fase 3 (Coach de Validación) usaba `fase=3` acá para su selector de
    evidencia -- se eliminó del flujo (ver docstring de
    agents/orquestador.py); `fase` ya no acepta ese valor."""

    fase: int = 1
    nodo_id: str
    idioma: str = "en"
    pregunta_id: str | None = None
    detalle_libre: str | None = None


class SeleccionConfirmadaResponse(BaseModel):
    """`cobertura` (Fase 1) y `respuestas` (Fase 4) son mutuamente
    excluyentes -- cuál viene poblada depende de `fase` en el request.
    `mostrar_valores` (Fase 1) es True exactamente en el turno donde se
    completa la 2da selección y todavía no se pasó por
    `POST /api/seleccion/valores` -- ahí el frontend debe mostrar el
    paso único de "tus valores" (ver agents/orquestador.py::SesionTelos.
    confirmar_seleccion). `puede_cerrar` (Fase 1) habilita el botón "Ver
    mi propósito" -- llegar al mínimo NO cierra la fase sola, la persona
    decide cuándo con `POST /api/seleccion/cerrar-fase1` (ver
    cerrar_fase_1_manual)."""

    cobertura: dict[str, int] | None = None
    respuestas: dict[str, dict] | None = None
    mostrar_valores: bool = False
    puede_cerrar: bool = False
    cerrado: bool
    mensaje_cierre: str | None
    fase_actual: int


class ConfirmarValoresRequest(BaseModel):
    """Fase 1: hasta MAX_VALORES valores elegidos de VALORES_DISPONIBLES
    (tools/categorias_ikigai.py) -- ver agents/orquestador.py::
    SesionTelos.confirmar_valores."""

    valores: list[str]
    idioma: str = "en"


class CerrarFase1Request(BaseModel):
    idioma: str = "en"


class SugerirCategoriaRequest(BaseModel):
    """Chat de apoyo de Fase 1 (ver ArbolSelector.tsx): la persona
    describe en texto libre qué quiere expresar y el backend busca, ENTRE
    LAS CATEGORÍAS QUE YA EXISTEN, la que mejor encaje -- ver
    agents/asistente_categorias.py. Nunca crea categorías nuevas."""

    descripcion: str
    idioma: str = "en"


class SugerenciaCategoriaResponse(BaseModel):
    """`verbo_id`/`dominio_id`/`hoja_id` solo vienen presentes cuando
    `encontrada=True`, y ya fueron re-validados contra la taxonomía real
    (ver agents/asistente_categorias.py::sugerir_categoria) -- el
    frontend puede usarlos directo para resaltar/navegar el árbol."""

    encontrada: bool
    verbo_id: str | None = None
    dominio_id: str | None = None
    hoja_id: str | None = None
    explicacion: str


class FichaVersion(BaseModel):
    fase: int
    datos: dict
    motivo_version: str
    fecha: str


class FichaResponse(BaseModel):
    existe: bool
    actual: FichaVersion | None
    historial: list[FichaVersion]
    racha: int
    vista_resumen: str
    nombre: str | None


class SuscripcionPushKeys(BaseModel):
    p256dh: str
    auth: str


class SuscripcionPushRequest(BaseModel):
    """Misma forma que PushSubscription.toJSON() en el navegador -- ver
    web/src/lib/push.ts."""

    endpoint: str
    keys: SuscripcionPushKeys


class EliminarSuscripcionPushRequest(BaseModel):
    endpoint: str


class EnviarPruebaPushRequest(BaseModel):
    idioma: str = "en"


class CrearEventoCalendarioResponse(BaseModel):
    """Respuesta de `POST /api/calendario/crear-evento` -- ver
    tools/calendario.py::crear_evento_calendario. `url_autorizacion`
    viene poblado (y `confirmado=False`) cuando todavía hace falta que
    la persona autorice el acceso a su Google Calendar -- el frontend
    lo muestra como un link real para abrir en una pestaña nueva, nunca
    parseado de `mensaje` (ese es solo el texto para mostrar, no la
    fuente de verdad del link)."""

    confirmado: bool
    mensaje: str
    url_autorizacion: str | None = None
