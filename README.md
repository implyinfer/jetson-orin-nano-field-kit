# Jetson Orin Nano Field Kit

A comprehensive toolkit for the NVIDIA Jetson Orin Nano, featuring reliable camera streaming, AI inference, and edge computing capabilities.

## Features

- **Dual Camera RTSP/WebRTC Streaming** - Ultra low-latency video streaming via MediaMTX
- **Roboflow Local Inference** - GPU-accelerated object detection with pre-downloaded models
- **Web-based Monitoring** - Browser-accessible video streams with real-time inference overlays

## Quick Start

### 1. Start Core Services

```bash
cd system
docker compose up -d
```

This starts:
- **Roboflow Inference Server** on port `9001`
- **Kiwix** (offline wiki) on port `8001`
- **Open WebUI** (Ollama frontend) on port `8080`

### 2. Start Camera Streams

The MediaMTX service provides reliable RTSP/WebRTC streaming from both cameras:

```bash
# Start MediaMTX service (if not already running)
sudo systemctl start mediamtx.service
```

**Available Streams:**

| Camera | Protocol | URL |
|--------|----------|-----|
| cam0   | RTSP     | `rtsp://<JETSON_IP>:8554/cam0` |
| cam0   | HLS      | `http://<JETSON_IP>:8888/cam0` |
| cam0   | WebRTC   | `http://<JETSON_IP>:8889/cam0` |
| cam1   | RTSP     | `rtsp://<JETSON_IP>:8554/cam1` |
| cam1   | HLS      | `http://<JETSON_IP>:8888/cam1` |
| cam1   | WebRTC   | `http://<JETSON_IP>:8889/cam1` |

## Camera Streaming (MediaMTX)

The system uses MediaMTX for reliable, low-latency camera streaming with three protocols:

- **RTSP** (port 8554) - Best for programmatic access and VLC
- **HLS** (port 8888) - Works in any web browser
- **WebRTC** (port 8889) - Ultra low-latency web viewing

### Stream Configuration

Camera streams are configured in `system/mediamtx/mediamtx.yml` with optimized scripts:
- `system/mediamtx/start_cam0.sh` - Left stereo camera (sensor-id=0)
- `system/mediamtx/start_cam1.sh` - Right stereo camera (sensor-id=1)

Both stereo cameras stream at **1280x720 @ 30fps** with ultra low-latency encoding optimizations.

### Viewing Streams

**VLC Player:**
```bash
vlc rtsp://<JETSON_IP>:8554/cam0
```

**FFplay:**
```bash
ffplay -rtsp_transport tcp rtsp://<JETSON_IP>:8554/cam0
```

**Web Browser:**
Open `http://<JETSON_IP>:8888/cam0` or `http://<JETSON_IP>:8889/cam0`

For detailed setup instructions, see [RTSP_SETUP.md](RTSP_SETUP.md).

## Roboflow Inference

The kit includes GPU-accelerated object detection using Roboflow's inference server with locally cached models.

### Download Models (One-time Setup)

Pre-download models for offline inference:

```bash
cd apps/vision/roboflow
source venv/bin/activate
python download_models.py
```

**Available Models:**

| Model | Description |
|-------|-------------|
| `yolov11n-640` | YOLOv11 Nano - Fast, lightweight |
| `yolov11s-640` | YOLOv11 Small - Balanced |
| `rfdetr-small` | RF-DETR Small - High accuracy |
| `rfdetr-medium` | RF-DETR Medium - Highest accuracy |
| `yolov8n-640` | YOLOv8 Nano - Fast |
| `yolov8s-640` | YOLOv8 Small - Balanced |
| `yolov11n-seg-640` | YOLOv11 Nano Segmentation |

### Run Web Stream Inference

Stream camera feed with real-time object detection to a web browser:

```bash
cd apps/vision/roboflow
source venv/bin/activate
python run_roboflow_web_stream.py
```

Open `http://<JETSON_IP>:5000` in your browser to view the annotated stream.

**Options:**
```bash
# Use a different model
python run_roboflow_web_stream.py --model rfdetr-small

# Change confidence threshold
python run_roboflow_web_stream.py --confidence 0.7

# Use cam1 instead of cam0
python run_roboflow_web_stream.py --rtsp-url rtsp://127.0.0.1:8554/cam1

# Change web server port
python run_roboflow_web_stream.py --port 8080
```

## Directory Structure

```
jetson-orin-nano-field-kit/
├── apps/
│   ├── vision/
│   │   └── roboflow/          # Roboflow inference scripts
│   │       ├── download_models.py
│   │       ├── run_roboflow_web_stream.py
│   │       └── run_stereo_disparity.py
│   ├── dashboard/             # Web dashboard
│   ├── docs/                  # Documentation app
│   └── web/                   # Web applications
├── system/
│   ├── docker-compose.yml     # Core services
│   └── mediamtx/              # Camera streaming
│       ├── mediamtx.yml       # MediaMTX configuration
│       ├── start_cam0.sh      # Camera 0 pipeline
│       └── start_cam1.sh      # Camera 1 pipeline
└── packages/                  # Shared packages
```

## Service Ports Summary

| Port | Service | Description |
|------|---------|-------------|
| 5000 | Roboflow Web Stream | Inference visualization |
| 8001 | Kiwix | Offline Wikipedia |
| 8080 | Open WebUI | Ollama chat interface |
| 8554 | MediaMTX RTSP | Camera RTSP streams |
| 8888 | MediaMTX HLS | Camera HLS streams |
| 8889 | MediaMTX WebRTC | Camera WebRTC streams |
| 9001 | Roboflow Inference | GPU inference API |

## Requirements

- NVIDIA Jetson Orin Nano Developer Kit
- JetPack 6.2
- Dual Stereo IMX219 camera module
- Docker and Docker Compose

## License

This project is provided as-is for educational and development purposes.
