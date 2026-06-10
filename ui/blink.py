"""BlinkController -- zentrale Blink-Uhr fuer alle blinkenden Layer/Telltales.

Ein einziger schneller Timer treibt zwei unterschiedliche Muster, sodass die
Darstellung im Cart-View und in der Telltale-Leiste synchron laeuft:

- "turn"   (Blinker links/rechts): ruhiges Blinken (Rechteck-Welle,
            Halbperiode BLINK_INTERVAL_MS).
- "beacon" (Rundumleuchte): Doppelblitz -- zwei kurze Blitze schnell
            hintereinander, dann eine laengere Pause.

Wichtig: Beim Einschalten (off->on) wird der jeweilige Takt neu gestartet
(eigener Phasen-Ursprung pro Muster). Sonst kann das erste Blinken extrem kurz
ausfallen, wenn man zufaellig kurz vor dem naechsten Umschaltpunkt einschaltet.

Widgets verbinden sich mit `tick` (wird nur bei tatsaechlicher Zustands-
aenderung emittiert) und fragen pro Aktor `is_on(name)` ab.
"""

from PySide6.QtCore import QObject, QTimer, Signal

import config

# Aktoren, deren Sichtbarkeit von einem Blink-Muster moduliert wird.
_TURN = ("blinker_left", "blinker_right")
_BEACON = "beacon"

_RESOLUTION_MS = 25  # Timer-Aufloesung (40 Hz) -> knackige Blitze


class BlinkController(QObject):
    tick = Signal()

    def __init__(self, state, parent=None):
        super().__init__(parent)
        self.state = state
        self._elapsed = 0
        # Phasen-Ursprung je Muster (wird beim Einschalten neu gesetzt).
        self._turn_origin = 0
        self._beacon_origin = 0
        # Letzter bekannter Ein-Zustand, um steigende Flanken zu erkennen.
        self._prev = {"blinker_left": False, "blinker_right": False,
                      "beacon": False}

        self._turn_on = self._compute_turn(0)
        self._beacon_on = self._compute_beacon(0)

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._on_timeout)
        self._timer.start(_RESOLUTION_MS)

        # Auf Zustandsaenderungen lauschen, um beim Einschalten neu zu starten.
        self.state.changed.connect(self._on_state_changed)

    # --- Muster-Berechnung (relativ zum jeweiligen Ursprung) --------------
    def _compute_turn(self, elapsed: int) -> bool:
        period = 2 * config.BLINK_INTERVAL_MS
        return ((elapsed - self._turn_origin) % period) < config.BLINK_INTERVAL_MS

    def _compute_beacon(self, elapsed: int) -> bool:
        f = config.BEACON_FLASH_MS
        g = config.BEACON_GAP_MS
        cycle = 2 * f + g + config.BEACON_PAUSE_MS
        t = (elapsed - self._beacon_origin) % cycle
        # Blitz 1: [0, f)   Blitz 2: [f+g, f+g+f)
        return (t < f) or (f + g <= t < 2 * f + g)

    def _refresh(self):
        turn = self._compute_turn(self._elapsed)
        beacon = self._compute_beacon(self._elapsed)
        if turn != self._turn_on or beacon != self._beacon_on:
            self._turn_on = turn
            self._beacon_on = beacon
            self.tick.emit()

    def _on_timeout(self):
        self._elapsed += _RESOLUTION_MS
        self._refresh()

    def _on_state_changed(self):
        """Steigende Flanke (off->on) -> Takt des Musters neu starten, damit das
        erste Blinken volle Laenge hat."""
        reset_turn = False
        for name in _TURN:
            now = self.state.get_actuator(name)
            if now and not self._prev[name]:
                reset_turn = True
            self._prev[name] = now

        now_beacon = self.state.get_actuator(_BEACON)
        reset_beacon = now_beacon and not self._prev[_BEACON]
        self._prev[_BEACON] = now_beacon

        if reset_turn:
            self._turn_origin = self._elapsed
        if reset_beacon:
            self._beacon_origin = self._elapsed
        if reset_turn or reset_beacon:
            self._refresh()  # sofort in die EIN-Phase

    # --- Abfrage ----------------------------------------------------------
    def is_on(self, actuator: str) -> bool:
        """Blink-Phase fuer einen Aktor. Nicht-blinkende Aktoren -> immer True
        (ihre Sichtbarkeit haengt dann allein am VehicleState)."""
        if actuator == _BEACON:
            return self._beacon_on
        if actuator in _TURN:
            return self._turn_on
        return True
