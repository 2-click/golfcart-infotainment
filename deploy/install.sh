#!/usr/bin/env bash
# Richtet auf einem frisch installierten Raspberry Pi OS Lite den
# produktionsnahen Boot ein:
#   1. Stiller Boot ohne Kernel-Text und ohne die 4 Raspberry-Logos
#   2. CUSHMAN Plymouth-Splash (Runge Engineering)
#   3. systemd-Service, der die PySide6-UI per eglfs auf den Schirm bringt
#
# Idempotent: mehrfaches Ausfuehren ist unschaedlich.
# Aufruf auf dem Pi:   sudo bash deploy/install.sh
set -euo pipefail

if [[ $EUID -ne 0 ]]; then
  echo "Bitte mit sudo ausfuehren: sudo bash deploy/install.sh" >&2
  exit 1
fi

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# --- Boot-Verzeichnis finden (Bookworm: /boot/firmware, aelter: /boot) -----
if [[ -f /boot/firmware/config.txt ]]; then
  BOOT=/boot/firmware
elif [[ -f /boot/config.txt ]]; then
  BOOT=/boot
else
  echo "Weder /boot/firmware/config.txt noch /boot/config.txt gefunden." >&2
  exit 1
fi
echo "[1/4] Boot-Verzeichnis: $BOOT"

# --- config.txt: Rainbow-Splash am Power-On abschalten ---------------------
CONFIG="$BOOT/config.txt"
if ! grep -q '^disable_splash=1' "$CONFIG"; then
  echo 'disable_splash=1' >> "$CONFIG"
  echo "    + disable_splash=1 in config.txt"
else
  echo "    = disable_splash=1 bereits gesetzt"
fi

# --- cmdline.txt: stille Boot-Parameter (eine einzige Zeile!) --------------
CMDLINE="$BOOT/cmdline.txt"
cp -n "$CMDLINE" "$CMDLINE.bak" || true   # einmaliges Backup
line="$(tr -d '\n' < "$CMDLINE")"
for tok in quiet splash loglevel=3 logo.nologo vt.global_cursor_default=0 \
           consoleblank=0 plymouth.ignore-serial-consoles; do
  key="${tok%%=*}"
  # Token nur anhaengen, wenn sein Schluessel noch nicht vorkommt
  if ! grep -qE "(^| )${key}(=| |$)" <<<"$line"; then
    line="$line $tok"
  fi
done
echo "$line" > "$CMDLINE"
echo "[2/4] cmdline.txt aktualisiert:"
echo "      $line"

# --- Plymouth + Theme ------------------------------------------------------
echo "[3/4] Plymouth installieren und Theme setzen ..."
export DEBIAN_FRONTEND=noninteractive
apt-get install -y plymouth plymouth-themes >/dev/null

DEST=/usr/share/plymouth/themes/cushman
mkdir -p "$DEST"
install -m 0644 "$HERE/plymouth/cushman/cushman.plymouth" "$DEST/cushman.plymouth"
install -m 0644 "$HERE/plymouth/cushman/cushman.script"   "$DEST/cushman.script"
install -m 0644 "$HERE/plymouth/cushman/splash.png"       "$DEST/splash.png"

plymouth-set-default-theme cushman
# Raspberry Pi OS bootet i.d.R. ohne initramfs -> Theme wird direkt aus dem
# rootfs gelesen. Falls doch ein initramfs verwendet wird, best-effort neu bauen.
if command -v update-initramfs >/dev/null 2>&1; then
  update-initramfs -u >/dev/null 2>&1 || true
fi
echo "    = Theme 'cushman' als Standard gesetzt"

# --- systemd-Service -------------------------------------------------------
echo "[4/4] systemd-Service installieren ..."
install -m 0644 "$HERE/cushman-infotainment.service" \
        /etc/systemd/system/cushman-infotainment.service
systemctl daemon-reload
systemctl enable cushman-infotainment.service >/dev/null
echo "    = cushman-infotainment.service aktiviert (startet beim Boot)"

cat <<'DONE'

Fertig. Vor dem Neustart pruefen:
  * Service-User/Pfad in /etc/systemd/system/cushman-infotainment.service
    (Default: User=pi, WorkingDirectory=/home/pi/golfcart-infotainment)
  * Projekt liegt am passenden Pfad und die requirements sind installiert:
      pip install -r requirements.txt --break-system-packages
  * Touch-Geraet ggf. via QT_QPA_EVDEV_TOUCHSCREEN_PARAMETERS setzen.

Testen ohne Reboot:
  sudo systemctl start cushman-infotainment.service
  journalctl -u cushman-infotainment.service -f

Splash vorab ansehen:
  sudo plymouthd ; sudo plymouth show-splash ; sleep 3 ; sudo plymouth quit

Dann:  sudo reboot
DONE
