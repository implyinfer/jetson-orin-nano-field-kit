# Roboflow Vision Project Overview

Complete object detection solution for Jetson Orin Nano using Roboflow inference on RTSP camera streams.

## Project Structure

```
apps/vision/roboflow/
├── README.md                    # Full documentation
├── QUICKSTART.md                # 5-minute quick start guide
├── PROJECT_OVERVIEW.md          # This file
├── requirements.txt             # Python dependencies
├── .env.example                 # Environment configuration template
├── .gitignore                   # Git ignore rules
│
├── inference_rtsp.py            # Main inference script ⭐
├── run_inference.sh             # Quick launcher with options
├── setup.sh                     # Automated setup script
│
└── (Additional utilities)
    ├── imx219_direct.py         # Direct camera access
    ├── imx219_rtsp_client.py    # RTSP client test
    ├── test_opencv_gstreamer.py # OpenCV/GStreamer test
    └── monitoring.py            # System monitoring
```

## What This Does

This project enables **real-time object detection** on video streams from IMX219 cameras connected to a Jetson Orin Nano:

1. **Captures video** from RTSP streams (MediaMTX server)
2. **Runs YOLOv8** object detection using Roboflow models
3. **Displays results** with bounding boxes and FPS stats on screen
4. **Supports 80 object classes** from COCO dataset (person, car, dog, etc.)

## Quick Usage

### First Time Setup

```bash
# 1. Navigate to directory
cd /home/box/Workspace/jetson-orin-nano-field-kit/apps/vision/roboflow

# 2. Run setup
bash setup.sh

# 3. Configure API key
nano .env
# Add your Roboflow API key

# 4. Run inference
python3 inference_rtsp.py
```

### Subsequent Runs

```bash
# Simple run
python3 inference_rtsp.py

# Or use launcher with options
./run_inference.sh --model yolov8n-640 --camera cam0

# Different camera
./run_inference.sh --camera cam1

# Higher confidence threshold
./run_inference.sh --confidence 0.7
```

## Key Files Explained

### `inference_rtsp.py` - Main Script
The core inference script that:
- Connects to RTSP camera stream
- Runs YOLOv8 object detection
- Displays results in real-time
- Monitors FPS performance

**Key configuration (lines 26-29):**
```python
MODEL_ALIAS = "yolov8n-640"              # Model to use
RTSP_URL = "rtsp://localhost:8554/cam0"  # Camera stream
API_KEY = "your_key_here"                # Your API key
CONFIDENCE = 0.5                         # Detection threshold
```

### `run_inference.sh` - Quick Launcher
Convenient wrapper script that:
- Sets environment variables
- Validates RTSP stream
- Accepts command-line arguments
- Shows configuration before running

**Usage examples:**
```bash
./run_inference.sh                              # Default settings
./run_inference.sh --model yolov8m-640          # Different model
./run_inference.sh --camera cam1                # Different camera
./run_inference.sh --confidence 0.7             # Higher threshold
./run_inference.sh --host 192.168.1.171         # Remote RTSP server
```

### `setup.sh` - Automated Setup
One-command setup that:
- Installs system dependencies
- Installs Python packages
- Verifies OpenCV GUI support
- Creates .env configuration file
- Checks RTSP server status
- Sets DISPLAY environment variable

### `.env.example` - Configuration Template
Environment variable template for:
- Roboflow API key
- RTSP stream URLs
- Model selection
- Confidence thresholds
- Display settings

Copy to `.env` and customize for your setup.

### `requirements.txt` - Dependencies
Python package dependencies:
- `inference` - Roboflow inference library
- `opencv-contrib-python` - OpenCV with GUI support
- `supervision` - Computer vision utilities
- Supporting libraries

## Available Models

| Model Alias | Model ID | Resolution | Speed | Accuracy | Recommended For |
|-------------|----------|------------|-------|----------|-----------------|
| yolov8n-640 | coco/3 | 640x640 | Fast (25-30 FPS) | Good | Real-time applications |
| yolov8n-1280 | coco/9 | 1280x1280 | Medium (15-20 FPS) | Better | Balanced use |
| yolov8m-640 | coco/8 | 640x640 | Slow (12-18 FPS) | Best | High accuracy needs |

## COCO Object Classes

The models detect 80 object classes including:
- **People:** person
- **Vehicles:** car, truck, bus, motorcycle, bicycle
- **Animals:** dog, cat, horse, bird, etc.
- **Objects:** bottle, cup, laptop, phone, etc.
- **Sports:** sports ball, tennis racket, etc.

[Full COCO class list](https://tech.amikelive.com/node-718/what-object-categories-labels-are-in-coco-dataset/)

## System Requirements

### Minimum
- Jetson Orin Nano 4GB
- JetPack 5.0+
- 1 IMX219 camera
- Active cooling

### Recommended
- Jetson Orin Nano 8GB
- JetPack 5.1+
- Stereo IMX219 cameras
- Active cooling with heatsink
- Wired Ethernet connection

## Performance Expectations

### Jetson Orin Nano (8GB)
- **yolov8n-640:** 25-30 FPS @ 1080p input
- **yolov8n-1280:** 15-20 FPS @ 1080p input
- **yolov8m-640:** 12-18 FPS @ 1080p input

### Jetson Orin Nano (4GB)
- **yolov8n-640:** 20-25 FPS @ 1080p input
- **yolov8n-1280:** 12-15 FPS @ 1080p input
- **yolov8m-640:** 8-12 FPS @ 1080p input

*Performance with CPU inference on single stream*

## Customization Examples

### Use Your Own Model

1. Train model on Roboflow
2. Get model ID (e.g., `my-project/1`)
3. Update `inference_rtsp.py`:
   ```python
   MODEL_ALIAS = "my-project/1"
   ```

### Change Camera Resolution

Edit RTSP server config (see `../../../RTSP_SETUP.md`):
```bash
# Edit ~/mediamtx/stream_cam0.sh
'video/x-raw(memory:NVMM),width=1280,height=720,framerate=30/1'
```

### Save Detections to File

Add to `on_prediction()` function:
```python
import json
from datetime import datetime

def on_prediction(predictions, video_frame):
    render_boxes(predictions, video_frame, fps_monitor, display_statistics=True)

    # Save detections
    with open('detections.jsonl', 'a') as f:
        f.write(json.dumps({
            'timestamp': datetime.now().isoformat(),
            'detections': predictions.get('predictions', [])
        }) + '\n')
```

### Count Objects by Class

```python
def on_prediction(predictions, video_frame):
    render_boxes(predictions, video_frame, fps_monitor, display_statistics=True)

    # Count objects
    counts = {}
    for pred in predictions.get('predictions', []):
        class_name = pred['class']
        counts[class_name] = counts.get(class_name, 0) + 1

    if counts:
        print(f"Detected: {counts}")
```

## Integration Points

This project can integrate with:

1. **Web APIs** - Send detections to web services
2. **Databases** - Store detection history
3. **Alert Systems** - Trigger notifications on specific objects
4. **Analytics** - Track object counts over time
5. **Automation** - Control devices based on detections
6. **Recording** - Save video when objects detected

## Troubleshooting Quick Reference

| Issue | Solution |
|-------|----------|
| No display | `export DISPLAY=:0` |
| RTSP connection failed | `sudo systemctl start mediamtx.service` |
| Low FPS | Use `yolov8n-640` model |
| Invalid API key | Check `.env` file |
| OpenCV GUI error | Reinstall `opencv-contrib-python` |
| Camera not detected | Check `v4l2-ctl --list-devices` |

See `README.md` for detailed troubleshooting.

## Documentation Files

- **README.md** - Complete documentation with setup, usage, and troubleshooting
- **QUICKSTART.md** - 5-minute quick start guide
- **PROJECT_OVERVIEW.md** - This file, high-level overview
- **../../../RTSP_SETUP.md** - RTSP server setup guide

## External Resources

- [Roboflow Documentation](https://docs.roboflow.com/)
- [Roboflow Inference GitHub](https://github.com/roboflow/inference)
- [YOLOv8 Documentation](https://docs.ultralytics.com/)
- [Jetson Orin Nano Guide](https://developer.nvidia.com/embedded/learn/get-started-jetson-orin-nano-devkit)

## Support

- **Roboflow Issues:** [GitHub](https://github.com/roboflow/inference/issues)
- **RTSP Setup:** See `../../../RTSP_SETUP.md`
- **Jetson Forums:** [NVIDIA Developer](https://forums.developer.nvidia.com/)

## Version Information

- **Roboflow Inference:** 0.60.0
- **OpenCV:** 4.10.0.84
- **Python:** 3.10+
- **Tested on:** JetPack 5.x, Ubuntu 22.04

---

**Last Updated:** 2025-11-16

**Status:** ✅ Production Ready

**Tested Hardware:**
- Jetson Orin Nano 8GB
- IMX219-83 Stereo Camera Module
- Ubuntu 22.04 / JetPack 5.x
