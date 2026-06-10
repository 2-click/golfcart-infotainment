"""MockCAN -- simuliertes CAN-Backend fuer die Entwicklung (WSL, keine Hardware).

Verhalten:
- Closed-Loop: Auf send_command() hin wird der interne IST-Status sofort
  aktualisiert und via status_received zurueckgemeldet -- so fuehlt sich das
  Schalten in der Entwicklung direkt an (wie eine ideale, fehlerfreie SPS).
- Telemetrie: erzeugt eine plausible, sanft schwankende Geschwindigkeit und
  meldet sie periodisch via speed_received.
"""

import math
import random
import threading

from .interface import CANInterface
from . import canmap
import config


class MockCAN(CANInterface):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._states = {name: False for name in config.ACTUATORS}
        self._lock = threading.Lock()
        self._t = 0.0  # Simulationszeit (s)
        # Tempo-Limit: die simulierte Geschwindigkeit bleibt darunter. Wird im
        # Admin-Modus angehoben; das wirksame Limit folgt sanft -> Speed steigt
        # fluessig statt zu springen.
        self._speed_limit = float(config.SPEEDO_MAX_DEFAULT)
        self._eff_limit = float(config.SPEEDO_MAX_DEFAULT)

    def set_speed_limit(self, limit: float):
        """Thread-sicher das Ziel-Tempolimit setzen (z.B. Admin-Modus)."""
        with self._lock:
            self._speed_limit = float(limit)

    # --- TX: Display -> SPS ------------------------------------------------
    def send_command(self, actuator: str, on: bool):
        # Eine ideale SPS schaltet sofort und meldet den neuen IST-Status.
        with self._lock:
            self._states[actuator] = bool(on)
            mask = canmap.decode_status(canmap.encode_status(self._states))
        self.status_received.emit(mask)

    # --- RX-Loop: Telemetrie simulieren -----------------------------------
    def run(self):
        self._running = True
        # Sanfte Geschwindigkeitskurve, skaliert aufs wirksame Tempolimit.
        while self._running:
            self._t += 0.1
            with self._lock:
                target = self._speed_limit
            # Wirksames Limit sanft nachfuehren (fluessiger Uebergang 10<->30).
            self._eff_limit += (target - self._eff_limit) * 0.04
            # Welle zwischen ~15 % und ~95 % des wirksamen Limits.
            wave = 0.55 + 0.40 * math.sin(self._t * 0.15)
            noise = random.uniform(-0.02, 0.02) * self._eff_limit
            speed = max(0.0, min(self._eff_limit, self._eff_limit * wave + noise))
            self.speed_received.emit(speed)
            self.msleep(100)  # 10 Hz
