"""
Whisp — Icon Generator
Erzeugt whisp.ico (Multi-Size) via Pillow.
Ausführen: python inference/assets/whisp_icon.py
"""
from pathlib import Path
from PIL import Image, ImageDraw

OUT = Path(__file__).parent / "whisp.ico"


def make_icon(size: int) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d   = ImageDraw.Draw(img)
    s   = size

    # Hintergrund-Kreis — Indigo
    pad = max(1, s // 16)
    d.ellipse([pad, pad, s - pad, s - pad], fill=(99, 102, 241, 255))

    # Mikrofon-Körper (abgerundetes Rechteck)
    mx  = s // 2
    mw  = max(4, s // 5)      # halbe Breite
    mt  = max(2, s // 6)      # Abstand oben
    mb  = max(4, s * 55 // 100)  # unterende Körper
    r   = mw // 2             # Eckenradius

    d.rounded_rectangle(
        [mx - mw, mt, mx + mw, mb],
        radius=r,
        fill="white",
    )

    # Bogen (Mikrofon-Halterung)
    arc_t = mb - s // 8
    arc_b = mb + s // 5
    arc_l = mx - mw - max(2, s // 12)
    arc_r = mx + mw + max(2, s // 12)
    d.arc([arc_l, arc_t, arc_r, arc_b], 0, 180, fill="white", width=max(2, s // 20))

    # Stiel
    stiel_t = arc_b - max(2, s // 14)
    stiel_b = s - max(3, s // 6)
    lw = max(2, s // 20)
    d.line([mx, stiel_t, mx, stiel_b], fill="white", width=lw)

    # Basis-Linie
    base_w = mw + max(2, s // 10)
    d.line([mx - base_w, stiel_b, mx + base_w, stiel_b], fill="white", width=lw)

    return img


def build() -> None:
    sizes = [16, 24, 32, 48, 64, 128, 256]
    frames = [make_icon(s) for s in sizes]
    # .ico mit allen Größen speichern
    frames[0].save(
        OUT,
        format="ICO",
        sizes=[(s, s) for s in sizes],
        append_images=frames[1:],
    )
    print(f"Icon gespeichert: {OUT}  ({len(frames)} Größen)")


if __name__ == "__main__":
    build()
