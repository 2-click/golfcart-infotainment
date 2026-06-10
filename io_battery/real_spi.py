"""RealSPI -- echtes BMS-Backend ueber SPI (Platzhalter).

Das konkrete BMS-SPI-Protokoll muss noch gesniffed werden. Dieser Platzhalter
zeigt die Struktur: spidev wird LAZY importiert (erst in run()), damit der
Mock-Betrieb in WSL nicht an einer fehlenden Library scheitert.

TODO (sobald Protokoll bekannt):
- SPI-Bus/Device, Mode, max_speed_hz festlegen
- Roh-Frames lesen und in SOC (%) und Strom (A) dekodieren
- soc_received / current_received emittieren
"""

from .interface import BatteryInterface
import config


class RealSPI(BatteryInterface):
    def __init__(self, parent=None, bus: int = 0, device: int = 0):
        super().__init__(parent)
        self._bus = bus
        self._device = device
        self._spi = None

    def _ensure_spi(self):
        if self._spi is None:
            import spidev  # lazy import (nur im real-Backend)
            self._spi = spidev.SpiDev()
            self._spi.open(self._bus, self._device)
            self._spi.max_speed_hz = 1_000_000
            self._spi.mode = 0
        return self._spi

    def run(self):
        self._running = True
        spi = self._ensure_spi()
        while self._running:
            # TODO: echtes Protokoll. Beispiel-Skelett:
            #   raw = spi.xfer2([REGISTER, 0x00, 0x00])
            #   soc = decode_soc(raw)
            #   current = decode_current(raw)
            #   self.soc_received.emit(soc)
            #   self.current_received.emit(current)
            self.msleep(1000)

    def stop(self):
        super().stop()
        if self._spi is not None:
            try:
                self._spi.close()
            except Exception:
                pass
            self._spi = None
