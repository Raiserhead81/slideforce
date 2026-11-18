#!/usr/bin/env python3
"""Erzeugt die BRIDGE28-Logo-PNGs (1:1-Port aus bridge28-handbuch/b28-folien.js).

Quelle: bridgeMotiv() / bridgeMini() — stilisierte Bogenbruecke:
goldener Spannbogen (quadr. Bezier M 12 40 Q 100 10 188 40), 2 navy Pylonen,
5 feine Vertikalseile, Deckslinie y=62, 2 Wasser-Wellen; dazu der goldene
Schriftzug BRIDGE28 (nur im grossen Logo). Mini = monochrom navy, ohne Wellen.

Ausgabe: slideforce/assets/bridge_logo.png (Titelfolie)
         slideforce/assets/bridge_mini.png (Footer jeder Folie)
"""
import sys
from pathlib import Path

import cairosvg

ASSETS = Path(__file__).resolve().parent.parent / "slideforce" / "assets"
NAVY = "#002846"
GOLD_BOGEN = "#f0b25a"   # so steht es in b28-folien.js (Bridge-Motiv)
GOLD_WORT = "#C9A961"    # Palette-GOLD fuer den Schriftzug


def bogen_y(x, y0=40, yc=10):
    """Quadratische Bezier y(x) — exakt wie bogenY() in b28-folien.js."""
    u = (x - 12) / 176
    a, b, c = (1 - u) ** 2, 2 * u * (1 - u), u * u
    return a * y0 + b * yc + c * y0


def motiv_svg():
    seil_x = [26, 52, 100, 148, 174]
    seile = "".join(
        f'<line x1="{sx}" y1="{bogen_y(sx):.1f}" x2="{sx}" y2="62" '
        f'stroke="{NAVY}" stroke-width="1.4" opacity=".72"/>' for sx in seil_x)

    def welle(y, op):
        return (f'<path d="M 16 {y} q 14 -5 28 0 t 28 0 t 28 0 t 28 0 '
                f't 28 0 t 28 0" fill="none" stroke="{NAVY}" '
                f'stroke-width="1.3" opacity="{op}"/>')

    body = (
        welle(74, ".5") + welle(81, ".3")                                   # Wasser
        + f'<line x1="8" y1="62" x2="192" y2="62" stroke="{NAVY}" '
          f'stroke-width="2" stroke-linecap="round"/>'                      # Deck
        + seile                                                            # 5 Seile
        + f'<line x1="68" y1="{bogen_y(68):.1f}" x2="68" y2="62" '
          f'stroke="{NAVY}" stroke-width="2"/>'                            # Pylon 1
        + f'<line x1="132" y1="{bogen_y(132):.1f}" x2="132" y2="62" '
          f'stroke="{NAVY}" stroke-width="2"/>'                            # Pylon 2
        + f'<path d="M 12 40 Q 100 10 188 40" fill="none" stroke="{GOLD_BOGEN}" '
          f'stroke-width="3" stroke-linecap="round"/>'                     # Spannbogen
    )
    wort = (f'<text x="99" y="113" text-anchor="middle" '
            f'font-family="Arial, Helvetica, sans-serif" font-size="19" '
            f'font-weight="700" letter-spacing="3.5" fill="{GOLD_WORT}">BRIDGE28</text>')
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="200" height="120" '
            f'viewBox="0 0 200 120">{body}{wort}</svg>')


def mini_svg():
    """bridgeMini() 1:1: monochrom navy, Bogen/Deck/Pylonen dick genug fuer 16px."""
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" width="64" height="26" viewBox="0 0 64 26">'
        f'<path d="M 3 15 Q 32 1 61 15" fill="none" stroke="{NAVY}" '
        f'stroke-width="4.6" stroke-linecap="round"/>'
        f'<line x1="22" y1="9.5" x2="22" y2="23" stroke="{NAVY}" stroke-width="3"/>'
        f'<line x1="42" y1="9.5" x2="42" y2="23" stroke="{NAVY}" stroke-width="3"/>'
        f'<line x1="1" y1="23" x2="63" y2="23" stroke="{NAVY}" stroke-width="4" '
        f'stroke-linecap="round"/></svg>'
    )


def main():
    ASSETS.mkdir(parents=True, exist_ok=True)
    (ASSETS / "bridge_logo.svg").write_text(motiv_svg())
    (ASSETS / "bridge_mini.svg").write_text(mini_svg())
    cairosvg.svg2png(bytestring=motiv_svg().encode(), write_to=str(ASSETS / "bridge_logo.png"),
                     output_width=760)
    cairosvg.svg2png(bytestring=mini_svg().encode(), write_to=str(ASSETS / "bridge_mini.png"),
                     output_width=256)
    for f in ("bridge_logo.png", "bridge_mini.png"):
        print(f, (ASSETS / f).stat().st_size, "Bytes")
    return 0


if __name__ == "__main__":
    sys.exit(main())
