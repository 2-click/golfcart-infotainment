"""Abstrakte CAN-Schnittstelle als QThread.

Beide Implementierungen (real_can, mock_can) erben hiervon. Der Thread treibt
das RX-Loop; eingehende Frames werden via Qt-Signale thread-sicher an den
GUI-Thread gemeldet. TX (Aktor-Befehl) wird ueber send_command() ausgeloest.
"""

from abc import abstractmethod

from PySide6.QtCore import QThread, Signal


class CANInterface(QThread):
    # SPS -> Display: neue Aktor-IST-Bitmaske (8 Bit).
    status_received = Signal(int)
    # SPS -> Display: neue Geschwindigkeit in km/h.
    speed_received = Signal(float)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._running = False

    @abstractmethod
    def send_command(self, actuator: str, on: bool):
        """Display -> SPS: Aktor schalten (TX). Thread-sicher aufrufbar."""
        raise NotImplementedError

    def stop(self):
        """Beendet das RX-Loop und wartet auf den Thread."""
        self._running = False
        self.wait(2000)
