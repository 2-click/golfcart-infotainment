"""Reichweitenberechnung aus SOC, Strom und Geschwindigkeit.

Akku: BATTERY_CAPACITY_AH bei SYSTEM_VOLTAGE_V (config.py).

Formeln:
  verbleibende Energie [Wh] = (SOC% / 100) * Ah * V
  aktuelle Leistung    [W]  = Strom (A) * V
  Reststunden               = Wh / W
  Reichweite [km]           = Reststunden * Geschwindigkeit [km/h]

Praxis:
- gleitender Mittelwert ueber Strom und Geschwindigkeit (sonst springt der Wert)
- Fallback bei Stillstand / ohne Last: Reichweite 0 (statt unendlich)
"""

from collections import deque

import config


class RangeCalculator:
    def __init__(self,
                 voltage: float = None,
                 capacity_ah: float = None,
                 window: int = None):
        self.voltage = voltage if voltage is not None else config.SYSTEM_VOLTAGE_V
        self.capacity_ah = (capacity_ah if capacity_ah is not None
                            else config.BATTERY_CAPACITY_AH)
        window = window if window is not None else config.RANGE_AVG_WINDOW
        self._current_samples = deque(maxlen=window)
        self._speed_samples = deque(maxlen=window)

    @staticmethod
    def _avg(samples) -> float:
        return sum(samples) / len(samples) if samples else 0.0

    def update(self, soc_pct: float, current_a: float, speed_kmh: float) -> float:
        """Fuegt neue Messwerte hinzu und liefert die geglaettete Reichweite (km).

        Liefert 0.0, wenn das Fahrzeug steht oder keine Last anliegt
        (sonst wuerde die Reichweite gegen unendlich gehen).
        """
        self._current_samples.append(current_a)
        self._speed_samples.append(speed_kmh)

        avg_current = self._avg(self._current_samples)
        avg_speed = self._avg(self._speed_samples)

        if avg_speed < config.MIN_SPEED_KMH or avg_current < config.MIN_CURRENT_A:
            return 0.0

        remaining_wh = (soc_pct / 100.0) * self.capacity_ah * self.voltage
        power_w = avg_current * self.voltage
        if power_w <= 0:
            return 0.0

        remaining_hours = remaining_wh / power_w
        return remaining_hours * avg_speed
