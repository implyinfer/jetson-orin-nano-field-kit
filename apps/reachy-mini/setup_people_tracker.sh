#!/bin/bash
# Setup script for Reachy Mini People Tracker
# Configures dependencies and services for people detection and greeting

set -e

echo "=========================================="
echo "   Reachy Mini People Tracker Setup      "
echo "=========================================="

# Check if running on Jetson
if [[ $(uname -m) == "aarch64" ]]; then
    echo "✓ Detected ARM64 architecture (Jetson device)"
    IS_JETSON=true
else
    echo "⚠ Not running on Jetson - some optimizations will be skipped"
    IS_JETSON=false
fi

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to check if a service is running
service_running() {
    if command_exists systemctl; then
        systemctl is-active --quiet "$1" 2>/dev/null
    else
        return 1
    fi
}

# Check Python version
echo "Checking Python version..."
if command_exists python3; then
    PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
    echo "✓ Python $PYTHON_VERSION found"
    if [[ $(echo "$PYTHON_VERSION >= 3.8" | bc -l) -eq 0 ]]; then
        echo "❌ Python 3.8+ required"
        exit 1
    fi
else
    echo "❌ Python3 not found"
    exit 1
fi

# Check pip
if ! command_exists pip3; then
    echo "Installing pip3..."
    sudo apt update
    sudo apt install -y python3-pip
fi

# Install system dependencies
echo "Installing system dependencies..."
if command_exists apt; then
    sudo apt update
    sudo apt install -y \
        python3-opencv \
        python3-numpy \
        libgstreamer1.0-0 \
        gstreamer1.0-plugins-base \
        gstreamer1.0-plugins-good \
        gstreamer1.0-plugins-bad \
        gstreamer1.0-plugins-ugly \
        gstreamer1.0-libav \
        v4l-utils \
        bc
fi

# Create project directories
echo "Creating project directories..."
mkdir -p logs
mkdir -p config
mkdir -p static
mkdir -p templates

# Install Python dependencies
echo "Installing Python dependencies..."
pip3 install --upgrade pip

# Install base requirements
if [[ -f "requirements.txt" ]]; then
    echo "Installing main requirements..."
    pip3 install -r requirements.txt
else
    echo "⚠ requirements.txt not found - installing minimal dependencies"
    pip3 install opencv-contrib-python numpy requests pydantic-settings asyncio-mqtt
fi

# Install people tracker specific requirements  
if [[ -f "people_tracker_requirements.txt" ]]; then
    echo "Installing people tracker requirements..."
    pip3 install -r people_tracker_requirements.txt
fi

# Install Reachy SDK if not in simulation mode
read -p "Install Reachy SDK? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Installing Reachy SDK..."
    pip3 install reachy-sdk
    echo "✓ Reachy SDK installed"
else
    echo "⚠ Skipping Reachy SDK - will run in simulation mode"
fi

# Check Roboflow inference service
echo "Checking Roboflow inference service..."
if curl -s http://localhost:9001/health >/dev/null 2>&1; then
    echo "✓ Roboflow inference service is running"
else
    echo "⚠ Roboflow inference service not accessible"
    echo "Make sure to start the Roboflow Docker service:"
    echo "  cd system/roboflow"
    echo "  docker compose up -d"
fi

# Check camera access
echo "Checking camera access..."
if [[ -e /dev/video0 ]]; then
    echo "✓ Camera device found: /dev/video0"
    
    # Test camera access
    if timeout 3 python3 -c "
import cv2
cap = cv2.VideoCapture(0)
ret, frame = cap.read()
cap.release()
if ret:
    print('✓ Camera test successful')
else:
    print('❌ Camera test failed')
" 2>/dev/null; then
        echo "✓ Camera access verified"
    else
        echo "⚠ Camera test failed - check permissions"
        echo "Try: sudo usermod -a -G video $USER"
    fi
else
    echo "⚠ No camera device found at /dev/video0"
    echo "Connect a USB camera or check camera connections"
fi

# Create configuration file
echo "Creating default configuration..."
cat > config/people_tracker.env << EOF
# Reachy Mini People Tracker Configuration
# Copy this file to .env and customize as needed

# Reachy connection
REACHY_HOST=192.168.1.100
REACHY_PORT=50051

# Roboflow inference
ROBOFLOW_HOST=localhost
ROBOFLOW_PORT=9001
ROBOFLOW_MODEL=yolov8n-640
CONFIDENCE_THRESHOLD=0.5

# Camera settings
CAMERA_DEVICE=0
CAMERA_WIDTH=1280
CAMERA_HEIGHT=720
CAMERA_FPS=15

# Person tracking
PERSON_MEMORY_DURATION=10
MIN_PERSON_AREA=5000
MAX_TRACKING_DISTANCE=100.0

# Reachy behavior
LOOK_DURATION=2.0
NOD_AFTER_LOOK=true
MAX_HEAD_YAW=45.0
MAX_HEAD_PITCH=30.0
MOVEMENT_SMOOTHNESS=1.5

# Performance
DETECTION_INTERVAL=0.2
MAX_CONCURRENT_ACTIONS=1
ENABLE_SAFETY_LIMITS=true
EOF

if [[ ! -f ".env" ]]; then
    cp config/people_tracker.env .env
    echo "✓ Created .env configuration file"
else
    echo "✓ Using existing .env configuration"
fi

# Create systemd service (optional)
read -p "Create systemd service for auto-start? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    SCRIPT_DIR=$(pwd)
    cat > people_tracker.service << EOF
[Unit]
Description=Reachy Mini People Tracker
After=network.target
Wants=network-online.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$SCRIPT_DIR
ExecStart=/usr/bin/python3 $SCRIPT_DIR/run_people_tracker.py
Restart=always
RestartSec=10
Environment=DISPLAY=:0

[Install]
WantedBy=multi-user.target
EOF
    
    echo "Service file created. To install:"
    echo "  sudo cp people_tracker.service /etc/systemd/system/"
    echo "  sudo systemctl enable people_tracker.service"
    echo "  sudo systemctl start people_tracker.service"
fi

# Create desktop shortcut (if running with desktop)
if [[ -n "$DISPLAY" ]] && [[ -d "$HOME/Desktop" ]]; then
    read -p "Create desktop shortcut? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        cat > "$HOME/Desktop/People_Tracker.desktop" << EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=Reachy People Tracker
Comment=Detect people and make Reachy greet them
Exec=python3 $(pwd)/run_people_tracker.py
Icon=applications-development
Terminal=true
Categories=Development;Robotics;
EOF
        chmod +x "$HOME/Desktop/People_Tracker.desktop"
        echo "✓ Desktop shortcut created"
    fi
fi

# Jetson-specific optimizations
if [[ "$IS_JETSON" == true ]]; then
    echo "Applying Jetson optimizations..."
    
    # Check if jetson_clocks is available
    if command_exists jetson_clocks; then
        echo "Found jetson_clocks - consider running 'sudo jetson_clocks' for best performance"
    fi
    
    # Check thermal management
    if [[ -f "/sys/class/thermal/thermal_zone0/temp" ]]; then
        TEMP=$(cat /sys/class/thermal/thermal_zone0/temp)
        TEMP_C=$((TEMP / 1000))
        echo "Current temperature: ${TEMP_C}°C"
        if [[ $TEMP_C -gt 70 ]]; then
            echo "⚠ High temperature detected - ensure adequate cooling"
        fi
    fi
fi

# Test installation
echo "Testing installation..."
if python3 -c "
import sys
sys.path.insert(0, '.')
try:
    from people_tracker import Settings, PersonTracker, ReachyPeopleTracker
    print('✓ People tracker modules imported successfully')
except ImportError as e:
    print(f'❌ Import error: {e}')
    sys.exit(1)

try:
    import cv2
    print('✓ OpenCV available')
except ImportError:
    print('❌ OpenCV not available')
    sys.exit(1)

try:
    import requests
    print('✓ Requests library available')
except ImportError:
    print('❌ Requests library not available')
    sys.exit(1)

print('✓ All required modules available')
" 2>/dev/null; then
    echo "✓ Installation test passed"
else
    echo "❌ Installation test failed"
    exit 1
fi

echo ""
echo "=========================================="
echo "           Setup Complete!                "
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Edit .env file with your Reachy's IP address"
echo "2. Start Roboflow inference service if not running"
echo "3. Run the people tracker:"
echo "   python3 run_people_tracker.py"
echo ""
echo "For help:"
echo "   python3 run_people_tracker.py --help-extended"
echo ""
echo "Happy people tracking! 🤖👋"