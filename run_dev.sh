#!/usr/bin/env bash
# Startet die App im Mock-Modus als Fenster (WSL/WSLg).
# Keine CAN-/SPI-Hardware noetig -- alle Backends sind simuliert.
set -euo pipefail
cd "$(dirname "$0")"

export CAN_BACKEND=mock
export BATTERY_BACKEND=mock

# Qt-Plattform-Plugin: unter WSLg ist xcb (X11) der zuverlaessige Pfad.
# Das Qt-Wayland-Plugin bleibt hier beim Start gerne haengen.
# Einmalig noetige System-Libs fuer das xcb-Plugin (sonst startet es nicht):
#     sudo apt install -y libxcb-cursor0 libxcb-icccm4 libxcb-keysyms1 \
#                         libxkbcommon-x11-0 libegl1
# Mit QT_QPA_PLATFORM=wayland kann man Wayland manuell erzwingen.
export QT_QPA_PLATFORM="${QT_QPA_PLATFORM:-xcb}"

echo "[run_dev] QT_QPA_PLATFORM=$QT_QPA_PLATFORM"
exec python3 main.py
