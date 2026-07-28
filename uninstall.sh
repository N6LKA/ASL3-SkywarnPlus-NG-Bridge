#!/bin/bash
# ASL3-SkywarnPlus-NG-Bridge uninstaller
#
# curl -fsSL https://raw.githubusercontent.com/N6LKA/ASL3-SkywarnPlus-NG-Bridge/main/uninstall.sh | sudo bash
#
# Pass --purge to also remove the config directory (kept by default).

set -euo pipefail

PURGE=0
if [[ "${1:-}" == "--purge" ]]; then
    PURGE=1
fi

if [[ "$(id -u)" -ne 0 ]]; then
    echo "This uninstaller must be run as root (sudo)." >&2
    exit 1
fi

echo "==> Removing cron job"
rm -f /etc/cron.d/asl3-swp-ng-bridge

echo "==> Removing script"
rm -f /usr/local/sbin/asl3-swp-ng-bridge.py

if [[ "${PURGE}" -eq 1 ]]; then
    echo "==> Removing config (--purge)"
    rm -rf /etc/asl3-swp-ng-bridge
else
    echo "==> Leaving /etc/asl3-swp-ng-bridge in place (use --purge to remove it too)"
fi

echo "==> Done. Allmon3/Supermon output files (swp-data.json, swp-alerts.html, AUTOSKY/warnings.txt) are left as-is."
