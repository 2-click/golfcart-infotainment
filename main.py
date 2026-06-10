"""Entrypoint: Qt-App, Backend-Auswahl, Thread-Verdrahtung.

Ein einziger Python-Prozess fuer UI, CAN und SPI. CAN und Batterie laufen je in
einem eigenen QThread und schreiben thread-sicher (ueber Qt-Signale) in den
VehicleState. range_calc ergaenzt periodisch die Reichweite. Die UI liest.
"""

import signal
import sys

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

import config
from core.state import VehicleState
from core.range_calc import RangeCalculator
from ui.main_window import MainWindow


def make_can():
    """Waehlt das CAN-Backend. real_can importiert seine HW-Lib erst beim Start."""
    if config.CAN_BACKEND == "real":
        from io_can.real_can import RealCAN
        return RealCAN()
    from io_can.mock_can import MockCAN
    return MockCAN()


def make_battery():
    """Waehlt das Batterie-Backend. real_spi importiert spidev erst beim Start."""
    if config.BATTERY_BACKEND == "real":
        from io_battery.real_spi import RealSPI
        return RealSPI()
    from io_battery.mock_battery import MockBattery
    return MockBattery()


def main():
    app = QApplication(sys.argv)
    from ui import theme
    app.setStyleSheet(theme.global_qss())

    state = VehicleState()
    can = make_can()
    battery = make_battery()
    range_calc = RangeCalculator()

    # --- Verdrahtung: Backends -> VehicleState (Qt queued ueber Thread-Grenze)
    can.status_received.connect(state.set_actuators_from_mask)
    can.speed_received.connect(lambda v: setattr(state, "speed_kmh", v))
    battery.soc_received.connect(lambda v: setattr(state, "soc_pct", v))
    battery.current_received.connect(lambda v: setattr(state, "current_a", v))

    # --- Reichweite periodisch berechnen (GUI-Thread, 1 Hz) ---
    def update_range():
        state.range_km = range_calc.update(
            state.soc_pct, state.current_a, state.speed_kmh)

    range_timer = QTimer()
    range_timer.timeout.connect(update_range)
    range_timer.start(1000)

    window = MainWindow(state, can)
    window.show()

    # --- Threads starten ---
    can.start()
    battery.start()

    # --- Sauberes Herunterfahren ---
    def shutdown():
        can.stop()
        battery.stop()

    app.aboutToQuit.connect(shutdown)

    # --- Ctrl-C im Terminal sauber behandeln ---
    # Waehrend app.exec() in C++ laeuft, ruft Python seinen SIGINT-Handler nicht
    # auf -> Ctrl-C wuerde ignoriert. Loesung: SIGINT -> app.quit() und ein
    # leerer QTimer, der den Interpreter regelmaessig aufweckt, damit das Signal
    # verarbeitet wird (loest dann aboutToQuit -> shutdown aus).
    signal.signal(signal.SIGINT, lambda *_: app.quit())
    wakeup = QTimer()
    wakeup.timeout.connect(lambda: None)
    wakeup.start(200)

    print(f"[main] CAN_BACKEND={config.CAN_BACKEND} "
          f"BATTERY_BACKEND={config.BATTERY_BACKEND} "
          f"voltage={config.SYSTEM_VOLTAGE_V}V")

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
