#!/bin/bash

# Script de désinstallation du service systemd GSGUI

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

SERVICE_NAME="gsgui@$(whoami)"

echo -e "${BLUE}=== Désinstallation du service systemd GSGUI ===${NC}"

if [[ $EUID -ne 0 ]]; then
    exec sudo "$0" "$@"
fi

if ! systemctl list-unit-files "${SERVICE_NAME}.service" &>/dev/null; then
    echo -e "${YELLOW}Service $SERVICE_NAME non trouvé.${NC}"
    exit 0
fi

systemctl stop "$SERVICE_NAME" 2>/dev/null || true
systemctl disable "$SERVICE_NAME" 2>/dev/null || true
rm -f "/etc/systemd/system/${SERVICE_NAME}.service"
systemctl daemon-reload

echo -e "${GREEN}Service $SERVICE_NAME désinstallé.${NC}"
