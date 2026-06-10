"""Telemetry -- mittlere Spalte im Cockpit-Stil.

Aufbau (von oben nach unten):
- Telltale-Leiste: genormte Kfz-Kontrollleuchten, die dem IST-Status folgen
  (Blinker blinken synchron).
- SpeedGauge: analoges Rund-Tacho (Hero-Element).
- Stat-Kacheln: SOC / Strom / Reichweite mit Icons.

Alles reaktiv aus VehicleState (changed-Signal).
"""

from PySide6.QtCore import Qt, QRectF, QPointF
from PySide6.QtGui import QPainter, QColor, QPen, QBrush, QFont, QFontMetrics
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QStackedWidget

from . import theme, icons
from .gauge import SpeedGauge
from .throttle import ThrottleControl


def _mix(c: QColor, bg: QColor, t: float) -> QColor:
    """Lineare Mischung c->bg (t=0..1)."""
    return QColor(
        int(c.red() * (1 - t) + bg.red() * t),
        int(c.green() * (1 - t) + bg.green() * t),
        int(c.blue() * (1 - t) + bg.blue() * t),
    )


class TelltaleStrip(QWidget):
    """Reihe von Kontrollleuchten. Aktiv -> volle Farbe + Glow, sonst gedimmt."""

    ORDER = ["blinker_left", "day_lights", "low_beam", "high_beam",
             "work_light", "beacon", "horn", "blinker_right"]

    def __init__(self, state, blink, parent=None):
        super().__init__(parent)
        self.state = state
        self.blink = blink
        self.setFixedHeight(58)
        self.blink.tick.connect(self.update)
        self.state.changed.connect(self.update)

    def _is_on(self, name: str) -> bool:
        return self.state.get_actuator(name) and self.blink.is_on(name)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        n = len(self.ORDER)
        cw = self.width() / n
        size = min(cw, self.height()) * 0.74
        for i, name in enumerate(self.ORDER):
            cell = QRectF(i * cw, 0, cw, self.height())
            icon_rect = QRectF(0, 0, size, size)
            icon_rect.moveCenter(cell.center())
            on = self._is_on(name)
            base = theme.ACTUATOR_COLOR[name]
            color = base if on else _mix(base, theme.BG_DEEP, 0.82)
            if on:
                glow = QColor(base)
                glow.setAlpha(60)
                p.setPen(Qt.NoPen)
                p.setBrush(QBrush(glow))
                p.drawEllipse(cell.center(), size * 0.62, size * 0.62)
            icons.draw_icon(name, p, icon_rect, color)
        p.end()


class StatTile(QWidget):
    """Kennwert-Kachel: Icon, grosser Mono-Wert, Label."""

    # Feste Innen-Hoehen des zentrierten Inhaltsblocks.
    ICON_H = 30
    VALUE_H = 30
    LABEL_H = 16
    GAP = 6          # Abstand zwischen den drei Elementen
    PAD = 14         # Innen-Padding oben/unten (gleich)
    SIDE_PAD = 12    # Innen-Padding links/rechts fuer den Wert
    VALUE_PT = 22    # Basis-Schriftgroesse der Zahl (wird bei Bedarf verkleinert)

    def __init__(self, icon_fn, label, accent: QColor, unit: str = "", parent=None):
        super().__init__(parent)
        self._icon_fn = icon_fn
        self._label = label
        self._accent = accent
        self._unit = unit
        self._value = "--"
        # Hoehe = Padding + Inhalt + Padding -> nichts beruehrt den Rand.
        content = self.ICON_H + self.VALUE_H + self.LABEL_H + 2 * self.GAP
        self.setFixedHeight(content + 2 * self.PAD)

    def set_value(self, text: str):
        if text != self._value:
            self._value = text
            self.update()

    def _draw_value(self, p: QPainter, row: QRectF):
        """Zeichnet 'Zahl + kleine Einheit' zentriert, baseline-gleich.
        Die Zahl wird verkleinert, falls Zahl+Einheit breiter als die Kachel
        waeren -> kein Ueberlauf, einheitliche Raender."""
        avail = row.width() - 2 * self.SIDE_PAD
        size = self.VALUE_PT
        while size >= 11:
            vf = theme.mono(size, QFont.Bold)
            uf = theme.mono(max(9, round(size * 0.60)), QFont.Medium)
            fmv, fmu = QFontMetrics(vf), QFontMetrics(uf)
            gap = round(size * 0.22) if self._unit else 0
            vw = fmv.horizontalAdvance(self._value)
            uw = fmu.horizontalAdvance(self._unit) if self._unit else 0
            if vw + gap + uw <= avail:
                break
            size -= 1

        total = vw + gap + uw
        x = row.center().x() - total / 2
        baseline = row.center().y() + (fmv.ascent() - fmv.descent()) / 2

        p.setFont(vf)
        p.setPen(theme.TEXT)
        p.drawText(QPointF(x, baseline), self._value)
        if self._unit:
            p.setFont(uf)
            p.setPen(theme.TEXT_DIM)
            p.drawText(QPointF(x + vw + gap, baseline), self._unit)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        r = QRectF(2, 2, self.width() - 4, self.height() - 4)
        # Hintergrund
        p.setPen(QPen(theme.STROKE, 1))
        p.setBrush(QBrush(theme.BG_ELEVATED))
        p.drawRoundedRect(r, 12, 12)
        # Akzentstreifen oben
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(self._accent))
        p.drawRoundedRect(QRectF(r.left() + 12, r.top() + 1, r.width() - 24, 3),
                          1.5, 1.5)

        # Inhaltsblock vertikal zentrieren.
        content = self.ICON_H + self.VALUE_H + self.LABEL_H + 2 * self.GAP
        y = r.center().y() - content / 2

        # Icon
        ir = QRectF(0, 0, self.ICON_H, self.ICON_H)
        ir.moveCenter(QRectF(r.left(), y, r.width(), self.ICON_H).center())
        self._icon_fn(p, ir, self._accent)
        y += self.ICON_H + self.GAP

        # Wert (Zahl + kleine Einheit, auto-skaliert)
        self._draw_value(p, QRectF(r.left(), y, r.width(), self.VALUE_H))
        y += self.VALUE_H + self.GAP

        # Label
        p.setPen(theme.TEXT_DIM)
        p.setFont(theme.label(9, spacing=1.5))
        p.drawText(QRectF(r.left(), y, r.width(), self.LABEL_H),
                   Qt.AlignCenter, self._label)
        p.end()


class Telemetry(QWidget):
    def __init__(self, state, blink, parent=None):
        super().__init__(parent)
        self.state = state

        # Einheitliches Spacing-Raster: gleicher Abstand aussen, zwischen den
        # Sektionen (Telltale<->Tacho<->Karten) und zwischen den Karten.
        GAP = 16
        root = QVBoxLayout(self)
        root.setContentsMargins(GAP, GAP, GAP, GAP)
        root.setSpacing(GAP)

        self.telltales = TelltaleStrip(state, blink)

        # Tacho <-> Handgas/Tempomat umschaltbar (Doppeltipp auf den Tacho).
        self.gauge = SpeedGauge(state)
        self.throttle = ThrottleControl(state)
        self.center = QStackedWidget()
        self.center.addWidget(self.gauge)      # Index 0
        self.center.addWidget(self.throttle)   # Index 1
        self.gauge.doubleTapped.connect(
            lambda: self.center.setCurrentWidget(self.throttle))
        self.throttle.back.connect(
            lambda: self.center.setCurrentWidget(self.gauge))

        tiles = QHBoxLayout()
        tiles.setSpacing(GAP)
        self.soc = StatTile(icons.stat_battery, "SOC", theme.GREEN, unit="%")
        self.current = StatTile(icons.stat_bolt, "Strom", theme.AMBER, unit="A")
        self.range = StatTile(icons.stat_route, "Reichweite", theme.ICE, unit="km")
        for t in (self.soc, self.current, self.range):
            tiles.addWidget(t)

        root.addWidget(self.telltales)
        root.addWidget(self.center, 1)
        root.addLayout(tiles)

        self.state.changed.connect(self.refresh)
        self.refresh()

    def refresh(self):
        self.soc.set_value(f"{self.state.soc_pct:.0f}")
        self.current.set_value(f"{self.state.current_a:.0f}")
        # Reichweite: unter 100 km mit einer Nachkommastelle, ab 100 ohne ->
        # bleibt schmal; der Auto-Fit faengt Extremfaelle zusaetzlich ab.
        rng = self.state.range_km
        self.range.set_value(f"{rng:.1f}" if rng < 100 else f"{rng:.0f}")
