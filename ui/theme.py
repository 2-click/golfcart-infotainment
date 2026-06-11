"""Zentrales UI-Theme: Farben, Fonts, Gradienten, globales Stylesheet.

Designsprache: modernes KFZ-Cockpit (tiefes Anthrazit, Tiefen ueber Gradienten,
gluehende Akzente) mit Retro-Note (warmes Bernstein als Primaerfarbe, analoges
Rundinstrument, dezente digitale Mono-Ziffern).
"""

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
# Stufenkanten verschwimmen.
#
# Methode: GEORDNETES Dithering (Bayer-Matrix), KEIN Zufallsrauschen. Zufalls-
# rauschen, das stark genug ist, um eine Bandkante aufzubrechen, sieht immer wie
# TV-Schnee aus. Das Bayer-Muster verteilt helle/dunkle Punkte regelmaessig, das
# Auge mittelt es zu einem glatten Halbton -> Banding weg, aber kaum sichtbar.
#
# DITHER_AMP = Spanne der Stoerung (Alpha, Spitze hell wie dunkel). Klein halten:
# es muss nur ~eine Panel-Stufe ueberbruecken. Auf dem echten Panel justieren --
# hoeher, wenn noch Banding sichtbar; niedriger, wenn das Muster auffaellt.
DITHER_AMP = 14
_DITHER_TILE = None


def _bayer(n: int) -> list:
    """Rekursive Bayer-Schwellenmatrix (n = Zweierpotenz), Werte 0..n*n-1."""
    if n == 1:
        return [[0]]
    h = _bayer(n // 2)
    m = n // 2
    out = [[0] * n for _ in range(n)]
    for y in range(m):
        for x in range(m):
            v = h[y][x] * 4
            out[y][x] = v + 0
            out[y][x + m] = v + 2
            out[y + m][x] = v + 3
            out[y + m][x + m] = v + 1
    return out


def _dither_tile() -> QPixmap:
    """Einmalig erzeugte, gekachelte Bayer-Dither-Textur.

    Pro Pixel ein signierter Versatz aus der Bayer-Matrix: helle Punkte heben,
    dunkle senken -- mit zur Matrix-Position glatt steigender Deckkraft. Die
    Mitte (Schwelle ~0,5) bleibt fast transparent. Ergebnis ist ein feines,
    regelmaessiges Halbton statt Schnee."""
    global _DITHER_TILE
    if _DITHER_TILE is None:
        n = 8
        mat = _bayer(n)
        amp = DITHER_AMP
        img = QImage(n, n, QImage.Format_ARGB32)
        for y in range(n):
            for x in range(n):
                th = (mat[y][x] + 0.5) / (n * n)   # 0..1
                off = th - 0.5                      # -0.5..0.5
                v = 255 if off >= 0 else 0          # hell hebt, dunkel senkt
                a = round(abs(off) * 2 * amp)       # 0..amp
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
