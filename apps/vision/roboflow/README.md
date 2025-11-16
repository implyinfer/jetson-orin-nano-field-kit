# Roboflow Inference on Jetson Orin Nano

Complete setup guide for running Roboflow object detection models on RTSP camera streams using the Jetson Orin Nano.

## Table of Contents
- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [Available Scripts](#available-scripts)
- [Troubleshooting](#troubleshooting)
- [Performance Optimization](#performance-optimization)

## Overview

This setup enables real-time object detection on RTSP camera streams using Roboflow's inference library. It supports:
- YOLOv8 models (nano, medium, large)
- RTSP stream ingestion from IMX219 cameras
- Real-time visualization with bounding boxes
- FPS monitoring and statistics
- Custom model deployment

## Prerequisites

### Hardware
- NVIDIA Jetson Orin Nano Developer Kit
- IMX219 camera module(s) connected
- Display connected to Jetson (for GUI visualization)
- Stable power supply (5V 4A)

### Software
- JetPack 5.x or later
- Ubuntu 20.04/22.04
- Python 3.10+
- Active RTSP server (see [RTSP Setup Guide](../../../RTSP_SETUP.md))

### RTSP Server
Ensure your RTSP server is running. If not set up, follow the [RTSP Setup Guide](../../../RTSP_SETUP.md).

Quick check:
```bash
# Verify RTSP stream is available
ffplay rtsp://localhost:8554/cam0

# Or check service status
sudo systemctl status mediamtx.service
```

## Installation

### Step 1: Install System Dependencies

```bash
# Update package lists
sudo apt update

# Install OpenCV dependencies (if not already installed)
sudo apt install -y \
    libgtk2.0-dev \
    pkg-config \
    python3-dev \
    python3-pip
```

### Step 2: Install Python Dependencies

```bash
cd /home/box/Workspace/jetson-orin-nano-field-kit/apps/vision/roboflow

# Install required packages
pip install -r requirements.txt
```

**Note:** This will install:
- `inference` - Roboflow inference library
- `opencv-contrib-python` - OpenCV with GUI support
- `supervision` - Computer vision utilities
- Other required dependencies

### Step 3: Set Up Display Environment

The Jetson needs access to the X display for GUI windows:

```bash
# Add to your shell profile for persistence
echo 'export DISPLAY=:0' >> ~/.bashrc
source ~/.bashrc

# Or set temporarily
export DISPLAY=:0
```

### Step 4: Get Your Roboflow API Key

1. Sign up at [Roboflow](https://roboflow.com)
2. Navigate to Settings → API Keys
3. Copy your API key
4. Create a `.env` file:

```bash
# Create environment file
cat > .env << EOF
ROBOFLOW_API_KEY=your_api_key_here
RTSP_URL=rtsp://localhost:8554/cam0
MODEL_ALIAS=yolov8n-640
CONFIDENCE=0.5
EOF
```

## Configuration

### Model Selection

Edit the configuration in `inference_rtsp.py` or use environment variables:

```python
# Available model aliases
REGISTERED_ALIASES = {
    "yolov8n-640": "coco/3",      # Nano - Fast, lower accuracy
    "yolov8n-1280": "coco/9",     # Nano - Slower, better accuracy
    "yolov8m-640": "coco/8"       # Medium - Balanced
}
```

**Model Selection Guide:**
- `yolov8n-640` - Best for real-time (30+ FPS), good accuracy
- `yolov8n-1280` - Better accuracy, slower (15-20 FPS)
- `yolov8m-640` - Best accuracy, slowest (10-15 FPS)

### Camera Selection

Change the RTSP URL to switch between cameras:

```python
# Camera 0 (Left camera on stereo setup)
RTSP_URL = "rtsp://192.168.1.171:8554/cam0"

# Camera 1 (Right camera on stereo setup)
RTSP_URL = "rtsp://192.168.1.171:8554/cam1"

# Or use localhost if running locally
RTSP_URL = "rtsp://localhost:8554/cam0"
```

### Confidence Threshold

Adjust detection sensitivity:

```python
CONFIDENCE = 0.5  # Default (50% confidence)
CONFIDENCE = 0.3  # More detections, more false positives
CONFIDENCE = 0.7  # Fewer detections, higher confidence
```

## Usage

### Basic Usage

Run the inference pipeline with default settings:

```bash
python3 inference_rtsp.py
```

### Custom Configuration

Edit `inference_rtsp.py` to customize:

```python
# Configuration section (lines 20-24)
MODEL_ALIAS = "yolov8n-640"  # Change model
RTSP_URL = "rtsp://localhost:8554/cam0"  # Change camera
API_KEY = "your_api_key_here"  # Your Roboflow API key
CONFIDENCE = 0.5  # Detection threshold
```

### Command-Line Usage

Create a wrapper script for easy configuration:

```bash
# Run with custom settings
DISPLAY=:0 python3 -c "
import os
os.environ['MODEL_ALIAS'] = 'yolov8m-640'
os.environ['RTSP_URL'] = 'rtsp://localhost:8554/cam1'
os.environ['CONFIDENCE'] = '0.6'
exec(open('inference_rtsp.py').read())
"
```

### Viewing the Output

- A GUI window will open on your connected display
- Bounding boxes show detected objects
- FPS statistics appear in the top-left corner
- Press 'q' or Ctrl+C to stop

## Available Scripts

### `inference_rtsp.py`
Main inference script for real-time object detection on RTSP streams.

**Features:**
- Real-time YOLOv8 inference
- RTSP stream ingestion
- Bounding box visualization
- FPS monitoring
- Multiple model support

**Usage:**
```bash
python3 inference_rtsp.py
```

### `imx219_direct.py`
Direct camera capture without RTSP (lower latency).

**Usage:**
```bash
python3 imx219_direct.py
```

### `imx219_rtsp_client.py`
Simple RTSP client for testing stream connectivity.

**Usage:**
```bash
python3 imx219_rtsp_client.py
```

### `test_opencv_gstreamer.py`
Test OpenCV and GStreamer installation.

**Usage:**
```bash
python3 test_opencv_gstreamer.py
```

### `monitoring.py`
System monitoring and performance metrics.

**Usage:**
```bash
python3 monitoring.py
```

## Troubleshooting

### Display Issues

**Error:** `qt.qpa.xcb: could not connect to display`

**Solution:**
```bash
# Set DISPLAY environment variable
export DISPLAY=:0

# Verify X server is running
ps aux | grep Xorg

# Check who is logged into the display
who
```

### OpenCV GUI Not Working

**Error:** `The function is not implemented. Rebuild the library with Windows, GTK+ 2.x or Cocoa support`

**Solution:**
```bash
# Reinstall OpenCV with GUI support
pip uninstall opencv-python opencv-python-headless
pip install opencv-contrib-python

# Verify GUI support
python3 -c "import cv2; print(cv2.getBuildInformation())" | grep GUI
```

### RTSP Stream Connection Issues

**Error:** `Could not connect to RTSP stream`

**Solution:**
```bash
# Check if MediaMTX is running
sudo systemctl status mediamtx.service

# Test stream directly
ffplay rtsp://localhost:8554/cam0

# Check network connectivity
ping 192.168.1.171

# Verify firewall allows RTSP
sudo ufw allow 8554/tcp
```

### Low FPS / Performance Issues

**Symptoms:** FPS below 10, choppy video

**Solutions:**
1. **Use smaller model:**
   ```python
   MODEL_ALIAS = "yolov8n-640"  # Fastest
   ```

2. **Lower resolution:**
   - Edit RTSP server configuration to use 1280x720 instead of 1920x1080

3. **Increase confidence threshold:**
   ```python
   CONFIDENCE = 0.7  # Fewer detections = faster
   ```

4. **Check CPU/GPU usage:**
   ```bash
   # Monitor resources
   jtop
   ```

5. **Enable GPU acceleration:**
   ```bash
   # Install CUDA-enabled inference (if available)
   pip install inference-gpu
   ```

### Model Loading Errors

**Error:** `ModelDependencyMissing` warnings

**Solution:**
These are warnings for optional models. To suppress:
```python
import os
os.environ['CORE_MODEL_SAM_ENABLED'] = 'False'
os.environ['CORE_MODEL_SAM2_ENABLED'] = 'False'
os.environ['CORE_MODEL_GAZE_ENABLED'] = 'False'
os.environ['CORE_MODEL_GROUNDINGDINO_ENABLED'] = 'False'
```

### ONNX Runtime Provider Warnings

**Warning:** `CUDAExecutionProvider is not in available provider names`

**Explanation:** Your installation is using CPU inference. This is normal for standard installations.

**To enable GPU acceleration:**
```bash
# Install ONNX Runtime with GPU support (advanced)
pip install onnxruntime-gpu
```

## Performance Optimization

### 1. Model Selection
- **Real-time (>20 FPS):** Use `yolov8n-640`
- **Balanced (15-20 FPS):** Use `yolov8n-1280` or `yolov8m-640`
- **Accuracy (10-15 FPS):** Use larger models

### 2. Resolution Optimization
Edit your RTSP stream configuration (see [RTSP Setup Guide](../../../RTSP_SETUP.md)):
```bash
# Lower resolution = faster processing
# Edit ~/mediamtx/stream_cam0.sh
'video/x-raw(memory:NVMM),width=1280,height=720,framerate=30/1'
```

### 3. Bitrate Adjustment
Lower bitrate reduces network overhead:
```bash
# Edit stream script
x264enc tune=zerolatency bitrate=2000 speed-preset=superfast
```

### 4. Confidence Threshold
Higher threshold = fewer detections = faster:
```python
CONFIDENCE = 0.7  # vs default 0.5
```

### 5. Frame Skipping
Process every Nth frame for higher FPS:
```python
# Add to on_prediction function
frame_counter = 0
def on_prediction(predictions, video_frame):
    global frame_counter
    frame_counter += 1
    if frame_counter % 2 == 0:  # Process every 2nd frame
        render_boxes(...)
```

### 6. Enable Hardware Acceleration
Use Jetson's hardware encoder/decoder:
- Ensure NVMM buffers are used in GStreamer pipeline
- Use `nvv4l2decoder` instead of software decoders

### 7. Thermal Management
Prevent throttling:
```bash
# Monitor temperature
jtop

# Set fan to max (if available)
sudo jetson_clocks

# Ensure good cooling/heatsink
```

## Performance Benchmarks

Typical FPS on Jetson Orin Nano (1920x1080 @ 30fps input):

| Model | Resolution | Avg FPS | CPU Usage | Notes |
|-------|-----------|---------|-----------|-------|
| yolov8n-640 | 640x640 | 25-30 | ~60% | Best for real-time |
| yolov8n-1280 | 1280x1280 | 15-20 | ~80% | Better accuracy |
| yolov8m-640 | 640x640 | 12-18 | ~90% | High accuracy |

*Benchmarks with CPU inference, single stream*

## Using Custom Models

### Deploy Your Own Model

1. **Train model on Roboflow:**
   - Upload dataset to Roboflow
   - Train YOLOv8 model
   - Note your model ID (e.g., `my-project/1`)

2. **Update configuration:**
   ```python
   # In inference_rtsp.py
   MODEL_ALIAS = "my-project/1"  # Use your model ID directly
   ```

3. **Run inference:**
   ```bash
   python3 inference_rtsp.py
   ```

### Model Version Management

```python
# Use specific version
model_id = "my-project/2"  # Version 2

# Use latest version
model_id = "my-project"  # Automatically uses latest
```

## Integration Examples

### Save Detections to File

```python
import json
from datetime import datetime

def on_prediction(predictions, video_frame):
    # Render as usual
    render_boxes(predictions, video_frame, fps_monitor, display_statistics=True)

    # Save detections
    if predictions.get('predictions'):
        timestamp = datetime.now().isoformat()
        with open('detections.jsonl', 'a') as f:
            f.write(json.dumps({
                'timestamp': timestamp,
                'detections': predictions['predictions']
            }) + '\n')
```

### Count Objects

```python
object_counts = {}

def on_prediction(predictions, video_frame):
    render_boxes(predictions, video_frame, fps_monitor, display_statistics=True)

    # Count by class
    counts = {}
    for pred in predictions.get('predictions', []):
        class_name = pred.get('class', 'unknown')
        counts[class_name] = counts.get(class_name, 0) + 1

    print(f"Current counts: {counts}")
```

### Alert on Specific Objects

```python
def on_prediction(predictions, video_frame):
    render_boxes(predictions, video_frame, fps_monitor, display_statistics=True)

    # Alert on person detection
    for pred in predictions.get('predictions', []):
        if pred.get('class') == 'person' and pred.get('confidence', 0) > 0.8:
            print(f"⚠️  High-confidence person detected! Confidence: {pred['confidence']:.2f}")
            # Add your alert logic here (email, webhook, etc.)
```

## Additional Resources

- [Roboflow Documentation](https://docs.roboflow.com/)
- [Roboflow Inference GitHub](https://github.com/roboflow/inference)
- [Supervision Library](https://github.com/roboflow/supervision)
- [YOLOv8 Documentation](https://docs.ultralytics.com/)
- [RTSP Setup Guide](../../../RTSP_SETUP.md)
- [Jetson Orin Nano Documentation](https://developer.nvidia.com/embedded/learn/get-started-jetson-orin-nano-devkit)

## Support

For issues specific to:
- **Roboflow Inference:** [GitHub Issues](https://github.com/roboflow/inference/issues)
- **RTSP Setup:** See [RTSP_SETUP.md](../../../RTSP_SETUP.md)
- **Jetson Hardware:** [NVIDIA Developer Forums](https://forums.developer.nvidia.com/c/agx-autonomous-machines/jetson-embedded-systems/)

## License

See project root for license information.
