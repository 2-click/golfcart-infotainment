"""VehicleState: die einzige Wahrheit ueber den Fahrzeugzustand.

QObject mit einem zentralen `changed`-Signal. CAN- und SPI-Threads schreiben
hier rein (thread-sicher ueber Qt-Signal/Slot bzw. einfache Attribut-Setter,
die im jeweiligen Thread laufen und dann `changed` emittieren), range_calc
ergaenzt die Reichweite, die UI liest und rendert reaktiv.

WICHTIG (Closed-Loop): Die Aktor-Felder spiegeln den IST-Status, den die SPS
via CAN zurueckmeldet -- nicht den Button-Wunsch. Ein Button loest nur ein
CAN-TX aus; gesetzt wird das Feld erst durch die Status-Rueckmeldung.
"""

from PySide6.QtCore import QObject, Signal

import config


class VehicleState(QObject):
    # Wird bei jeder Aenderung emittiert. Die UI verbindet sich damit und
    # rendert neu. Bewusst ein einziges, einfaches Signal (kein Feld-Detail),
    # damit Sender sich nicht um Granularitaet kuemmern muessen.
    changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)

        # --- Aktoren / Lichter (IST-Status, von SPS via CAN) ---
        for name in config.ACTUATORS:
            setattr(self, f"_{name}", False)

        # --- Telemetrie ---
        self._speed_kmh = 0.0   # via CAN
        self._soc_pct = 0.0     # via SPI/BMS
        self._current_a = 0.0    # via SPI/BMS
        self._range_km = 0.0     # berechnet in range_calc

        # --- Handgas (Gasgriff-Stellung 0..100 %, vom Fahrer eingestellt).
        # Das resultierende Tempo ist nicht bekannt -> reine Prozent-Stellung. ---
        self._throttle_pct = 0.0  # 0 = aus

        # --- Admin-Modus (hebt u.a. das Tempo-Limit von 10 auf 30 km/h) ---
        self._admin_mode = False

    # ------------------------------------------------------------------
    # Aktor-Zugriff
    # ------------------------------------------------------------------
    def get_actuator(self, name: str) -> bool:
        return getattr(self, f"_{name}")

    def set_actuators_from_mask(self, mask: int):
        """Setzt alle Aktor-IST-Zustaende aus einer 8-Bit-Bitmaske (CAN-Status).

        Bit i entspricht config.ACTUATORS[i]. Emittiert `changed` nur, wenn
        sich tatsaechlich etwas geaendert hat.
        """
        dirty = False
        for i, name in enumerate(config.ACTUATORS):
            new = bool(mask & (1 << i))
            attr = f"_{name}"
            if getattr(self, attr) != new:
                setattr(self, attr, new)
                dirty = True
        if dirty:
            self.changed.emit()

    # ------------------------------------------------------------------
    # Telemetrie-Properties (setter emittieren changed bei Aenderung)
    # ------------------------------------------------------------------
    def _set(self, attr: str, value):
        if getattr(self, attr) != value:
            setattr(self, attr, value)
            self.changed.emit()

    @property
    def speed_kmh(self) -> float:
        return self._speed_kmh

    @speed_kmh.setter
    def speed_kmh(self, v: float):
        self._set("_speed_kmh", float(v))

    @property
    def soc_pct(self) -> float:
        return self._soc_pct

    @soc_pct.setter
    def soc_pct(self, v: float):
        self._set("_soc_pct", float(v))

    @property
    def current_a(self) -> float:
        return self._current_a

    @current_a.setter
    def current_a(self, v: float):
        self._set("_current_a", float(v))

    @property
    def range_km(self) -> float:
        return self._range_km

    @range_km.setter
    def range_km(self, v: float):
        self._set("_range_km", float(v))

    @property
    def throttle_pct(self) -> float:
        return self._throttle_pct

    @throttle_pct.setter
    def throttle_pct(self, v: float):
        self._set("_throttle_pct", float(v))

    @property
    def throttle_active(self) -> bool:
        return self._throttle_pct > 0.0

    @property
    def admin_mode(self) -> bool:
        return self._admin_mode

    @admin_mode.setter
    def admin_mode(self, v: bool):
        self._set("_admin_mode", bool(v))
