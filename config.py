"""Zentrale Konfiguration: Backend-Switch (mock/real), Akkudaten, Konstanten.

Alle Werte koennen per Umgebungsvariable ueberschrieben werden, damit der
gleiche Code auf dem Pi (real) und in WSL (mock) laeuft.
"""

import os

# --- Backend-Auswahl ------------------------------------------------------
# "mock"  -> simulierte Backends (WSL/Entwicklung, keine Hardware noetig)
# "real"  -> echte Hardware (Raspberry Pi 5: socketcan / spidev)
CAN_BACKEND = os.getenv("CAN_BACKEND", "mock").lower()
BATTERY_BACKEND = os.getenv("BATTERY_BACKEND", "mock").lower()

# --- CAN ------------------------------------------------------------------
CAN_CHANNEL = os.getenv("CAN_CHANNEL", "can0")
CAN_BITRATE = int(os.getenv("CAN_BITRATE", "250000"))

# --- Akku / Batterie ------------------------------------------------------
# Systemspannung (V). Default 48 V (vom Nutzer bestaetigt). Konfigurierbar,
# spaeter ggf. live vom BMS gemeldet.
SYSTEM_VOLTAGE_V = float(os.getenv("SYSTEM_VOLTAGE_V", "48.0"))

# Nennkapazitaet des Akkus (Ah).
BATTERY_CAPACITY_AH = float(os.getenv("BATTERY_CAPACITY_AH", "105.0"))

# --- Reichweitenberechnung -----------------------------------------------
# Fenstergroesse (Anzahl Samples) fuer den gleitenden Mittelwert von Strom
# und Geschwindigkeit. Glaettet das Springen des Reichweitenwertes.
RANGE_AVG_WINDOW = int(os.getenv("RANGE_AVG_WINDOW", "10"))

# Unterhalb dieser Schwellen gilt das Fahrzeug als "steht" / "zieht nichts";
# die Reichweite wird dann nicht berechnet (sonst -> unendlich).
MIN_SPEED_KMH = 0.5
MIN_CURRENT_A = 0.5

# --- Aktoren --------------------------------------------------------------
# Reihenfolge = CAN-Bitmaske-Index (Byte0, Bit0..Bit7) im Status-Frame.
# Dieser Index ist die einzige Wahrheit fuer die SPS-Doku (siehe canmap.py).
ACTUATORS = [
    "day_lights",     # 0  Tagfahrlicht
    "low_beam",       # 1  Abblendlicht
    "high_beam",      # 2  Fernlicht
    "work_light",     # 3  Arbeitsscheinwerfer
    "beacon",         # 4  Rundumleuchte (blinkt)
    "blinker_left",   # 5  Blinker links (blinkt)
    "blinker_right",  # 6  Blinker rechts (blinkt)
    "horn",           # 7  Hupe (Halte-Taster)
]

# Welche Aktoren in der UI blinken (synchroner zentraler Timer).
BLINKING_ACTUATORS = ["beacon", "blinker_left", "blinker_right"]

# Blinker (blinker_left/right): ruhiges Blinken, Halbperiode in ms.
BLINK_INTERVAL_MS = int(os.getenv("BLINK_INTERVAL_MS", "500"))

# Rundumleuchte (beacon): Doppelblitz -- zwei schnelle Blitze, dann Pause.
# Zykluslaenge = 2*FLASH + GAP + PAUSE.
BEACON_FLASH_MS = int(os.getenv("BEACON_FLASH_MS", "70"))   # Dauer eines Blitzes
BEACON_GAP_MS = int(os.getenv("BEACON_GAP_MS", "110"))      # Pause zwischen den Blitzen
BEACON_PAUSE_MS = int(os.getenv("BEACON_PAUSE_MS", "600"))  # Pause nach dem Doppelblitz

# --- UI -------------------------------------------------------------------
SCREEN_WIDTH = 1600
SCREEN_HEIGHT = 600
CART_AREA = 600  # quadratischer Cart-Bereich links

# Skalenendwert des Tachos (km/h). Standard 10, im Admin-Modus 30 (die Gauge
# animiert fluessig dazwischen). Der Mock haelt die simulierte Geschwindigkeit
# innerhalb des jeweiligen Limits.
SPEEDO_MAX_DEFAULT = float(os.getenv("SPEEDO_MAX_DEFAULT", "10"))
SPEEDO_MAX_ADMIN = float(os.getenv("SPEEDO_MAX_ADMIN", "30"))

# Temporaerer Kalibrier-Modus: Klick auf den Cart -> PNG-Koordinaten ausgeben
# (Terminal + Fadenkreuz auf dem Display). Aktivieren mit CART_CALIBRATE=1.
CART_CALIBRATE = os.getenv("CART_CALIBRATE", "0") == "1"
