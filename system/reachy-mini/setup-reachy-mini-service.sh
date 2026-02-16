#!/usr/bin/env bash
set -euo pipefail

# =============================================================================
# Reachy Mini Control App - Setup Script
# =============================================================================
# This script sets up the Reachy Mini web dashboard service:
# 1. Installs uv package manager (recommended by Reachy Mini SDK)
# 2. Sets up Linux USB permissions for Reachy Mini
# 3. Installs system dependencies (portaudio, etc.)
# 4. Creates Python virtual environment and installs dependencies
# 5. Installs systemd service for auto-start
#
# Official SDK docs: https://huggingface.co/docs/reachy_mini/SDK/installation
# =============================================================================

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
APP_DIR="$REPO_ROOT/apps/reachy-mini"
SYSTEMD_DIR="/etc/systemd/system"
SERVICE_USER="${SUDO_USER:-$USER}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
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

print_section() {
    echo ""
    echo -e "${BLUE}----------------------------------------${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}----------------------------------------${NC}"
}

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    print_error "This script must be run as root (use sudo)"
    exit 1
fi

echo ""
echo "=============================================="
echo "  Reachy Mini Control App - Setup"
echo "=============================================="
echo ""

# -----------------------------------------------------------------------------
# Step 1: Install system dependencies
# -----------------------------------------------------------------------------
print_section "Installing system dependencies"

print_status "Installing required packages..."
apt-get update
apt-get install -y \
    git \
    git-lfs \
    libportaudio2 \
    python3-pip \
    python3-venv \
    curl

# Initialize git lfs
sudo -u "$SERVICE_USER" git lfs install || true

# -----------------------------------------------------------------------------
# Step 2: Set up USB permissions for Reachy Mini
# -----------------------------------------------------------------------------
print_section "Setting up USB permissions for Reachy Mini"

UDEV_RULES="/etc/udev/rules.d/99-reachy-mini.rules"

print_status "Creating udev rules for Reachy Mini USB access..."
cat > "$UDEV_RULES" << 'EOF'
# Reachy Mini USB device rules
# Allows non-root users to access the robot via USB
SUBSYSTEM=="usb", ATTRS{idVendor}=="1a86", ATTRS{idProduct}=="55d3", MODE="0666", GROUP="dialout"
SUBSYSTEM=="usb", ATTRS{idVendor}=="38fb", ATTRS{idProduct}=="1001", MODE="0666", GROUP="dialout"
EOF

print_status "Reloading udev rules..."
udevadm control --reload-rules
udevadm trigger

print_status "Adding user $SERVICE_USER to dialout group..."
usermod -aG dialout "$SERVICE_USER"

# -----------------------------------------------------------------------------
# Step 3: Install uv package manager (recommended by Reachy Mini SDK)
# -----------------------------------------------------------------------------
print_section "Installing uv package manager"

if command -v uv &> /dev/null; then
    print_status "uv is already installed"
else
    print_status "Installing uv..."
    # Install uv for the service user
    sudo -u "$SERVICE_USER" bash -c 'curl -LsSf https://astral.sh/uv/install.sh | sh'
fi

# -----------------------------------------------------------------------------
# Step 4: Set up Python virtual environment
# -----------------------------------------------------------------------------
print_section "Setting up Python virtual environment"

cd "$APP_DIR"

# Create venv if it doesn't exist
if [ ! -d "venv" ]; then
    print_status "Creating virtual environment..."
    sudo -u "$SERVICE_USER" python3 -m venv venv
fi

# Install dependencies
print_status "Installing Python dependencies..."
sudo -u "$SERVICE_USER" bash -c "source $APP_DIR/venv/bin/activate && pip install --upgrade pip && pip install -r $APP_DIR/requirements.txt"

# Create logs directory
print_status "Creating logs directory..."
sudo -u "$SERVICE_USER" mkdir -p "$APP_DIR/logs"

# Create static directory if it doesn't exist
sudo -u "$SERVICE_USER" mkdir -p "$APP_DIR/static"

# -----------------------------------------------------------------------------
# Step 5: Create .env file if it doesn't exist
# -----------------------------------------------------------------------------
print_section "Checking configuration"

if [ ! -f "$APP_DIR/.env" ]; then
    if [ -f "$APP_DIR/.env.example" ]; then
        print_status "Creating .env from .env.example..."
        sudo -u "$SERVICE_USER" cp "$APP_DIR/.env.example" "$APP_DIR/.env"
        print_warning "Please edit $APP_DIR/.env to configure your Reachy Mini IP address"
    fi
else
    print_status ".env file already exists"
fi

# -----------------------------------------------------------------------------
# Step 6: Install systemd service
# -----------------------------------------------------------------------------
print_section "Installing systemd service"

print_status "Installing reachy-mini.service..."
cp "$SCRIPT_DIR/reachy-mini.service" "$SYSTEMD_DIR/reachy-mini.service"
chmod 644 "$SYSTEMD_DIR/reachy-mini.service"

# Update service file with correct paths and user
sed -i "s|/home/box|$REPO_ROOT/..|g" "$SYSTEMD_DIR/reachy-mini.service"
sed -i "s|User=box|User=$SERVICE_USER|g" "$SYSTEMD_DIR/reachy-mini.service"
sed -i "s|Group=box|Group=$SERVICE_USER|g" "$SYSTEMD_DIR/reachy-mini.service"

# -----------------------------------------------------------------------------
# Step 7: Reload systemd and enable service
# -----------------------------------------------------------------------------
print_section "Enabling service"

print_status "Reloading systemd daemon..."
systemctl daemon-reload

print_status "Enabling reachy-mini.service..."
systemctl enable reachy-mini.service

# -----------------------------------------------------------------------------
# Step 8: Start service
# -----------------------------------------------------------------------------
print_section "Starting service"

print_status "Starting reachy-mini.service..."
systemctl start reachy-mini.service || print_warning "Service may need Reachy Mini connected to start properly"

echo ""
echo "=============================================="
echo "  Setup Complete!"
echo "=============================================="
echo ""
echo "Service installed:"
echo "  - reachy-mini.service (Web dashboard on port 8080)"
echo ""
echo "Configuration:"
echo "  - Edit $APP_DIR/.env to set REACHY_HOST"
echo ""
echo "IMPORTANT: Log out and log back in for USB permissions to take effect!"
echo ""
echo "Access the dashboard:"
echo "  - http://localhost:8080"
echo "  - http://<jetson-ip>:8080"
echo ""
echo "Service management commands:"
echo "  sudo systemctl status reachy-mini"
echo "  sudo systemctl restart reachy-mini"
echo "  sudo journalctl -u reachy-mini -f"
echo ""
