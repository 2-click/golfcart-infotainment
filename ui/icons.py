"""Vektorielle KFZ-Telltale-Symbole, gezeichnet mit QPainter.

Jede Funktion zeichnet ihr Symbol in ein gegebenes QRectF, eingefaerbt in
`color`. Die Symbole orientieren sich an genormten Kfz-Kontrollleuchten
(Fern-/Abblendlicht-Lampe mit Strahlen, Blinkerpfeil, Rundumleuchte, Hupe ...).

Die Funktionen werden sowohl von der Telltale-Leiste als auch von den
Steuer-Buttons genutzt -> ein Symbolsatz, konsistente Optik.
"""

import math

from PySide6.QtCore import Qt, QRectF, QPointF
from PySide6.QtGui import QPainter, QColor, QPen, QBrush, QPainterPath


def _pen(color: QColor, w: float) -> QPen:
    p = QPen(color, w)
    p.setCapStyle(Qt.RoundCap)
    p.setJoinStyle(Qt.RoundJoin)
    return p


def _lamp_path(cx: float, cy: float, r: float) -> QPainterPath:
    """Die klassische 'Scheinwerfer-Lampe': halbe Ellipse mit flacher
    rechter Seite (die Strahlen treten rechts aus)."""
    path = QPainterPath()
    rect = QRectF(cx - r, cy - r, 2 * r, 2 * r)
    # Bogen von oben (90 deg) gegen den Uhrzeigersinn ueber links nach unten (-90).
    path.moveTo(cx, cy - r)
    path.arcTo(rect, 90, 180)   # linke Haelfte
    path.closeSubpath()
    return path


def _draw_beam_lamp(p: QPainter, rect: QRectF, color: QColor, rays_angled: bool):
    """Fern-/Abblendlicht-Telltale. rays_angled=True -> Strahlen nach unten
    geneigt (Abblendlicht), sonst waagerecht (Fernlicht)."""
    s = min(rect.width(), rect.height())
    cx = rect.center().x() - s * 0.12
    cy = rect.center().y()
    r = s * 0.26
    lw = max(2.0, s * 0.055)

    p.setPen(Qt.NoPen)
    p.setBrush(QBrush(color))
    p.drawPath(_lamp_path(cx, cy, r))

    # Strahlen rechts der Lampe.
    p.setPen(_pen(color, lw))
    x0 = cx + lw * 0.4
    n = 4
    for i in range(n):
        y = cy - r + (2 * r) * (i + 0.5) / n
        x1 = x0 + s * 0.30
        y1 = y + (s * 0.12 if rays_angled else 0.0)
        p.drawLine(QPointF(x0, y), QPointF(x1, y1))


def low_beam(p, rect, color):
    _draw_beam_lamp(p, rect, color, rays_angled=True)


def high_beam(p, rect, color):
    _draw_beam_lamp(p, rect, color, rays_angled=False)


def day_lights(p, rect, color):
    """Tagfahrlicht: Lampe mit kurzen, geraden Strahlen (Punkte/Striche)."""
    s = min(rect.width(), rect.height())
    cx = rect.center().x() - s * 0.10
    cy = rect.center().y()
    r = s * 0.24
    lw = max(2.0, s * 0.05)
    p.setPen(Qt.NoPen)
    p.setBrush(QBrush(color))
    p.drawPath(_lamp_path(cx, cy, r))
    p.setPen(_pen(color, lw))
    x0 = cx + lw * 0.4
    n = 4
    for i in range(n):
        y = cy - r + (2 * r) * (i + 0.5) / n
        p.drawLine(QPointF(x0, y), QPointF(x0 + s * 0.16, y))


def work_light(p, rect, color):
    """Arbeitsscheinwerfer: Lampe oben, Strahlen senkrecht nach unten auf
    eine kurze Bodenlinie."""
    s = min(rect.width(), rect.height())
    cx = rect.center().x()
    top = rect.center().y() - s * 0.24
    lw = max(2.0, s * 0.05)
    # Lampe (halbe Ellipse, flache Seite unten).
    p.setPen(Qt.NoPen)
    p.setBrush(QBrush(color))
    path = QPainterPath()
    r = s * 0.22
    lamp = QRectF(cx - r, top - r * 0.5, 2 * r, r)
    path.moveTo(cx - r, top)
    path.arcTo(lamp, 180, 180)
    path.closeSubpath()
    p.drawPath(path)
    # Strahlen nach unten.
    p.setPen(_pen(color, lw))
    n = 4
    for i in range(n):
        x = cx - r * 0.7 + (1.4 * r) * i / (n - 1)
        p.drawLine(QPointF(x, top + s * 0.06), QPointF(x, top + s * 0.30))


def beacon(p, rect, color):
    """Rundumleuchte: Kuppel auf Sockel mit abstrahlenden Linien."""
    s = min(rect.width(), rect.height())
    cx = rect.center().x()
    cy = rect.center().y() + s * 0.10
    w = s * 0.34
    h = s * 0.22
    lw = max(2.0, s * 0.05)
    p.setPen(Qt.NoPen)
    p.setBrush(QBrush(color))
    # Kuppel (halbe Ellipse) + Sockel.
    dome = QRectF(cx - w / 2, cy - h, w, 2 * h)
    path = QPainterPath()
    path.moveTo(cx - w / 2, cy)
    path.arcTo(dome, 180, 180)
    path.closeSubpath()
    p.drawPath(path)
    p.drawRoundedRect(QRectF(cx - w * 0.62, cy, w * 1.24, h * 0.5), 2, 2)
    # Strahlen oben.
    p.setPen(_pen(color, lw))
    for ang in (-55, -25, 25, 55):
        a = math.radians(ang - 90)
        x0 = cx + math.cos(a) * (h * 1.2)
        y0 = cy - h + math.sin(a) * (h * 0.6) - h * 0.2
        x1 = cx + math.cos(a) * (h * 2.1)
        y1 = cy - h + math.sin(a) * (h * 1.4) - h * 0.2
        p.drawLine(QPointF(x0, y0), QPointF(x1, y1))


def _arrow(p, rect, color, to_left: bool):
    s = min(rect.width(), rect.height())
    cx = rect.center().x()
    cy = rect.center().y()
    hw = s * 0.26   # halbe Hoehe des Pfeilkopfs
    head = s * 0.20
    tail = s * 0.16
    p.setPen(Qt.NoPen)
    p.setBrush(QBrush(color))
    path = QPainterPath()
    d = 1 if to_left else -1
    tip = cx - d * (s * 0.28)
    base = cx - d * (s * 0.28) + d * head
    # Pfeilkopf (Dreieck)
    path.moveTo(tip, cy)
    path.lineTo(base, cy - hw)
    path.lineTo(base, cy - hw * 0.45)
    # Schaft
    path.lineTo(cx + d * (s * 0.28), cy - hw * 0.45)
    path.lineTo(cx + d * (s * 0.28), cy + hw * 0.45)
    path.lineTo(base, cy + hw * 0.45)
    path.lineTo(base, cy + hw)
    path.closeSubpath()
    p.drawPath(path)


def blinker_left(p, rect, color):
    _arrow(p, rect, color, to_left=True)


def blinker_right(p, rect, color):
    _arrow(p, rect, color, to_left=False)


def hazard(p, rect, color):
    """Warnblinker: Warndreieck (Umriss, nach oben)."""
    s = min(rect.width(), rect.height())
    cx, cy = rect.center().x(), rect.center().y()
    r = s * 0.38
    lw = max(2.0, s * 0.08)
    path = QPainterPath()
    pts = []
    for ang in (-90, 30, 150):  # gleichseitiges Dreieck, Spitze oben
        a = math.radians(ang)
        pts.append(QPointF(cx + r * math.cos(a), cy + r * math.sin(a) + s * 0.04))
    path.moveTo(pts[0])
    path.lineTo(pts[1])
    path.lineTo(pts[2])
    path.closeSubpath()
    p.setBrush(Qt.NoBrush)
    p.setPen(_pen(color, lw))
    p.drawPath(path)


def horn(p, rect, color):
    """Hupe: stilisiertes Horn (Trichter) mit zwei Schallbogen."""
    s = min(rect.width(), rect.height())
    cx = rect.center().x() - s * 0.06
    cy = rect.center().y()
    lw = max(2.0, s * 0.055)
    p.setPen(Qt.NoPen)
    p.setBrush(QBrush(color))
    # Trichter: kleines Rechteck (Mundstueck) + Trapez (Schalltrichter).
    path = QPainterPath()
    x = cx - s * 0.22
    path.addRoundedRect(QRectF(x - s * 0.10, cy - s * 0.10, s * 0.12, s * 0.20),
                        2, 2)
    path.moveTo(x, cy - s * 0.14)
    path.lineTo(x + s * 0.22, cy - s * 0.24)
    path.lineTo(x + s * 0.22, cy + s * 0.24)
    path.lineTo(x, cy + s * 0.14)
    path.closeSubpath()
    p.drawPath(path)
    # Schallbogen rechts.
    p.setPen(_pen(color, lw))
    p.setBrush(Qt.NoBrush)
    for k in (0.34, 0.46):
        rr = s * k
        p.drawArc(QRectF(cx - rr + s * 0.30, cy - rr, 2 * rr, 2 * rr),
                  -55 * 16, 110 * 16)


# --- Stat-Icons (Telemetrie-Kacheln) -------------------------------------
def stat_battery(p, rect, color):
    s = min(rect.width(), rect.height())
    cx, cy = rect.center().x(), rect.center().y()
    w, h = s * 0.62, s * 0.40
    lw = max(2.0, s * 0.07)
    p.setBrush(Qt.NoBrush)
    p.setPen(_pen(color, lw))
    body = QRectF(cx - w / 2, cy - h / 2, w, h)
    p.drawRoundedRect(body, 3, 3)
    # Pluspol
    p.setPen(Qt.NoPen)
    p.setBrush(QBrush(color))
    p.drawRoundedRect(QRectF(cx + w / 2, cy - h * 0.18, lw, h * 0.36), 1, 1)
    # Fuellung (3 Balken)
    inner = body.adjusted(lw, lw, -lw, -lw)
    bw = inner.width() / 3.4
    for i in range(3):
        p.drawRoundedRect(QRectF(inner.left() + i * (bw * 1.12),
                                 inner.top(), bw, inner.height()), 1, 1)


def stat_bolt(p, rect, color):
    s = min(rect.width(), rect.height())
    cx, cy = rect.center().x(), rect.center().y()
    path = QPainterPath()
    path.moveTo(cx + s * 0.06, cy - s * 0.30)
    path.lineTo(cx - s * 0.18, cy + s * 0.04)
    path.lineTo(cx - s * 0.01, cy + s * 0.04)
    path.lineTo(cx - s * 0.06, cy + s * 0.30)
    path.lineTo(cx + s * 0.20, cy - s * 0.06)
    path.lineTo(cx + s * 0.02, cy - s * 0.06)
    path.closeSubpath()
    p.setPen(Qt.NoPen)
    p.setBrush(QBrush(color))
    p.drawPath(path)


def stat_route(p, rect, color):
    """Routen-/Reichweiten-Symbol: Pin auf einer geschwungenen Strecke."""
    s = min(rect.width(), rect.height())
    cx, cy = rect.center().x(), rect.center().y()
    lw = max(2.0, s * 0.07)
    p.setPen(_pen(color, lw))
    p.setBrush(Qt.NoBrush)
    path = QPainterPath()
    path.moveTo(cx - s * 0.26, cy + s * 0.26)
    path.cubicTo(cx - s * 0.30, cy - s * 0.06,
                 cx + s * 0.30, cy + s * 0.10,
                 cx + s * 0.24, cy - s * 0.20)
    pen = _pen(color, lw)
    pen.setStyle(Qt.DotLine)
    p.setPen(pen)
    p.drawPath(path)
    # Pin
    p.setPen(Qt.NoPen)
    p.setBrush(QBrush(color))
    p.drawEllipse(QPointF(cx + s * 0.22, cy - s * 0.24), s * 0.06, s * 0.06)


# Aktor-Name -> Zeichenfunktion.
ICONS = {
    "day_lights": day_lights,
    "low_beam": low_beam,
    "high_beam": high_beam,
    "work_light": work_light,
    "beacon": beacon,
    "blinker_left": blinker_left,
    "blinker_right": blinker_right,
    "horn": horn,
    "hazard": hazard,
}


def draw_icon(actuator: str, p: QPainter, rect: QRectF, color: QColor):
    fn = ICONS.get(actuator)
    if fn is not None:
        fn(p, rect, color)
