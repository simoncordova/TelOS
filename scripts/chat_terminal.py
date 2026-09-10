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
from tools.ficha import leer_ficha_usuario  # noqa: E402

_NOMBRES_FASE = {
    1: "Explorador",
    2: "Sintetizador",
    3: "Coach de Validación",
    4: "Estratega de Sistemas",
    5: "Seguimiento",
}


def main() -> None:
    usuario_id = sys.argv[1] if len(sys.argv) > 1 else "prueba-cloudshell"
    idioma = sys.argv[2] if len(sys.argv) > 2 else "es"
    sesion = SesionTelos(usuario_id, idioma=idioma)

    print(f"--- Telos (usuario_id={usuario_id}, idioma={idioma}) ---")
    print(f"Fase inicial: {_NOMBRES_FASE.get(sesion.fase_actual, sesion.fase_actual)}")
    print("Escribí 'salir' para terminar, 'ficha' para ver el estado guardado.\n")

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

        respuesta = sesion.enviar_mensaje(texto)
        nombre_fase = _NOMBRES_FASE.get(sesion.fase_actual, sesion.fase_actual)
        print(f"\nTelos [{nombre_fase}]: {respuesta}\n")


if __name__ == "__main__":
    main()
