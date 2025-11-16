# Quick Start Guide

Get up and running with Roboflow inference in 5 minutes!

## Prerequisites

- Jetson Orin Nano with JetPack installed
- Display connected
- RTSP server running (MediaMTX)
- Roboflow account and API key

## Quick Setup

### 1. Run Setup Script

```bash
cd /home/box/Workspace/jetson-orin-nano-field-kit/apps/vision/roboflow
bash setup.sh
```

### 2. Configure API Key

Edit the `.env` file with your Roboflow API key:

```bash
nano .env
```

Update this line:
```
ROBOFLOW_API_KEY=your_actual_api_key_here
```

Save and exit (Ctrl+X, Y, Enter)

### 3. Verify RTSP Stream

Check that your camera stream is working:

```bash
# Check MediaMTX service
sudo systemctl status mediamtx.service

# Test stream (Ctrl+C to exit)
ffplay rtsp://localhost:8554/cam0
```

### 4. Run Inference

```bash
python3 inference_rtsp.py
```

That's it! You should see a window with real-time object detection.

## Common Issues

### Issue: "Could not connect to display"

**Fix:**
```bash
export DISPLAY=:0
python3 inference_rtsp.py
```

### Issue: "RTSP stream connection failed"

**Fix:**
```bash
# Start MediaMTX if not running
sudo systemctl start mediamtx.service

# Verify it's running
sudo systemctl status mediamtx.service
```

### Issue: "Invalid API key"

**Fix:**
- Get your API key from https://app.roboflow.com/settings/api
- Update `.env` file with correct key
- Make sure there are no quotes around the key

### Issue: Low FPS / Slow Performance

**Fix:**
Edit `inference_rtsp.py` and change:
```python
MODEL_ALIAS = "yolov8n-640"  # Use fastest model
```

## Next Steps

- Read [README.md](README.md) for detailed documentation
- Customize model and confidence in `inference_rtsp.py`
- Deploy your own custom models from Roboflow
- Integrate detections into your application

## Key Files

- `inference_rtsp.py` - Main inference script
- `.env` - Configuration file
- `requirements.txt` - Python dependencies
- `README.md` - Full documentation

## Stopping the Inference

- Press `q` in the video window
- Or press `Ctrl+C` in the terminal

## Default Settings

- Model: YOLOv8 Nano (640x640)
- Confidence: 50%
- Camera: cam0 (first camera)
- Classes: COCO dataset (80 classes including person, car, dog, etc.)

Enjoy real-time object detection! 🚀
