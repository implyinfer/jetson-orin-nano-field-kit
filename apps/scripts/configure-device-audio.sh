#!/bin/bash

# Audio configuration script for Jetson Orin Nano
# Configures USB speaker and microphone as default audio devices

set -e

echo "=== Jetson Orin Nano Audio Configuration ==="
echo ""

# Check if running as root (needed for some operations)
if [ "$EUID" -ne 0 ]; then 
  echo "Warning: Not running as root. Some operations may require sudo."
  SUDO="sudo"
else
  SUDO=""
fi

# Function to check if command exists
command_exists() {
  command -v "$1" >/dev/null 2>&1
}

# Check for required tools
if ! command_exists pactl; then
  echo "Error: pactl (PulseAudio) not found. Installing..."
  $SUDO apt-get update
  $SUDO apt-get install -y pulseaudio pulseaudio-utils
fi

# Restart PulseAudio to detect new devices
echo "Restarting PulseAudio..."
$SUDO systemctl --global stop pulseaudio.socket 2>/dev/null || true
$SUDO systemctl --global stop pulseaudio.service 2>/dev/null || true
sleep 2
$SUDO systemctl --global start pulseaudio.socket
$SUDO systemctl --global start pulseaudio.service
sleep 2

# List available audio devices
echo ""
echo "=== Available Audio Devices ==="
echo ""
echo "Audio Outputs (Sinks):"
pactl list short sinks | while read -r line; do
  echo "  $line"
done

echo ""
echo "Audio Inputs (Sources):"
pactl list short sources | while read -r line; do
  echo "  $line"
done

echo ""
echo "=== USB Audio Devices ==="
echo ""

# Find USB audio devices
USB_SINKS=$(pactl list short sinks | grep -i usb || true)
USB_SOURCES=$(pactl list short sources | grep -i usb || true)

if [ -z "$USB_SINKS" ]; then
  echo "Warning: No USB audio output (speaker) devices found."
  echo "Please ensure your USB speaker is connected."
else
  echo "Found USB audio outputs:"
  echo "$USB_SINKS"
fi

if [ -z "$USB_SOURCES" ]; then
  echo "Warning: No USB audio input (microphone) devices found."
  echo "Please ensure your USB microphone is connected."
else
  echo "Found USB audio inputs:"
  echo "$USB_SOURCES"
fi

# Set default USB speaker (sink)
if [ -n "$USB_SINKS" ]; then
  USB_SINK_ID=$(echo "$USB_SINKS" | head -n1 | awk '{print $1}')
  USB_SINK_NAME=$(echo "$USB_SINKS" | head -n1 | awk '{print $2}')
  
  echo ""
  echo "Setting default audio output to USB speaker: $USB_SINK_NAME"
  pactl set-default-sink "$USB_SINK_NAME"
  
  # Verify
  DEFAULT_SINK=$(pactl info | grep "Default Sink:" | awk '{print $3}')
  if [ "$DEFAULT_SINK" = "$USB_SINK_NAME" ]; then
    echo "✓ Default audio output set successfully"
  else
    echo "✗ Failed to set default audio output"
    exit 1
  fi
fi

# Set default USB microphone (source)
if [ -n "$USB_SOURCES" ]; then
  USB_SOURCE_ID=$(echo "$USB_SOURCES" | head -n1 | awk '{print $1}')
  USB_SOURCE_NAME=$(echo "$USB_SOURCES" | head -n1 | awk '{print $2}')
  
  echo ""
  echo "Setting default audio input to USB microphone: $USB_SOURCE_NAME"
  pactl set-default-source "$USB_SOURCE_NAME"
  
  # Verify
  DEFAULT_SOURCE=$(pactl info | grep "Default Source:" | awk '{print $3}')
  if [ "$DEFAULT_SOURCE" = "$USB_SOURCE_NAME" ]; then
    echo "✓ Default audio input set successfully"
  else
    echo "✗ Failed to set default audio input"
    exit 1
  fi
fi

# Set volume levels (optional - adjust as needed)
if [ -n "$USB_SINKS" ]; then
  echo ""
  echo "Setting speaker volume to 70%..."
  USB_SINK_NAME=$(echo "$USB_SINKS" | head -n1 | awk '{print $2}')
  pactl set-sink-volume "$USB_SINK_NAME" 70%
fi

if [ -n "$USB_SOURCES" ]; then
  echo ""
  echo "Setting microphone volume to 80%..."
  USB_SOURCE_NAME=$(echo "$USB_SOURCES" | head -n1 | awk '{print $2}')
  pactl set-source-volume "$USB_SOURCE_NAME" 80%
fi

# Display current configuration
echo ""
echo "=== Current Audio Configuration ==="
echo ""
pactl info | grep -E "Default (Sink|Source):"
echo ""

# Test audio (optional)
echo "=== Audio Test ==="
echo ""
read -p "Would you like to test the audio? (y/n) " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]; then
  if [ -n "$USB_SINKS" ]; then
    echo "Testing speaker (you should hear a beep)..."
    speaker-test -t sine -f 1000 -l 1 -c 2 -s 1 2>/dev/null || \
      paplay /usr/share/sounds/alsa/Front_Left.wav 2>/dev/null || \
      echo "Note: Test audio file not found, but device is configured"
  fi
  
  if [ -n "$USB_SOURCES" ]; then
    echo ""
    echo "Testing microphone (speak into the mic, then press Ctrl+C to stop)..."
    echo "Recording 5 seconds of audio..."
    timeout 5 arecord -d 5 -f cd /tmp/test_mic.wav 2>/dev/null || \
      timeout 5 parecord /tmp/test_mic.wav 2>/dev/null || \
      echo "Note: Could not record test audio, but device is configured"
    
    if [ -f /tmp/test_mic.wav ]; then
      echo "Playing back recorded audio..."
      paplay /tmp/test_mic.wav 2>/dev/null || true
      rm -f /tmp/test_mic.wav
    fi
  fi
fi

echo ""
echo "=== Configuration Complete ==="
echo ""
echo "Current default devices:"
pactl info | grep -E "Default (Sink|Source):"
echo ""
echo "To manually change devices, use:"
echo "  pactl set-default-sink <sink_name>"
echo "  pactl set-default-source <source_name>"
echo ""
echo "To list all devices:"
echo "  pactl list short sinks"
echo "  pactl list short sources"
echo ""

