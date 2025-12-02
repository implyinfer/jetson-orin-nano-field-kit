<h1 align="center"><strong>Jetson Orin Nano Field Kit</strong></h1>

<p align="center">
Open source application layer for the Jetson Orin Nano Field Kit.<br>
AI-powered vision and voice applications optimized for edge deployment.
</p>

<p align="center">
<a href="#overview">About</a> ·
<a href="https://www.implyinfer.com/jetson-field-kit">How to Purchase</a> ·
<a href="#quick-start">Get Started</a> ·
<a href="#documentation">Documentation</a> ·
<a href="#contributing">Contributing</a>
</p>

---

![Jetson Orin Nano Field Kit](images/jetson-orin-nano-field-kit-poster.png)

## Overview

This repository contains the application software stack for the Jetson Orin Nano Field Kit, an out of the box configured jetson orin nano developer kit setup. The kit provides dual IMX219 cameras and pre-installed AI tools for offline deployment on top of what's already provided on the jetson orin nano.

This application layer is designed to work with the Jetson Orin Nano system image configured using the setup instructions in the [implyinfer-jetson-orin-nano-field-kit-notes](https://github.com/implyinfer/implyinfer-jetson-orin-nano-field-kit-notes) repository and is part of the [implyinfer-landing](https://github.com/implyinfer/implyinfer-landing) project.

## Features

- **Dual Camera RTSP/WebRTC Streaming** - Ultra low-latency video streaming via MediaMTX
- **Roboflow Local Inference** - GPU-accelerated object detection with pre-downloaded models
- **Web-based Monitoring** - Browser-accessible video streams with real-time inference overlays
- **Voice Assistant** - Wake word-enabled assistant with tool calling and offline knowledge base

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

## Architecture

This is a monorepo built with Turborepo, containing multiple applications and shared packages:

### Applications

- **Vision** (`apps/vision/roboflow`) - Real-time object detection using Roboflow inference on RTSP camera streams
- **Voice Assistant** (`apps/voice-assistant`) - Wake word-enabled voice assistant with tool calling, Linux command execution, and offline knowledge base integration
- **Docs** (`apps/docs`) - Documentation site built with Next.js

### System Services

System-level services configured for the Jetson Orin Nano:

- **MediaMTX** (`system/mediamtx`) - RTSP streaming server for IMX219 camera modules
- **LiveKit** (`system/livekit`) - Real-time communication infrastructure for voice assistant
- **Kiwix** (`system/kiwix`) - Offline Wikipedia and knowledge base server
- **Roboflow** (`system/roboflow`) - Docker service for Roboflow inference server
- **Ultralytics** (`system/ultralytics`) - YOLO model inference service

### Shared Packages

- `packages/ui` - Shared UI components
- `packages/eslint-config` - Shared ESLint configurations
- `packages/typescript-config` - Shared TypeScript configurations

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

## Installation

### System Image Setup

Before using this application layer, ensure you have:

1. **Downloaded the latest release image** from the [releases page](https://github.com/implyinfer/jetson-orin-nano-field-kit/releases)
2. **Flashed the Jetson Orin Nano with the system image** - See [FLASH_NVME.md](FLASH_NVME.md) for complete instructions on flashing the image to an NVMe SSD
3. Completed the initial setup using instructions from [implyinfer-jetson-orin-nano-field-kit-notes](https://github.com/implyinfer/implyinfer-jetson-orin-nano-field-kit-notes)
4. Verified camera detection and basic system functionality

### 1. Clone the Repository

```bash
git clone https://github.com/implyinfer/implyinfer-jetson-orin-nano-field-kit.git
cd implyinfer-jetson-orin-nano-field-kit
```

### 2. Install Dependencies

```bash
# Install pnpm if not already installed
npm install -g pnpm@9.0.0

# Install project dependencies
pnpm install
```

### 3. Set Up System Services

```bash
# Provision all system services
cd system
bash provision.sh
```

This will set up:
- MediaMTX RTSP server
- Kiwix offline knowledge base
- Docker services for Roboflow and other services

### 4. Configure Applications

#### Vision Application

```bash
cd apps/vision/roboflow
bash setup.sh

# Configure your Roboflow API key
nano .env
# Add: ROBOFLOW_API_KEY=your_api_key_here
```

See [apps/vision/roboflow/README.md](apps/vision/roboflow/README.md) for detailed setup instructions.

#### Voice Assistant

```bash
cd apps/voice-assistant
bash configure.sh

# Configure environment variables
nano .env
# Add required API keys and configuration
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

## Project Structure

```
.
├── apps/
│   ├── docs/              # Documentation site
│   ├── scripts/           # Utility scripts
│   ├── vision/            # Vision applications
│   │   └── roboflow/      # Roboflow inference
│   │       ├── download_models.py
│   │       ├── run_roboflow_web_stream.py
│   │       └── run_stereo_disparity.py
│   └── voice-assistant/   # Voice assistant application
├── packages/              # Shared packages
│   ├── eslint-config/     # ESLint configurations
│   ├── typescript-config/ # TypeScript configurations
│   └── ui/                # Shared UI components
├── system/                # System services
│   ├── docker-compose.yml # Core services
│   ├── kiwix/             # Kiwix offline knowledge base
│   ├── livekit/           # LiveKit server setup
│   ├── mediamtx/          # MediaMTX RTSP server
│   │   ├── mediamtx.yml   # MediaMTX configuration
│   │   ├── start_cam0.sh  # Camera 0 pipeline
│   │   └── start_cam1.sh  # Camera 1 pipeline
│   ├── roboflow/          # Roboflow Docker service
│   └── ultralytics/       # Ultralytics service
├── package.json           # Root package configuration
├── turbo.json             # Turborepo configuration
└── pnpm-workspace.yaml    # pnpm workspace configuration
```

## Development

### Monorepo Commands

```bash
# Run all builds
pnpm build

# Run all linters
pnpm lint

# Run type checking
pnpm check-types

# Format code
pnpm format

# Run development servers
pnpm dev
```

### Adding New Applications

1. Create application directory in `apps/`
2. Add package.json with appropriate dependencies
3. Update `turbo.json` if custom build steps are needed
4. Add to workspace in `pnpm-workspace.yaml` if needed

### Code Style

- JavaScript/TypeScript: Follows Standard.js rules (2 spaces, no semicolons, single quotes)
- Python: Follows PEP 8 conventions
- Use functional and declarative programming patterns
- Prefer composition over inheritance

## Troubleshooting

### Camera Not Detected

```bash
# Check camera hardware
v4l2-ctl --list-devices

# Verify camera access
ls -l /dev/video*
```

See [RTSP_SETUP.md](RTSP_SETUP.md) for detailed camera troubleshooting.

### Service Issues

```bash
# Check service status
sudo systemctl status mediamtx.service
sudo systemctl status kiwix.service

# View service logs
sudo journalctl -u mediamtx.service -f
```

### Performance Issues

- Monitor system resources: `jtop` (if installed)
- Check thermal throttling: `cat /sys/devices/virtual/thermal/thermal_zone*/temp`
- Adjust camera resolution/bitrate in MediaMTX configuration
- Use smaller AI models for real-time performance

## Requirements

- NVIDIA Jetson Orin Nano Developer Kit
- JetPack 6.2
- Dual Stereo IMX219 camera module
- Docker and Docker Compose

## Documentation

- [NVMe Flashing Guide](FLASH_NVME.md) - Complete instructions for flashing the system image to an NVMe SSD
- [RTSP Setup Guide](RTSP_SETUP.md) - Complete RTSP streaming setup
- [Vision Application](apps/vision/roboflow/README.md) - Roboflow inference documentation
- [Vision Quick Start](apps/vision/roboflow/QUICKSTART.md) - Quick setup guide

### Release Images

The latest system images are available on the [releases page](https://github.com/implyinfer/jetson-orin-nano-field-kit/releases). Always use the latest release image when flashing your NVMe SSD.

## Contributing

This is an open source project. Contributions are welcome. Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes following the code style guidelines
4. Submit a pull request

## Related Projects

- [implyinfer-jetson-orin-nano-field-kit-notes](https://github.com/implyinfer/implyinfer-jetson-orin-nano-field-kit-notes) - System image setup instructions
- [implyinfer-landing](https://github.com/implyinfer/implyinfer-landing) - Main project repository

## Resources

- [Jetson Orin Nano Developer Guide](https://developer.nvidia.com/embedded/learn/get-started-jetson-orin-nano-devkit)
- [MediaMTX Documentation](https://github.com/bluenviron/mediamtx)
- [Roboflow Documentation](https://docs.roboflow.com/)
- [LiveKit Documentation](https://docs.livekit.io/)

## License

See LICENSE file for license information.

## Support

For issues and questions:

- Open an issue on GitHub
- Check existing documentation in application directories
- Refer to troubleshooting sections in individual README files
