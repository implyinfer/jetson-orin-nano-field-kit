#!/usr/bin/env bash
set -euo pipefail

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SERVICE_FILE="$SCRIPT_DIR/ultralytics.service"
SYSTEMD_DIR="/etc/systemd/system"
TARGET_SERVICE="$SYSTEMD_DIR/ultralytics.service"

# Check if running as root
if [ "$EUID" -ne 0 ]; then
  echo "Error: This script must be run as root (use sudo)"
  exit 1
fi

# Create systemd service file content
cat > "$TARGET_SERVICE" << 'EOF'
[Unit]
Description=Ultralytics YOLO Server (Docker Compose)
After=docker.service network-online.target
Requires=docker.service
Wants=network-online.target

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/etc/ultralytics
ExecStart=/usr/bin/docker compose up -d
ExecStop=/usr/bin/docker compose down
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

# Create /etc/ultralytics directory
ULTRALYTICS_ETC_DIR="/etc/ultralytics"
mkdir -p "$ULTRALYTICS_ETC_DIR"

# Create data directory if it doesn't exist
mkdir -p "$SCRIPT_DIR/data"

# Create docker-compose.yml with absolute path to data directory
cat > "$ULTRALYTICS_ETC_DIR/docker-compose.yml" << EOF
version: "3.8"

services:
  ultralytics:
    image: ultralytics/ultralytics:latest-jetson-jetpack6
    ipc_mode: host
    runtime: nvidia
    stdin_open: true
    tty: true
    volumes:
      - $SCRIPT_DIR/data:/data
    environment:
      - NVIDIA_VISIBLE_DEVICES=all
      - NVIDIA_DRIVER_CAPABILITIES=compute,utility
EOF

# Reload systemd daemon
systemctl daemon-reload

# Enable the service
systemctl enable ultralytics.service

echo "Ultralytics service has been set up successfully!"
echo "Service file installed at: $TARGET_SERVICE"
echo "Docker compose file installed at: $ULTRALYTICS_ETC_DIR/docker-compose.yml"
echo ""
echo "To start the service, run: sudo systemctl start ultralytics"
echo "To check status, run: sudo systemctl status ultralytics"

