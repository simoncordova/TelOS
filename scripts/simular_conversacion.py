"""Simula una conversación completa contra Bedrock real, sin manos --
para diagnosticar el flujo sin depender de probarlo a mano en el
navegador turno por turno (varias rondas de bugs solo aparecieron
después de una conversación larga y específica, imposible de reproducir
rápido a mano). Esto NO mockea el modelo -- sigue siendo Bedrock real,
las mismas credenciales de scripts/chat_terminal.py -- mockea el lado de
la PERSONA: un guion fijo de respuestas que se mandan una por una, sin
esperar input humano.

Uso:
    python scripts/simular_conversacion.py [usuario_id] [idioma: es|en] [guion.json]

Sin guion.json usa _GUION_DEFAULT de abajo -- una conversación de
exploración completa (perfil "inventor de apps", el mismo tipo que
destapó los bugs reales de cierre falso y transición). Un guion.json
propio es solo una lista de strings en orden, ej.:
    ["cuando estaba creando una app nueva", "...", ...]

Cada turno imprime, además del texto de la respuesta:
  - la fase antes y después (para ver cuándo cascadea de verdad, no
    cuándo el texto *dice* que cascadeó)
  - si la tool guardar_ficha_usuario se ejecutó en esa invocación
    puntual (se lee del mismo contenedor que usa el Orquestador, no de
    una relectura de la ficha -- ver agents/orquestador.py)
  - si el texto de la respuesta "suena" a que ya guardó (la misma regex
    que agents/orquestador.py usa para forzar un reintento) -- si esto
    aparece en TRUE pero "guardó" en False, es una alerta directa de que
    el bug de cierre falso reapareció y el freno no lo agarró
  - las claves de `datos` en la ficha después del turno (para el bug de
    "las cajas de texto no se llenan": si el Sintetizador dice que
    guardó y "proposito" no aparece acá, el bug sigue vivo)

Requiere credenciales de AWS reales configuradas (boto3 las toma del
entorno, igual que chat_terminal.py) -- sin ellas, cada turno falla con
el mismo NoCredentialsError que cualquier llamada real a Bedrock.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agents.orquestador import _FRASE_CIERRE_FALSO, SesionTelos  # noqa: E402
from agents.seguimiento import construir_vista_resumen  # noqa: E402
from tools.ficha import leer_ficha_usuario  # noqa: E402

_NOMBRES_FASE = {
    0: "Bienvenida",
    1: "Explorador",
    2: "Sintetizador",
    3: "Coach de Validación",
    4: "Estratega de Sistemas",
    5: "Seguimiento",
}

# Perfil "inventor de apps" -- el mismo tipo de conversación que destapó
# los bugs reales de cierre falso y transición rota. Las primeras 6
# respuestas cubren los 5 ejes del Explorador (con margen); después
# sigue con una elección de candidato, evidencia para el Coach, y
# respuestas para el Estratega (una a propósito vaga, "hacer ejercicio",
# para confirmar que la rechaza con cariño y pide precisión).
_GUION_DEFAULT = [
    "Mark",  # respuesta al Paso 0 (nombre)
    "cuando estaba creando una aplicacion nueva",
    "imaginar como la usarian, las funcionalidades que necesitarian, la experiencia que queria brindarles, el impacto que les daria esto en sus vidas",
    (
        "seguiria inventando cosas, me gusta me mueve, de hecho con dinero tendria menos "
        "limitantes, podria contratar personas que me ayudaran con sus especialidades, y "
        "compraria recursos que me facilitaran no solo la ideacion sino tambien la "
        "construccion, y ya no estaria limitado a lo digital tambien crearia cosas fisicas"
    ),
    "validar mis ideas con el publico objetivo me da miedo y verguenza, el posible hecho de que rechacen la idea, o que alguien me la robe",
    "como el gran inventor, que continuo generando cosas para el mundo, como un steve jobs o thomas edison",
    "mi honestidad, lealtad, y responsabilidad con mi familia",
    # A partir de acá ya debería haber cascadeado a Sintetizador.
    "el primero me resuena mas",
    "si, tiene sentido",
    "cuando lance mi primera app y la uso mas de 100 personas",
    "ok",
    "hacer ejercicio todos los dias",  # a propósito vago, para el Estratega
    "a las 7am en el gimnasio de mi barrio, 30 minutos",
    "si marco el checkbox en mi app de habitos",
    "que me quede dormido, en ese caso lo hago apenas me levanto sin excusas",
]


def _resumen_ficha(usuario_id: str) -> dict:
    ficha = leer_ficha_usuario(usuario_id)
    if not ficha["existe"]:
        return {}
    return (ficha["actual"] or {}).get("datos", {}) or {}


def _imprimir_turno(sesion: SesionTelos, patron, fase_antes: int, texto: str, opciones: list[str]) -> None:
    fase_despues = sesion.fase_actual
    nombre_antes = _NOMBRES_FASE.get(fase_antes, fase_antes)
    cambio = f" -> {_NOMBRES_FASE.get(fase_despues, fase_despues)}" if fase_despues != fase_antes else ""
    guardo = bool(sesion._contenedor_guardado)
    sonaba_a_guardado = bool(patron.search(texto))

    print(f"\n[{nombre_antes}{cambio}] {texto}")
    if opciones:
        print(f"   opciones ofrecidas: {opciones}")
    print(f"   guardar_ficha_usuario se ejecutó: {guardo}")
    if sonaba_a_guardado and not guardo:
        print("   !!! ALERTA: el texto suena a que guardó, pero la tool NO se ejecutó (cierre falso)")


def main() -> None:
    usuario_id = sys.argv[1] if len(sys.argv) > 1 else "prueba-simulada"
    idioma = sys.argv[2] if len(sys.argv) > 2 else "es"
    ruta_guion = sys.argv[3] if len(sys.argv) > 3 else None
    guion = json.loads(Path(ruta_guion).read_text(encoding="utf-8")) if ruta_guion else _GUION_DEFAULT
    patron = _FRASE_CIERRE_FALSO.get(idioma, _FRASE_CIERRE_FALSO["es"])

    print(f"--- Simulación Telos (usuario_id={usuario_id}, idioma={idioma}, {len(guion)} turnos) ---")

    sesion = SesionTelos(usuario_id, idioma=idioma)

    # La Vista de resumen de Fase 5 ya no viene en el texto del agente
    # (ver agents/seguimiento.py) -- se muestra aparte, con código.
    if sesion.fase_actual == 5:
        ficha = leer_ficha_usuario(usuario_id)
        print("\n--- Tu resumen ---")
        print(construir_vista_resumen(ficha["actual"], idioma, sesion.nombre))
        print("------------------")

    fase_previa = sesion.fase_actual
    for fase, texto, opciones in sesion.abrir_conversacion():
        _imprimir_turno(sesion, patron, fase_previa, texto, opciones)
        fase_previa = sesion.fase_actual

    for entrada in guion:
        print(f"\n>>> Usuario: {entrada}")
        fase_previa = sesion.fase_actual
        for fase, texto, opciones in sesion.enviar_mensaje(entrada):
            _imprimir_turno(sesion, patron, fase_previa, texto, opciones)
            fase_previa = sesion.fase_actual

        datos = _resumen_ficha(usuario_id)
        print(f"   ficha.datos claves: {sorted(datos.keys())}")

    print("\n--- Fin de la simulación ---")
    print(f"Fase final: {_NOMBRES_FASE.get(sesion.fase_actual, sesion.fase_actual)}")
    print(f"Nombre capturado: {sesion.nombre}")
    print(f"Claves finales en ficha.datos: {sorted(_resumen_ficha(usuario_id).keys())}")


if __name__ == "__main__":
    main()
