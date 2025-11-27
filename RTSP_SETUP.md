# RTSP Streaming Setup for Jetson Orin Nano

Complete guide for setting up RTSP streaming from IMX219 cameras on Jetson Orin Nano from scratch, including automatic startup on boot.

## Table of Contents
- [Prerequisites](#prerequisites)
- [Hardware Setup](#hardware-setup)
- [Software Installation](#software-installation)
- [Configuration](#configuration)
- [Testing the Setup](#testing-the-setup)
- [Automatic Startup Service](#automatic-startup-service)
- [Viewing Streams](#viewing-streams)
- [Troubleshooting](#troubleshooting)

## Prerequisites

### Hardware Requirements
- NVIDIA Jetson Orin Nano Developer Kit
- Dual Stereo IMX219 camera module
- Stable power supply (5V 4A recommended)
- Network connection

### Software Requirements
- JetPack 6.2 installed
- Ubuntu 22.04 (comes with JetPack)
- Internet connection for downloading MediaMTX

## Hardware Setup

1. **Power down your Jetson Orin Nano completely**
   ```bash
   sudo shutdown -h now
   ```

2. **Connect IMX219 camera(s)**
   - For single camera: Connect to CAM0 port
   - For dual cameras: Connect to both CAM0 and CAM1 ports
   - Ensure the ribbon cable is properly seated with contacts facing inward

3. **Power on the Jetson**

4. **Verify camera detection**
   ```bash
   v4l2-ctl --list-devices
   ```

   Expected output:
   ```
   vi-output, imx219 9-0010 (platform:tegra-capture-vi:2):
       /dev/video0

   vi-output, imx219 10-0010 (platform:tegra-capture-vi:1):
       /dev/video1
   ```

## Software Installation

### Step 1: Install Required Packages

```bash
# Update package lists
sudo apt update

# Install GStreamer and tools (usually pre-installed on JetPack)
sudo apt install -y \
    gstreamer1.0-tools \
    gstreamer1.0-plugins-good \
    gstreamer1.0-plugins-bad \
    ffmpeg \
    v4l-utils
```

### Step 2: Download and Install MediaMTX

```bash
# Create installation directory
mkdir -p ~/mediamtx
cd ~/mediamtx

# Download MediaMTX for ARM64
wget https://github.com/bluenviron/mediamtx/releases/download/v1.15.3/mediamtx_v1.15.3_linux_arm64.tar.gz

# Extract
tar -xzf mediamtx_v1.15.3_linux_arm64.tar.gz

# Make executable
chmod +x mediamtx

# Verify installation
./mediamtx --version
```

### Step 3: Test Camera Pipeline

Before setting up RTSP, verify your camera works with GStreamer:

```bash
# Test camera 0 (simple preview)
gst-launch-1.0 nvarguscamerasrc sensor-id=0 ! nvvidconv ! autovideosink

# If the above works, press Ctrl+C to stop and continue
```

## Configuration

### Step 1: Create MediaMTX Configuration File

Create `~/mediamtx/mediamtx.yml`:

```yaml
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
    runOnInit: bash /home/box/mediamtx/stream_cam0.sh
    runOnInitRestart: yes

  # Right camera (video1) - uncomment if using dual cameras
  # cam1:
  #   runOnInit: bash /home/box/mediamtx/stream_cam1.sh
  #   runOnInitRestart: yes
```

### Step 2: Create Camera Stream Scripts

**For Camera 0 (CAM0 / /dev/video0):**

Create `~/mediamtx/stream_cam0.sh`:

```bash
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
```

Make it executable:
```bash
chmod +x ~/mediamtx/stream_cam0.sh
```

**For Camera 1 (CAM1 / /dev/video1) - Optional:**

Create `~/mediamtx/stream_cam1.sh`:

```bash
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
```

Make it executable:
```bash
chmod +x ~/mediamtx/stream_cam1.sh
```

### Step 3: Create Startup Script (Optional)

Create `~/mediamtx/start_rtsp.sh`:

```bash
#!/bin/bash
# Startup script for MediaMTX RTSP server

cd /home/box/mediamtx

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
```

Make it executable:
```bash
chmod +x ~/mediamtx/start_rtsp.sh
```

## Testing the Setup

### Manual Test

1. **Start MediaMTX server**
   ```bash
   cd ~/mediamtx
   ./start_rtsp.sh
   ```

2. **Check that streams are running**

   You should see output indicating:
   - MediaMTX started
   - Camera streams publishing
   - No errors in the logs

3. **Test stream from another terminal**
   ```bash
   # Using ffplay
   ffplay rtsp://localhost:8554/cam0

   # Or using GStreamer
   gst-launch-1.0 rtspsrc location=rtsp://localhost:8554/cam0 ! \
     rtph264depay ! h264parse ! nvv4l2decoder ! nvvidconv ! autovideosink
   ```

4. **Stop the server**
   Press `Ctrl+C` in the terminal running MediaMTX

## Automatic Startup Service

To automatically start the RTSP server on boot, create a systemd service.

### Step 1: Create Service File

Create `/etc/systemd/system/mediamtx.service`:

```bash
sudo nano /etc/systemd/system/mediamtx.service
```

Add the following content:

```ini
[Unit]
Description=MediaMTX RTSP Server for IMX219 Camera(s)
After=network.target
Wants=network-online.target

[Service]
Type=simple
User=box
Group=box
WorkingDirectory=/home/box/mediamtx
ExecStart=/home/box/mediamtx/mediamtx /home/box/mediamtx/mediamtx.yml
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

# Environment
Environment="PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"

[Install]
WantedBy=multi-user.target
```

**Important:** Replace `box` with your actual username if different.

### Step 2: Enable and Start Service

```bash
# Reload systemd to read new service
sudo systemctl daemon-reload

# Enable service to start on boot
sudo systemctl enable mediamtx.service

# Start service now
sudo systemctl start mediamtx.service

# Check service status
sudo systemctl status mediamtx.service
```

### Step 3: Verify Automatic Startup

```bash
# View service logs
sudo journalctl -u mediamtx.service -f

# Test stream
ffplay rtsp://localhost:8554/cam0
```

### Service Management Commands

```bash
# Start service
sudo systemctl start mediamtx.service

# Stop service
sudo systemctl stop mediamtx.service

# Restart service
sudo systemctl restart mediamtx.service

# Check status
sudo systemctl status mediamtx.service

# View logs
sudo journalctl -u mediamtx.service -n 50

# Disable automatic startup
sudo systemctl disable mediamtx.service
```

## Viewing Streams

### Get Your Jetson's IP Address

```bash
hostname -I | awk '{print $1}'
```

### Access Methods

#### 1. RTSP (Best for low latency)
```
rtsp://YOUR_JETSON_IP:8554/cam0
```

**Using VLC:**
```bash
vlc rtsp://YOUR_JETSON_IP:8554/cam0
```

**Using FFplay:**
```bash
ffplay -rtsp_transport tcp rtsp://YOUR_JETSON_IP:8554/cam0
```

**Using GStreamer:**
```bash
gst-launch-1.0 rtspsrc location=rtsp://YOUR_JETSON_IP:8554/cam0 latency=0 ! \
  rtph264depay ! h264parse ! avdec_h264 ! autovideosink
```

#### 2. HLS (Works in web browsers)
```
http://YOUR_JETSON_IP:8888/cam0
```

Open in any modern web browser (Chrome, Firefox, Safari, Edge)

#### 3. WebRTC (Low latency web viewing)
```
http://YOUR_JETSON_IP:8889/cam0
```

Requires WebRTC-compatible player or custom web application

### Mobile Viewing

**iOS:**
- Use VLC app: Open Network Stream → Enter RTSP URL

**Android:**
- Use VLC app: Open Network Stream → Enter RTSP URL
- Or any RTSP player from Play Store

## Customization

### Change Resolution and Framerate

Edit the stream script (`stream_cam0.sh`):

```bash
# Current: 1920x1080 @ 30fps
'video/x-raw(memory:NVMM),width=1920,height=1080,framerate=30/1'

# Change to 1280x720 @ 60fps
'video/x-raw(memory:NVMM),width=1280,height=720,framerate=60/1'
```

**Supported IMX219 modes:**
- 3280x2464 @ 21 fps (max resolution)
- 3280x1848 @ 28 fps
- 1920x1080 @ 30 fps (default)
- 1640x1232 @ 30 fps
- 1280x720 @ 60 fps

### Change Bitrate

Edit the stream script:

```bash
# Current: 4000 kbps
x264enc tune=zerolatency bitrate=4000 speed-preset=superfast

# Lower quality (saves bandwidth): 2000 kbps
x264enc tune=zerolatency bitrate=2000 speed-preset=superfast

# Higher quality: 8000 kbps
x264enc tune=zerolatency bitrate=8000 speed-preset=superfast
```

### Add Authentication

Edit `mediamtx.yml`:

```yaml
authMethod: internal
authInternalUsers:
- user: admin
  pass: your_password_here
  ips: []
  permissions:
  - action: publish
  - action: read
```

Then access stream with:
```
rtsp://admin:your_password_here@YOUR_IP:8554/cam0
```

### Change Ports

Edit `mediamtx.yml`:

```yaml
rtspAddress: :8554    # Change to :9554 for different port
hlsAddress: :8888     # Change as needed
webrtcAddress: :8889  # Change as needed
```

## Troubleshooting

### Camera Not Detected

```bash
# Check camera hardware
v4l2-ctl --list-devices

# Check if camera is accessible
ls -l /dev/video*

# Test camera with simple pipeline
gst-launch-1.0 nvarguscamerasrc sensor-id=0 ! fakesink
```

### GStreamer Errors

```bash
# Check GStreamer version
gst-launch-1.0 --version

# List available plugins
gst-inspect-1.0 | grep -i argus

# Test without encoding
gst-launch-1.0 nvarguscamerasrc sensor-id=0 ! nvvidconv ! autovideosink
```

### Port Already in Use

```bash
# Check what's using port 8554
sudo lsof -i :8554

# Or use fuser
fuser 8554/tcp

# Kill process if needed
sudo kill -9 <PID>
```

### Service Not Starting

```bash
# Check detailed service status
sudo systemctl status mediamtx.service

# View full logs
sudo journalctl -u mediamtx.service -b

# Check file permissions
ls -la /home/box/mediamtx/

# Ensure scripts are executable
chmod +x /home/box/mediamtx/*.sh
chmod +x /home/box/mediamtx/mediamtx
```

### No Video / Black Screen

```bash
# Test camera directly
gst-launch-1.0 nvarguscamerasrc sensor-id=0 ! \
  'video/x-raw(memory:NVMM),width=1920,height=1080,framerate=30/1' ! \
  nvvidconv ! autovideosink

# Check MediaMTX logs for errors
sudo journalctl -u mediamtx.service -f

# Verify stream is publishing
curl http://localhost:8554/cam0
```

### High CPU Usage

- Lower resolution: Use 1280x720 instead of 1920x1080
- Reduce framerate: Use 15fps instead of 30fps
- Lower bitrate: Use 2000 instead of 4000
- Use hardware encoding (x264enc is CPU-based, consider nvv4l2h264enc)

### Network Issues

```bash
# Check firewall
sudo ufw status

# Allow RTSP port if needed
sudo ufw allow 8554/tcp
sudo ufw allow 8888/tcp

# Check if service is listening
sudo netstat -tulpn | grep -E '8554|8888'
```

## Performance Tips

1. **Use wired Ethernet** instead of WiFi for better stability
2. **Adjust bitrate** based on network bandwidth
3. **Lower resolution** if experiencing lag
4. **Use RTSP with TCP** for reliable streaming: `rtsp_transport tcp`
5. **Disable unnecessary services** to free up resources
6. **Use active cooling** to prevent thermal throttling

## Additional Resources

- [MediaMTX Documentation](https://github.com/bluenviron/mediamtx)
- [GStreamer Documentation](https://gstreamer.freedesktop.org/documentation/)
- [NVIDIA Jetson Orin Nano Developer Guide](https://developer.nvidia.com/embedded/learn/get-started-jetson-orin-nano-devkit)
- [IMX219 Camera Module Documentation](https://www.raspberrypi.org/documentation/hardware/camera/)

## License

This setup guide is provided as-is for educational and development purposes.
