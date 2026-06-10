# Projektplan: Golfcart Infotainment

## Ziel

Infotainment-Anwendung für ein Golfcart, dargestellt auf einem fest verbauten
9,3-Zoll-Touchdisplay (1600 x 600 px, Querformat) an einem Raspberry Pi 5.

Links eine Cart-Abbildung aus gestapelten PNG-Layern, die den realen Zustand der
Beleuchtung spiegelt. Rechts Touch-Buttons zum Schalten. In der Mitte Telemetrie.

## Technologie-Entscheidung

- GUI: PySide6 (Qt 6), native Desktop-App. KEIN Browser, KEIN WebSocket.
- Ein einziger Python-Prozess fuer UI, CAN und SPI.
- CAN: python-can ueber socketcan (can0) auf dem Pi.
- SPI/BMS: spidev (spaeter, sobald Protokoll gesniffed).
- Sprache: Python 3.11+
- Pi-Display-Target: Qt EGLFS direkt auf den Framebuffer (kein X/Wayland/Desktop noetig).
- Entwicklung: WSL (WSLg) unter Windows. GUI erscheint via WSLg als Windows-Fenster.
  Mock-Backends ersetzen CAN/SPI-Hardware.

## Display-Geometrie

- 1600 px breit x 600 px hoch (extremes Querformat, Seitenverhaeltnis ~2,67:1)
- Horizontale Dreiteilung (QHBoxLayout):
  - Links  (~600 px): Cart-PNG-Layer-Stack (quadratischer Bereich)
  - Mitte  (~360 px): Telemetrie (Speed gross, darunter SOC / A / km)
  - Rechts (~640 px): Touch-Button-Grid (8 Aktoren, fingergross)

## Layout-Skizze (1600 x 600)

    +---------------------+----------------+--------------------------+
    |                     |                |                          |
    |  Cart-PNG-Layer-    |  Telemetrie    |  Touch-Button-Grid       |
    |  Stack              |  Speed (gross) |  [TFL ] [Abbl] [Fern]    |  600
    |  (Golfcart-Ansicht) |  SOC | A | km  |  [Arb ] [Rund] [Hupe]    |  px
    |                     |                |  [Bl< ] [    ] [Bl> ]    |
    |   ~600 px           |   ~360 px      |   ~640 px                |
    +---------------------+----------------+--------------------------+
                             1600 px

## Button-Anordnung (rechte Spalte)

    [ Tagfahrlicht ] [ Abblendlicht ] [ Fernlicht  ]
    [ Arbeitslicht ] [ Rundumleuchte] [ Hupe       ]
    [ Blinker <    ] [              ] [ Blinker >   ]

- Blinker links/rechts aussen (intuitiv).
- Hupe als Halte-Taster (nur aktiv solange gedrueckt), nicht als Toggle.
- Restliche Aktoren als Toggle.

## Aktoren (8 Stueck)

- day_lights     (Tagfahrlicht)
- low_beam       (Abblendlicht)
- high_beam      (Fernlicht)
- work_light     (Arbeitsscheinwerfer)
- beacon         (Rundumleuchte, BLINKT)
- blinker_left   (Blinker links, BLINKT)
- blinker_right  (Blinker rechts, BLINKT)
- horn           (Hupe, Halte-Taster)

## Steuerungslogik (Closed-Loop)

WICHTIG: Ein Button setzt NICHT direkt den Layer.

Ablauf:

1. Tippen "Fernlicht"
2. CAN-TX "Aktor high_beam ON" an SPS
3. SPS schaltet Relais
4. SPS meldet IST-Status via CAN-RX zurueck
5. VehicleState.high_beam = True
6. UI blendet Layer high_beam.png ein

So spiegelt das Display immer die Realitaet (Relais/Sicherung defekt -> Layer
bleibt aus). Im Mock meldet MockCAN den Status sofort zurueck, damit es sich in
der Entwicklung direkt anfuehlt.

## Datenmodell: VehicleState

QObject mit "changed"-Signal, damit die UI reaktiv neu rendert.

Felder:

- Aktoren / Lichter (IST-Status, von SPS via CAN gemeldet):
  day_lights, low_beam, high_beam, beacon, blinker_left, blinker_right,
  work_light, horn  (alle bool)
- Telemetrie:
  - speed_kmh: float   (via CAN)
  - soc_pct:   float   (via SPI/BMS)
  - current_a: float   (via SPI/BMS)
  - range_km:  float   (berechnet in range_calc)

Einzige Wahrheit. CAN + SPI schreiben rein, range_calc ergaenzt Reichweite, UI liest.

## Datenquellen-Aufteilung

- CAN: Licht-/Aktor-IST-Status (RX), Aktor-Befehle (TX), Geschwindigkeit (RX)
- SPI (BMS): SOC, Verbrauch in Ampere
- Berechnet: Reichweite

## CAN-Protokoll (selbst definiert, in canmap.py)

Noch kein Protokoll vorhanden -> wir definieren ein simples, dokumentiertes Schema,
das der SPS-Seite vorgegeben wird. Vorschlag (IDs/Bitrate final abzustimmen):

- Command-Frame (Display -> SPS), ID 0x200:
  Byte0 = Aktor-Index, Byte1 = 0/1 (aus/an). Alternativ Bitmaske.
- Status-Frame (SPS -> Display), ID 0x201:
  Byte0 = Bitmaske aller 8 Aktor-IST-Zustaende.
- Telemetrie-Frame (SPS -> Display), ID 0x202:
  Byte0..1 = Geschwindigkeit (z.B. in 0,1 km/h, Endianness festzulegen).

Bitrate, Endianness und finale IDs im README dokumentieren.

## SPI / Batterie

Eigenstaendiges Interface parallel zum CAN.

- BatteryInterface (ABC)
- MockBattery (Dev): SOC sinkt langsam, Strom schwankt plausibel
- real_spi.py (Platzhalter, bis BMS-Protokoll gesniffed)

Liefert SOC und Strom (A) in den VehicleState.

## Reichweitenberechnung (range_calc.py)

Akku: 105 Ah, 48 V oder 52 V (Systemspannung konfigurierbar, ggf. spaeter vom BMS).

Formeln:

- verbleibende Energie [Wh] = (SOC% / 100) * 105 Ah * Spannung
- aktuelle Leistung    [W]  = Strom (A) * Spannung
- Reststunden               = verbleibende Energie / aktuelle Leistung
- Reichweite [km]           = Reststunden * aktuelle Geschwindigkeit

Praxis-Feinheiten:

- gleitender Mittelwert ueber Strom und Geschwindigkeit (sonst springt der Wert)
- sinnvoller Fallback bei Stillstand (Strom->0 oder Speed->0 ergaebe sonst "unendlich")
- Konstanten in config.py

## Frontend / Layer-Konzept

- Alle PNGs deckungsgleich (gleiche Canvas-Groesse), als gestapelte QLabel mit
  transparentem Hintergrund, position-exakt uebereinander.
- Toggle = setVisible(True/False) je nach VehicleState.
- Blinken = EIN zentraler QTimer (z.B. 500 ms), der die blinkenden Layer
  (blinker_left, blinker_right, beacon) synchron umschaltet. Frequenz zentral steuerbar.
- Echte Assets kommen spaeter und werden 1:1 ausgetauscht. Jetzt: farbige
  Platzhalter-PNGs, gleiche Canvas-Groesse (Cart-Bereich ~600x600).

## Projektstruktur

    golfcart-infotainment/
    |- main.py                  # Entrypoint: Qt-App, Threads, Verdrahtung
    |- config.py                # Env-Switch (mock/real), Akkudaten, Spannung, Konstanten
    |- core/
    |  |- state.py              # VehicleState (QObject + Signal)
    |  |- range_calc.py         # Reichweitenberechnung
    |- io_can/
    |  |- interface.py          # ABC CANInterface (QThread-basiert)
    |  |- real_can.py           # python-can socketcan, RX/TX
    |  |- mock_can.py           # Sim: Status-Rueckmeldung + Speed
    |  |- canmap.py             # CAN-ID <-> Signal Mapping (selbst definiert)
    |- io_battery/
    |  |- interface.py          # ABC BatteryInterface (QThread-basiert)
    |  |- real_spi.py           # spidev (Platzhalter)
    |  |- mock_battery.py       # Sim: SOC + Strom
    |- ui/
    |  |- main_window.py        # 1600x600 Layout, 3 Spalten (QHBoxLayout)
    |  |- cart_view.py          # PNG-Layer-Stack + synchrone Blink-Logik
    |  |- controls.py           # 8 Touch-Buttons (Closed-Loop)
    |  |- telemetry.py          # Speed/SOC/A/Reichweite
    |  |- assets/
    |     |- cart_base.png
    |     |- day_lights.png
    |     |- low_beam.png
    |     |- high_beam.png
    |     |- work_light.png
    |     |- beacon.png
    |     |- blinker_left.png
    |     |- blinker_right.png
    |- run_dev.sh               # Startet App im Mock-Modus (Fenster, WSL)
    |- requirements.txt
    |- README.md

## Threading

- Qt-Eventloop treibt die UI.
- CAN und SPI laufen je in eigenem QThread.
- Sie schreiben thread-sicher in VehicleState; State emittiert "changed"-Signal,
  das die UI im GUI-Thread aktualisiert (Qt-Signal/Slot ueber Thread-Grenze).

## WSL-spezifische Einrichtung

Einmalig in Windows PowerShell:

    wsl --update

In WSL pruefen (sollte z.B. ":0" zeigen):

    echo $DISPLAY

Eventuell noetige System-Libs (falls Qt beim Start meckert):

    sudo apt install -y libxcb-cursor0 libxkbcommon-x11-0 libegl1

run_dev.sh setzt automatisch:

    export CAN_BACKEND=mock
    export BATTERY_BACKEND=mock
    export QT_QPA_PLATFORM=xcb

## requirements.txt (geplant)

- PySide6              (immer)
- python-can          (nur Pi/real; im Mock nicht zwingend importiert)
- spidev              (nur Pi/real; im Mock nicht zwingend importiert)

Mock-Betrieb darf NICHT an fehlender Hardware/Lib scheitern: real_can und
real_spi importieren ihre Hardware-Libs erst beim tatsaechlichen Start des
real-Backends (lazy import), nicht beim Modul-Import.

## Build-Reihenfolge

1. Grundgeruest: VehicleState (QObject + Signal), config.py, main.py, leeres
   1600x600-Fenster.
2. MockCAN (Thread): Status-Rueckmeldung + simulierte Geschwindigkeit, RX/TX.
3. MockBattery (Thread): SOC + Strom.
4. range_calc: Reichweite aus den Mock-Daten.
5. UI Cart-View: Platzhalter-Layer-Stack + synchrones Blinken.
6. UI Controls: 8 steuernde Touch-Buttons (Closed-Loop ueber Mock).
7. UI Telemetry: Speed/SOC/A/Reichweite live.
8. RealCAN + finales canmap.py (sobald CAN-Spec fixiert).
9. RealSPI (sobald BMS-Protokoll gesniffed).
10. Pi-5-Deployment: EGLFS-Vollbild, Autostart (systemd), Touch-Kalibrierung.

## Offene Punkte (beim Bauen klaeren)

- Systemspannung: 48 V oder 52 V als Default fuer die Reichweite?
  (Konfigurierbar, spaeter ggf. live vom BMS.)
- CAN-IDs / Bitrate / Endianness: finale Werte fuer die SPS-Doku.
- BMS-SPI-Protokoll: muss noch gesniffed werden.
