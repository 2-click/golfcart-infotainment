"""Controls -- 8 Touch-Tiles im Cockpit-Stil (Closed-Loop).

Jede Kachel zeigt das genormte Telltale-Symbol + Label. Aktiv = volle Akzent-
farbe, gluehender Rahmen und getoenter Hintergrund; aus = gedimmt.

WICHTIG (Closed-Loop): Ein Tipp setzt NICHT direkt die Optik. Er loest nur ein
CAN-TX aus (send_command). Die Aktiv-Darstellung folgt dem VehicleState, also
dem IST-Status der SPS.

- Hupe = Halte-Taster (an solange gedrueckt).
- Restliche Aktoren = Toggle.
"""

from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QPainter, QColor, QPen, QBrush, QFont
from PySide6.QtWidgets import QWidget, QGridLayout, QAbstractButton

from . import theme, icons

# (actuator, Label, Zeile, Spalte, ist_halte_taster)
# "hazard" ist kein eigener Aktor -> steuert blinker_left+right gemeinsam.
BUTTONS = [
    ("day_lights",    "Tagfahrlicht",   0, 0, False),
    ("low_beam",      "Abblendlicht",   0, 1, False),
    ("high_beam",     "Fernlicht",      0, 2, False),
    ("work_light",    "Arbeitslicht",   1, 0, False),
    ("beacon",        "Rundumleuchte",  1, 1, False),
    ("horn",          "Hupe",           1, 2, True),
    ("blinker_left",  "Blinker links",  2, 0, False),
    ("hazard",        "Warnblinker",    2, 1, False),
    ("blinker_right", "Blinker rechts", 2, 2, False),
]


def _mix(c: QColor, bg: QColor, t: float) -> QColor:
    return QColor(
        int(c.red() * (1 - t) + bg.red() * t),
        int(c.green() * (1 - t) + bg.green() * t),
        int(c.blue() * (1 - t) + bg.blue() * t),
    )


class ControlButton(QAbstractButton):
    def __init__(self, actuator: str, label: str, accent: QColor, parent=None):
        super().__init__(parent)
        self.actuator = actuator
        self._label = label
        self._accent = accent
        self._active = False   # IST-Status (aus VehicleState)
        self.setMinimumSize(150, 120)
        self.setFocusPolicy(Qt.NoFocus)
        self.setCursor(Qt.PointingHandCursor)

    def set_active(self, on: bool):
        if on != self._active:
            self._active = on
            self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        r = QRectF(3, 3, self.width() - 6, self.height() - 6)
        pressed = self.isDown()
        on = self._active

        # --- Glow hinter aktiver Kachel ---
        if on:
            glow = QColor(self._accent)
            glow.setAlpha(55)
            p.setPen(Qt.NoPen)
            p.setBrush(QBrush(glow))
            p.drawRoundedRect(r.adjusted(-2, -2, 2, 2), 18, 18)

        # --- Flaeche (flache Fuellung -- bewusst kein Verlauf, das bandet auf
        #     dem Produktionsdisplay) ---
        if on:
            fill = _mix(self._accent, theme.BG_DEEP, 0.70)
            border = self._accent
            icon_color = QColor("#11151b")  # dunkel auf hellem Akzent
            text_color = QColor("#0e1217")
        else:
            fill = theme.BG_HILITE if pressed else theme.BG_ELEVATED
            border = theme.STROKE
            icon_color = _mix(self._accent, theme.BG_DEEP, 0.35)
            text_color = theme.TEXT_DIM

        p.setPen(QPen(border, 2 if on else 1))
        p.setBrush(QBrush(fill))
        p.drawRoundedRect(r, 16, 16)

        if pressed and not on:
            p.setPen(Qt.NoPen)
            ov = QColor(255, 255, 255, 10)
            p.setBrush(QBrush(ov))
            p.drawRoundedRect(r, 16, 16)

        # --- Icon ---
        isz = min(r.width() * 0.42, r.height() * 0.5, 64)
        ir = QRectF(0, 0, isz, isz)
        ir.moveCenter(QRectF(r.left(), r.top() + r.height() * 0.10,
                             r.width(), r.height() * 0.52).center())
        icons.draw_icon(self.actuator, p, ir, icon_color)

        # --- Label ---
        p.setPen(text_color)
        p.setFont(theme.label(11, QFont.DemiBold, spacing=1.0))
        lr = QRectF(r.left(), r.bottom() - r.height() * 0.26,
                    r.width(), r.height() * 0.22)
        p.drawText(lr, Qt.AlignCenter, self._label)
        p.end()


class Controls(QWidget):
    def __init__(self, state, can, parent=None):
        super().__init__(parent)
        self.state = state
        self.can = can
        self._buttons: dict[str, ControlButton] = {}

        grid = QGridLayout(self)
        grid.setContentsMargins(16, 16, 16, 16)
        grid.setSpacing(16)

        for actuator, label, row, col, is_hold in BUTTONS:
            accent = theme.RED if actuator == "hazard" else theme.ACTUATOR_COLOR[actuator]
            btn = ControlButton(actuator, label, accent)
            if actuator == "hazard":
                btn.clicked.connect(lambda _=False: self._toggle_hazard())
            elif actuator == "blinker_left":
                btn.clicked.connect(lambda _=False: self._set_blinker("left"))
            elif actuator == "blinker_right":
                btn.clicked.connect(lambda _=False: self._set_blinker("right"))
            elif actuator in self.LIGHT_GROUP:
                btn.clicked.connect(lambda _=False, a=actuator: self._set_light(a))
            elif is_hold:
                btn.pressed.connect(lambda a=actuator: self.can.send_command(a, True))
                btn.released.connect(lambda a=actuator: self.can.send_command(a, False))
            else:
                btn.clicked.connect(lambda _=False, a=actuator: self._toggle(a))
            grid.addWidget(btn, row, col)
            self._buttons[actuator] = btn

        for c in range(3):
            grid.setColumnStretch(c, 1)
        for r in range(3):
            grid.setRowStretch(r, 1)

        self.state.changed.connect(self.refresh)
        self.refresh()

    # Scheinwerfer-Modus: Tagfahr-/Abblend-/Fernlicht schliessen sich aus
    # (nur eines an; erneutes Tippen auf das aktive schaltet es aus).
    LIGHT_GROUP = ("day_lights", "low_beam", "high_beam")

    def _toggle(self, actuator: str):
        self.can.send_command(actuator, not self.state.get_actuator(actuator))

    def _set_light(self, actuator: str):
        if self.state.get_actuator(actuator):
            self.can.send_command(actuator, False)
        else:
            self.can.send_command(actuator, True)
            for other in self.LIGHT_GROUP:
                if other != actuator:
                    self.can.send_command(other, False)

    # --- Blinker-Gruppe: links / rechts / Warnblinker schliessen sich aus ---
    def _set_blinker(self, side: str):
        """Tippen auf einen Richtungsblinker. Schaltet den anderen aus; ein
        zweiter Tipp auf den bereits einzeln aktiven Blinker schaltet ihn aus."""
        left = self.state.get_actuator("blinker_left")
        right = self.state.get_actuator("blinker_right")
        if side == "left":
            left_only = left and not right
            self.can.send_command("blinker_left", not left_only)
            self.can.send_command("blinker_right", False)
        else:
            right_only = right and not left
            self.can.send_command("blinker_right", not right_only)
            self.can.send_command("blinker_left", False)

    def _toggle_hazard(self):
        """Warnblinker: beide Blinker gemeinsam an/aus."""
        hazard_on = (self.state.get_actuator("blinker_left")
                     and self.state.get_actuator("blinker_right"))
        target = not hazard_on
        self.can.send_command("blinker_left", target)
        self.can.send_command("blinker_right", target)

    def refresh(self):
        for actuator, btn in self._buttons.items():
            if actuator == "hazard":
                active = (self.state.get_actuator("blinker_left")
                          and self.state.get_actuator("blinker_right"))
            else:
                active = self.state.get_actuator(actuator)
            btn.set_active(active)
