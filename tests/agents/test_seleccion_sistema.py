"""Cobertura de agents/orquestador.py::SesionTelos.confirmar_seleccion_sistema
-- el selector visual de Fase 4 (Estratega de Sistemas). Sin AWS, sin
Bedrock -- a diferencia de Fase 1, el cierre de Fase 4 TAMPOCO invoca al
modelo (son 4 respuestas fijas, _formatear_sistema arma el texto por
código), así que acá sí se prueba el camino completo de cierre, incluido
el guardado real en la ficha (backend local)."""

import os

os.environ.setdefault("TELOS_FICHA_BACKEND", "local")

import pytest

from agents.orquestador import SesionTelos, extraer_accion_y_cuando
from tools.ficha import borrar_ficha_usuario, guardar_ficha_usuario_fusionada, leer_ficha_usuario
from tools.selecciones_estructuradas import borrar_selecciones_estructuradas


def _sesion_fase_4(usuario_id: str) -> SesionTelos:
    borrar_ficha_usuario(usuario_id)
    borrar_selecciones_estructuradas(usuario_id)
    sesion = SesionTelos(usuario_id, idioma="es")
    sesion.fase_actual = 4
    return sesion


def test_confirmar_una_pregunta_no_cierra():
    sesion = _sesion_fase_4("test_seleccion_sistema_u1")
    resultado = sesion.confirmar_seleccion_sistema("accion", "ejercicio_cardio")
    assert resultado["cerrado"] is False
    assert resultado["mensaje_cierre"] is None
    assert set(resultado["respuestas"].keys()) == {"accion"}


def test_confirmar_las_4_cierra_sin_invocar_bedrock():
    usuario_id = "test_seleccion_sistema_u2"
    sesion = _sesion_fase_4(usuario_id)
    sesion.confirmar_seleccion_sistema("accion", "ejercicio_cardio")
    sesion.confirmar_seleccion_sistema("cuando_donde", "manana_temprano_ctx1")
    sesion.confirmar_seleccion_sistema("metrica", "binario_si_no")
    resultado = sesion.confirmar_seleccion_sistema(
        "obstaculo", "llego_sin_energia", detalle_libre="Salgo a caminar 5 minutos igual"
    )
    assert resultado["cerrado"] is True
    assert resultado["mensaje_cierre"]
    assert sesion.fase_actual == 5

    ficha = leer_ficha_usuario(usuario_id)
    sistema = ficha["actual"]["datos"]["sistema"]
    assert "Acción: Ejercicio cardiovascular" in sistema
    assert "Cuándo/dónde: Todos los días, en casa" in sistema
    assert "Métrica: Sí o no" in sistema
    assert "Obstáculo: Llego sin energía -- Salgo a caminar 5 minutos igual" in sistema


def test_obstaculo_sin_detalle_libre_usa_plan_por_defecto():
    # Si la persona deja el campo de plan vacío, se completa por código
    # con FALLBACK_PLAN_OBSTACULO -- nunca queda la línea sin plan.
    usuario_id = "test_seleccion_sistema_u7"
    sesion = _sesion_fase_4(usuario_id)
    sesion.confirmar_seleccion_sistema("accion", "ejercicio_cardio")
    sesion.confirmar_seleccion_sistema("cuando_donde", "manana_temprano_ctx1")
    sesion.confirmar_seleccion_sistema("metrica", "binario_si_no")
    sesion.confirmar_seleccion_sistema("obstaculo", "llego_sin_energia")

    ficha = leer_ficha_usuario(usuario_id)
    sistema = ficha["actual"]["datos"]["sistema"]
    assert "Obstáculo: Llego sin energía -- hacer solo los primeros quince minutos" in sistema


def test_confirmar_seleccion_sistema_fuera_de_fase_4_lanza():
    sesion = _sesion_fase_4("test_seleccion_sistema_u3")
    sesion.fase_actual = 1
    with pytest.raises(ValueError):
        sesion.confirmar_seleccion_sistema("accion", "ejercicio_cardio")


def test_confirmar_seleccion_sistema_pregunta_desconocida_lanza():
    sesion = _sesion_fase_4("test_seleccion_sistema_u4")
    with pytest.raises(ValueError):
        sesion.confirmar_seleccion_sistema("pregunta_rara", "ejercicio_cardio")


def test_confirmar_seleccion_sistema_nodo_desconocido_lanza():
    sesion = _sesion_fase_4("test_seleccion_sistema_u5")
    with pytest.raises(ValueError):
        sesion.confirmar_seleccion_sistema("accion", "id_que_no_existe")


def test_proposito_se_hereda_de_version_anterior():
    usuario_id = "test_seleccion_sistema_u6"
    borrar_ficha_usuario(usuario_id)
    borrar_selecciones_estructuradas(usuario_id)
    guardar_ficha_usuario_fusionada(usuario_id, {"proposito": "Ayudar a otros a crecer"}, fase=3, motivo_version="test")
    sesion = SesionTelos(usuario_id, idioma="es")
    sesion.fase_actual = 4
    sesion.confirmar_seleccion_sistema("accion", "ejercicio_cardio")
    sesion.confirmar_seleccion_sistema("cuando_donde", "manana_temprano_ctx1")
    sesion.confirmar_seleccion_sistema("metrica", "binario_si_no")
    sesion.confirmar_seleccion_sistema("obstaculo", "llego_sin_energia")
    ficha = leer_ficha_usuario(usuario_id)
    assert ficha["actual"]["datos"]["proposito"] == "Ayudar a otros a crecer"
    assert "sistema" in ficha["actual"]["datos"]


def test_extraer_accion_y_cuando_texto_es():
    # Inverso de _formatear_sistema -- ver agents/orquestador.py::
    # extraer_accion_y_cuando, usado por api/main.py para agendar el
    # evento de calendario sin necesitar los datos crudos de Fase 4.
    sistema_texto = (
        "Acción: Ejercicio cardiovascular\n"
        "Cuándo/dónde: Todos los días, en casa\n"
        "Métrica: Sí o no\n"
        "Obstáculo: Llego sin energía -- Recordar mi propósito"
    )
    accion, cuando = extraer_accion_y_cuando(sistema_texto)
    assert accion == "Ejercicio cardiovascular"
    assert cuando == "Todos los días, en casa"


def test_extraer_accion_y_cuando_texto_en():
    sistema_texto = "Action: Journaling\nWhen/where: Every night, at home\nMetric: Yes or no\nObstacle: --"
    accion, cuando = extraer_accion_y_cuando(sistema_texto)
    assert accion == "Journaling"
    assert cuando == "Every night, at home"


def test_extraer_accion_y_cuando_texto_no_reconocido_no_lanza():
    accion, cuando = extraer_accion_y_cuando("esto no sigue el formato esperado")
    assert accion == ""
    assert cuando == ""


def test_extraer_accion_y_cuando_texto_vacio_no_lanza():
    assert extraer_accion_y_cuando("") == ("", "")
    assert extraer_accion_y_cuando(None) == ("", "")
