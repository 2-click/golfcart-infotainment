"""MainWindow -- 1600x600 Cockpit-Layout, horizontale Dreiteilung.

  Links  (~600 px): CartView (PNG-Layer-Stack + Spotlight-Backdrop)
  Mitte  (~380 px): Telemetry (Telltales + Tacho + Stat-Kacheln)
  Rechts (~620 px): Controls (8 Touch-Tiles)
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QMainWindow, QWidget, QHBoxLayout, QFrame,
                               QStackedWidget)

import config
from . import theme
from .blink import BlinkController
from .cart_view import CartView
from .telemetry import Telemetry
from .controls import Controls
from .splash import SplashScreen
from .pinpad import PinPad

ADMIN_PIN = "0000"

MID_WIDTH = 380


class MainWindow(QMainWindow):
    def __init__(self, state, can, parent=None):
        super().__init__(parent)
        self.state = state
        self.setWindowTitle("Golfcart Infotainment")
        self.setFixedSize(config.SCREEN_WIDTH, config.SCREEN_HEIGHT)

        central = QWidget()
        central.setStyleSheet(
            "QWidget {"
            f"  background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1,"
            f"    stop:0 {theme.BG_PANEL.name()}, stop:1 {theme.BG_DEEP.name()});"
            "}"
        )
        self.setCentralWidget(central)
        layout = QHBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Eine zentrale Blink-Uhr fuer Cart-View und Telltale-Leiste -> beide
        # blinken synchron (ruhiger Blinker + Doppelblitz der Rundumleuchte).
        # Bekommt den State, um beim Einschalten den Takt neu zu starten.
        self.blink = BlinkController(state, self)

        # Links: Cart (quadratisch, ~600 px), umschaltbar mit dem versteckten
        # PIN-Pad (Admin-Zugang). Der Spotlight-Backdrop der CartView fuellt
        # die ganze Spalte -> nahtlos.
        cart_wrap = QFrame()
        cart_wrap.setFixedWidth(config.CART_AREA)
        cart_wrap.setStyleSheet("background: transparent;")
        cart_layout = QHBoxLayout(cart_wrap)
        cart_layout.setContentsMargins(0, 0, 0, 0)
        cart_layout.setSpacing(0)
        self.cart = CartView(state, self.blink)
        self.pinpad = PinPad()
        self.left_stack = QStackedWidget()
        self.left_stack.addWidget(self.cart)     # Index 0
        self.left_stack.addWidget(self.pinpad)   # Index 1
        cart_layout.addWidget(self.left_stack)

        # Verstecktes Admin-Flow: 5 Klicks -> PIN, korrekt -> Admin-Modus.
        self._can = can
        self.cart.pinRequested.connect(self._show_pin)
        self.pinpad.submitted.connect(self._check_pin)
        self.pinpad.cancelled.connect(self._show_cart)
        self.cart.adminChanged.connect(self._on_admin)

        # Mitte: Telemetrie.
        self.telemetry = Telemetry(state, self.blink)
        self.telemetry.setFixedWidth(MID_WIDTH)
        self.telemetry.setStyleSheet("background: transparent;")

        # Rechts: Controls (Rest).
        self.controls = Controls(state, can)
        self.controls.setStyleSheet("background: transparent;")

        layout.addWidget(cart_wrap)
        layout.addWidget(self._divider())
        layout.addWidget(self.telemetry)
        layout.addWidget(self._divider())
        layout.addWidget(self.controls, 1)

        # Splash-Overlay ueber dem gesamten Fenster (blendet nach kurzer Zeit
        # aus und gibt das Cockpit frei).
        self.splash = SplashScreen(self)
        self.splash.setGeometry(0, 0, config.SCREEN_WIDTH, config.SCREEN_HEIGHT)
        self.splash.raise_()

    # --- Versteckter Admin-Flow ------------------------------------------
    def _show_pin(self):
        self.pinpad.clear()
        self.left_stack.setCurrentWidget(self.pinpad)

    def _show_cart(self):
        self.left_stack.setCurrentWidget(self.cart)

    def _check_pin(self, pin: str):
        if pin == ADMIN_PIN:
            self.cart.set_admin(True)
            self._show_cart()
        else:
            self.pinpad.reject()

    def _on_admin(self, on: bool):
        # Admin hebt das Tempo-Limit (Tacho-Endwert + Mock-Geschwindigkeit).
        self.state.admin_mode = on
        limit = config.SPEEDO_MAX_ADMIN if on else config.SPEEDO_MAX_DEFAULT
        if hasattr(self._can, "set_speed_limit"):
            self._can.set_speed_limit(limit)

    @staticmethod
    def _divider() -> QFrame:
        """Feine, vertikal verlaufende Trennlinie (in der Mitte am hellsten)."""
        line = QFrame()
        line.setFixedWidth(2)
        c = theme.STROKE.name()
        soft = theme.BG_DEEP.name()
        line.setStyleSheet(
            "QFrame {"
            f"  background: qlineargradient(x1:0, y1:0, x2:0, y2:1,"
            f"    stop:0 {soft}, stop:0.5 {c}, stop:1 {soft});"
            "}"
        )
        return line
