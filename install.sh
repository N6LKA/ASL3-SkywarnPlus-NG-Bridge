#!/bin/bash
# ASL3-SkywarnPlus-NG-Bridge installer
#
# curl -fsSL https://raw.githubusercontent.com/N6LKA/ASL3-SkywarnPlus-NG-Bridge/main/install.sh | sudo bash

set -euo pipefail

REPO="N6LKA/ASL3-SkywarnPlus-NG-Bridge"
BRANCH="${1:-main}"
REPO_RAW="https://raw.githubusercontent.com/${REPO}/${BRANCH}"

BIN_PATH="/usr/local/sbin/asl3-swp-ng-bridge.py"
CONFIG_DIR="/etc/asl3-swp-ng-bridge"
CONFIG_FILE="${CONFIG_DIR}/config.yaml"
CRON_FILE="/etc/cron.d/asl3-swp-ng-bridge"

if [[ "$(id -u)" -ne 0 ]]; then
    echo "This installer must be run as root (sudo)." >&2
    exit 1
fi

echo "==> Installing dependencies"
if command -v apt-get >/dev/null 2>&1; then
    apt-get update -qq
    apt-get install -y python3-requests python3-ruamel.yaml
else
    echo "apt-get not found; ensure python3-requests and python3-ruamel.yaml (or pip equivalents) are installed." >&2
fi

echo "==> Installing ${BIN_PATH}"
curl -fsSL "${REPO_RAW}/swp-ng-bridge.py" -o "${BIN_PATH}"
chmod 755 "${BIN_PATH}"

echo "==> Installing config"
mkdir -p "${CONFIG_DIR}"
if [[ -f "${CONFIG_FILE}" ]]; then
    echo "    Existing config found at ${CONFIG_FILE}, leaving it untouched."
else
    curl -fsSL "${REPO_RAW}/config.yaml.example" -o "${CONFIG_FILE}"
    echo "    Wrote default config to ${CONFIG_FILE} — edit this before the bridge does anything useful."
fi

echo "==> Installing cron job (runs every minute)"
cat > "${CRON_FILE}" <<EOF
* * * * * root ${BIN_PATH} >> /var/log/asl3-swp-ng-bridge.log 2>&1
EOF
chmod 644 "${CRON_FILE}"

echo ""
echo "==> Done."
echo "    1. Edit ${CONFIG_FILE} — set Allmon3.Enable and/or Supermon.Enable to true,"
echo "       and adjust WebRoot/Paths/Weather settings for your system."
echo "    2. Confirm SkywarnPlus-NG is installed and running (systemctl status skywarnplus-ng)."
echo "    3. The cron job runs every minute once enabled — no service to start."
echo "    4. Test a run manually: sudo ${BIN_PATH}"
