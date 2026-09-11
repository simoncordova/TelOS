"""Modelos Pydantic de request/response de la API -- separados de
agents/tools a propósito: son el contrato HTTP con el frontend Node.js,
no vocabulario de dominio (ver docs/agente-proposito-de-vida-prompts.md
para el vocabulario real, que sigue viviendo solo en agents/tools)."""

from pydantic import BaseModel


class AbrirSesionRequest(BaseModel):
    idioma: str = "es"


class EnviarMensajeRequest(BaseModel):
    texto: str
    idioma: str = "es"


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
