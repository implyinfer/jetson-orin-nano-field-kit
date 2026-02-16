# Reachy Mini People Tracker

An intelligent people detection and greeting system that makes Reachy Mini automatically look at and nod to people detected through the Roboflow inference service running on the Jetson Orin Nano Field Kit.

## Overview

This script creates an engaging interactive experience where Reachy Mini:
- 🎥 Continuously monitors camera feed for people
- 👁️ Tracks multiple people with persistent IDs  
- 👀 Automatically looks at each detected person
- 👋 Nods as a friendly greeting
- 🧠 Remembers who has been acknowledged
- 🛡️ Operates with built-in safety limits

## Features

### Core Functionality
- **Real-time People Detection**: Uses Roboflow inference API on port 9001
- **Multi-person Tracking**: Tracks multiple people simultaneously with persistent IDs
- **Intelligent Attention System**: Prioritizes new/unacknowledged people
- **Natural Head Movement**: Smooth head positioning to look at people
- **Greeting Behavior**: Friendly nodding gesture after looking
- **Memory System**: Remembers acknowledged people for configurable duration

### Safety & Reliability  
- **Safety Limits**: Configurable joint limits and torque restrictions
- **Emergency Recovery**: Graceful handling of connection failures
- **Collision Avoidance**: Head movement within safe angular ranges
- **Timeout Protection**: Prevents stuck movements
- **Compliance Mode**: Auto-relaxation when not actively moving

### Performance Optimizations
- **Efficient Detection**: Throttled inference calls to balance performance
- **Smart Tracking**: Distance-based person ID persistence
- **Async Operations**: Non-blocking robot movements
- **Resource Management**: Automatic camera and connection cleanup

## Quick Start

### 1. Setup
```bash
cd apps/reachy-mini
chmod +x setup_people_tracker.sh
./setup_people_tracker.sh
```

### 2. Configuration  
Edit `.env` file with your settings:
```bash
# Essential settings
REACHY_HOST=192.168.1.100        # Your Reachy's IP
ROBOFLOW_HOST=localhost          # Roboflow service
ROBOFLOW_PORT=9001              # Roboflow port
CAMERA_DEVICE=0                 # Camera index
```

### 3. Run
```bash
# Basic usage
python3 run_people_tracker.py

# With debug output
python3 run_people_tracker.py --debug

# Simulation mode (no Reachy connection)
python3 run_people_tracker.py --simulate
```

## Usage Guide

### Interactive Controls

When running with display window:
- **Q** - Quit application
- **R** - Reset person tracking (forget all people)
- **N** - Return Reachy head to neutral position
- **SPACE** - Pause/unpause detection

### Command Line Options

```bash
python3 run_people_tracker.py [options]

Options:
  --help, -h          Show help message
  --config, -c FILE   Use custom config file  
  --debug, -d         Enable debug logging
  --no-display        Run without video window
  --simulate          Simulation mode (no robot)
```

### Environment Variables

Override settings via environment:
```bash
REACHY_HOST=192.168.1.150 python3 run_people_tracker.py
CONFIDENCE_THRESHOLD=0.7 python3 run_people_tracker.py --debug
```

## Configuration Reference

### Detection Settings
```env
CONFIDENCE_THRESHOLD=0.5         # Minimum detection confidence
MIN_PERSON_AREA=5000            # Minimum bounding box area  
DETECTION_INTERVAL=0.2          # Seconds between detections
PERSON_MEMORY_DURATION=10       # Person tracking timeout
MAX_TRACKING_DISTANCE=100.0     # Max pixel distance for ID matching
```

### Robot Behavior
```env
LOOK_DURATION=2.0               # Time to look at person
NOD_AFTER_LOOK=true            # Enable nodding gesture
MAX_HEAD_YAW=45.0              # Maximum side-to-side angle
MAX_HEAD_PITCH=30.0            # Maximum up-down angle
MOVEMENT_SMOOTHNESS=1.5        # Smoothing duration for movements
```

### Camera Setup  
```env
CAMERA_DEVICE=0                 # Camera device index
CAMERA_WIDTH=1280              # Capture resolution width
CAMERA_HEIGHT=720              # Capture resolution height
CAMERA_FPS=15                  # Capture frame rate
```

## System Integration

### Prerequisites
- **Roboflow Inference**: Docker service running on port 9001
- **Camera Access**: USB camera or Reachy's built-in cameras
- **Reachy Connection**: Network access to Reachy Mini robot
- **Python 3.8+**: With required packages installed

### Service Dependencies
```bash
# Check Roboflow service
curl http://localhost:9001/health

# Start if needed
cd system/roboflow
docker compose up -d
```

### Jetson Optimization
The script includes Jetson Orin Nano optimizations:
- Hardware-accelerated video processing
- Thermal monitoring  
- Performance tuning recommendations
- Efficient memory usage

## Troubleshooting

### Common Issues

**No People Detected:**
- Check camera connection and permissions
- Verify Roboflow service is running
- Lower confidence threshold
- Ensure adequate lighting

**Robot Not Moving:**
- Verify Reachy IP address and network connection
- Check safety limits configuration  
- Ensure Reachy is powered and responsive
- Try manual control first

**High CPU Usage:**
- Increase detection interval
- Reduce camera resolution  
- Check thermal throttling
- Close unnecessary applications

**Connection Errors:**
```bash
# Test Roboflow
curl -X POST http://localhost:9001/infer/yolov8n-640 \
  -F "image=@test_image.jpg"

# Test Reachy (if SDK available)
python3 -c "from reachy_sdk import ReachySDK; r = ReachySDK('192.168.1.100')"
```

### Debug Mode
Enable detailed logging for troubleshooting:
```bash
python3 run_people_tracker.py --debug
```

This shows:
- Detection API requests/responses  
- Person tracking state changes
- Robot movement commands
- Performance timing information

## Advanced Usage

### Custom Behaviors
Extend the `ReachyPeopleTracker` class to add custom greeting behaviors:

```python
class CustomPeopleTracker(ReachyPeopleTracker):
    async def custom_greeting(self, person):
        # Add your custom greeting sequence
        await self.wave_at_person(person)
        await self.look_at_person(person)
```

### Integration with Main Dashboard
Run alongside the main control dashboard on different ports:
- Main dashboard: port 8080
- People tracker: runs independently with display/logging

### Systemd Service
Install as system service for automatic startup:
```bash
sudo cp people_tracker.service /etc/systemd/system/
sudo systemctl enable people_tracker.service  
sudo systemctl start people_tracker.service
```

## Performance Notes

### Typical Performance
- **Detection Rate**: 5-15 FPS depending on model
- **Tracking Latency**: <100ms for movement initiation  
- **Memory Usage**: ~200MB typical
- **CPU Usage**: 15-30% on Jetson Orin Nano

### Optimization Tips
- Use YOLOv8n for fastest detection
- Reduce camera resolution for better FPS
- Adjust detection interval based on scenario
- Monitor thermal performance during extended use

## License

Part of the Jetson Orin Nano Field Kit project.