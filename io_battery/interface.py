"""Abstrakte Batterie-Schnittstelle (BMS) als QThread.

Eigenstaendiges Interface parallel zum CAN. Liefert SOC (%) und Strom (A)
periodisch via Qt-Signale in den GUI-Thread.
"""

from PySide6.QtCore import QThread, Signal


class BatteryInterface(QThread):
    # BMS -> Display: neuer Ladezustand in Prozent.
    soc_received = Signal(float)
    # BMS -> Display: neuer Strom in Ampere.
    current_received = Signal(float)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._running = False

    def stop(self):
        self._running = False
        self.wait(2000)
