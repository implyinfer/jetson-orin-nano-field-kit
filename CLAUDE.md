# CLAUDE.md - AI Assistant Guide

This document provides comprehensive guidance for AI assistants working with the Jetson Orin Nano Field Kit codebase.

## Project Overview

**Jetson Orin Nano Field Kit** is a sophisticated edge AI platform designed for field deployment on NVIDIA Jetson Orin Nano hardware. It combines:

- **Web Applications**: Next.js-based web interfaces and documentation
- **Voice Assistant**: Advanced voice AI agent with LiveKit integration
- **Computer Vision**: Roboflow and Ultralytics YOLO-based vision processing
- **Offline Knowledge**: Kiwix-powered offline Wikipedia access
- **System Integration**: Hardware control (GPIO, audio, camera) for edge deployment

**Key Design Philosophy**: Built for environments with limited internet connectivity, emphasizing offline capabilities and local model execution.

---

## Repository Structure

### Monorepo Layout

```
jetson-orin-nano-field-kit/
├── apps/                    # Application workspaces
│   ├── docs/               # Documentation site (Next.js, port 3001)
│   ├── web/                # Main web application (Next.js, port 3000)
│   ├── vision/             # Computer vision applications (Python/OpenCV)
│   ├── voice-assistant/    # Voice AI agent (Python/LiveKit)
│   └── scripts/            # System configuration scripts (Bash)
├── packages/               # Shared packages
│   ├── ui/                 # @repo/ui - Shared React components
│   ├── eslint-config/      # @repo/eslint-config - ESLint rules
│   └── typescript-config/  # @repo/typescript-config - TS configs
├── system/                 # Infrastructure and services
│   ├── kiwix/             # Offline Wikipedia service
│   ├── livekit/           # Real-time communication server
│   ├── roboflow/          # Vision inference server (Docker)
│   ├── ultralytics/       # YOLO training/inference (Docker)
│   ├── docker-compose.yml # Main service orchestration
│   └── provision.sh       # System provisioning script
├── .vscode/               # VSCode workspace settings
├── package.json           # Root workspace configuration
├── pnpm-workspace.yaml    # pnpm monorepo definition
└── turbo.json             # Turborepo build configuration
```

### Key Directories Explained

**`/apps/`** - Independent applications with different tech stacks:
- `docs/` and `web/` - Next.js 16 React applications
- `voice-assistant/` - Python-based LiveKit voice agent
- `vision/` - Computer vision scripts (Python/OpenCV/Roboflow)
- `scripts/` - System administration scripts (audio config, etc.)

**`/packages/`** - Shared code consumed by multiple apps:
- All packages use workspace protocol (`workspace:*`)
- Changes here affect multiple applications
- Must maintain backward compatibility

**`/system/`** - Docker services and system-level configurations:
- Each subdirectory contains service-specific setup scripts
- `docker-compose.yml` orchestrates all containerized services
- Services run as systemd daemons for production

---

## Technology Stack

### Frontend/Web (TypeScript/React)

- **Framework**: Next.js 16.0.1 with App Router
- **React**: 19.2.0 (latest)
- **Package Manager**: pnpm 9.0.0+ (REQUIRED - do not use npm/yarn)
- **Build Tool**: Turborepo 2.6.1 (parallel builds, caching)
- **TypeScript**: 5.9.2 with strict type checking
- **Linting**: ESLint 9.39.1 (flat config format)
- **Formatting**: Prettier (auto-format on save)
- **Styling**: CSS Modules, Geist font system

### Backend/Voice Assistant (Python)

- **Framework**: LiveKit Agents SDK
- **STT**: faster_whisper (local inference)
- **TTS**: piper-tts (local synthesis)
- **Wake Word**: Silero VAD
- **Vision**: Moondream (local vision model)
- **LLM Providers**: OpenAI, Anthropic, Google, Groq, Deepgram
- **Web Framework**: Flask (for utilities)
- **Data**: pandas, numpy (data processing)

### Computer Vision (Python)

- **OpenCV** (`cv2`) - Image/video processing
- **Roboflow** - Inference API client
- **Ultralytics** - YOLOv8/v11 training and inference
- **Matplotlib** - Visualization
- **Pandas** - Data analysis

### Infrastructure

- **Containerization**: Docker & Docker Compose
- **Service Management**: systemd (for production services)
- **Audio**: PulseAudio (configured via scripts)
- **Hardware Platform**: NVIDIA Jetson Orin Nano (JetPack 6.0.0)
- **GPU Runtime**: NVIDIA Container Runtime (for Docker)

---

## Development Workflows

### Initial Setup

```bash
# Install dependencies (use pnpm, not npm!)
pnpm install

# Install Python dependencies for voice assistant
cd apps/voice-assistant
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your API keys and configuration
```

### Common Development Commands

**Root-level commands** (run from `/home/user/jetson-orin-nano-field-kit/`):

```bash
# Run all apps in development mode (parallel)
pnpm dev

# Build all apps for production
pnpm build

# Lint all TypeScript/JavaScript code
pnpm lint

# Format all code with Prettier
pnpm format

# Type check all TypeScript code
pnpm check-types
```

**Application-specific commands**:

```bash
# Web/Docs applications
cd apps/web  # or apps/docs
pnpm dev           # Start dev server (with hot reload)
pnpm build         # Production build
pnpm start         # Run production build
pnpm lint          # Lint this app only

# Voice Assistant
cd apps/voice-assistant
python main.py     # Run voice assistant
./configure.sh     # Setup environment/dependencies

# Vision applications
cd apps/vision/roboflow
python monitoring.py  # Run video monitoring
```

### Turborepo Build System

The project uses **Turborepo** for orchestrating builds across the monorepo:

**Defined tasks** (in `turbo.json`):
- `build` - Compiles apps for production (outputs to `.next/**`)
- `dev` - Runs development servers with hot reload
- `lint` - Runs ESLint with zero-warning policy
- `check-types` - TypeScript type checking

**Key features**:
- **Parallel execution**: Tasks run concurrently when possible
- **Dependency awareness**: Shared packages (`@repo/ui`) build first
- **Persistent dev mode**: Dev servers stay running between commands
- **Caching**: Build outputs cached for faster subsequent builds

### Git Workflow

**Current branch**: `claude/claude-md-mi262ay6v7u5topg-018XepescH7zLzxDZWDX1FeW`

**Important conventions**:
- All development happens on feature branches
- Branch names starting with `claude/` are AI-assisted development branches
- Commit messages should be descriptive and follow conventional commits style
- Push with: `git push -u origin <branch-name>`

---

## Key Conventions and Patterns

### Monorepo Conventions

1. **Workspace Dependencies**: Use `workspace:*` protocol for internal packages
   ```json
   {
     "dependencies": {
       "@repo/ui": "workspace:*"
     }
   }
   ```

2. **Shared Configurations**: Apps inherit from shared packages
   - ESLint: `@repo/eslint-config/next-js`
   - TypeScript: `@repo/typescript-config/nextjs.json`

3. **Package Naming**: Shared packages use `@repo/` scope

### Code Style Guidelines

**TypeScript/JavaScript**:
- Strict TypeScript mode enabled
- ESLint with zero warnings (warnings treated as errors)
- Prettier for consistent formatting
- Prefer functional components and hooks (React)
- Use Next.js App Router patterns (not Pages Router)

**Python**:
- Docstrings for functions and classes
- Type hints where appropriate
- Follow PEP 8 conventions
- Use plugin architecture for extensibility (see voice-assistant)

### File Organization

**Next.js apps** (App Router):
```
apps/web/
├── app/              # App Router pages and layouts
│   ├── page.tsx     # Home page (/)
│   ├── layout.tsx   # Root layout
│   └── globals.css  # Global styles
├── public/          # Static assets
└── package.json
```

**Python apps**:
```
apps/voice-assistant/
├── main.py          # Entry point
├── plugins/         # Modular plugins (STT, TTS, LLM, etc.)
├── requirements.txt # Python dependencies
└── .env.example     # Environment variable template
```

---

## Important Files and Configurations

### Root Configuration Files

**`pnpm-workspace.yaml`** - Defines monorepo workspaces:
```yaml
packages:
  - "apps/*"
  - "packages/*"
```

**`turbo.json`** - Build orchestration configuration:
- Defines tasks: `build`, `dev`, `lint`, `check-types`
- Specifies outputs for caching
- Manages task dependencies

**`package.json`** - Root workspace configuration:
- Scripts for running monorepo-wide commands
- Defines pnpm version requirement: `>=9.0.0`
- DevDependencies for build tools (Turbo, Prettier)

### Application-Specific Configurations

**Next.js apps** (`apps/web/next.config.ts`, `apps/docs/next.config.ts`):
- Transpile workspace packages: `@repo/ui`
- Currently minimal configuration

**Voice Assistant** (`apps/voice-assistant/.env.example`):
```bash
LIVEKIT_URL=ws://localhost:7880
LIVEKIT_API_KEY=your_api_key
LIVEKIT_API_SECRET=your_secret
```

**Docker Compose** (`system/docker-compose.yml`):
- **kiwix**: Port 8001, offline Wikipedia
- **roboflow**: Port 9001, vision inference server (GPU-enabled)
- **ultralytics**: Interactive mode, YOLO training/inference

### VSCode Workspace Settings

**`.vscode/settings.json`**:
- ESLint working directories: `apps/web`, `apps/docs`, `packages/ui`
- Auto-detects TypeScript version
- Configure Prettier as default formatter

---

## System Services and Provisioning

### Docker Services

**Start all services**:
```bash
cd system
docker-compose up -d
```

**Individual services**:
```bash
docker-compose up -d kiwix      # Offline Wikipedia
docker-compose up -d roboflow   # Vision inference
docker run -it ultralytics      # YOLO (interactive)
```

### LiveKit Server

**Installation** (system/livekit/):
```bash
cd system/livekit
./install-livekit.sh  # Installs LiveKit v1.9.3
```

**Configuration**: `system/livekit/server.yaml`
- Real-time communication server for voice assistant
- Runs as systemd service: `livekit.service`

### Kiwix (Offline Wikipedia)

**Setup** (system/kiwix/):
```bash
./download-zim.sh              # Downloads Wikipedia ZIM file
./setup-kiwix-service.sh       # Sets up systemd service
```

**Access**: http://localhost:8001

### Audio Configuration

**Configure audio devices** (for voice assistant):
```bash
cd apps/scripts
./configure-device-audio.sh
```

This script:
- Lists available audio devices
- Configures default USB speaker/microphone
- Sets up PulseAudio for Jetson hardware

### System Provisioning

**Full system setup**:
```bash
cd system
./provision.sh
```

This script:
1. Downloads Wikipedia ZIM file
2. Sets up Kiwix systemd service
3. Starts Docker services
4. (Optional) Installs LiveKit server

---

## Testing and Deployment

### Current State

- **No formal test suite** currently implemented
- **No CI/CD pipeline** (no GitHub Actions workflows)
- Development focus on Jetson hardware deployment

### Manual Testing

**Web applications**:
```bash
cd apps/web
pnpm build      # Verify build succeeds
pnpm start      # Test production build
```

**Voice assistant**:
```bash
cd apps/voice-assistant
python main.py  # Test locally with LiveKit
```

**Vision applications**:
```bash
cd apps/vision/roboflow
python monitoring.py --help  # Test CLI
```

### Deployment Targets

**Jetson Orin Nano** (primary target):
- OS: Ubuntu with JetPack 6.0.0
- Architecture: ARM64 (aarch64)
- GPU: NVIDIA with CUDA support
- Services managed via systemd

**Web apps** (optional):
- Can deploy to Vercel, Netlify, or similar
- Standard Next.js deployment process

---

## Jetson-Specific Considerations

### Hardware Capabilities

- **GPU**: NVIDIA Orin with CUDA cores
- **RAM**: 8GB (shared between CPU/GPU)
- **Camera**: Supports MIPI CSI cameras (e.g., IMX219)
- **GPIO**: Hardware control for LEDs, sensors, etc.
- **USB**: Audio devices, peripherals

### JetPack 6.0.0 Compatibility

**Docker images**:
- Base: `l4t-base` (NVIDIA L4T = Linux for Tegra)
- Inference: `roboflow-inference-server-jetson-6.0.0`
- YOLO: `ultralytics:latest-jetson-jetpack6`

**GPU access in Docker**:
```yaml
runtime: nvidia
deploy:
  resources:
    reservations:
      devices:
        - driver: nvidia
          count: all
          capabilities: [gpu]
```

### Camera Access

**GStreamer pipeline** (for CSI cameras):
```python
gst_str = (
    "nvarguscamerasrc sensor-id=0 ! "
    "video/x-raw(memory:NVMM), width=1280, height=720, framerate=30/1 ! "
    "nvvidconv ! video/x-raw, format=BGRx ! "
    "videoconvert ! appsink"
)
cap = cv2.VideoCapture(gst_str, cv2.CAP_GSTREAMER)
```

### Performance Optimization

- **Use GPU-accelerated containers** for vision tasks
- **Optimize model size** for 8GB RAM constraint
- **Use local models** (faster_whisper, piper-tts) to avoid latency
- **Monitor temperature** and throttle compute if needed

---

## Voice Assistant Architecture

### Plugin System

The voice assistant uses a modular plugin architecture:

**Core plugins** (`apps/voice-assistant/plugins/`):
- `stt_plugin.py` - Speech-to-Text (faster_whisper)
- `tts_plugin.py` - Text-to-Speech (piper-tts)
- `llm_plugin.py` - Language Model (OpenAI, Anthropic, etc.)
- `vision_plugin.py` - Camera/Vision (Moondream)
- `kiwix_tool.py` - Offline Wikipedia search

**Main application** (`apps/voice-assistant/main.py`):
- Wake word detection (default: "nano")
- Tool calling framework
- Safe Linux command execution (whitelist-based)
- GPIO LED status indicators
- LiveKit room management

### Key Features

1. **Wake Word Detection**: Uses Silero VAD to detect "nano" (configurable)
2. **Tool Calling**: LLM can call tools (search Wikipedia, execute commands, vision)
3. **Offline First**: Works without internet (local models + offline Wikipedia)
4. **Hardware Integration**: GPIO control for LED status indicators
5. **Safety**: Command execution uses whitelist for safe operations

### Configuration

Environment variables (`.env`):
```bash
LIVEKIT_URL=ws://localhost:7880
LIVEKIT_API_KEY=devkey
LIVEKIT_API_SECRET=secret

# Optional: LLM API keys
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
```

---

## Computer Vision Workflows

### Roboflow Integration

**Video monitoring** (`apps/vision/roboflow/monitoring.py`):
```python
# Extract frames from video
# Send to Roboflow inference API (localhost:9001)
# Collect predictions with timestamps
# Generate monitoring data
```

**Usage**:
```bash
cd apps/vision/roboflow
python monitoring.py --video input.mp4 --interval 1.0
```

### Ultralytics YOLO

**Interactive container**:
```bash
docker run -it --runtime nvidia ultralytics:latest-jetson-jetpack6
```

**Use cases**:
- Custom model training on Jetson
- Real-time object detection
- Export models for deployment

---

## Common Tasks for AI Assistants

### Adding a New Web Page

1. Navigate to the appropriate app:
   ```bash
   cd apps/web  # or apps/docs
   ```

2. Create page in `app/` directory:
   ```tsx
   // app/about/page.tsx
   export default function AboutPage() {
     return <div>About</div>
   }
   ```

3. Optionally use shared UI components:
   ```tsx
   import { Button } from "@repo/ui/button"
   ```

4. Test:
   ```bash
   pnpm dev  # Verify at http://localhost:3000/about
   ```

### Adding a Shared UI Component

1. Create component in `packages/ui/src/`:
   ```tsx
   // packages/ui/src/avatar.tsx
   export const Avatar = ({ src }: { src: string }) => {
     return <img src={src} alt="Avatar" />
   }
   ```

2. Export from `packages/ui/src/index.tsx`:
   ```tsx
   export { Avatar } from "./avatar"
   ```

3. Use in apps:
   ```tsx
   import { Avatar } from "@repo/ui/avatar"
   ```

4. Rebuild (Turborepo auto-handles dependencies):
   ```bash
   pnpm build
   ```

### Adding a Voice Assistant Plugin

1. Create plugin file:
   ```python
   # apps/voice-assistant/plugins/weather_plugin.py
   from livekit.agents import llm

   class WeatherPlugin:
       @llm.ai_callable()
       async def get_weather(self, city: str):
           """Get weather for a city"""
           # Implementation
           return {"temp": 72, "condition": "sunny"}
   ```

2. Register in `main.py`:
   ```python
   from plugins.weather_plugin import WeatherPlugin

   weather = WeatherPlugin()
   assistant.register_tool(weather.get_weather)
   ```

3. Test:
   ```bash
   python main.py
   ```

### Modifying Docker Services

1. Edit `system/docker-compose.yml`:
   ```yaml
   services:
     new-service:
       image: myimage:latest
       ports:
         - "8080:80"
   ```

2. Restart services:
   ```bash
   cd system
   docker-compose up -d new-service
   ```

3. Verify:
   ```bash
   docker-compose ps
   docker-compose logs new-service
   ```

### Updating Dependencies

**JavaScript/TypeScript**:
```bash
# Update specific package
pnpm update next --latest

# Update all dependencies
pnpm update --latest --recursive
```

**Python**:
```bash
cd apps/voice-assistant
pip install --upgrade <package-name>
pip freeze > requirements.txt  # Update lockfile
```

---

## Debugging Tips

### Web Applications

**Build errors**:
```bash
# Clear cache and rebuild
rm -rf apps/web/.next
pnpm build
```

**Type errors**:
```bash
# Run type checker
pnpm check-types

# Check specific app
cd apps/web
pnpm run build  # Next.js does type checking during build
```

**ESLint errors**:
```bash
pnpm lint --fix  # Auto-fix issues
```

### Voice Assistant

**LiveKit connection issues**:
- Verify LiveKit server is running: `systemctl status livekit`
- Check environment variables in `.env`
- Test with: `curl http://localhost:7880`

**Audio device issues**:
```bash
# List audio devices
pactl list sources short
pactl list sinks short

# Reconfigure
cd apps/scripts
./configure-device-audio.sh
```

**Plugin errors**:
- Check Python dependencies: `pip install -r requirements.txt`
- Verify model downloads (faster_whisper, piper-tts)
- Check logs for specific error messages

### Docker Services

**Service not starting**:
```bash
docker-compose ps                    # Check status
docker-compose logs <service-name>   # View logs
docker-compose restart <service-name> # Restart
```

**GPU not accessible**:
```bash
# Verify nvidia runtime
docker run --rm --runtime=nvidia nvidia/cuda:12.0-base nvidia-smi
```

**Port conflicts**:
```bash
# Check what's using a port
sudo lsof -i :9001
```

---

## Best Practices for AI Assistants

### Before Making Changes

1. **Read existing code** to understand patterns and conventions
2. **Check package.json** to see what dependencies are available
3. **Review recent commits** to understand recent changes
4. **Verify working directory** before running commands

### When Writing Code

1. **Follow existing patterns** - Don't introduce new patterns unnecessarily
2. **Use shared packages** - Leverage `@repo/ui`, configs, etc.
3. **Type everything** - TypeScript strict mode is enabled
4. **Test locally** - Run `pnpm dev` or `pnpm build` before committing
5. **Lint before committing** - Run `pnpm lint` to catch issues

### When Working with Monorepo

1. **Install at root** - Always run `pnpm install` from root
2. **Build dependencies first** - Turborepo handles this automatically
3. **Use workspace protocol** - `workspace:*` for internal dependencies
4. **Don't modify shared packages** without considering impact on all apps

### When Working with Python

1. **Use virtual environments** - Don't pollute system Python
2. **Update requirements.txt** - Keep dependencies documented
3. **Follow plugin architecture** - Don't monolithify the voice assistant
4. **Test on actual hardware** - Jetson-specific code may behave differently

### Communication with Users

1. **Explain changes** - Describe what you changed and why
2. **Provide commands** - Give exact commands to run
3. **Warn about breaking changes** - If changes affect other apps
4. **Suggest testing steps** - How to verify changes work

---

## File Reference Quick Guide

### Must-Read Files

- `README.md` - Project overview (currently minimal)
- `package.json` - Root workspace config and scripts
- `turbo.json` - Build system configuration
- `pnpm-workspace.yaml` - Monorepo structure
- `apps/voice-assistant/main.py` - Voice assistant entry point
- `system/docker-compose.yml` - Service orchestration

### Configuration Files by Purpose

**Build & Development**:
- `turbo.json` - Turborepo tasks
- `next.config.ts` - Next.js configuration
- `.vscode/settings.json` - Editor settings

**Dependencies**:
- `package.json` - JS/TS dependencies
- `pnpm-lock.yaml` - Lockfile (do not edit manually)
- `requirements.txt` - Python dependencies (voice-assistant)

**Services & Infrastructure**:
- `system/docker-compose.yml` - All Docker services
- `system/livekit/server.yaml` - LiveKit config
- `system/kiwix/*.sh` - Kiwix setup scripts
- `system/provision.sh` - Full system provisioning

**Linting & Formatting**:
- `packages/eslint-config/*` - Shared ESLint rules
- `packages/typescript-config/*` - Shared TS configs

---

## Environment Variables Reference

### Voice Assistant

Located in `apps/voice-assistant/.env`:

```bash
# LiveKit Connection (Required)
LIVEKIT_URL=ws://localhost:7880
LIVEKIT_API_KEY=devkey
LIVEKIT_API_SECRET=secret

# LLM Providers (At least one required)
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
GOOGLE_API_KEY=...
GROQ_API_KEY=...

# STT/TTS Services (Optional - uses local models by default)
DEEPGRAM_API_KEY=...
ELEVENLABS_API_KEY=...

# Application Settings
WAKE_WORD=nano
DEBUG=false
```

### Web Applications

Currently no environment variables required for basic Next.js apps. If deploying:

```bash
# Standard Next.js vars
NEXT_PUBLIC_API_URL=https://api.example.com
```

---

## Troubleshooting Common Issues

### "pnpm command not found"

```bash
# Install pnpm globally
npm install -g pnpm@latest

# Or use corepack (Node 16+)
corepack enable
corepack prepare pnpm@latest --activate
```

### "Cannot find module '@repo/ui'"

```bash
# Rebuild shared packages
pnpm install
pnpm build
```

### "Docker daemon not running"

```bash
# Start Docker service
sudo systemctl start docker

# Enable on boot
sudo systemctl enable docker
```

### "nvidia-smi not found" in Docker

```bash
# Install NVIDIA Container Runtime
sudo apt-get install nvidia-container-runtime

# Restart Docker
sudo systemctl restart docker
```

### "Port already in use"

```bash
# Find process using port (e.g., 3000)
sudo lsof -i :3000

# Kill process
kill -9 <PID>
```

### TypeScript errors in Next.js

```bash
# Clear Next.js cache
rm -rf apps/web/.next apps/docs/.next

# Rebuild
pnpm build
```

---

## Additional Resources

### Documentation Locations

- **Next.js**: https://nextjs.org/docs
- **LiveKit Agents**: https://docs.livekit.io/agents/
- **Roboflow**: https://docs.roboflow.com/
- **Ultralytics**: https://docs.ultralytics.com/
- **Turborepo**: https://turbo.build/repo/docs
- **pnpm**: https://pnpm.io/

### Jetson Resources

- **JetPack**: https://developer.nvidia.com/embedded/jetpack
- **Jetson Containers**: https://github.com/dusty-nv/jetson-containers
- **L4T Base Images**: https://catalog.ngc.nvidia.com/orgs/nvidia/containers/l4t-base

### Project-Specific Docs

- Voice assistant plugins: See `apps/voice-assistant/plugins/README.md` (if exists)
- Vision workflows: See `apps/vision/README.md` (if exists)
- System setup: See `system/README.md` (if exists)

---

## Changelog

### 2025-11-16
- Initial creation of CLAUDE.md
- Documented current repository structure and workflows
- Added comprehensive guides for common tasks
- Included Jetson-specific considerations
- Documented voice assistant plugin architecture

---

## Questions or Issues?

If you encounter issues or have questions not covered in this guide:

1. Check recent commits for context: `git log --oneline -20`
2. Review related code files for patterns
3. Check Docker/systemd logs for service issues
4. Consult official documentation for specific technologies
5. Ask the user for clarification on project-specific conventions

---

**Last Updated**: 2025-11-16
**Repository**: jetson-orin-nano-field-kit
**Primary Branch**: claude/claude-md-mi262ay6v7u5topg-018XepescH7zLzxDZWDX1FeW
