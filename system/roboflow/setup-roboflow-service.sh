#!/usr/bin/env bash
set -euo pipefail

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SERVICE_FILE="$SCRIPT_DIR/roboflow.service"
SYSTEMD_DIR="/etc/systemd/system"
TARGET_SERVICE="$SYSTEMD_DIR/roboflow.service"

# Check if running as root
if [ "$EUID" -ne 0 ]; then
  echo "Error: This script must be run as root (use sudo)"
  exit 1
fi

# Create systemd service file content
cat > "$TARGET_SERVICE" << 'EOF'
[Unit]
Description=Roboflow Inference Server (Docker Compose)
After=docker.service network-online.target
Requires=docker.service
Wants=network-online.target

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/etc/roboflow
ExecStart=/usr/bin/docker compose up -d
ExecStop=/usr/bin/docker compose down
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

# Create /etc/roboflow directory and copy docker-compose.yml
ROBOFLOW_ETC_DIR="/etc/roboflow"
mkdir -p "$ROBOFLOW_ETC_DIR"

# Copy docker-compose.yml to /etc/roboflow
cp "$SCRIPT_DIR/docker-compose.yml" "$ROBOFLOW_ETC_DIR/docker-compose.yml"

# Reload systemd daemon
systemctl daemon-reload

# Enable the service
systemctl enable roboflow.service

echo "Roboflow service has been set up successfully!"
echo "Service file installed at: $TARGET_SERVICE"
echo "Docker compose file installed at: $ROBOFLOW_ETC_DIR/docker-compose.yml"
echo ""
echo "To start the service, run: sudo systemctl start roboflow"
echo "To check status, run: sudo systemctl status roboflow"



