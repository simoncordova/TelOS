"""Genera los íconos PWA de web/public/ (manifest.json) -- un sol sobre
un horizonte, mismo motivo que el "🧭"/la frase "el propósito no es una
meta, es un horizonte" del resto de la app. Se corre una sola vez a
mano, no en cada build (los PNG resultantes se commitean como cualquier
otro asset estático) -- necesita Pillow, que no está en ningún
requirements.txt del proyecto porque es una herramienta de desarrollo
puntual, no una dependencia de la app (`pip install Pillow` si hace
falta).

Uso:
    python scripts/generar_iconos.py
"""

from pathlib import Path

from PIL import Image, ImageDraw

_SALIDA = Path(__file__).resolve().parent.parent / "web" / "public"

_TERRACOTA = (224, 142, 109)
_BEIGE = (255, 251, 247)


def _dibujar_icono(tamano: int, margen_relativo: float) -> Image.Image:
    """`margen_relativo` deja aire alrededor del dibujo -- los íconos
    "maskable" de Android recortan hasta un ~20% del borde, así que ese
    caso necesita más margen que un ícono normal (favicon/apple-touch)."""
    img = Image.new("RGB", (tamano, tamano), _TERRACOTA)
    dibujo = ImageDraw.Draw(img)

    margen = int(tamano * margen_relativo)
    y_horizonte = tamano * 0.6

    radio_sol = tamano * 0.18
    cx, cy = tamano / 2, y_horizonte - radio_sol  # el sol apoya justo sobre la línea, no flota

    dibujo.line([(margen, y_horizonte), (tamano - margen, y_horizonte)], fill=_BEIGE, width=max(2, tamano // 40))
    dibujo.ellipse([cx - radio_sol, cy - radio_sol, cx + radio_sol, cy + radio_sol], fill=_BEIGE)

    return img


def main() -> None:
    _SALIDA.mkdir(parents=True, exist_ok=True)

    _dibujar_icono(192, margen_relativo=0.12).save(_SALIDA / "icon-192.png")
    _dibujar_icono(512, margen_relativo=0.12).save(_SALIDA / "icon-512.png")
    # Maskable: más margen, para que el recorte adaptativo de Android no
    # se coma el sol ni el horizonte.
    _dibujar_icono(512, margen_relativo=0.22).save(_SALIDA / "icon-maskable-512.png")

    print(f"Íconos generados en {_SALIDA}")


if __name__ == "__main__":
    main()
