# YOLO Ultralytics Vision App

Real-time object detection using YOLO Ultralytics with the IMX-219 CSI camera on Jetson Orin Nano.

## Features

- Real-time object detection using YOLO models (YOLOv8, YOLOv11, etc.)
- Optimized GStreamer pipeline for IMX-219 camera
- GPU acceleration with CUDA support
- Configurable confidence and IoU thresholds
- Optional display window for visual feedback
- Frame saving with detections
- FPS monitoring and detection statistics

## Prerequisites

### Hardware
- NVIDIA Jetson Orin Nano
- IMX-219 CSI Camera (connected to CSI port)

### Software
- JetPack 5.x or later
- Python 3.8+
- PyTorch for Jetson (see installation instructions below)

## Installation

### 1. Install PyTorch for Jetson

PyTorch must be installed using NVIDIA's pre-built wheels for Jetson:

```bash
# For JetPack 5.x, install PyTorch 2.x
# Check the official NVIDIA forums for the latest wheel:
# https://forums.developer.nvidia.com/t/pytorch-for-jetson/72048

# Example for PyTorch 2.1.0 on JetPack 5.1:
wget https://developer.download.nvidia.com/compute/redist/jp/v512/pytorch/torch-2.1.0a0+41361538.nv23.06-cp38-cp38-linux_aarch64.whl
pip3 install torch-2.1.0a0+41361538.nv23.06-cp38-cp38-linux_aarch64.whl
```

### 2. Install OpenCV with GStreamer support

OpenCV should already be installed with JetPack and includes GStreamer support. Verify:

```bash
python3 -c "import cv2; print(cv2.getBuildInformation())" | grep GStreamer
```

If you need to install or rebuild OpenCV with GStreamer support, refer to NVIDIA's documentation.

### 3. Install Ultralytics and dependencies

```bash
cd apps/vision/ultralytics
pip3 install -r requirements.txt
```

### 4. Verify camera access

Test that the IMX-219 camera is accessible:

```bash
gst-launch-1.0 nvarguscamerasrc sensor-id=0 ! \
  'video/x-raw(memory:NVMM),width=1280,height=720,framerate=30/1' ! \
  nvvidconv ! 'video/x-raw,format=BGRx' ! \
  videoconvert ! 'video/x-raw,format=BGR' ! \
  autovideosink
```

Press Ctrl+C to stop. If you see the camera feed, you're ready to go!

## Usage

### Basic Usage

Run detection with default settings (YOLOv8n model, no display):

```bash
python3 detect.py
```

### Display Detection Window

Show real-time detection window (useful for testing):

```bash
python3 detect.py --show
```

Press 'q' to quit.

### Use Different YOLO Models

```bash
# YOLOv8 nano (fastest, less accurate)
python3 detect.py --model yolov8n.pt

# YOLOv8 small
python3 detect.py --model yolov8s.pt

# YOLOv8 medium
python3 detect.py --model yolov8m.pt

# YOLOv8 large (slower, more accurate)
python3 detect.py --model yolov8l.pt

# YOLOv11 (latest)
python3 detect.py --model yolov11n.pt

# Custom trained model
python3 detect.py --model /path/to/your/custom_model.pt
```

The first time you run with a model name, it will be automatically downloaded.

### Save Detections

Save frames with detections to output directory:

```bash
python3 detect.py --save --output-dir detections
```

Save every N frames (default 30):

```bash
python3 detect.py --save --save-interval 60
```

### Adjust Detection Parameters

```bash
# Lower confidence threshold (more detections, more false positives)
python3 detect.py --conf 0.15

# Higher confidence threshold (fewer but more confident detections)
python3 detect.py --conf 0.5

# Adjust IoU threshold for Non-Maximum Suppression
python3 detect.py --iou 0.5
```

### Camera Configuration

```bash
# Use different sensor ID (if you have multiple cameras)
python3 detect.py --sensor-id 1

# Adjust resolution
python3 detect.py --width 640 --height 480

# Adjust FPS
python3 detect.py --fps 15

# Flip camera image (useful if camera is mounted upside down)
python3 detect.py --flip-method 2  # rotate 180 degrees
```

Flip methods:
- 0: No flip (default)
- 1: Counterclockwise 90 degrees
- 2: Rotate 180 degrees
- 3: Clockwise 90 degrees
- 4: Horizontal flip
- 5: Upper right diagonal flip
- 6: Vertical flip
- 7: Upper left diagonal flip

### Process Limited Frames

```bash
# Process only 1000 frames then exit
python3 detect.py --max-frames 1000
```

### Full Example

Comprehensive example with multiple options:

```bash
python3 detect.py \
  --model yolov8s.pt \
  --conf 0.3 \
  --iou 0.45 \
  --show \
  --save \
  --output-dir my_detections \
  --save-interval 30 \
  --width 1280 \
  --height 720 \
  --fps 30 \
  --verbose
```

## Command Line Arguments

### Camera Arguments
- `--device`: Camera device (default: /dev/video0)
- `--use-gstreamer`: Use GStreamer pipeline (default: True)
- `--sensor-id`: Camera sensor ID for GStreamer (default: 0)
- `--width`: Camera width (default: 1280)
- `--height`: Camera height (default: 720)
- `--fps`: Camera FPS (default: 30)
- `--flip-method`: Flip method 0-7 (default: 0)

### Model Arguments
- `--model`: YOLO model path or name (default: yolov8n.pt)
- `--conf`: Confidence threshold (default: 0.25)
- `--iou`: IoU threshold for NMS (default: 0.45)
- `--device-type`: Device for inference, cuda:0 or cpu (default: cuda:0)

### Display Arguments
- `--show`: Show detection window (default: False)
- `--no-labels`: Do not show labels on detections
- `--no-conf`: Do not show confidence scores

### Output Arguments
- `--save`: Save annotated frames
- `--output-dir`: Output directory (default: output)
- `--save-interval`: Save every N frames when detections present (default: 30)

### Other Arguments
- `--max-frames`: Maximum frames to process, 0=unlimited (default: 0)
- `--verbose`: Enable verbose logging

## Performance Tips

### For Best Performance
1. Use smaller models (yolov8n.pt or yolov8s.pt) for real-time performance
2. Lower resolution if needed (e.g., 640x480 instead of 1280x720)
3. Ensure the model runs on GPU (--device-type cuda:0)
4. Use appropriate confidence threshold to reduce false positives

### For Best Accuracy
1. Use larger models (yolov8m.pt or yolov8l.pt)
2. Higher resolution (1280x720 or 1920x1080)
3. Lower confidence threshold to catch more objects
4. Fine-tune IoU threshold based on your use case

## Troubleshooting

### Camera Not Found
If you get "Failed to open camera" error:

1. Check that the camera is properly connected to the CSI port
2. Verify camera is detected:
   ```bash
   ls /dev/video*
   ```
3. Try running the GStreamer test command (see Installation step 4)

### Model Download Issues
If models fail to download automatically:

1. Download manually from [Ultralytics releases](https://github.com/ultralytics/assets/releases)
2. Place in the same directory as detect.py
3. Specify the full path: `--model ./yolov8n.pt`

### Low FPS
If you're getting low FPS:

1. Use a smaller model (yolov8n.pt)
2. Reduce camera resolution
3. Verify GPU is being used (check logs for "cuda:0")
4. Reduce FPS from camera: `--fps 15`

### Out of Memory
If you run out of GPU memory:

1. Use smaller model
2. Reduce camera resolution
3. Close other GPU-intensive applications

## Example Output

```
2025-11-16 10:30:15 - __main__ - INFO - Setting up camera with GStreamer pipeline
2025-11-16 10:30:15 - __main__ - INFO - Camera opened successfully
2025-11-16 10:30:16 - __main__ - INFO - Loading YOLO model: yolov8n.pt
2025-11-16 10:30:18 - __main__ - INFO - Model loaded successfully on cuda:0
2025-11-16 10:30:18 - __main__ - INFO - Starting detection loop (press 'q' to quit)
2025-11-16 10:30:18 - __main__ - INFO - Frame processed in 28.5ms - Detections: 3 - {'person': 2, 'chair': 1}
2025-11-16 10:30:18 - __main__ - INFO - Frame processed in 27.2ms - Detections: 2 - {'person': 2}
2025-11-16 10:30:19 - __main__ - INFO - Frame processed in 26.8ms - Detections: 4 - {'person': 2, 'chair': 1, 'laptop': 1}
```

## License

This project uses [Ultralytics YOLO](https://github.com/ultralytics/ultralytics) which is licensed under AGPL-3.0.

## References

- [Ultralytics Documentation](https://docs.ultralytics.com/)
- [NVIDIA Jetson Developer Forums](https://forums.developer.nvidia.com/)
- [GStreamer Documentation](https://gstreamer.freedesktop.org/documentation/)
