"""Maakt het icoontje van de site (een wit zeil op het blauw van de links) in tools/site_assets/: favicon.svg, favicon.ico
(16, 32 en 48 pixels), icon-192.png en apple-touch-icon.png (180). build_site.py kopieert ze naar de hoofdmap van de site.
Alleen opnieuw draaien als het ontwerp verandert; nodig: Pillow (pip install pillow). Plan: docs/bereikplan.md, B0.6.

    python tools/make_icons.py
"""
from pathlib import Path

from PIL import Image, ImageDraw

ASSETS = Path(__file__).resolve().parent / "site_assets"
BLAUW, WIT = "#2b59c3", "#ffffff"

# Ontwerp op een raster van 64 bij 64: afgeronde achtergrond, mast, zeil met een bolle achterlijk en een gebogen plank.
SVG = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">
<rect width="64" height="64" rx="14" fill="{BLAUW}"/>
<path d="M26 9 C39 18 47 32 48 45 L26 47 Z" fill="{WIT}"/>
<rect x="21" y="8" width="3.5" height="42" rx="1.75" fill="{WIT}"/>
<path d="M12 53 Q32 58 52 52" stroke="{WIT}" stroke-width="4" fill="none" stroke-linecap="round"/>
</svg>
"""


def bezier(p0, p1, p2, p3, n=40):
    return [tuple((1 - t) ** 3 * a + 3 * (1 - t) ** 2 * t * b + 3 * (1 - t) * t ** 2 * c + t ** 3 * d for a, b, c, d in zip(p0, p1, p2, p3))
            for t in (i / n for i in range(n + 1))]


def quad(p0, p1, p2, n=30):
    return [tuple((1 - t) ** 2 * a + 2 * (1 - t) * t * b + t ** 2 * c for a, b, c in zip(p0, p1, p2)) for t in (i / n for i in range(n + 1))]


def teken(size):
    k = 8                                    # eerst groot tekenen en dan verkleinen: gladde randen
    s = size * k / 64
    im = Image.new("RGBA", (size * k, size * k), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    sc = lambda pts: [(x * s, y * s) for x, y in pts]
    d.rounded_rectangle([0, 0, 64 * s - 1, 64 * s - 1], radius=14 * s, fill=BLAUW)
    d.polygon(sc(bezier((26, 9), (39, 18), (47, 32), (48, 45)) + [(26, 47)]), fill=WIT)
    d.rounded_rectangle(sc([(21, 8), (24.5, 50)]), radius=1.75 * s, fill=WIT)
    plank = sc(quad((12, 53), (32, 58), (52, 52)))
    d.line(plank, fill=WIT, width=round(4 * s), joint="curve")
    for x, y in (plank[0], plank[-1]):
        r = 2 * s; d.ellipse([x - r, y - r, x + r, y + r], fill=WIT)
    return im.resize((size, size), Image.LANCZOS)


def main():
    (ASSETS / "favicon.svg").write_text(SVG, encoding="utf-8")
    teken(48).save(ASSETS / "favicon.ico", sizes=[(16, 16), (32, 32), (48, 48)])
    teken(192).save(ASSETS / "icon-192.png", optimize=True)
    teken(180).save(ASSETS / "apple-touch-icon.png", optimize=True)
    print("icoontjes geschreven in", ASSETS)


if __name__ == "__main__":
    main()
