# Claude Documentation - Jetson Orin Nano Field Kit

This document provides context and guidelines for AI assistants working with this codebase.

## Project Context

This repository is the open source application layer for the Jetson Orin Nano Field Kit. It provides AI-powered applications including computer vision and voice assistance optimized for edge deployment on NVIDIA Jetson hardware.

## Repository Structure

### Applications (`apps/`)

**Vision Application** (`apps/vision/roboflow/`)
- Real-time object detection using Roboflow inference
- Processes RTSP camera streams from IMX219 modules
- Supports YOLOv8 models (nano, medium, large)
- Python-based with OpenCV and GStreamer integration
- Key files:
  - `run_roboflow_inference.py` - Main inference script
  - `client.py` - RTSP client utilities
  - `monitoring.py` - System monitoring and metrics
  - `start_rtsp_server.py` - RTSP server utilities

**Voice Assistant** (`apps/voice-assistant/`)
- Wake word-enabled voice assistant using LiveKit
- Tool calling for system operations
- Safe Linux command execution with whitelisting
- Offline knowledge base integration via Kiwix
- Vision plugin integration for object detection queries
- Key files:
  - `main.py` - Main assistant application
  - `llm_plugin.py` - LLM integration
  - `stt_plugin.py` - Speech-to-text plugin
  - `tts_plugin.py` - Text-to-speech plugin
  - `kiwix_tool.py` - Offline knowledge base tool
  - `vision_plugin.py` - Vision integration

### System Services (`system/`)

**MediaMTX** (`system/mediamtx/`)
- RTSP streaming server for camera feeds
- Configuration: `mediamtx.yml`
- Service setup: `setup-mediamtx-service.sh`
- Binary: `mediamtx` (ARM64)

**LiveKit** (`system/livekit/`)
- Real-time communication infrastructure
- Used by voice assistant
- Configuration: `server.yaml`
- Installation: `install-livekit.sh`

**Kiwix** (`system/kiwix/`)
- Offline Wikipedia and knowledge base
- Docker-based service
- ZIM file downloads: `download-zim.sh`
- Service setup: `setup-kiwix-service.sh`

**Roboflow** (`system/roboflow/`)
- Docker service for Roboflow inference server
- Jetson-optimized image
- Service setup: `setup-roboflow-service.sh`

**Ultralytics** (`system/ultralytics/`)
- YOLO model inference service
- Docker-based
- Separate compose file for interactive use

### Shared Packages (`packages/`)

- `ui/` - Shared React components (Button, Card, Code)
- `eslint-config/` - Shared ESLint configurations
- `typescript-config/` - Shared TypeScript configurations

## Technology Stack

### Frontend
- Next.js 14+ (App Router)
- React 18+
- TypeScript
- Tailwind CSS
- Shadcn UI / Radix UI
- Turborepo for monorepo management
- pnpm for package management

### Backend / Services
- Python 3.10+
- LiveKit for real-time communication
- Roboflow Inference for computer vision
- OpenCV for image processing
- GStreamer for video pipelines
- Docker for service containerization

### System Integration
- systemd for service management
- MediaMTX for RTSP streaming
- Kiwix for offline knowledge base
- NVIDIA JetPack for Jetson hardware support

## Development Guidelines

### Code Style

**JavaScript/TypeScript:**
- Follow Standard.js rules
- 2 space indentation
- Single quotes for strings
- No semicolons (unless required)
- Use functional and declarative patterns
- Prefer named exports for components

**Python:**
- Follow PEP 8 conventions
- Use type hints where appropriate
- Async/await for asynchronous operations
- Proper error handling and logging

### File Organization

- Applications in `apps/` directory
- Shared code in `packages/` directory
- System services in `system/` directory
- Configuration files at appropriate levels
- Documentation in markdown files

### Naming Conventions

- Directories: lowercase with dashes (`voice-assistant`)
- Files: lowercase with dashes or underscores
- Components: PascalCase (`VoiceAssistant`)
- Functions/variables: camelCase (`getCameraStream`)
- Constants: UPPER_SNAKE_CASE (`MAX_RETRIES`)

## Key Workflows

### Adding a New Application

1. Create directory in `apps/`
2. Add `package.json` or `requirements.txt` as appropriate
3. Update `turbo.json` if build steps needed
4. Add to workspace configuration if needed
5. Create README with setup instructions

### Adding a System Service

1. Create directory in `system/`
2. Add service configuration files
3. Create setup script (`setup-*-service.sh`)
4. Create systemd service file if needed
5. Update `system/provision.sh` to include new service
6. Add Docker compose configuration if containerized

### Modifying Vision Pipeline

1. Camera streams via MediaMTX RTSP server
2. Applications consume RTSP streams
3. Processing uses GStreamer pipelines for hardware acceleration
4. AI inference via Roboflow or Ultralytics
5. Results can be visualized or streamed back

### Modifying Voice Assistant

1. Input via LiveKit
2. Wake word detection for privacy
3. STT converts speech to text
4. LLM processes with tool calling
5. Tools execute system operations safely
6. TTS converts response to speech
7. Vision plugin can query camera feeds

## Environment Variables

Common environment variables across applications:

- `ROBOFLOW_API_KEY` - Roboflow API key for vision
- `RTSP_URL` - RTSP stream URL (default: `rtsp://localhost:8554/cam0`)
- `WAKE_WORD` - Voice assistant wake word (default: "nano")
- `DISPLAY` - X display for GUI applications (default: `:0`)

Check individual application directories for specific requirements.

## Hardware Considerations

### Jetson Orin Nano Specifications
- 67 TOPS AI performance
- Dual IMX219 camera support
- GPIO pins for LED control
- Thermal management important for sustained performance

### Performance Optimization
- Use hardware-accelerated GStreamer pipelines
- Leverage NVMM memory for video buffers
- Monitor thermal throttling
- Adjust model sizes for real-time performance
- Use appropriate camera resolutions

## Common Tasks

### Starting All Services

```bash
cd system
bash provision.sh
```

### Running Vision Application

```bash
cd apps/vision/roboflow
python3 run_roboflow_inference.py
```

### Running Voice Assistant

```bash
cd apps/voice-assistant
python3 main.py dev
```

### Checking Service Status

```bash
sudo systemctl status mediamtx.service
sudo systemctl status kiwix.service
docker compose -f system/docker-compose.yml ps
```

## Testing

- Vision: Test with `ffplay` or OpenCV display
- Voice: Test wake word and command execution
- Services: Check systemd logs and Docker logs

## Troubleshooting

### Camera Issues
- Verify hardware connection
- Check `/dev/video*` devices
- Test with `v4l2-ctl --list-devices`
- Review MediaMTX logs

### Performance Issues
- Monitor with `jtop` if available
- Check thermal status
- Reduce camera resolution
- Use smaller AI models
- Check system resource usage

### Service Issues
- Check systemd service status
- Review service logs
- Verify configuration files
- Check file permissions
- Ensure dependencies installed

## Related Documentation

- `README.md` - Main project documentation
- `RTSP_SETUP.md` - RTSP streaming setup guide
- `apps/vision/roboflow/README.md` - Vision application docs
- `apps/vision/roboflow/QUICKSTART.md` - Quick start guide

## External Resources

- [NVIDIA Jetson Documentation](https://developer.nvidia.com/embedded/learn/get-started-jetson-orin-nano-devkit)
- [MediaMTX GitHub](https://github.com/bluenviron/mediamtx)
- [Roboflow Documentation](https://docs.roboflow.com/)
- [LiveKit Documentation](https://docs.livekit.io/)
- [Turborepo Documentation](https://turbo.build/repo/docs)

## Notes for AI Assistants

When working with this codebase:

1. **Hardware Context**: Always consider Jetson Orin Nano hardware constraints and capabilities
2. **Real-time Performance**: Applications are optimized for real-time edge deployment
3. **Offline Capability**: System designed for offline operation where possible
4. **Service Dependencies**: Understand service dependencies (e.g., vision needs RTSP, voice needs LiveKit)
5. **Monorepo Structure**: Respect Turborepo structure and shared packages
6. **System Integration**: Services use systemd and Docker for deployment
7. **Camera Integration**: Dual camera support via MediaMTX RTSP streams
8. **AI Models**: Use appropriate model sizes for Jetson hardware performance

When suggesting changes:
- Consider Jetson hardware limitations
- Maintain offline capability where possible
- Preserve real-time performance characteristics
- Follow existing code style and patterns
- Update relevant documentation
- Test on actual hardware when possible

