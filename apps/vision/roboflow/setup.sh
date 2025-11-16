#!/bin/bash
# Setup script for Roboflow Inference on Jetson Orin Nano
# Run with: bash setup.sh

set -e  # Exit on error

echo "=========================================="
echo "Roboflow Inference Setup for Jetson Orin"
echo "=========================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if running on Jetson
if [ ! -f /etc/nv_tegra_release ]; then
    echo -e "${YELLOW}Warning: This script is designed for NVIDIA Jetson devices${NC}"
    echo "Continue anyway? (y/n)"
    read -r response
    if [ "$response" != "y" ]; then
        exit 1
    fi
fi

echo "Step 1: Updating system packages..."
sudo apt update

echo ""
echo "Step 2: Installing system dependencies..."
sudo apt install -y \
    libgtk2.0-dev \
    pkg-config \
    python3-dev \
    python3-pip \
    v4l-utils

echo ""
echo "Step 3: Checking Python version..."
PYTHON_VERSION=$(python3 --version | awk '{print $2}')
echo "Python version: $PYTHON_VERSION"

if [[ "$PYTHON_VERSION" < "3.8" ]]; then
    echo -e "${RED}Error: Python 3.8 or higher is required${NC}"
    exit 1
fi

echo ""
echo "Step 4: Installing Python dependencies..."
pip install -r requirements.txt

echo ""
echo "Step 5: Verifying OpenCV installation..."
python3 -c "import cv2; print('OpenCV version:', cv2.__version__)" || {
    echo -e "${RED}Error: OpenCV installation failed${NC}"
    exit 1
}

# Check for GUI support
GUI_SUPPORT=$(python3 -c "import cv2; info = cv2.getBuildInformation(); print('QT5' in info or 'GTK' in info)")
if [ "$GUI_SUPPORT" = "True" ]; then
    echo -e "${GREEN}✓ OpenCV GUI support detected${NC}"
else
    echo -e "${YELLOW}⚠ OpenCV may not have GUI support. Video display might not work.${NC}"
fi

echo ""
echo "Step 6: Setting up environment file..."
if [ ! -f .env ]; then
    cp .env.example .env
    echo -e "${YELLOW}Created .env file. Please edit it with your API key:${NC}"
    echo "  nano .env"
else
    echo -e "${GREEN}.env file already exists${NC}"
fi

echo ""
echo "Step 7: Checking RTSP server..."
if systemctl is-active --quiet mediamtx.service; then
    echo -e "${GREEN}✓ MediaMTX RTSP server is running${NC}"

    # Get IP address
    IP_ADDR=$(hostname -I | awk '{print $1}')
    echo "  RTSP streams available at:"
    echo "    rtsp://$IP_ADDR:8554/cam0"
    echo "    rtsp://$IP_ADDR:8554/cam1"
else
    echo -e "${YELLOW}⚠ MediaMTX RTSP server is not running${NC}"
    echo "  To set up RTSP server, see: ../../../RTSP_SETUP.md"
    echo "  Or start it with: sudo systemctl start mediamtx.service"
fi

echo ""
echo "Step 8: Verifying camera detection..."
echo "Detected cameras:"
v4l2-ctl --list-devices 2>/dev/null || echo -e "${YELLOW}No cameras detected or v4l2-utils not installed${NC}"

echo ""
echo "Step 9: Setting DISPLAY environment variable..."
if [ -z "$DISPLAY" ]; then
    export DISPLAY=:0
    echo "export DISPLAY=:0" >> ~/.bashrc
    echo -e "${GREEN}✓ DISPLAY set to :0 and added to ~/.bashrc${NC}"
else
    echo -e "${GREEN}✓ DISPLAY already set to $DISPLAY${NC}"
fi

echo ""
echo "=========================================="
echo -e "${GREEN}Setup Complete!${NC}"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Edit .env file with your Roboflow API key:"
echo "   nano .env"
echo ""
echo "2. Ensure RTSP server is running:"
echo "   sudo systemctl start mediamtx.service"
echo ""
echo "3. Run the inference pipeline:"
echo "   python3 inference_rtsp.py"
echo ""
echo "For more information, see README.md"
echo ""
