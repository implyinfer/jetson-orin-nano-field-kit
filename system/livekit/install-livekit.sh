#!/usr/bin/env bash
set -euo pipefail

# Pin a version so installs are reproducible
: "${LIVEKIT_VERSION:=v1.9.3}"             # <- choose the version you want

BIN_DIR="/usr/local/bin"
SERVICE_USER="livekit"

if ! id -u "$SERVICE_USER" &>/dev/null; then
  sudo useradd --system --create-home --shell /usr/sbin/nologin "$SERVICE_USER"
fi

# Install script from livekit (or swap to a direct tarball URL you pin)
# Using the official installer but pinning version explicitly:
curl -sSL https://get.livekit.io | bash -s -- --version "$LIVEKIT_VERSION"

sudo chown root:root "${BIN_DIR}/livekit-server"
sudo chmod 0755 "${BIN_DIR}/livekit-server"

# Install config & env
sudo mkdir -p /etc/livekit
sudo install -m 0644 "$(dirname "$0")/server.yaml" /etc/livekit/server.yaml
sudo install -m 0640 "$(dirname "$0")/livekit.env" /etc/livekit/livekit.env
sudo chgrp "$SERVICE_USER" /etc/livekit/livekit.env

# Install systemd unit
sudo install -m 0644 "$(dirname "$0")/livekit.service" /etc/systemd/system/livekit.service
sudo systemctl daemon-reload
sudo systemctl enable --now livekit.service