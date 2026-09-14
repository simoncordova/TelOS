"""Cobertura de agents/orquestador.py::SesionTelos.confirmar_proposito_elegido
-- el cierre determinístico de Fase 2 por click en una tarjeta de
candidato (ver Sintesis/CandidatosProposito.tsx), pedido explícito del
dueño del producto (14/09/2026): elegir una tarjeta ya es un evento
inequívoco, no hace falta otra invocación real a Bedrock para que el
Sintetizador "confirme" algo que la interfaz ya sabe con certeza. Sin
AWS, sin Bedrock -- mismo criterio que el resto del proyecto para no
depender de Bedrock en tests."""

import os

os.environ.setdefault("TELOS_FICHA_BACKEND", "local")

import pytest

from agents.orquestador import SesionTelos
from tools.ficha import leer_ficha_usuario
from tools.selecciones_estructuradas import (
    borrar_selecciones_estructuradas,
    guardar_selecciones_estructuradas,
    leer_selecciones_estructuradas,
)

_CANDIDATOS = [
    {"frase": "Enseñar con el ejemplo", "explicacion": "e1", "ejemplo": "j1"},
    {"frase": "Construir puentes", "explicacion": "e2", "ejemplo": "j2"},
]


def _sesion_en_fase_2_con_candidatos(usuario_id: str) -> SesionTelos:
    borrar_selecciones_estructuradas(usuario_id)
    sesion = SesionTelos(usuario_id, idioma="es")
    sesion.fase_actual = 2  # mismo atajo que otros tests -- ver test_seleccion_ikigai.py
    guardar_selecciones_estructuradas(usuario_id, {"fase": 2, "candidatos": list(_CANDIDATOS)})
    return sesion


def test_elegir_un_candidato_presentado_cierra_la_fase():
    usuario_id = "test_confirmar_proposito_u1"
    sesion = _sesion_en_fase_2_con_candidatos(usuario_id)

    resultado = sesion.confirmar_proposito_elegido("Construir puentes")

    assert resultado["cerrado"] is True
    assert resultado["mensaje_cierre"]
    # Pasa directo a Fase 4 (construir el sistema) -- Fase 3 (Coach de
    # Validación) se eliminó del flujo, ver agents/orquestador.py.
    assert sesion.fase_actual == 4


def test_elegir_un_candidato_guarda_el_proposito_en_la_ficha():
    usuario_id = "test_confirmar_proposito_u2"
    sesion = _sesion_en_fase_2_con_candidatos(usuario_id)

    sesion.confirmar_proposito_elegido("Enseñar con el ejemplo")

    ficha = leer_ficha_usuario(usuario_id)
    assert ficha["existe"] is True
    assert ficha["actual"]["datos"]["proposito"] == "Enseñar con el ejemplo"


def test_elegir_un_candidato_borra_el_progreso_transitorio():
    usuario_id = "test_confirmar_proposito_u3"
    sesion = _sesion_en_fase_2_con_candidatos(usuario_id)

    sesion.confirmar_proposito_elegido("Construir puentes")

    # {} (progreso vacío) es la representación de "nada guardado" -- ver
    # tools/selecciones_estructuradas_local.py::leer_selecciones_estructuradas.
    assert not leer_selecciones_estructuradas(usuario_id)


def test_frase_que_no_fue_presentada_lanza_value_error():
    usuario_id = "test_confirmar_proposito_u4"
    sesion = _sesion_en_fase_2_con_candidatos(usuario_id)

    with pytest.raises(ValueError):
        sesion.confirmar_proposito_elegido("Un propósito que el Sintetizador nunca presentó")

    # No cerró nada -- sigue en Fase 2, sin propósito guardado.
    assert sesion.fase_actual == 2
    assert leer_ficha_usuario(usuario_id)["existe"] is False


def test_fase_actual_distinta_de_2_lanza_value_error():
    usuario_id = "test_confirmar_proposito_u5"
    borrar_selecciones_estructuradas(usuario_id)
    sesion = SesionTelos(usuario_id, idioma="es")
    sesion.fase_actual = 4
    guardar_selecciones_estructuradas(usuario_id, {"fase": 2, "candidatos": list(_CANDIDATOS)})

    with pytest.raises(ValueError):
        sesion.confirmar_proposito_elegido("Construir puentes")
