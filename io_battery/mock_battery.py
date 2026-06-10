"""MockBattery -- simuliertes BMS fuer die Entwicklung.

- SOC sinkt langsam (und springt am unteren Ende wieder hoch, damit die Demo
  weiterlaeuft).
- Strom schwankt plausibel um einen Fahr-Grundwert.
"""

import random

from .interface import BatteryInterface


class MockBattery(BatteryInterface):
    def __init__(self, parent=None, start_soc: float = 87.0):
        super().__init__(parent)
        self._soc = start_soc

    def run(self):
        self._running = True
        while self._running:
            # Strom: Grundlast ~30 A, schwankt plausibel (Beschleunigen/Rollen).
            current = max(2.0, random.gauss(30.0, 8.0))
            self.current_received.emit(current)

            # SOC sinkt langsam; Demo-Wraparound bei 5 %.
            self._soc -= 0.02
            if self._soc < 5.0:
                self._soc = 87.0
            self.soc_received.emit(self._soc)

            self.msleep(1000)  # 1 Hz
