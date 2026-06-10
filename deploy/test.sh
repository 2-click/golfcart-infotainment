#!/usr/bin/env bash
# Schneller Test-Loop auf dem Pi: stoppt kurz die Produktiv-UI, startet die App
# im Vordergrund (Mock-Backends, linuxfb) mit Live-Ausgabe im Terminal und
# stellt beim Beenden (q/Ctrl-C/Absturz) die Produktiv-UI wieder her.
#
# Aufruf auf dem Pi:   sudo bash deploy/test.sh
# Beenden:             Ctrl-C  (oder die App schliessen)
set -uo pipefail

if [[ $EUID -ne 0 ]]; then
  echo "Bitte mit sudo ausfuehren: sudo bash deploy/test.sh" >&2
  exit 1
fi

PROD=cushman-infotainment.service
APP_USER="${APP_USER:-pi}"
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"   # Repo-Wurzel (deploy/..)

# War die Produktiv-UI aktiv? Dann nach dem Test wieder hochfahren.
WAS_ACTIVE="$(systemctl is-active "$PROD" 2>/dev/null || true)"

restore() {
  if [[ "$WAS_ACTIVE" == "active" ]]; then
    echo
    echo "[test] Produktiv-UI wird wieder gestartet ..."
    systemctl start "$PROD" || true
  fi
}
trap restore EXIT

if [[ "$WAS_ACTIVE" == "active" ]]; then
  echo "[test] Stoppe $PROD (Framebuffer freigeben) ..."
  systemctl stop "$PROD"
fi

echo "[test] Starte App im Vordergrund (CAN/BATTERY=mock, linuxfb) -- Ctrl-C beendet."
echo "[test] Repo: $REPO   User: $APP_USER"
echo "--------------------------------------------------------------------------"

# Im Vordergrund als App-User. Lokale Code-Aenderungen werden direkt getestet.
sudo -u "$APP_USER" env \
  CAN_BACKEND="${CAN_BACKEND:-mock}" \
  BATTERY_BACKEND="${BATTERY_BACKEND:-mock}" \
  QT_QPA_PLATFORM="${QT_QPA_PLATFORM:-linuxfb}" \
  python3 "$REPO/main.py"

# Rueckkehr hier -> trap 'restore' faehrt die Produktiv-UI wieder hoch.
