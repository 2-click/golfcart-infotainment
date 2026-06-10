# Golfcart Infotainment

Infotainment-Anwendung für ein Golfcart auf einem fest verbauten 9,3-Zoll-
Touchdisplay (**1600 × 600 px**, Querformat) an einem **Raspberry Pi 5**.

- **Links:** Cart-Abbildung aus gestapelten PNG-Layern, die den realen
  Beleuchtungszustand spiegelt (Closed-Loop).
- **Mitte:** Telemetrie (Speed groß, darunter SOC / Strom / Reichweite).
- **Rechts:** 8 fingergroße Touch-Buttons zum Schalten der Aktoren.

GUI: **PySide6 (Qt 6)**, native Desktop-App. Kein Browser, kein WebSocket.
Ein einziger Python-Prozess für UI, CAN und SPI.

---

## Schnellstart (Entwicklung, WSL/WSLg)

```bash
pip install --user PySide6      # bzw. requirements.txt
./run_dev.sh
```

`run_dev.sh` setzt automatisch:

```bash
export CAN_BACKEND=mock
export BATTERY_BACKEND=mock
export QT_QPA_PLATFORM=xcb
```

Im Mock-Modus wird **keine Hardware** benötigt: `MockCAN` meldet Aktor-Status
sofort zurück (fühlt sich direkt an) und simuliert Geschwindigkeit,
`MockBattery` simuliert SOC und Strom.

### WSL-Hinweise

Einmalig in Windows PowerShell: `wsl --update`. In WSL `echo $DISPLAY` sollte
z. B. `:0` zeigen. Falls Qt beim Start meckert:

```bash
sudo apt install -y libxcb-cursor0 libxkbcommon-x11-0 libegl1
```

---

## Architektur

```
main.py            Entrypoint: Qt-App, Backend-Auswahl, Thread-Verdrahtung
config.py          Env-Switch (mock/real), Akkudaten, Spannung, Konstanten
core/
  state.py         VehicleState (QObject + changed-Signal) — einzige Wahrheit
  range_calc.py    Reichweitenberechnung (gleitender Mittelwert)
io_can/
  interface.py     ABC CANInterface (QThread)
  canmap.py        CAN-Protokoll: ID <-> Signal Mapping (verbindliche SPS-Doku)
  mock_can.py      Sim: sofortige Status-Rückmeldung + Speed
  real_can.py      python-can / socketcan (lazy import)
io_battery/
  interface.py     ABC BatteryInterface (QThread)
  mock_battery.py  Sim: SOC sinkt, Strom schwankt
  real_spi.py      spidev (Platzhalter, BMS-Protokoll noch zu sniffen)
ui/
  main_window.py   1600×600, 3 Spalten (QHBoxLayout)
  cart_view.py     PNG-Layer-Stack + synchrone Blink-Logik
  controls.py      8 Touch-Buttons (Closed-Loop)
  telemetry.py     Speed/SOC/A/Reichweite
  assets/          Platzhalter-PNGs (gleiche Canvas-Größe, transparent)
tools/
  gen_assets.py    erzeugt die Platzhalter-PNGs neu
```

### Threading

Qt-Eventloop treibt die UI. CAN und SPI laufen je in einem eigenen `QThread`
und schreiben über Qt-Signale (queued über die Thread-Grenze) in den
`VehicleState`. Der State emittiert `changed`; die UI aktualisiert im
GUI-Thread. `range_calc` läuft per QTimer (1 Hz) im GUI-Thread.

### Closed-Loop-Steuerung

Ein Button setzt **nicht** direkt den Layer:

1. Tippen „Fernlicht“
2. CAN-TX „Aktor `high_beam` ON“ → SPS
3. SPS schaltet Relais
4. SPS meldet IST-Status via CAN-RX zurück
5. `VehicleState.high_beam = True`
6. UI blendet Layer `high_beam.png` ein

So spiegelt das Display immer die Realität (Relais/Sicherung defekt → Layer
bleibt aus). Im Mock meldet `MockCAN` den Status sofort zurück.

---

## CAN-Protokoll (selbst definiert, `io_can/canmap.py`)

Verbindliche Spezifikation für die SPS-Seite.

| Parameter   | Wert                                  |
|-------------|---------------------------------------|
| Bitrate     | **250 kbit/s** (`config.CAN_BITRATE`) |
| Endianness  | **Big-Endian** (Motorola)             |
| Frame-Typ   | Standard (11-Bit IDs)                 |

### Aktor-Index (Bitmaske-Position)

| Index | Aktor          | Bedeutung           |
|-------|----------------|---------------------|
| 0     | `day_lights`   | Tagfahrlicht        |
| 1     | `low_beam`     | Abblendlicht        |
| 2     | `high_beam`    | Fernlicht           |
| 3     | `work_light`   | Arbeitsscheinwerfer |
| 4     | `beacon`       | Rundumleuchte       |
| 5     | `blinker_left` | Blinker links       |
| 6     | `blinker_right`| Blinker rechts      |
| 7     | `horn`         | Hupe                |

### Frames

**Command — Display → SPS — ID `0x200`, DLC 2**

| Byte | Inhalt                       |
|------|------------------------------|
| 0    | Aktor-Index (0..7)           |
| 1    | `0` = aus, `1` = an          |

**Status — SPS → Display — ID `0x201`, DLC 1**

| Byte | Inhalt                                          |
|------|-------------------------------------------------|
| 0    | Bitmaske aller 8 Aktor-IST-Zustände (Bit i = Index i) |

**Telemetrie — SPS → Display — ID `0x202`, DLC 2**

| Byte | Inhalt                                                |
|------|-------------------------------------------------------|
| 0..1 | Geschwindigkeit in **0,1 km/h**, Big-Endian, unsigned |

Beispiel: `0x00 0xFA` = 250 → **25,0 km/h**.

---

## SPI / Batterie (BMS)

Eigenständiges Interface parallel zum CAN, liefert **SOC (%)** und **Strom (A)**.

- `MockBattery` (Dev): SOC sinkt langsam, Strom schwankt plausibel.
- `real_spi.py`: **Platzhalter** — das BMS-SPI-Protokoll muss noch gesniffed
  werden (Bus/Device, Mode, Register, Dekodierung von SOC/Strom). `spidev`
  wird lazy importiert.

---

## Reichweitenberechnung (`core/range_calc.py`)

Akku: **105 Ah** bei **48 V** (Default, vom Nutzer bestätigt;
`config.SYSTEM_VOLTAGE_V`, später ggf. live vom BMS).

```
verbleibende Energie [Wh] = (SOC% / 100) · Ah · V
aktuelle Leistung    [W]  = Strom (A) · V
Reststunden               = Wh / W
Reichweite [km]           = Reststunden · Geschwindigkeit [km/h]
```

- Gleitender Mittelwert über Strom und Geschwindigkeit (`RANGE_AVG_WINDOW`),
  sonst springt der Wert.
- Fallback bei Stillstand / ohne Last → Reichweite `0` (statt unendlich).

---

## Konfiguration (`config.py` / ENV)

| ENV                | Default  | Bedeutung                          |
|--------------------|----------|------------------------------------|
| `CAN_BACKEND`      | `mock`   | `mock` / `real`                    |
| `BATTERY_BACKEND`  | `mock`   | `mock` / `real`                    |
| `CAN_CHANNEL`      | `can0`   | socketcan-Interface                |
| `CAN_BITRATE`      | `250000` | CAN-Bitrate                        |
| `SYSTEM_VOLTAGE_V` | `48.0`   | Systemspannung für Reichweite      |
| `BATTERY_CAPACITY_AH` | `105.0` | Akku-Nennkapazität              |
| `BLINK_INTERVAL_MS`| `500`    | Blink-Halbperiode                  |

---

## Assets

Alle PNGs sind **deckungsgleich** (gleiche Canvas-Größe, transparent) und
werden position-exakt gestapelt. `cart_base.png` ist die echte Cart-Grafik
(aktuell **1213 × 925**, RGBA). `CartView` passt den Stack seitenverhältnis-treu
in die linke Spalte ein und zeichnet alle Layer in dasselbe Zielrechteck.

Die **Licht-Layer sind noch Platzhalter** (Glows grob über den realen
Lichtpositionen). `tools/gen_assets.py` liest die Größe von `cart_base.png` und
erzeugt die Licht-Layer deckungsgleich dazu neu:

```bash
QT_QPA_PLATFORM=offscreen python3 tools/gen_assets.py
```

Echte Licht-PNGs ersetzen die Platzhalter 1:1 (gleiche Dateinamen, **gleiche
Canvas-Größe wie cart_base.png**). `horn` hat bewusst keinen Layer (akustisch,
kein Licht).

---

## Raspberry Pi 5 Deployment (real)

```bash
# CAN-Interface hochziehen (Bitrate muss zur SPS passen)
sudo ip link set can0 up type can bitrate 250000

# Backends auf real
export CAN_BACKEND=real
export BATTERY_BACKEND=real

# Vollbild direkt auf den Framebuffer (kein X/Wayland/Desktop nötig)
export QT_QPA_PLATFORM=eglfs
python3 main.py
```

Offene Punkte für den Pi-Betrieb: EGLFS-Vollbild, Autostart via systemd,
Touch-Kalibrierung.

---

## Offene Punkte

- **Systemspannung:** Default **48 V** gesetzt (konfigurierbar, später ggf.
  live vom BMS).
- **CAN-IDs / Bitrate / Endianness:** oben dokumentiert (250 kbit/s,
  Big-Endian, IDs 0x200/0x201/0x202) — final mit der SPS-Seite abstimmen.
- **BMS-SPI-Protokoll:** muss noch gesniffed werden (`real_spi.py`).
```
