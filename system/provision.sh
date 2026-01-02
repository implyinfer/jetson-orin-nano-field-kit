#!/usr/bin/env bash
set -euo pipefail

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_section() {
  echo ""
  echo -e "${BLUE}========================================${NC}"
  echo -e "${BLUE}$1${NC}"
  echo -e "${BLUE}========================================${NC}"
  echo ""
}

print_status() {
  echo -e "${GREEN}[*]${NC} $1"
}

print_warning() {
  echo -e "${YELLOW}[!]${NC} $1"
}

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

print_section "System Provisioning Script"
echo "This script will set up all system services:"
echo "  - Roboflow (vision inference)"
echo "  - MediaMTX (RTSP streaming)"
echo "  - Hotspot (WiFi access point)"
echo ""
echo "Note: Kiwix setup is skipped (not fully supported yet)"
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then
  echo "Error: This script must be run as root (use sudo)"
  exit 1
fi

# -----------------------------------------------------------------------------
# Setup Roboflow
# -----------------------------------------------------------------------------
print_section "Setting up Roboflow Vision Experience"
ROBOFLOW_DIR="$SCRIPT_DIR/roboflow"
if [ -f "$ROBOFLOW_DIR/setup-roboflow-service.sh" ]; then
  bash "$ROBOFLOW_DIR/setup-roboflow-service.sh"
  print_status "Roboflow setup complete"
else
  print_warning "Roboflow setup script not found, skipping..."
fi

# -----------------------------------------------------------------------------
# Setup MediaMTX
# -----------------------------------------------------------------------------
print_section "Setting up MediaMTX RTSP Server"
MEDIAMTX_DIR="$SCRIPT_DIR/mediamtx"
if [ -f "$MEDIAMTX_DIR/setup.sh" ]; then
  print_status "Running MediaMTX initial setup..."
  bash "$MEDIAMTX_DIR/setup.sh"
  print_status "MediaMTX initial setup complete"
else
  print_warning "MediaMTX setup.sh not found, skipping initial setup..."
fi

if [ -f "$MEDIAMTX_DIR/setup-mediamtx-service.sh" ]; then
  print_status "Setting up MediaMTX systemd service..."
  bash "$MEDIAMTX_DIR/setup-mediamtx-service.sh"
  print_status "MediaMTX service setup complete"
else
  print_warning "MediaMTX service setup script not found, skipping..."
fi

# -----------------------------------------------------------------------------
# Setup Hotspot
# -----------------------------------------------------------------------------
print_section "Setting up WiFi Hotspot"
HOTSPOT_DIR="$SCRIPT_DIR/hotspot"
if [ -f "$HOTSPOT_DIR/setup-hotspot-service.sh" ]; then
  bash "$HOTSPOT_DIR/setup-hotspot-service.sh"
  print_status "Hotspot service setup complete"
else
  print_warning "Hotspot setup script not found, skipping..."
fi

# -----------------------------------------------------------------------------
# Reload systemd and show status
# -----------------------------------------------------------------------------
print_section "Finalizing Setup"
print_status "Reloading systemd daemon..."
systemctl daemon-reload

print_section "Provisioning Complete!"
echo "All system services have been configured."
echo ""
echo "Services installed:"
echo "  - rf-inference.service (Roboflow inference server)"
echo "  - roboflow-web-stream.service (Web vision stream)"
echo "  - mediamtx.service (RTSP streaming server)"
echo "  - hotspot.service (WiFi access point)"
echo "  - nginx.service (Web reverse proxy)"
echo ""
echo "Services will start automatically on boot."
echo ""
echo "To start services now:"
echo "  sudo systemctl start rf-inference"
echo "  sudo systemctl start roboflow-web-stream"
echo "  sudo systemctl start mediamtx"
echo "  sudo systemctl start hotspot"
echo ""
echo "To check service status:"
echo "  sudo systemctl status <service-name>"
echo ""

