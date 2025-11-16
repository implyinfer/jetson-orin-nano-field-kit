#!/bin/bash
# Example usage scripts for YOLO Ultralytics Vision App on Jetson Orin Nano

echo "YOLO Ultralytics Vision App - Example Usage"
echo "==========================================="
echo ""

# Color output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Example 1: Basic detection with display
example1() {
    echo -e "${BLUE}Example 1: Basic Detection with Display${NC}"
    echo "Runs YOLOv8n with display window. Press 'q' to quit."
    echo ""
    python3 detect.py --show
}

# Example 2: High-performance detection (no display)
example2() {
    echo -e "${BLUE}Example 2: High-Performance Detection (No Display)${NC}"
    echo "Optimized for maximum FPS with nano model"
    echo ""
    python3 detect.py \
        --model yolov8n.pt \
        --width 640 \
        --height 480 \
        --conf 0.3 \
        --device-type cuda:0
}

# Example 3: High-accuracy detection with saving
example3() {
    echo -e "${BLUE}Example 3: High-Accuracy Detection with Saving${NC}"
    echo "Uses larger model and saves detections"
    echo ""
    python3 detect.py \
        --model yolov8m.pt \
        --conf 0.25 \
        --save \
        --output-dir high_accuracy_detections \
        --save-interval 30 \
        --show
}

# Example 4: Person detection with custom settings
example4() {
    echo -e "${BLUE}Example 4: Sensitive Detection (Lower Threshold)${NC}"
    echo "Lower confidence for more detections"
    echo ""
    python3 detect.py \
        --model yolov8s.pt \
        --conf 0.15 \
        --iou 0.5 \
        --show
}

# Example 5: Limited run for testing
example5() {
    echo -e "${BLUE}Example 5: Test Run (100 Frames)${NC}"
    echo "Process only 100 frames for testing"
    echo ""
    python3 detect.py \
        --model yolov8n.pt \
        --max-frames 100 \
        --show \
        --verbose
}

# Example 6: Upside-down camera mount
example6() {
    echo -e "${BLUE}Example 6: Flipped Camera (Upside Down Mount)${NC}"
    echo "For cameras mounted upside down"
    echo ""
    python3 detect.py \
        --flip-method 2 \
        --show
}

# Example 7: Lower resolution for maximum FPS
example7() {
    echo -e "${BLUE}Example 7: Maximum FPS (Lower Resolution)${NC}"
    echo "Optimized for speed with lower resolution"
    echo ""
    python3 detect.py \
        --model yolov8n.pt \
        --width 416 \
        --height 416 \
        --fps 30 \
        --conf 0.4
}

# Example 8: Custom model (you need to provide your own)
example8() {
    echo -e "${BLUE}Example 8: Custom Trained Model${NC}"
    echo "Use your own trained YOLO model"
    echo "Note: Replace 'custom_model.pt' with your model path"
    echo ""
    # python3 detect.py \
    #     --model /path/to/custom_model.pt \
    #     --conf 0.25 \
    #     --show
    echo "Uncomment and modify the command above to use your custom model"
}

# Example 9: Continuous monitoring with periodic saves
example9() {
    echo -e "${BLUE}Example 9: Continuous Monitoring${NC}"
    echo "Run continuously, save detections every 60 frames"
    echo ""
    python3 detect.py \
        --model yolov8s.pt \
        --save \
        --output-dir monitoring \
        --save-interval 60 \
        --conf 0.3
}

# Example 10: Debug mode
example10() {
    echo -e "${BLUE}Example 10: Debug Mode${NC}"
    echo "Verbose logging for troubleshooting"
    echo ""
    python3 detect.py \
        --model yolov8n.pt \
        --verbose \
        --show \
        --max-frames 50
}

# Menu
show_menu() {
    echo ""
    echo -e "${GREEN}Select an example to run:${NC}"
    echo "1) Basic detection with display"
    echo "2) High-performance detection (no display)"
    echo "3) High-accuracy detection with saving"
    echo "4) Sensitive detection (lower threshold)"
    echo "5) Test run (100 frames)"
    echo "6) Flipped camera (upside down)"
    echo "7) Maximum FPS (lower resolution)"
    echo "8) Custom trained model"
    echo "9) Continuous monitoring"
    echo "10) Debug mode"
    echo "q) Quit"
    echo ""
}

# Main loop
while true; do
    show_menu
    read -p "Enter your choice: " choice
    case $choice in
        1) example1 ;;
        2) example2 ;;
        3) example3 ;;
        4) example4 ;;
        5) example5 ;;
        6) example6 ;;
        7) example7 ;;
        8) example8 ;;
        9) example9 ;;
        10) example10 ;;
        q|Q) echo "Exiting..."; exit 0 ;;
        *) echo "Invalid choice. Please try again." ;;
    esac
    echo ""
    read -p "Press Enter to continue..."
done
