#!/bin/bash
# Startup script for MediaMTX RTSP server

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "========================================"
echo "Starting MediaMTX RTSP Server"
echo "========================================"
echo ""
echo "RTSP Stream(s) available at:"
echo "  Camera 0: rtsp://$(hostname -I | awk '{print $1}'):8554/cam0"
echo ""
echo "HLS Stream(s) available at:"
echo "  Camera 0: http://$(hostname -I | awk '{print $1}'):8888/cam0"
echo ""
echo "Press Ctrl+C to stop..."
echo "========================================"
echo ""

./mediamtx mediamtx.yml
