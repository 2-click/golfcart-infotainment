"""PinPad -- versteckter PIN-Dialog fuer den Admin-Modus.

Erscheint in der linken Spalte (anstelle des Carts), wenn der Cart 5x getippt
wird. Bei korrektem PIN meldet `submitted` den eingegebenen Code; der Aufrufer
entscheidet (richtig -> Admin-Modus, falsch -> reject()). `cancelled` kehrt
ohne Freischaltung zum Cart zurueck.
"""

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QGridLayout, QPushButton,
                               QLabel)

from . import theme

PIN_LENGTH = 4


class PinPad(QWidget):
    submitted = Signal(str)
    cancelled = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._entry = ""

        root = QVBoxLayout(self)
        root.setContentsMargins(40, 30, 40, 30)
        root.setSpacing(8)

        title = QLabel("ADMIN-ZUGANG")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet(
            f"color: {theme.TEXT.name()}; font-size: 22px; font-weight: 700;"
            " letter-spacing: 3px;")

        self.status = QLabel("PIN EINGEBEN")
        self.status.setAlignment(Qt.AlignCenter)
        self.status.setStyleSheet(
            f"color: {theme.TEXT_DIM.name()}; font-size: 13px; letter-spacing: 2px;")

        self.dots = QLabel()
        self.dots.setAlignment(Qt.AlignCenter)
        self.dots.setStyleSheet(
            f"color: {theme.AMBER_HI.name()}; font-family: '{theme.MONO_FAMILY}';"
            " font-size: 40px; letter-spacing: 10px;")

        root.addStretch(1)
        root.addWidget(title)
        root.addWidget(self.status)
        root.addSpacing(6)
        root.addWidget(self.dots)
        root.addSpacing(14)

        grid = QGridLayout()
        grid.setSpacing(12)
        # 1..9
        for i in range(9):
            d = str(i + 1)
            grid.addWidget(self._digit(d), i // 3, i % 3)
        # ⌫  0  ✕
        grid.addWidget(self._action("⌫", self._backspace), 3, 0)
        grid.addWidget(self._digit("0"), 3, 1)
        grid.addWidget(self._action("✕", self.cancelled.emit), 3, 2)
        root.addLayout(grid)
        root.addStretch(1)

        self._update_dots()

    # --- Buttons ----------------------------------------------------------
    def _digit(self, d: str) -> QPushButton:
        b = self._button(d)
        b.clicked.connect(lambda _=False, x=d: self._press(x))
        return b

    def _action(self, text: str, slot) -> QPushButton:
        b = self._button(text)
        b.clicked.connect(lambda _=False: slot())
        return b

    def _button(self, text: str) -> QPushButton:
        b = QPushButton(text)
        b.setFocusPolicy(Qt.NoFocus)
        b.setCursor(Qt.PointingHandCursor)
        b.setMinimumSize(96, 70)
        b.setStyleSheet(
            "QPushButton {"
            f"  color: {theme.TEXT.name()}; background: {theme.BG_ELEVATED.name()};"
            f"  border: 1px solid {theme.STROKE.name()}; border-radius: 14px;"
            "  font-size: 30px; font-weight: 700; }"
            f"QPushButton:pressed {{ background: {theme.BG_HILITE.name()}; }}"
        )
        return b

    # --- Eingabe-Logik ----------------------------------------------------
    def _press(self, d: str):
        if len(self._entry) >= PIN_LENGTH:
            return
        self._entry += d
        self._update_dots()
        if len(self._entry) == PIN_LENGTH:
            # kurz anzeigen, dann pruefen lassen
            QTimer.singleShot(140, lambda: self.submitted.emit(self._entry))

    def _backspace(self):
        self._entry = self._entry[:-1]
        self._update_dots()

    def _update_dots(self):
        filled = "●" * len(self._entry)
        empty = "○" * (PIN_LENGTH - len(self._entry))
        self.dots.setText(filled + empty)

    def _set_status(self, text: str, error: bool = False):
        color = theme.RED.name() if error else theme.TEXT_DIM.name()
        self.status.setStyleSheet(
            f"color: {color}; font-size: 13px; letter-spacing: 2px;")
        self.status.setText(text)

    # --- Vom Aufrufer gesteuert ------------------------------------------
    def clear(self):
        self._entry = ""
        self._set_status("PIN EINGEBEN")
        self._update_dots()

    def reject(self):
        """Falscher PIN -> Hinweis + Eingabe leeren."""
        self._entry = ""
        self._set_status("FALSCHER PIN", error=True)
        self._update_dots()
