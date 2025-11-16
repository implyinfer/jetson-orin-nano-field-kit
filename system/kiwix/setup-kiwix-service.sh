#!/usr/bin/env bash
set -euo pipefail

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SERVICE_FILE="$SCRIPT_DIR/kiwix.service"
SYSTEMD_DIR="/etc/systemd/system"
TARGET_SERVICE="$SYSTEMD_DIR/kiwix.service"

# Check if running as root
if [ "$EUID" -ne 0 ]; then
  echo "Error: This script must be run as root (use sudo)"
  exit 1
fi

# Create systemd service file content
cat > "$TARGET_SERVICE" << 'EOF'
[Unit]
Description=Kiwix Server (Docker Compose)
After=docker.service
Requires=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/etc/kiwix
ExecStart=/usr/bin/docker compose up -d
ExecStop=/usr/bin/docker compose down
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

# Create /etc/kiwix directory and copy docker.compose
KIWIX_ETC_DIR="/etc/kiwix"
mkdir -p "$KIWIX_ETC_DIR"

# Create docker-compose.yml with absolute path to data directory
cat > "$KIWIX_ETC_DIR/docker-compose.yml" << EOF
version: "3"
services:
  kiwix:
    image: ghcr.io/kiwix/kiwix-serve
    ports:
      - "8001:8080"
    volumes:
      - $SCRIPT_DIR/data:/data
    command: ["*.zim", "-i", "all", "-p", "6000"]
EOF

# Reload systemd daemon
systemctl daemon-reload

# Enable the service
systemctl enable kiwix.service

echo "Kiwix service has been set up successfully!"
echo "Service file installed at: $TARGET_SERVICE"
echo "Docker compose file installed at: $KIWIX_ETC_DIR/docker-compose.yml"
echo ""
echo "To start the service, run: sudo systemctl start kiwix"
echo "To check status, run: sudo systemctl status kiwix"

