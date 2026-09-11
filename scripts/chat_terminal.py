"""Chat de terminal para probar los agentes sin la UI de Streamlit.

Pensado para validar rápido contra Bedrock real desde un lugar como
CloudShell, donde levantar Streamlit y abrirlo en un browser no es
práctico. Usa las mismas credenciales ambientales de la sesión (las que
ya tenga configuradas boto3) — no pide ni genera ninguna key.

Uso:
    python scripts/chat_terminal.py [usuario_id] [idioma: es|en]

Comandos dentro del chat: "ficha" muestra el estado guardado, "salir"
termina.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agents.orquestador import SesionTelos  # noqa: E402
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


def _imprimir(fase: int, parte: str, opciones: list[str]) -> None:
    nombre_fase = _NOMBRES_FASE.get(fase, fase)
    print(f"Telos [{nombre_fase}]: {parte}\n")
    if opciones:
        for i, opcion in enumerate(opciones, start=1):
            print(f"  {i}) {opcion}")
        print()


def main() -> None:
    usuario_id = sys.argv[1] if len(sys.argv) > 1 else "prueba-cloudshell"
    idioma = sys.argv[2] if len(sys.argv) > 2 else "es"
    sesion = SesionTelos(usuario_id, idioma=idioma)

    print(f"--- Telos (usuario_id={usuario_id}, idioma={idioma}) ---")
    print(f"Fase inicial: {_NOMBRES_FASE.get(sesion.fase_actual, sesion.fase_actual)}")
    print("Escribe 'salir' para terminar, 'ficha' para ver el estado guardado.\n")

    # La Vista de resumen de Fase 5 ya no viene en el texto del agente
    # (ver agents/seguimiento.py) -- se muestra aparte, con código, igual
    # que en ui/app.py.
    if sesion.fase_actual == 5:
        ficha = leer_ficha_usuario(usuario_id)
        print("--- Tu resumen ---")
        print(construir_vista_resumen(ficha["actual"], idioma, sesion.nombre))
        print("------------------\n")

    # El agente habla primero, siempre -- nueva conversación o retomada.
    for fase, parte, opciones in sesion.abrir_conversacion():
        _imprimir(fase, parte, opciones)

    while True:
        try:
            texto = input("Tú: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if not texto:
            continue
        if texto.lower() == "salir":
            break
        if texto.lower() == "ficha":
            print(leer_ficha_usuario(usuario_id))
            continue

        # Generador: si hay cambio de fase en este turno, imprime cada
        # mensaje apenas está listo (no espera a tener los dos juntos).
        for fase, parte, opciones in sesion.enviar_mensaje(texto):
            print()
            _imprimir(fase, parte, opciones)


if __name__ == "__main__":
    main()
