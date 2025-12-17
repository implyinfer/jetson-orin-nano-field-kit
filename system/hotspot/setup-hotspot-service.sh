#!/usr/bin/env bash
set -euo pipefail

# =============================================================================
# Install WiFi Hotspot as a systemd service
# =============================================================================
# This script installs the hotspot service to start automatically on boot.
#
# Usage:
#   sudo ./setup-hotspot-service.sh [--enable|--disable|--remove]
# =============================================================================

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SERVICE_NAME="hotspot.service"
SYSTEMD_DIR="/etc/systemd/system"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    log_error "This script must be run as root (use sudo)"
    exit 1
fi

ACTION="${1:-install}"

case "$ACTION" in
    install|--enable)
        log_info "Installing hotspot service..."

        # Update paths in service file to use absolute paths
        HOTSPOT_DIR="$SCRIPT_DIR"

        # Create service file with correct paths
        cat > "$SYSTEMD_DIR/$SERVICE_NAME" << EOF
[Unit]
Description=WiFi Hotspot for Jetson Field Kit
After=network-online.target NetworkManager.service
Wants=network-online.target
StartLimitIntervalSec=60
StartLimitBurst=3

[Service]
Type=oneshot
RemainAfterExit=yes
EnvironmentFile=-${HOTSPOT_DIR}/hotspot.conf
ExecStart=${HOTSPOT_DIR}/setup-hotspot.sh
ExecStop=${HOTSPOT_DIR}/setup-hotspot.sh --stop

# Wait for WiFi to connect before starting hotspot
ExecStartPre=/bin/bash -c 'for i in {1..30}; do nmcli -t -f STATE g 2>/dev/null | grep -q connected && exit 0; sleep 2; done; exit 1'

[Install]
WantedBy=multi-user.target
EOF

        systemctl daemon-reload
        systemctl enable "$SERVICE_NAME"
        log_info "Hotspot service installed and enabled"
        log_info "Start with: sudo systemctl start hotspot"
        log_info "Check status: sudo systemctl status hotspot"
        ;;

    --disable)
        log_info "Disabling hotspot service..."
        systemctl disable "$SERVICE_NAME" 2>/dev/null || true
        log_info "Hotspot service disabled (will not start on boot)"
        ;;

    --remove)
        log_info "Removing hotspot service..."
        systemctl stop "$SERVICE_NAME" 2>/dev/null || true
        systemctl disable "$SERVICE_NAME" 2>/dev/null || true
        rm -f "$SYSTEMD_DIR/$SERVICE_NAME"
        systemctl daemon-reload
        log_info "Hotspot service removed"
        ;;

    *)
        echo "Usage: $0 [--enable|--disable|--remove]"
        echo ""
        echo "  --enable   Install and enable service (default)"
        echo "  --disable  Disable service (don't start on boot)"
        echo "  --remove   Remove service completely"
        exit 1
        ;;
esac
