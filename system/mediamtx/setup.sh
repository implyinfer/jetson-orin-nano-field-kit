#!/bin/bash
# MediaMTX Setup Script for Jetson Orin Nano
# Complete setup for RTSP streaming from IMX219 cameras

set -e

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MEDIAMTX_DIR="$SCRIPT_DIR"

echo "========================================"
echo "MediaMTX Setup for Jetson Orin Nano"
echo "========================================"
echo ""

# Step 1: Install Required Packages
echo "Step 1: Installing required packages..."
sudo apt update
sudo apt install -y \
  gstreamer1.0-tools \
  gstreamer1.0-plugins-good \
  gstreamer1.0-plugins-bad \
  ffmpeg \
  v4l-utils

# Step 2: Download and Install MediaMTX
echo ""
echo "Step 2: Downloading and installing MediaMTX..."
cd "$MEDIAMTX_DIR"

if [ ! -f "$MEDIAMTX_DIR/mediamtx_v1.15.3_linux_arm64.tar.gz" ]; then
  wget -O "$MEDIAMTX_DIR/mediamtx_v1.15.3_linux_arm64.tar.gz" \
    https://github.com/bluenviron/mediamtx/releases/download/v1.15.3/mediamtx_v1.15.3_linux_arm64.tar.gz
fi

if [ ! -f "$MEDIAMTX_DIR/mediamtx" ]; then
  tar -xzf "$MEDIAMTX_DIR/mediamtx_v1.15.3_linux_arm64.tar.gz" -C "$MEDIAMTX_DIR"
fi

chmod +x "$MEDIAMTX_DIR/mediamtx"

echo "MediaMTX version:"
"$MEDIAMTX_DIR/mediamtx" --version

# Step 3: Create MediaMTX Configuration File
echo ""
echo "Step 3: Creating MediaMTX configuration file..."

# Get the absolute path for the mediamtx directory
MEDIAMTX_ABS_DIR="$(cd "$MEDIAMTX_DIR" && pwd)"

# Create a simplified mediamtx.yml if it doesn't exist or backup existing one
if [ ! -f "$MEDIAMTX_DIR/mediamtx.yml" ] || ! grep -q "cam0:" "$MEDIAMTX_DIR/mediamtx.yml" 2>/dev/null; then
  # Backup existing config if it exists
  if [ -f "$MEDIAMTX_DIR/mediamtx.yml" ]; then
    cp "$MEDIAMTX_DIR/mediamtx.yml" "$MEDIAMTX_DIR/mediamtx.yml.backup"
  fi

  # Create camera-specific configuration
  cat > "$MEDIAMTX_DIR/mediamtx.yml" <<EOF
###############################################
# MediaMTX Configuration for IMX219 Camera(s)
###############################################

logLevel: info
logDestinations: [stdout]

# RTSP server settings
rtspAddress: :8554

# HLS server (for web browser viewing)
hlsAddress: :8888

# WebRTC server (for low-latency web viewing)
webrtcAddress: :8889

# Authentication - allow anyone (change for production!)
authMethod: internal
authInternalUsers:
- user: any
  pass:
  ips: []
  permissions:
  - action: publish
  - action: read
  - action: playback

###############################################
# Camera stream paths
###############################################

paths:
  # Single camera or Left camera (video0)
  cam0:
    runOnInit: bash $MEDIAMTX_ABS_DIR/stream_cam0.sh
    runOnInitRestart: yes

  # Right camera (video1) - uncomment if using dual cameras
  # cam1:
  #   runOnInit: bash $MEDIAMTX_ABS_DIR/stream_cam1.sh
  #   runOnInitRestart: yes
EOF
  echo "Created mediamtx.yml"
else
  echo "mediamtx.yml already exists with camera paths configured"
fi

# Step 4: Create Camera Stream Scripts
echo ""
echo "Step 4: Creating camera stream scripts..."

# Create stream_cam0.sh
cat > "$MEDIAMTX_DIR/stream_cam0.sh" <<'STREAM_CAM0_EOF'
#!/bin/bash
# GStreamer + FFmpeg pipeline for Camera 0 (sensor-id=0, /dev/video0)
# Captures from camera and publishes to MediaMTX via RTSP

gst-launch-1.0 -v \
  nvarguscamerasrc sensor-id=0 ! \
  'video/x-raw(memory:NVMM),width=1920,height=1080,framerate=30/1' ! \
  nvvidconv ! \
  'video/x-raw,format=I420' ! \
  x264enc tune=zerolatency bitrate=4000 speed-preset=superfast ! \
  h264parse ! \
  'video/x-h264,stream-format=byte-stream' ! \
  fdsink | \
  ffmpeg -re -f h264 -i pipe:0 -c:v copy -f rtsp rtsp://localhost:8554/cam0
STREAM_CAM0_EOF

chmod +x "$MEDIAMTX_DIR/stream_cam0.sh"
echo "Created stream_cam0.sh"

# Create stream_cam1.sh (optional, for dual camera setup)
cat > "$MEDIAMTX_DIR/stream_cam1.sh" <<'STREAM_CAM1_EOF'
#!/bin/bash
# GStreamer + FFmpeg pipeline for Camera 1 (sensor-id=1, /dev/video1)

gst-launch-1.0 -v \
  nvarguscamerasrc sensor-id=1 ! \
  'video/x-raw(memory:NVMM),width=1920,height=1080,framerate=30/1' ! \
  nvvidconv ! \
  'video/x-raw,format=I420' ! \
  x264enc tune=zerolatency bitrate=4000 speed-preset=superfast ! \
  h264parse ! \
  'video/x-h264,stream-format=byte-stream' ! \
  fdsink | \
  ffmpeg -re -f h264 -i pipe:0 -c:v copy -f rtsp rtsp://localhost:8554/cam1
STREAM_CAM1_EOF

chmod +x "$MEDIAMTX_DIR/stream_cam1.sh"
echo "Created stream_cam1.sh"

# Step 5: Create Startup Script
echo ""
echo "Step 5: Creating startup script..."

cat > "$MEDIAMTX_DIR/start_rtsp.sh" <<'START_EOF'
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
START_EOF

chmod +x "$MEDIAMTX_DIR/start_rtsp.sh"
echo "Created start_rtsp.sh"

# Step 6: Verify Camera Detection
echo ""
echo "Step 6: Verifying camera detection..."
echo "Detected cameras:"
v4l2-ctl --list-devices || echo "Warning: Could not list devices (cameras may not be connected)"

# Summary
echo ""
echo "========================================"
echo "Setup Complete!"
echo "========================================"
echo ""
echo "Files created in: $MEDIAMTX_ABS_DIR"
echo "  - mediamtx (executable)"
echo "  - mediamtx.yml (configuration)"
echo "  - stream_cam0.sh (camera 0 stream script)"
echo "  - stream_cam1.sh (camera 1 stream script - optional)"
echo "  - start_rtsp.sh (startup script)"
echo ""
echo "To start the RTSP server manually:"
echo "  cd $MEDIAMTX_ABS_DIR"
echo "  ./start_rtsp.sh"
echo ""
echo "To test the stream:"
echo "  ffplay rtsp://localhost:8554/cam0"
echo ""
echo "To set up automatic startup on boot, see RTSP_SETUP.md"
echo "  for systemd service setup instructions."
echo ""
