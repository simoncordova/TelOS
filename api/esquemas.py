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
    """Fase 1 y Fase 4: una hoja confirmada en un árbol de categorías
    (tools/categorias_ikigai.py o tools/categorias_sistema.py -- ver
    agents/orquestador.py::SesionTelos.confirmar_seleccion/
    confirmar_seleccion_sistema). `ruta`/`dimensiones` NO se mandan desde
    acá -- el backend las deriva de la taxonomía, nunca confía en lo que
    mande el cliente. `pregunta_id` es obligatorio solo cuando `fase=4`
    (cuál de las 4 preguntas fijas está respondiendo -- ver
    tools/categorias_sistema.py::PREGUNTAS_SISTEMA_IDS); Fase 1 no lo
    usa, su árbol es uno solo."""

    fase: int = 1
    nodo_id: str
    idioma: str = "en"
    pregunta_id: str | None = None
    detalle_libre: str | None = None


class SeleccionConfirmadaResponse(BaseModel):
    """`cobertura` (Fase 1) y `respuestas` (Fase 4) son mutuamente
    excluyentes -- cuál viene poblada depende de `fase` en el request."""

    cobertura: dict[str, int] | None = None
    respuestas: dict[str, dict] | None = None
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
