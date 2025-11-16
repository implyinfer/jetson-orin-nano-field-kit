#!/bin/bash
# Quick launcher script for Roboflow inference
# Usage: ./run_inference.sh [options]

# Set DISPLAY environment
export DISPLAY=:0

# Default values
MODEL="yolov8n-640"
CAMERA="cam0"
CONFIDENCE="0.5"
RTSP_HOST="localhost"

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -m|--model)
            MODEL="$2"
            shift 2
            ;;
        -c|--camera)
            CAMERA="$2"
            shift 2
            ;;
        -t|--confidence)
            CONFIDENCE="$2"
            shift 2
            ;;
        -h|--host)
            RTSP_HOST="$2"
            shift 2
            ;;
        --help)
            echo "Usage: ./run_inference.sh [options]"
            echo ""
            echo "Options:"
            echo "  -m, --model MODEL       Model to use (default: yolov8n-640)"
            echo "                          Options: yolov8n-640, yolov8n-1280, yolov8m-640"
            echo "  -c, --camera CAMERA     Camera to use (default: cam0)"
            echo "                          Options: cam0, cam1"
            echo "  -t, --confidence CONF   Confidence threshold 0.0-1.0 (default: 0.5)"
            echo "  -h, --host HOST         RTSP server host (default: localhost)"
            echo "  --help                  Show this help message"
            echo ""
            echo "Examples:"
            echo "  ./run_inference.sh"
            echo "  ./run_inference.sh --model yolov8m-640 --camera cam1"
            echo "  ./run_inference.sh --confidence 0.7"
            echo "  ./run_inference.sh --host 192.168.1.171"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Build RTSP URL
RTSP_URL="rtsp://${RTSP_HOST}:8554/${CAMERA}"

# Display configuration
echo "=========================================="
echo "Roboflow Inference Configuration"
echo "=========================================="
echo "Model:       $MODEL"
echo "Camera:      $CAMERA"
echo "RTSP URL:    $RTSP_URL"
echo "Confidence:  $CONFIDENCE"
echo "Display:     $DISPLAY"
echo "=========================================="
echo ""

# Check if RTSP stream is accessible
echo "Checking RTSP stream..."
timeout 3 ffmpeg -i "$RTSP_URL" -frames:v 1 -f null - 2>&1 | grep -q "Stream" && {
    echo "✓ RTSP stream is accessible"
} || {
    echo "⚠ Warning: Could not verify RTSP stream"
    echo "  Make sure MediaMTX is running: sudo systemctl status mediamtx.service"
}

echo ""
echo "Starting inference..."
echo "Press Ctrl+C to stop"
echo ""

# Run inference with environment variables
MODEL_ALIAS="$MODEL" \
RTSP_URL="$RTSP_URL" \
CONFIDENCE="$CONFIDENCE" \
python3 inference_rtsp.py
