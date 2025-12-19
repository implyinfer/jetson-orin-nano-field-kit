#!/usr/bin/env bash
set -euo pipefail

# =============================================================================
# Roboflow Vision Experience - Boot Setup Script
# =============================================================================
# This script sets up the complete vision experience for the Jetson Orin Nano:
# 1. rf-inference Docker container (Roboflow inference server)
# 2. roboflow-web-stream service (Web-based vision stream on port 5000)
# 3. nginx configuration (proxies port 80 to the web stream)
# =============================================================================

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SYSTEMD_DIR="/etc/systemd/system"
NGINX_SITES="/etc/nginx/sites-available"
NGINX_ENABLED="/etc/nginx/sites-enabled"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${GREEN}[*]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[!]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    print_error "This script must be run as root (use sudo)"
    exit 1
fi

echo ""
echo "=============================================="
echo "  Roboflow Vision Experience - Setup"
echo "=============================================="
echo ""

# -----------------------------------------------------------------------------
# Step 1: Create rf-inference container if it doesn't exist
# -----------------------------------------------------------------------------
print_status "Checking rf-inference Docker container..."

# Create cache directory
mkdir -p /var/cache/roboflow

if docker ps -a --format '{{.Names}}' | grep -q '^rf-inference$'; then
    print_status "rf-inference container already exists"
else
    print_status "Creating rf-inference container..."
    docker run -d \
        --name rf-inference \
        --runtime nvidia \
        --read-only \
        --tmpfs /tmp:rw,noexec,nosuid,size=256m \
        -p 9001:9001 \
        -v /var/cache/roboflow:/cache:rw \
        --security-opt="no-new-privileges" \
        --cap-drop="ALL" \
        --cap-add="NET_BIND_SERVICE" \
        -e MODEL_CACHE_DIR="/cache" \
        -e MPLCONFIGDIR="/tmp/matplotlib" \
        -e "ONNXRUNTIME_EXECUTION_PROVIDERS=[TensorrtExecutionProvider,CUDAExecutionProvider,CPUExecutionProvider]" \
        -e METRICS_ENABLED=false \
        -e ENABLE_BUILDER=True \
        roboflow/roboflow-inference-server-jetson-6.2.0:latest

    # Stop it since systemd will manage it
    docker stop rf-inference
    print_status "rf-inference container created"
fi

# -----------------------------------------------------------------------------
# Step 2: Install rf-inference systemd service
# -----------------------------------------------------------------------------
print_status "Installing rf-inference.service..."

cp "$SCRIPT_DIR/rf-inference.service" "$SYSTEMD_DIR/rf-inference.service"
chmod 644 "$SYSTEMD_DIR/rf-inference.service"

# -----------------------------------------------------------------------------
# Step 3: Install wait-for-inference script
# -----------------------------------------------------------------------------
print_status "Installing wait-for-inference script..."

chmod +x "$SCRIPT_DIR/wait-for-inference.sh"

# -----------------------------------------------------------------------------
# Step 4: Install roboflow-web-stream systemd service
# -----------------------------------------------------------------------------
print_status "Installing roboflow-web-stream.service..."

cp "$SCRIPT_DIR/roboflow-web-stream.service" "$SYSTEMD_DIR/roboflow-web-stream.service"
chmod 644 "$SYSTEMD_DIR/roboflow-web-stream.service"

# -----------------------------------------------------------------------------
# Step 5: Configure nginx
# -----------------------------------------------------------------------------
print_status "Configuring nginx..."

# Install nginx if not present
if ! command -v nginx &> /dev/null; then
    print_status "Installing nginx..."
    apt-get update && apt-get install -y nginx
fi

# Copy nginx configuration
cp "$SCRIPT_DIR/../nginx/default" "$NGINX_SITES/default"

# Enable the site (if not already)
if [ ! -L "$NGINX_ENABLED/default" ]; then
    ln -sf "$NGINX_SITES/default" "$NGINX_ENABLED/default"
fi

# Test nginx config
nginx -t

# -----------------------------------------------------------------------------
# Step 6: Reload systemd and enable services
# -----------------------------------------------------------------------------
print_status "Reloading systemd daemon..."
systemctl daemon-reload

print_status "Enabling services..."
systemctl enable rf-inference.service
systemctl enable roboflow-web-stream.service
systemctl enable nginx.service

# -----------------------------------------------------------------------------
# Step 7: Start services
# -----------------------------------------------------------------------------
print_status "Starting services..."

# Start rf-inference first
systemctl start rf-inference.service
print_status "rf-inference started, waiting for it to be ready..."

# Start web stream (it will wait for inference server)
systemctl start roboflow-web-stream.service &

# Reload nginx
systemctl reload nginx

echo ""
echo "=============================================="
echo "  Setup Complete!"
echo "=============================================="
echo ""
echo "Services installed and started:"
echo "  - rf-inference.service       (Roboflow inference server on port 9001)"
echo "  - roboflow-web-stream.service (Web stream on port 5000)"
echo "  - nginx.service              (Reverse proxy on port 80)"
echo ""
echo "The vision experience will now start automatically on boot!"
echo ""
echo "Access the vision stream:"
echo "  - Connect to 'jetsonfieldkit' WiFi"
echo "  - Open http://10.42.0.1 in your browser"
echo ""
echo "Service management commands:"
echo "  sudo systemctl status rf-inference"
echo "  sudo systemctl status roboflow-web-stream"
echo "  sudo journalctl -u roboflow-web-stream -f"
echo ""
