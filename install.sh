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

    ALLMON3_ENABLE="false"
    SUPERMON_ENABLE="false"
    if [[ -r /dev/tty ]]; then
        read -r -p "    Enable Allmon3 integration? [y/N]: " ans < /dev/tty || true
        [[ "${ans,,}" == "y" || "${ans,,}" == "yes" ]] && ALLMON3_ENABLE="true"
        read -r -p "    Enable Supermon integration? [y/N]: " ans < /dev/tty || true
        [[ "${ans,,}" == "y" || "${ans,,}" == "yes" ]] && SUPERMON_ENABLE="true"
    else
        echo "    No TTY available to prompt — leaving Allmon3/Supermon disabled (enable them in ${CONFIG_FILE} manually)."
    fi

    python3 - "${CONFIG_FILE}" "${ALLMON3_ENABLE}" "${SUPERMON_ENABLE}" <<'PYEOF'
import sys
from ruamel.yaml import YAML

path, allmon3_enable, supermon_enable = sys.argv[1], sys.argv[2], sys.argv[3]
yaml = YAML()
yaml.preserve_quotes = True
with open(path) as f:
    cfg = yaml.load(f)

cfg.setdefault("Allmon3", {})["Enable"] = (allmon3_enable == "true")
cfg.setdefault("Supermon", {})["Enable"] = (supermon_enable == "true")

with open(path, "w") as f:
    yaml.dump(cfg, f)
PYEOF

    echo "    Wrote config to ${CONFIG_FILE} (Allmon3.Enable=${ALLMON3_ENABLE}, Supermon.Enable=${SUPERMON_ENABLE})"
fi

echo "==> Installing cron job (runs every minute)"
cat > "${CRON_FILE}" <<EOF
* * * * * root ${BIN_PATH} >> /var/log/asl3-swp-ng-bridge.log 2>&1
EOF
chmod 644 "${CRON_FILE}"

echo ""
echo "==> Done."
echo "    1. Review ${CONFIG_FILE} — adjust WebRoot/Paths/Weather settings for your system"
echo "       (Allmon3.Enable/Supermon.Enable were set from your answers above, if this is a fresh install)."
echo "    2. Confirm SkywarnPlus-NG is installed and running (systemctl status skywarnplus-ng)."
echo "    3. The cron job runs every minute once enabled — no service to start."
echo "    4. Test a run manually: sudo ${BIN_PATH}"
