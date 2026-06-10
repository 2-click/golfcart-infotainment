"""RealCAN -- echtes CAN-Backend (Raspberry Pi 5, socketcan auf can0).

python-can wird LAZY importiert (erst in run()/send_command), damit der
Mock-Betrieb in WSL nicht an einer fehlenden Library scheitert.

Voraussetzung auf dem Pi (siehe README):
    sudo ip link set can0 up type can bitrate 250000
"""

import threading

from .interface import CANInterface
from . import canmap
import config


class RealCAN(CANInterface):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._bus = None
        self._lock = threading.Lock()

    def _ensure_bus(self):
        if self._bus is None:
            import can  # lazy import (nur im real-Backend)
            self._bus = can.Bus(
                interface="socketcan",
                channel=config.CAN_CHANNEL,
                bitrate=config.CAN_BITRATE,
            )
        return self._bus

    # --- TX: Display -> SPS ------------------------------------------------
    def send_command(self, actuator: str, on: bool):
        import can  # lazy import
        can_id, data = canmap.encode_command(actuator, on)
        msg = can.Message(arbitration_id=can_id, data=data, is_extended_id=False)
        with self._lock:
            bus = self._ensure_bus()
            bus.send(msg)

    # --- RX-Loop: Frames empfangen und dispatchen --------------------------
    def run(self):
        self._running = True
        bus = self._ensure_bus()
        while self._running:
            msg = bus.recv(timeout=0.2)  # blockiert max. 200 ms
            if msg is None:
                continue
            if msg.arbitration_id == canmap.STATUS_ID:
                self.status_received.emit(canmap.decode_status(msg.data))
            elif msg.arbitration_id == canmap.TELEMETRY_ID:
                self.speed_received.emit(canmap.decode_speed(msg.data))

    def stop(self):
        super().stop()
        if self._bus is not None:
            try:
                self._bus.shutdown()
            except Exception:
                pass
            self._bus = None
