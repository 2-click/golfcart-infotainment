"""Zentrales UI-Theme: Farben, Fonts, Gradienten, globales Stylesheet.

Designsprache: modernes KFZ-Cockpit (tiefes Anthrazit, Tiefen ueber Gradienten,
gluehende Akzente) mit Retro-Note (warmes Bernstein als Primaerfarbe, analoges
Rundinstrument, dezente digitale Mono-Ziffern).
"""

import random

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QImage, QPixmap, QPainter

# --- Farbpalette ----------------------------------------------------------
BG_DEEP = QColor("#0b0e12")     # Hintergrund ganz hinten (fast schwarz)
BG_PANEL = QColor("#11151b")    # Panelflaeche
BG_ELEVATED = QColor("#1a2028")  # erhabene Flaeche (Tiles, Gauge-Face)
BG_HILITE = QColor("#222a34")   # Hover/Innenkante

STROKE = QColor("#2b343f")      # feine Trennlinien/Raender
STROKE_SOFT = QColor("#1e242c")

TEXT = QColor("#eef3f8")        # Primaertext
TEXT_DIM = QColor("#788491")    # Sekundaertext/Labels
TEXT_FAINT = QColor("#49525d")  # Skalenbeschriftung

# Akzente
AMBER = QColor("#ff9e2c")       # Retro-Primaer (Tacho-Bogen, aktive Tiles)
AMBER_HI = QColor("#ffc061")    # heller Glow
AMBER_DEEP = QColor("#d4760f")
ICE = QColor("#5cc7ff")         # modern, kuehl (Akzent, Reichweite)
GREEN = QColor("#46d27a")       # Blinker / "go"
RED = QColor("#ff5a52")         # Hupe / Warnung
BLUE_HIGH = QColor("#4aa3ff")   # Fernlicht-Telltale (genormtes Blau)

# Aktiv-Farbe je Aktor (Telltales + Buttons), passend zu den Lichtfarben.
ACTUATOR_COLOR = {
    "day_lights": QColor("#dfe9f5"),
    "low_beam": QColor("#ffd24d"),
    "high_beam": BLUE_HIGH,
    "work_light": QColor("#ffae42"),
    "beacon": QColor("#ff7a18"),
    "blinker_left": GREEN,
    "blinker_right": GREEN,
    "horn": RED,
}

# --- Fonts ----------------------------------------------------------------
# Mono fuer Ziffern (digitaler Cockpit-Look), Sans fuer Labels.
MONO_FAMILY = "Ubuntu Mono"
SANS_FAMILY = "Ubuntu"


def mono(size: int, weight=QFont.Bold) -> QFont:
    f = QFont(MONO_FAMILY, size, weight)
    f.setStyleHint(QFont.Monospace)
    return f


def label(size: int, weight=QFont.DemiBold, spacing: float = 2.0) -> QFont:
    f = QFont(SANS_FAMILY, size, weight)
    f.setStyleHint(QFont.SansSerif)
    f.setLetterSpacing(QFont.AbsoluteSpacing, spacing)
    f.setCapitalization(QFont.AllUppercase)
    return f


def sans(size: int, weight=QFont.Normal) -> QFont:
    f = QFont(SANS_FAMILY, size, weight)
    f.setStyleHint(QFont.SansSerif)
    return f


# --- Dithering ------------------------------------------------------------
# Das Produktionsdisplay hat eine geringe Farbtiefe (vermutlich RGB565/18 Bit).
# Weiche Verlaeufe zeigen darauf sichtbares Banding (harte Stufen), waehrend
# sie auf einem 24-Bit-Laptop sauber aussehen. Gegenmittel: ein feines,
# statisches Rauschen ueber die Verlaufsflaeche legen. Das Display kann zwar
# weiterhin nur wenige Farben, aber das Auge mittelt das Rauschen -> die
# Stufenkanten verschwimmen. Klassisches Noise-Dithering.
#
# WICHTIG zur Staerke: damit das Rauschen eine Banding-Kante wirklich
# aufbricht, muss ein Punkt hell genug sein, um den Pixel ueber EINE
# darstellbare Stufe des Panels zu heben. Bei RGB565 ist das R/B-Raster ~8
# (von 256) -> auf den dunklen Cockpit-Verlaeufen (Pixelwert ~20) braucht ein
# weisser Punkt also Alpha ~10+ ((255-20)*a/255 >= 8 -> a >= 9). Mit zu kleinem
# Alpha bleibt das Banding sichtbar. Default daher bewusst hoch; auf dem echten
# Panel ueber DITHER_AMP feinjustieren (zu hoch -> sichtbares Korn).
DITHER_AMP = 26
_DITHER_TILE = None


def _dither_tile() -> QPixmap:
    """Einmalig erzeugte, gekachelte Rausch-Textur (deterministisch).

    Jeder Pixel bekommt Rauschen (volle Dichte), zufaellig hell oder dunkel.
    Auf dunklem Grund wirken vor allem die hellen Punkte (dunkel kann kaum
    weiter nach unten) -> sie heben ~50 % der Pixel ueber die naechste
    Panel-Stufe und loesen so die harte Bandkante in einen Dither auf."""
    global _DITHER_TILE
    if _DITHER_TILE is None:
        size = 64
        amp = DITHER_AMP
        lo = max(1, amp // 3)  # Mindest-Alpha -> jeder Pixel traegt bei
        img = QImage(size, size, QImage.Format_ARGB32)
        rnd = random.Random(0xC05CA47)  # fester Seed -> kein Flimmern/Reproduzierbar
        for y in range(size):
            for x in range(size):
                v = 255 if rnd.random() < 0.5 else 0
                a = rnd.randint(lo, amp)
                img.setPixelColor(x, y, QColor(v, v, v, a))
        _DITHER_TILE = QPixmap.fromImage(img)
    return _DITHER_TILE


def dither(painter: QPainter, rect, strength: float = 1.0) -> None:
    """Legt das Dither-Rauschen ueber rect. Direkt NACH dem Zeichnen eines
    Verlaufs aufrufen, bevor scharfe Inhalte (PNG/Text/Icon) darueber kommen --
    die bleiben dann knackig, nur der Verlauf wird entbandet. Fuer kleine/helle
    Flaechen (z. B. Buttons) ggf. strength < 1.0, um Korn zu daempfen. Auf eine
    runde Flaeche begrenzen: vorher painter.setClipPath(...) setzen."""
    painter.save()
    painter.setOpacity(strength)
    painter.setCompositionMode(QPainter.CompositionMode_SourceOver)
    painter.drawTiledPixmap(rect, _dither_tile())
    painter.restore()


# --- Globales Stylesheet --------------------------------------------------
def global_qss() -> str:
    return f"""
    QWidget {{
        color: {TEXT.name()};
        font-family: "{SANS_FAMILY}", "DejaVu Sans", sans-serif;
    }}
    QToolTip {{
        color: {TEXT.name()};
        background-color: {BG_ELEVATED.name()};
        border: 1px solid {STROKE.name()};
    }}
    """
