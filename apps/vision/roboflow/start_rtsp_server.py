#!/usr/bin/env python3
"""
RTSP Server for IMX219 Camera on Jetson Orin Nano

This script sets up an RTSP server that streams from the IMX219 camera
using MediaMTX or GStreamer RTSP server.

Usage:
    python3 start_rtsp_server.py [--port PORT] [--sensor-id ID] [--resolution WIDTHxHEIGHT]

Examples:
    python3 start_rtsp_server.py
    python3 start_rtsp_server.py --port 8554 --sensor-id 0 --resolution 1920x1080

Stream will be available at: rtsp://localhost:PORT/camera
"""

import argparse
import sys

try:
    import gi
    gi.require_version('Gst', '1.0')
    gi.require_version('GstRtspServer', '1.0')
    from gi.repository import Gst, GstRtspServer, GLib
except ImportError:
    print("Error: GStreamer RTSP server not installed")
    print("Install with: sudo apt-get install -y gstreamer1.0-rtsp libgstrtspserver-1.0-dev python3-gi")
    sys.exit(1)

Gst.init(None)


class RTSPCameraServer:
    """RTSP server for IMX219 camera streaming"""

    def __init__(self, port=8554, sensor_id=0, width=1920, height=1080, framerate=30, bitrate=5000):
        """
        Initialize RTSP server

        Args:
            port: RTSP server port (default: 8554)
            sensor_id: Camera sensor ID - 0 for /dev/video0, 1 for /dev/video1 (default: 0)
            width: Video width in pixels (default: 1920)
            height: Video height in pixels (default: 1080)
            framerate: Video framerate (default: 30)
            bitrate: H.264 encoding bitrate in kbps (default: 5000)
        """
        self.port = port
        self.server = GstRtspServer.RTSPServer()
        self.server.set_service(str(port))

        factory = GstRtspServer.RTSPMediaFactory()

        # GStreamer pipeline for IMX219 camera with hardware encoding
        pipeline = (
            "( "
            f"nvarguscamerasrc sensor-id={sensor_id} ! "
            f"video/x-raw(memory:NVMM),width={width},height={height},framerate={framerate}/1 ! "
            "nvvidconv ! "
            "video/x-raw,format=I420 ! "
            f"x264enc tune=zerolatency bitrate={bitrate} speed-preset=superfast ! "
            "rtph264pay name=pay0 pt=96 "
            ")"
        )

        factory.set_launch(pipeline)
        factory.set_shared(True)

        mounts = self.server.get_mount_points()
        mounts.add_factory("/camera", factory)

        self.server.attach(None)

        print("=" * 60)
        print("RTSP Camera Server Started")
        print("=" * 60)
        print(f"Stream URL:  rtsp://localhost:{port}/camera")
        print(f"Sensor ID:   {sensor_id}")
        print(f"Resolution:  {width}x{height}@{framerate}fps")
        print(f"Bitrate:     {bitrate} kbps")
        print("=" * 60)
        print("\nPress Ctrl+C to stop the server...")

    def run(self):
        """Run the RTSP server main loop"""
        loop = GLib.MainLoop()
        try:
            loop.run()
        except KeyboardInterrupt:
            print("\n\nStopping RTSP server...")


def parse_resolution(res_string):
    """Parse resolution string like '1920x1080' into (width, height)"""
    try:
        width, height = res_string.lower().split('x')
        return int(width), int(height)
    except:
        raise argparse.ArgumentTypeError(f"Invalid resolution format: {res_string}. Use WIDTHxHEIGHT (e.g., 1920x1080)")


def main():
    parser = argparse.ArgumentParser(
        description="RTSP server for IMX219 camera on Jetson Orin Nano",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s
  %(prog)s --port 8554 --sensor-id 0
  %(prog)s --resolution 1280x720 --framerate 60
  %(prog)s --bitrate 8000
        """
    )

    parser.add_argument(
        '--port', '-p',
        type=int,
        default=8554,
        help='RTSP server port (default: 8554)'
    )

    parser.add_argument(
        '--sensor-id', '-s',
        type=int,
        default=0,
        choices=[0, 1],
        help='Camera sensor ID: 0 for /dev/video0, 1 for /dev/video1 (default: 0)'
    )

    parser.add_argument(
        '--resolution', '-r',
        type=parse_resolution,
        default='1920x1080',
        help='Video resolution as WIDTHxHEIGHT (default: 1920x1080)'
    )

    parser.add_argument(
        '--framerate', '-f',
        type=int,
        default=30,
        help='Video framerate (default: 30)'
    )

    parser.add_argument(
        '--bitrate', '-b',
        type=int,
        default=5000,
        help='H.264 encoding bitrate in kbps (default: 5000)'
    )

    args = parser.parse_args()

    width, height = args.resolution

    server = RTSPCameraServer(
        port=args.port,
        sensor_id=args.sensor_id,
        width=width,
        height=height,
        framerate=args.framerate,
        bitrate=args.bitrate
    )

    server.run()


if __name__ == '__main__':
    main()
