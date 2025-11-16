#!/usr/bin/env bash
set -euo pipefail

# Setup Kiwix
KIWIX_DIR="$(dirname "$0")/kiwix"
bash "$KIWIX_DIR/download-zim.sh"
bash "$KIWIX_DIR/setup-kiwix-service.sh"

# Start Kiwix Docker container if not already running
KIWIX_COMPOSE="$KIWIX_DIR/docker-compose.yml"
if [ -f "$KIWIX_COMPOSE" ]; then
  cd "$KIWIX_DIR"
  if ! docker compose ps --services --filter "status=running" | grep -q "^kiwix$"; then
    echo "Starting Kiwix Docker container..."
    docker compose up -d
  else
    echo "Kiwix Docker container is already running"
  fi
  cd - > /dev/null
fi

# bash "$(dirname "$0")/livekit/install-livekit.sh"

