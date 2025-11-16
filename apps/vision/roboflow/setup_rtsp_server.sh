#!/bin/bash
#
# RTSP Server Setup for IMX219 Camera on Jetson
#
# This script sets up an RTSP server that streams from the IMX219 camera.
# You can then connect to it using rtsp://localhost:8554/camera

echo "Setting up RTSP server for IMX219 camera..."

# Check if gst-rtsp-server is installed
if ! dpkg -l | grep -q gstreamer1.0-rtsp; then
    echo "Installing gst-rtsp-server..."
    sudo apt-get update
    sudo apt-get install -y gstreamer1.0-rtsp libgstrtspserver-1.0-dev
fi

# Create RTSP server script
cat > /tmp/rtsp_server.py << 'EOF'
#!/usr/bin/env python3
"""
Simple RTSP Server for IMX219 Camera

This creates an RTSP server at rtsp://localhost:8554/camera
"""

import gi
gi.require_version('Gst', '1.0')
gi.require_version('GstRtspServer', '1.0')
from gi.repository import Gst, GstRtspServer, GLib

Gst.init(None)

class RTSPServer:
    def __init__(self, port=8554):
        self.server = GstRtspServer.RTSPServer()
        self.server.set_service(str(port))

        factory = GstRtspServer.RTSPMediaFactory()

        # GStreamer pipeline for IMX219 camera
        # Adjust sensor-id (0 or 1) and resolution as needed
        pipeline = (
            "( "
            "nvarguscamerasrc sensor-id=0 ! "
            "video/x-raw(memory:NVMM),width=1920,height=1080,framerate=30/1 ! "
            "nvvidconv ! "
            "video/x-raw,format=I420 ! "
            "x264enc tune=zerolatency bitrate=5000 speed-preset=superfast ! "
            "rtph264pay name=pay0 pt=96 "
            ")"
        )

        factory.set_launch(pipeline)
        factory.set_shared(True)

        mounts = self.server.get_mount_points()
        mounts.add_factory("/camera", factory)

        self.server.attach(None)

        print(f"RTSP server started at rtsp://localhost:{port}/camera")
        print("Press Ctrl+C to stop...")

    def run(self):
        loop = GLib.MainLoop()
        try:
            loop.run()
        except KeyboardInterrupt:
            print("\nStopping RTSP server...")

if __name__ == '__main__':
    server = RTSPServer(port=8554)
    server.run()
EOF

chmod +x /tmp/rtsp_server.py

echo ""
echo "RTSP server script created at /tmp/rtsp_server.py"
echo ""
echo "To start the RTSP server, run:"
echo "  python3 /tmp/rtsp_server.py"
echo ""
echo "Then connect to: rtsp://localhost:8554/camera"
echo "Or from another machine: rtsp://YOUR_JETSON_IP:8554/camera"
