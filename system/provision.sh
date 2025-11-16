#!/usr/bin/env bash
set -euo pipefail

bash "$(dirname "$0")/livekit/install-livekit.sh"

# Setup Kiwix
KIWIX_DIR="$(dirname "$0")/kiwix"
bash "$KIWIX_DIR/download-zim.sh"
bash "$KIWIX_DIR/setup-kiwix-service.sh"

