"""CAN-Protokoll (selbst definiert) -- Mapping zwischen CAN-Frames und Signalen.

Dies ist die verbindliche Spezifikation fuer die SPS-Seite. Bitrate, IDs und
Endianness sind hier zentral festgelegt und im README dokumentiert.

----------------------------------------------------------------------------
Bitrate:     250 kbit/s  (config.CAN_BITRATE)
Endianness:  Big-Endian (Telemetrie-Mehrbyte-Werte, "Motorola"-Format)
----------------------------------------------------------------------------

Frames:

  Command-Frame   Display -> SPS   ID 0x200, DLC 2
      Byte0 = Aktor-Index (0..7, siehe ACTUATORS)
      Byte1 = 0 (aus) / 1 (an)

  Status-Frame    SPS -> Display   ID 0x201, DLC 1
      Byte0 = Bitmaske aller 8 Aktor-IST-Zustaende
              Bit i = ACTUATORS[i]  (Bit0 = day_lights ... Bit7 = horn)

  Telemetrie-Frame  SPS -> Display  ID 0x202, DLC 2
      Byte0..1 = Geschwindigkeit in 0,1 km/h, Big-Endian, unsigned
                 (z.B. 0x00FA = 250 -> 25,0 km/h)
"""

import struct

import config

# --- CAN-IDs --------------------------------------------------------------
CMD_ID = 0x200      # Display -> SPS: Aktor-Befehl
STATUS_ID = 0x201   # SPS -> Display: Aktor-IST-Bitmaske
TELEMETRY_ID = 0x202  # SPS -> Display: Geschwindigkeit

# Geschwindigkeits-Aufloesung: Rohwert * SPEED_SCALE = km/h
SPEED_SCALE = 0.1


# --- Encode (Display -> SPS) ---------------------------------------------
def encode_command(actuator: str, on: bool) -> tuple[int, bytes]:
    """Baut einen Command-Frame. Liefert (can_id, data)."""
    index = config.ACTUATORS.index(actuator)
    return CMD_ID, bytes([index, 1 if on else 0])


# --- Decode (SPS -> Display) ---------------------------------------------
def decode_status(data: bytes) -> int:
    """Liefert die 8-Bit-Aktor-Bitmaske aus einem Status-Frame."""
    if not data:
        return 0
    return data[0]


def decode_speed(data: bytes) -> float:
    """Liefert die Geschwindigkeit in km/h aus einem Telemetrie-Frame."""
    if len(data) < 2:
        return 0.0
    (raw,) = struct.unpack(">H", data[:2])  # Big-Endian unsigned 16 Bit
    return raw * SPEED_SCALE


def encode_speed(speed_kmh: float) -> bytes:
    """Gegenstueck zu decode_speed -- vom Mock genutzt, um realistische
    Telemetrie-Frames zu erzeugen."""
    raw = max(0, min(0xFFFF, int(round(speed_kmh / SPEED_SCALE))))
    return struct.pack(">H", raw)


def encode_status(states: dict) -> bytes:
    """Baut einen Status-Frame aus {actuator: bool}. Vom Mock genutzt."""
    mask = 0
    for i, name in enumerate(config.ACTUATORS):
        if states.get(name):
            mask |= (1 << i)
    return bytes([mask])
