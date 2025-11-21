# Jetson Orin Nano Field Kit - Application Layer

Open source application layer for the Jetson Orin Nano Field Kit, providing AI-powered vision and voice applications optimized for edge deployment.

## Overview

This repository contains the application software stack for the Jetson Orin Nano Field Kit, an out of the box configured jetson orin nano developer kit setup. The kit provides dual IMX219 cameras and pre-installed AI tools for offline deployment on top of what's already provided on the jetson orin nano.

This application layer is designed to work with the Jetson Orin Nano system image configured using the setup instructions in the [implyinfer-jetson-orin-nano-field-kit-notes](https://github.com/implyinfer/implyinfer-jetson-orin-nano-field-kit-notes) repository and is part of the [implyinfer-landing](https://github.com/implyinfer/implyinfer-landing) project.

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

### System Image Setup

Before using this application layer, ensure you have:

1. Flashed the Jetson Orin Nano with the system image
2. Completed the initial setup using instructions from [implyinfer-jetson-orin-nano-field-kit-notes](https://github.com/implyinfer/implyinfer-jetson-orin-nano-field-kit-notes)
3. Verified camera detection and basic system functionality

## Installation

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

## Usage

### RTSP Camera Streaming

The MediaMTX service provides RTSP streaming from IMX219 cameras. See [RTSP_SETUP.md](RTSP_SETUP.md) for complete setup and configuration.

**Quick Start:**

```bash
# Check service status
sudo systemctl status mediamtx.service

# View stream (replace with your Jetson IP)
ffplay rtsp://YOUR_JETSON_IP:8554/cam0
```

### Vision Application

Run real-time object detection on camera streams:

```bash
cd apps/vision/roboflow
python3 run_roboflow_inference.py
```

For detailed usage, see [apps/vision/roboflow/README.md](apps/vision/roboflow/README.md) and [apps/vision/roboflow/QUICKSTART.md](apps/vision/roboflow/QUICKSTART.md).

### Voice Assistant

Start the voice assistant service:

```bash
cd apps/voice-assistant
python3 main.py dev
```

The assistant supports:
- Wake word detection for privacy
- Tool calling for system operations
- Safe Linux command execution
- Offline knowledge base queries via Kiwix
- Vision integration for object detection queries

## Project Structure

```
.
├── apps/
│   ├── docs/              # Documentation site
│   ├── scripts/           # Utility scripts
│   ├── vision/            # Vision applications
│   │   └── roboflow/      # Roboflow inference
│   └── voice-assistant/   # Voice assistant application
├── packages/              # Shared packages
│   ├── eslint-config/     # ESLint configurations
│   ├── typescript-config/ # TypeScript configurations
│   └── ui/                # Shared UI components
├── system/                # System services
│   ├── kiwix/             # Kiwix offline knowledge base
│   ├── livekit/           # LiveKit server setup
│   ├── mediamtx/          # MediaMTX RTSP server
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

## Configuration

### Environment Variables

Each application may require specific environment variables. Check individual application README files:

- Vision: `apps/vision/roboflow/README.md`
- Voice Assistant: `apps/voice-assistant/README.md` (if exists)
- System Services: Individual service directories

### Service Configuration

System services are configured via:

- MediaMTX: `system/mediamtx/mediamtx.yml`
- LiveKit: `system/livekit/server.yaml`
- Docker services: `system/docker-compose.yml`

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

## Documentation

- [RTSP Setup Guide](RTSP_SETUP.md) - Complete RTSP streaming setup
- [Vision Application](apps/vision/roboflow/README.md) - Roboflow inference documentation
- [Vision Quick Start](apps/vision/roboflow/QUICKSTART.md) - Quick setup guide

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
