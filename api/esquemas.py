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
    """Fases 1, 3 y 4: una opción confirmada en un árbol o selector de
    categorías (tools/categorias_ikigai.py, tools/categorias_validacion.py
    o tools/categorias_sistema.py -- ver agents/orquestador.py::
    SesionTelos.confirmar_seleccion/confirmar_seleccion_validacion/
    confirmar_seleccion_sistema). `ruta`/`dimensiones` NO se mandan desde
    acá -- el backend las deriva de la taxonomía, nunca confía en lo que
    mande el cliente. `nodo_id` sirve tanto para un id de nodo de árbol
    (Fases 1/4) como para un `area_id` del selector plano de Fase 3 --
    mismo campo, incluso el shape del origen sea distinto, porque
    conceptualmente es siempre "qué opción se eligió". `pregunta_id` es
    obligatorio solo cuando `fase=4` (cuál de las 4 preguntas fijas está
    respondiendo -- ver tools/categorias_sistema.py::PREGUNTAS_SISTEMA_IDS)."""

    fase: int = 1
    nodo_id: str
    idioma: str = "en"
    pregunta_id: str | None = None
    detalle_libre: str | None = None


class SeleccionConfirmadaResponse(BaseModel):
    """`cobertura` (Fase 1), `respuestas` (Fase 4) y `etapa`/
    `mensaje_apertura_refinado` (Fase 3) son mutuamente excluyentes --
    cuál viene poblada depende de `fase` en el request. Fase 3 nunca
    cierra a través de este endpoint (`cerrado` siempre False, ver
    agents/orquestador.py::SesionTelos.confirmar_seleccion_validacion)
    -- su cierre real pasa por `POST /api/sesion/mensaje` una vez en
    etapa "refinando", que sí es una conversación de texto."""

    cobertura: dict[str, int] | None = None
    respuestas: dict[str, dict] | None = None
    etapa: str | None = None
    mensaje_apertura_refinado: str | None = None
    cerrado: bool
    mensaje_cierre: str | None
    fase_actual: int


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
