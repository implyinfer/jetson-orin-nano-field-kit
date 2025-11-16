#!/usr/bin/env bash
set -euo pipefail

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SYSTEMD_DIR="/etc/systemd/system"
TARGET_SERVICE="$SYSTEMD_DIR/mediamtx.service"

# Get the current user (or the user who will run the service)
CURRENT_USER="${SUDO_USER:-$USER}"
if [ "$CURRENT_USER" = "root" ]; then
  # If running as root without sudo, try to get a real user
  CURRENT_USER=$(logname 2>/dev/null || echo "root")
fi

# Get absolute path to mediamtx directory
MEDIAMTX_DIR="$(cd "$SCRIPT_DIR" && pwd)"

# Check if running as root
if [ "$EUID" -ne 0 ]; then
  echo "Error: This script must be run as root (use sudo)"
  exit 1
fi

# Verify mediamtx binary exists
if [ ! -f "$MEDIAMTX_DIR/mediamtx" ]; then
  echo "Error: mediamtx binary not found at $MEDIAMTX_DIR/mediamtx"
  echo "Please run setup.sh first to install MediaMTX"
  exit 1
fi

# Verify mediamtx.yml exists
if [ ! -f "$MEDIAMTX_DIR/mediamtx.yml" ]; then
  echo "Error: mediamtx.yml not found at $MEDIAMTX_DIR/mediamtx.yml"
  echo "Please run setup.sh first to create the configuration"
  exit 1
fi

echo "Setting up MediaMTX systemd service..."
echo "  MediaMTX directory: $MEDIAMTX_DIR"
echo "  Service user: $CURRENT_USER"
echo ""

# Create systemd service file
cat > "$TARGET_SERVICE" << EOF
[Unit]
Description=MediaMTX RTSP Server for IMX219 Camera(s)
After=network.target
Wants=network-online.target

[Service]
Type=simple
User=$CURRENT_USER
Group=$CURRENT_USER
WorkingDirectory=$MEDIAMTX_DIR
ExecStart=$MEDIAMTX_DIR/mediamtx $MEDIAMTX_DIR/mediamtx.yml
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

# Environment
Environment="PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"

[Install]
WantedBy=multi-user.target
EOF

echo "Service file created at: $TARGET_SERVICE"
echo ""

# Reload systemd daemon
echo "Reloading systemd daemon..."
systemctl daemon-reload

# Enable the service
echo "Enabling mediamtx.service to start on boot..."
systemctl enable mediamtx.service

echo ""
echo "========================================"
echo "MediaMTX service setup complete!"
echo "========================================"
echo ""
echo "Service file: $TARGET_SERVICE"
echo "MediaMTX directory: $MEDIAMTX_DIR"
echo "Service user: $CURRENT_USER"
echo ""
echo "Service management commands:"
echo "  Start service:   sudo systemctl start mediamtx"
echo "  Stop service:    sudo systemctl stop mediamtx"
echo "  Restart service: sudo systemctl restart mediamtx"
echo "  Check status:    sudo systemctl status mediamtx"
echo "  View logs:        sudo journalctl -u mediamtx -f"
echo "  Disable startup: sudo systemctl disable mediamtx"
echo ""
echo "The service will automatically start on boot."
echo "To start it now, run: sudo systemctl start mediamtx"
echo ""

