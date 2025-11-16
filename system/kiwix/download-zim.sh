#!/usr/bin/env bash
set -euo pipefail

# Download Wikipedia ZIM file to data directory
ZIM_URL="https://download.kiwix.org/zim/wikipedia/wikipedia_en_all_mini_2025-06.zim"
DATA_DIR="$(dirname "$0")/data"
ZIM_FILE="$DATA_DIR/wikipedia_en_all_mini_2025-06.zim"

# Create data directory if it doesn't exist
mkdir -p "$DATA_DIR"

# Download the ZIM file if it doesn't exist
if [ ! -f "$ZIM_FILE" ]; then
  echo "Downloading Wikipedia ZIM file..."
  wget -O "$ZIM_FILE" "$ZIM_URL"
  echo "Download complete: $ZIM_FILE"
else
  echo "ZIM file already exists: $ZIM_FILE"
fi

