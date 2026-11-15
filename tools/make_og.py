"""Maakt tools/site_assets/og-eigen-domein.png: het deelplaatje (og.png, 1200 x 630) met onderaan het adres van het eigen domein in plaats
van "ned-61.com/windsurf-archief". build_site.py gebruikt het zodra EIGEN_DOMEIN aan staat (bereikplan, Domeindag). De rest van het
plaatje blijft pixel voor pixel gelijk: alleen de adresregel wordt overgeschilderd, in dezelfde letter, grootte en kleur.

Alleen opnieuw draaien als het adres of og.png verandert; nodig: Pillow en het lettertype Segoe UI (Windows).

    python tools/make_og.py [--adres windsurfarchief.nl]
"""
import argparse
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ASSETS = Path(__file__).resolve().parent / "site_assets"
FONT = "C:/Windows/Fonts/segoeui.ttf"
OUD = "ned-61.com/windsurf-archief"
REGEL = (80, 505, 1110, 580)   # het vlak van de adresregel, onder de grijze streep op y = 491


def inkt(im, box, bg):
    """Omhullende van alle pixels in box die duidelijk van de achtergrond afwijken."""
    px = im.load()
    xs, ys = [], []
    for y in range(box[1], box[3]):
        for x in range(box[0], box[2]):
            if sum(abs(a - b) for a, b in zip(px[x, y][:3], bg)) > 60: xs.append(x); ys.append(y)
    return min(xs), min(ys), max(xs), max(ys)


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--adres", default="windsurfarchief.nl"); a = ap.parse_args()
    im = Image.open(ASSETS / "og.png").convert("RGB")
    bg = im.getpixel((40, 540))
    x0, y0, x1, y1 = inkt(im, REGEL, bg)
    # kleur: de donkerste pixel van de oude tekst; grootte: zo dat de oude tekst in Segoe UI precies even breed wordt
    kleur = min((im.getpixel((x, y)) for x in range(x0, x1 + 1) for y in range(y0, y1 + 1)), key=sum)
    size = min(range(16, 60), key=lambda s: abs(ImageFont.truetype(FONT, s).getbbox(OUD)[2] - ImageFont.truetype(FONT, s).getbbox(OUD)[0] - (x1 - x0 + 1)))
    font = ImageFont.truetype(FONT, size)
    ox, oy = font.getbbox(OUD)[:2]          # waar de inkt begint ten opzichte van het tekenpunt
    d = ImageDraw.Draw(im)
    d.rectangle(REGEL, fill=bg)
    d.text((x0 - ox, y0 - oy), a.adres, font=font, fill=kleur)
    uit = ASSETS / "og-eigen-domein.png"
    im.save(uit, optimize=True)
    print(f"{uit.name}: '{a.adres}' in Segoe UI {size} px, kleur {kleur}, op ({x0}, {y0})")


if __name__ == "__main__":
    main()
