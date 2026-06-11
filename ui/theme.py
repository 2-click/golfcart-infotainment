"""Zentrales UI-Theme: Farben, Fonts, Gradienten, globales Stylesheet.

Designsprache: modernes KFZ-Cockpit (tiefes Anthrazit, Tiefen ueber Gradienten,
gluehende Akzente) mit Retro-Note (warmes Bernstein als Primaerfarbe, analoges
Rundinstrument, dezente digitale Mono-Ziffern).
"""

from PySide6.QtGui import QColor, QFont

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
