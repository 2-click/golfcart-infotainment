"""Erzeugt farbige Platzhalter-PNGs fuer die LICHT-Layer des Cart-Stacks.

Die echte Cart-Grafik (cart_base.png) wird NICHT ueberschrieben. Die Licht-
Layer werden in exakt derselben Canvas-Groesse wie cart_base.png erzeugt
(deckungsgleich), mit Glows grob ueber den realen Lichtpositionen des Carts.
So bleibt der Closed-Loop-Demo stimmig, bis echte Licht-PNGs kommen -- diese
ersetzen die Platzhalter dann 1:1 (gleiche Dateinamen, gleiche Groesse).

Aufruf:
    QT_QPA_PLATFORM=offscreen python3 tools/gen_assets.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtCore import Qt, QRectF, QPointF
from PySide6.QtGui import QGuiApplication, QImage, QPainter, QColor, QBrush

import config  # noqa: F401  (haelt die Abhaengigkeit explizit)

ASSET_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                         "ui", "assets")
BASE_PATH = os.path.join(ASSET_DIR, "cart_base.png")

# Canvas-Groesse = Groesse der echten Base (deckungsgleich). QImage liest die
# Groesse ohne laufende QGuiApplication.
_base_img = QImage(BASE_PATH)
if _base_img.isNull():
    raise SystemExit(f"cart_base.png nicht gefunden/lesbar: {BASE_PATH}")
W, H = _base_img.width(), _base_img.height()

# Lichtpositionen als Anteile der Canvas (robust gegen Groessenwechsel).
# Cart-Foto: Frontansicht, FRONT rechts, HECK links.
POS = {
    "headlight": (0.875, 0.745),   # Frontscheinwerfer (rechts/vorne)
    "front_marker": (0.86, 0.70),  # schmale Frontmarkierung (Tagfahrlicht)
    "blinker_right": (0.93, 0.78),  # Blinker vorne rechts (Front-Ecke)
    "blinker_left": (0.05, 0.745),  # Blinker hinten links (Heck-Ecke)
    "beacon": (0.60, 0.06),         # Rundumleuchte auf der Dachvorderkante
    "work_light": (0.10, 0.66),     # Arbeitsscheinwerfer (Heck)
}


def pt(key) -> QPointF:
    fx, fy = POS[key]
    return QPointF(fx * W, fy * H)


def new_canvas() -> QImage:
    img = QImage(W, H, QImage.Format_ARGB32)
    img.fill(Qt.transparent)
    return img


def glow(p: QPainter, center: QPointF, radius: float, color: QColor):
    """Weicher Lichtschein als gestaffelte, zunehmend transparente Kreise."""
    for i in range(8, 0, -1):
        c = QColor(color)
        c.setAlpha(int(38 * i / 8))
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(c))
        r = radius * i / 8
        p.drawEllipse(center, r, r)


def draw_layer(name: str, fn):
    img = new_canvas()
    p = QPainter(img)
    p.setRenderHint(QPainter.Antialiasing, True)
    fn(p)
    p.end()
    path = os.path.join(ASSET_DIR, name)
    img.save(path, "PNG")
    print("wrote", path, f"({W}x{H})")


def main():
    R = W * 0.10  # Basis-Glow-Radius relativ zur Breite

    draw_layer("day_lights.png", lambda p: (
        p.setPen(Qt.NoPen),
        p.setBrush(QBrush(QColor("#eaf2ff"))),
        p.drawRoundedRect(QRectF(pt("front_marker").x() - 22,
                                 pt("front_marker").y() - 6, 44, 12), 6, 6),
    ))

    draw_layer("low_beam.png", lambda p: glow(p, pt("headlight"), R * 1.2,
                                              QColor("#ffd24d")))

    def high(p):
        glow(p, pt("headlight"), R * 1.8, QColor("#ffffff"))
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(QColor("#3aa0ff")))
        p.drawEllipse(pt("front_marker"), R * 0.16, R * 0.16)
    draw_layer("high_beam.png", high)

    draw_layer("work_light.png", lambda p: glow(p, pt("work_light"), R * 1.5,
                                               QColor("#ffae42")))

    def beacon(p):
        c = QColor("#ff7a18")
        glow(p, pt("beacon"), R * 1.0, c)
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(c))
        bp = pt("beacon")
        p.drawRoundedRect(QRectF(bp.x() - R * 0.45, bp.y() - R * 0.22,
                                 R * 0.9, R * 0.44), 6, 6)
    draw_layer("beacon.png", beacon)

    draw_layer("blinker_left.png", lambda p: glow(p, pt("blinker_left"), R * 0.9,
                                                  QColor("#ff9b1a")))
    draw_layer("blinker_right.png", lambda p: glow(p, pt("blinker_right"), R * 0.9,
                                                   QColor("#ff9b1a")))


if __name__ == "__main__":
    app = QGuiApplication(sys.argv)
    main()
