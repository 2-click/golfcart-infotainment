"""Handgas / Tempomat -- Schubregler-Screen.

Wird vom Tacho per Doppeltipp geoeffnet. Ein vertikaler Schubregler stellt die
Tempomat-Soll-Geschwindigkeit (VehicleState.cruise_kmh) ein. Ueber "Zurueck"
geht es wieder zum Tacho; der eingestellte Wert wird dort als Bug-Marker
angezeigt.
"""

from PySide6.QtCore import Qt, QRectF, Signal
from PySide6.QtGui import QPainter, QColor, QPen, QBrush, QFont, QLinearGradient
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                               QLabel)

from . import theme


class ThrottleSlider(QWidget):
    """Vertikaler Schubregler 0..vmax (oben = mehr Gas)."""

    valueChanged = Signal(float)
    # Pads >= halbe Handle-Hoehe (HANDLE_H/2), damit der Handle an den Enden
    # (0 % / 100 %) nicht abgeschnitten wird.
    HANDLE_H = 30
    TOP_PAD = HANDLE_H // 2 + 6
    BOT_PAD = HANDLE_H // 2 + 6
    TRACK_W = 64

    def __init__(self, vmax: float, parent=None):
        super().__init__(parent)
        self._max = vmax
        self._value = 0.0
        self.setMinimumWidth(150)
        self.setCursor(Qt.PointingHandCursor)

    def value(self) -> float:
        return self._value

    def setValue(self, v: float):
        v = max(0.0, min(self._max, round(v)))
        if v != self._value:
            self._value = v
            self.update()
            self.valueChanged.emit(v)

    def _span(self):
        top = self.TOP_PAD
        bottom = self.height() - self.BOT_PAD
        return top, bottom

    def _value_to_y(self, v):
        top, bottom = self._span()
        return bottom - (v / self._max) * (bottom - top)

    def _y_to_value(self, y):
        top, bottom = self._span()
        frac = (bottom - y) / (bottom - top)
        return max(0.0, min(1.0, frac)) * self._max

    def mousePressEvent(self, e):
        self.setValue(self._y_to_value(e.position().y()))

    def mouseMoveEvent(self, e):
        self.setValue(self._y_to_value(e.position().y()))

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        cx = self.width() / 2
        top, bottom = self._span()
        tw = self.TRACK_W
        track = QRectF(cx - tw / 2, top, tw, bottom - top)

        # Track
        p.setPen(QPen(theme.STROKE, 1))
        p.setBrush(QBrush(theme.BG_ELEVATED))
        p.drawRoundedRect(track, tw / 2, tw / 2)

        # Fuellung von unten bis Handle
        hy = self._value_to_y(self._value)
        if self._value > 0:
            fill = QRectF(track.left(), hy, tw, bottom - hy)
            grad = QLinearGradient(0, hy, 0, bottom)
            grad.setColorAt(0.0, theme.AMBER_HI)
            grad.setColorAt(1.0, theme.AMBER_DEEP)
            p.setPen(Qt.NoPen)
            p.setBrush(QBrush(grad))
            p.drawRoundedRect(fill, tw / 2, tw / 2)

        # Skalen-Ticks (0, max/2, max) links
        p.setFont(theme.mono(11, QFont.Medium))
        for frac in (0.0, 0.5, 1.0):
            v = frac * self._max
            y = self._value_to_y(v)
            p.setPen(QPen(theme.STROKE, 2))
            p.drawLine(int(cx - tw / 2 - 12), int(y), int(cx - tw / 2 - 4), int(y))
            p.setPen(theme.TEXT_FAINT)
            p.drawText(QRectF(cx - tw / 2 - 56, y - 10, 38, 20),
                       Qt.AlignRight | Qt.AlignVCenter, f"{v:.0f}")

        # Handle
        hw, hh = tw + 30, self.HANDLE_H
        handle = QRectF(cx - hw / 2, hy - hh / 2, hw, hh)
        p.setPen(QPen(theme.AMBER, 2))
        p.setBrush(QBrush(theme.BG_HILITE))
        p.drawRoundedRect(handle, 9, 9)
        # Griffrillen
        p.setPen(QPen(theme.AMBER, 2))
        for dx in (-7, 0, 7):
            p.drawLine(int(cx + dx), int(hy - 7), int(cx + dx), int(hy + 7))
        p.end()


class ThrottleControl(QWidget):
    back = Signal()

    def __init__(self, state, parent=None):
        super().__init__(parent)
        self.state = state

        root = QVBoxLayout(self)
        root.setContentsMargins(8, 4, 8, 6)
        root.setSpacing(6)

        # Zurueck-Button (kompakt)
        self.back_btn = QPushButton("‹  ZURÜCK ZUM TACHO")
        self.back_btn.setFocusPolicy(Qt.NoFocus)
        self.back_btn.setCursor(Qt.PointingHandCursor)
        self.back_btn.setFixedHeight(34)
        self.back_btn.setStyleSheet(
            "QPushButton {"
            f"  color: {theme.TEXT.name()}; background: {theme.BG_ELEVATED.name()};"
            f"  border: 1px solid {theme.STROKE.name()}; border-radius: 9px;"
            "  font-size: 13px; font-weight: 600; letter-spacing: 1px; }"
            f"QPushButton:pressed {{ background: {theme.BG_HILITE.name()}; }}"
        )
        self.back_btn.clicked.connect(self.back)
        root.addWidget(self.back_btn)

        # Kompakter Kopf: kleine Beschriftung + Prozentwert (wenig Hoehe ->
        # mehr Platz fuer den Regler).
        caption = QLabel("HANDGAS")
        caption.setAlignment(Qt.AlignCenter)
        caption.setStyleSheet(
            f"color: {theme.TEXT_DIM.name()}; font-size: 12px;"
            " font-weight: 600; letter-spacing: 3px;")
        self.readout = QLabel("0 %")
        self.readout.setAlignment(Qt.AlignCenter)
        self.readout.setStyleSheet(
            f"color: {theme.AMBER_HI.name()}; font-family: '{theme.MONO_FAMILY}';"
            " font-size: 40px; font-weight: 800;")
        head = QVBoxLayout()
        head.setSpacing(0)
        head.addWidget(caption)
        head.addWidget(self.readout)
        root.addLayout(head)

        # Slider mit +/- Tasten -- bekommt den ganzen restlichen Platz.
        mid = QHBoxLayout()
        mid.setSpacing(10)
        self.minus = self._step_btn("–")
        self.plus = self._step_btn("+")
        self.slider = ThrottleSlider(100.0)   # Handgas in Prozent
        self.slider.valueChanged.connect(self._on_value)
        self.minus.clicked.connect(lambda: self.slider.setValue(self.slider.value() - 5))
        self.plus.clicked.connect(lambda: self.slider.setValue(self.slider.value() + 5))
        mid.addWidget(self.minus, 0, Qt.AlignVCenter)
        mid.addWidget(self.slider, 1)
        mid.addWidget(self.plus, 0, Qt.AlignVCenter)
        root.addLayout(mid, 1)

    def _step_btn(self, text) -> QPushButton:
        b = QPushButton(text)
        b.setFocusPolicy(Qt.NoFocus)
        b.setCursor(Qt.PointingHandCursor)
        b.setFixedSize(52, 52)
        b.setStyleSheet(
            "QPushButton {"
            f"  color: {theme.TEXT.name()}; background: {theme.BG_ELEVATED.name()};"
            f"  border: 1px solid {theme.STROKE.name()}; border-radius: 12px;"
            "  font-size: 28px; font-weight: 700; }"
            f"QPushButton:pressed {{ background: {theme.BG_HILITE.name()}; }}"
        )
        return b

    def _on_value(self, v: float):
        self.state.throttle_pct = v
        self.readout.setText(f"{v:.0f} %")

    def showEvent(self, event):
        # Beim Oeffnen die aktuelle Gasstellung uebernehmen.
        self.slider.setValue(self.state.throttle_pct)
        self.readout.setText(f"{self.state.throttle_pct:.0f} %")
        super().showEvent(event)
