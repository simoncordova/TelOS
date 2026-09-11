"""Borra TODOS los datos de un usuario_id -- ficha (todas las versiones),
turnos de conversación (las 5 fases) y nombre de perfil. Pensado para
resetear cuentas de prueba contaminadas por rondas de testing viejas
(varios bugs reales de esta semana quedaron mezclados con conversación
real en la misma cuenta, precargándose en cada sesión nueva y haciendo
más difícil saber si un síntoma es un bug nuevo o solo historial
confuso) -- no es una función de "elimina tus datos" para usuarios
reales todavía (eso sigue siendo P2 en el plan; esto es una herramienta
de desarrollo).

No toca los eventos del guardrail de crisis (tools/crisis.py) a
propósito: ese registro es de seguridad/auditoría, no algo que un reset
de cuenta de prueba deba poder borrar.

Uso:
    python scripts/borrar_usuario.py <usuario_id> [-y]

Sin -y, pide confirmación escribiendo el usuario_id de nuevo (operación
irreversible, mismo criterio de confirmación que cualquier borrado real
del proyecto). Usa el mismo TELOS_FICHA_BACKEND que el resto de las
herramientas -- local por default, agentcore si está seteado.
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tools.conversacion import borrar_turnos_usuario  # noqa: E402
from tools.ficha import borrar_ficha_usuario, leer_ficha_usuario  # noqa: E402
from tools.perfil import borrar_nombre_usuario, leer_nombre_usuario  # noqa: E402


def main() -> None:
    if len(sys.argv) < 2:
        print("Uso: python scripts/borrar_usuario.py <usuario_id> [-y]")
        sys.exit(1)

    usuario_id = sys.argv[1]
    confirmado = "-y" in sys.argv[2:] or "--si" in sys.argv[2:]
    backend = os.environ.get("TELOS_FICHA_BACKEND", "local")

    ficha = leer_ficha_usuario(usuario_id)
    nombre = leer_nombre_usuario(usuario_id)
    print(f"--- Borrar usuario_id={usuario_id!r} (backend={backend}) ---")
    print(f"Nombre guardado: {nombre!r}")
    print(f"Ficha existe: {ficha['existe']}" + (f" ({len(ficha['historial']) + 1} versiones)" if ficha["existe"] else ""))

    if not confirmado:
        respuesta = input(f"Esto borra TODO lo de '{usuario_id}' de forma irreversible. Escribí el usuario_id de nuevo para confirmar: ").strip()
        if respuesta != usuario_id:
            print("No coincide -- cancelado, no se borró nada.")
            sys.exit(1)

    borrar_ficha_usuario(usuario_id)
    borrar_turnos_usuario(usuario_id)
    borrar_nombre_usuario(usuario_id)
    print(f"Listo. '{usuario_id}' quedó como una cuenta nueva.")


if __name__ == "__main__":
    main()
