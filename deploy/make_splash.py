"""Erzeugt die Plymouth-Splash-Grafik fuer den CUSHMAN-Bootscreen.

Statisches Pendant zum In-App-Splash (ui/splash.py): amberfarbener Schriftzug
"CUSHMAN" mit dezentem Vertikal-Glanz auf fast schwarzem Cockpit-Hintergrund,
darunter die Subline "RUNGE ENGINEERING". Aufloesung passend zum 1600x600-Display.

Ausgabe: deploy/plymouth/cushman/splash.png

Aufruf:  python3 deploy/make_splash.py
"""

import os

from PIL import Image, ImageDraw, ImageFont

# --- Geometrie / Farben (gespiegelt aus ui/theme.py) ----------------------
W, H = 1600, 600
BG_DEEP = (11, 14, 18)          # #0b0e12
AMBER = (255, 158, 44)          # #ff9e2c
AMBER_HI = (255, 192, 97)       # #ffc061 -- Glanzkante
TEXT_DIM = (120, 132, 145)      # #788491 -- Subline

LOGO = "CUSHMAN"
SUBTITLE = "RUNGE ENGINEERING"

UBUNTU = "/usr/share/fonts/truetype/ubuntu/Ubuntu[wdth,wght].ttf"
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "plymouth", "cushman", "splash.png")


def _font(size, weight=700):
    f = ImageFont.truetype(UBUNTU, size)
    try:
        f.set_variation_by_axes([100, weight])  # wdth=100, wght
    except Exception:
        pass
    return f


def _centered(draw, text, font, cy, fill, tracking=0):
    """Zeichnet text horizontal zentriert auf Mittelhoehe cy, mit Letter-Spacing."""
    widths = [draw.textlength(ch, font=font) for ch in text]
    total = sum(widths) + tracking * (len(text) - 1)
    x = (W - total) / 2
    asc, desc = font.getmetrics()
    y = cy - (asc + desc) / 2
    for ch, w in zip(text, widths):
        draw.text((x, y), ch, font=font, fill=fill)
        x += w + tracking


def main():
    img = Image.new("RGB", (W, H), BG_DEEP)
    d = ImageDraw.Draw(img)

    # Logo: leichte Tiefe durch versetzte dunklere Kopie, dann amberner Schriftzug
    logo_font = _font(150, weight=800)
    cy = H * 0.46
    _centered(d, LOGO, logo_font, cy + 3, (90, 56, 14), tracking=8)   # Schatten
    _centered(d, LOGO, logo_font, cy, AMBER, tracking=8)
    # dezente Glanzkante oben
    _centered(d, LOGO, logo_font, cy - 2, AMBER_HI, tracking=8)

    # Subline
    sub_font = _font(40, weight=600)
    _centered(d, SUBTITLE, sub_font, H * 0.74, TEXT_DIM, tracking=14)

    img.save(OUT)
    print(f"[make_splash] geschrieben: {OUT}  ({W}x{H})")


if __name__ == "__main__":
    main()
