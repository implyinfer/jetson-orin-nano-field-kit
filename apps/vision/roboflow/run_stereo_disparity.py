#!/usr/bin/env python3
"""
Stereo Disparity Map Visualization

Displays both cameras with a real-time disparity (depth) map.
Closer objects appear brighter/warmer, farther objects appear darker/cooler.

Uses threaded capture for each camera to avoid sync lag.

Usage:
    python3 run_stereo_disparity.py [OPTIONS]

Examples:
    python3 run_stereo_disparity.py
    python3 run_stereo_disparity.py --port 5002
"""

import argparse
import threading
import time
import cv2
import numpy as np
from flask import Flask, Response, render_template_string

# Default configuration
DEFAULT_CAM0_URL = "rtsp://127.0.0.1:8554/cam0"
DEFAULT_CAM1_URL = "rtsp://127.0.0.1:8554/cam1"
DEFAULT_PORT = 5002


class ThreadedCamera:
    """
    Threaded camera capture - reads frames in background thread.
    Based on JetsonHacks CSI-Camera dual_camera.py approach.
    This prevents sequential read lag between cameras.
    """

    def __init__(self, rtsp_url, name="camera"):
        self.rtsp_url = rtsp_url
        self.name = name
        self.frame = None
        self.frame_time = 0
        self.lock = threading.Lock()
        self.running = False
        self.thread = None
        self.cap = None

    def start(self):
        """Start the capture thread"""
        self.running = True
        self.thread = threading.Thread(target=self._capture_loop, daemon=True)
        self.thread.start()
        return self

    def _capture_loop(self):
        """Background thread that continuously reads frames"""
        # Open capture with FFMPEG and TCP transport
        self.cap = cv2.VideoCapture(
            self.rtsp_url + "?rtsp_transport=tcp",
            cv2.CAP_FFMPEG
        )
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

        if not self.cap.isOpened():
            print(f"Error: Could not open {self.name}: {self.rtsp_url}")
            return

        print(f"  {self.name} connected")

        while self.running:
            # Grab multiple times to drain buffer and get latest frame
            self.cap.grab()
            ret, frame = self.cap.read()

            if ret and frame is not None:
                with self.lock:
                    self.frame = frame
                    self.frame_time = time.time()
            else:
                time.sleep(0.01)

        self.cap.release()

    def read(self):
        """Read the latest frame (thread-safe)"""
        with self.lock:
            if self.frame is not None:
                return True, self.frame.copy(), self.frame_time
            return False, None, 0

    def stop(self):
        """Stop the capture thread"""
        self.running = False
        if self.thread is not None:
            self.thread.join(timeout=2)

    def release(self):
        """Release resources"""
        self.stop()


class StereoDisparityStream:
    """Stereo camera disparity map visualization with threaded capture"""

    def __init__(self, cam0_url, cam1_url, port=5002):
        self.cam0_url = cam0_url
        self.cam1_url = cam1_url
        self.port = port

        # Thread-safe frame storage for web streaming
        self.current_frame = None
        self.frame_lock = threading.Lock()
        self.running = False

        # FPS monitoring
        self.fps = 0.0

        # Stereo matcher - StereoBM is faster than SGBM
        self.stereo = cv2.StereoBM_create(
            numDisparities=64,
            blockSize=11
        )
        self.stereo.setTextureThreshold(10)
        self.stereo.setUniquenessRatio(15)

        # Flask app
        self.app = Flask(__name__)
        self._setup_routes()

    def _setup_routes(self):
        """Setup Flask routes"""

        @self.app.route('/')
        def index():
            html = """
            <!DOCTYPE html>
            <html>
            <head>
                <title>Stereo Disparity Map</title>
                <style>
                    body {
                        margin: 0; padding: 20px;
                        background-color: #1a1a1a; color: #ffffff;
                        font-family: Arial, sans-serif;
                        display: flex; flex-direction: column; align-items: center;
                    }
                    h1 { margin-bottom: 10px; }
                    .subtitle { color: #888; margin-bottom: 20px; }
                    .video-container {
                        max-width: 100%; border: 2px solid #333;
                        border-radius: 8px; overflow: hidden;
                    }
                    img { width: 100%; height: auto; display: block; }
                    .legend {
                        margin-top: 20px; padding: 15px;
                        background-color: #2a2a2a; border-radius: 8px;
                        display: flex; align-items: center; gap: 20px;
                    }
                    .gradient {
                        width: 200px; height: 20px;
                        background: linear-gradient(to right, #000080, #0000ff, #00ffff, #00ff00, #ffff00, #ff0000);
                        border-radius: 4px;
                    }
                </style>
            </head>
            <body>
                <h1>Stereo Disparity Map</h1>
                <p class="subtitle">Left Camera | Right Camera | Depth Map (closer = warmer colors)</p>
                <div class="video-container">
                    <img src="{{ url_for('video_feed') }}" alt="Stereo Stream">
                </div>
                <div class="legend">
                    <span>Depth: Far</span>
                    <div class="gradient"></div>
                    <span>Close</span>
                </div>
            </body>
            </html>
            """
            return render_template_string(html)

        @self.app.route('/video_feed')
        def video_feed():
            return Response(
                self._generate_frames(),
                mimetype='multipart/x-mixed-replace; boundary=frame'
            )

    def _generate_frames(self):
        """Generate frames for MJPEG streaming"""
        while True:
            with self.frame_lock:
                if self.current_frame is not None:
                    frame = self.current_frame.copy()
                else:
                    frame = np.zeros((240, 960, 3), dtype=np.uint8)
                    cv2.putText(frame, "Waiting for stereo streams...", (300, 120),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)

            ret, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
            if ret:
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
            time.sleep(0.03)

    def capture_loop(self):
        """Main capture and processing loop with threaded cameras"""
        print(f"\nConnecting to cameras (threaded capture)...")
        print(f"  Left (cam0):  {self.cam0_url}")
        print(f"  Right (cam1): {self.cam1_url}")

        # Create threaded cameras
        cam0 = ThreadedCamera(self.cam0_url, "cam0 (left)")
        cam1 = ThreadedCamera(self.cam1_url, "cam1 (right)")

        # Start both capture threads
        cam0.start()
        cam1.start()

        # Wait for both cameras to connect (with retry)
        print("Waiting for frames...")
        timeout = 10
        start = time.time()
        while time.time() - start < timeout:
            ret0, frame0, _ = cam0.read()
            ret1, frame1, _ = cam1.read()
            if ret0 and ret1:
                print("Both cameras streaming!")
                break
            time.sleep(0.5)
        else:
            print("Error: Timeout waiting for both cameras!")
            cam0.stop()
            cam1.stop()
            return

        last_time = time.time()
        self.running = True

        while self.running:
            # Read latest frames from both threaded cameras
            ret0, frame0, time0 = cam0.read()
            ret1, frame1, time1 = cam1.read()

            if not ret0 or not ret1 or frame0 is None or frame1 is None:
                time.sleep(0.01)
                continue

            # Calculate FPS
            current_time = time.time()
            if current_time - last_time > 0:
                instant_fps = 1.0 / (current_time - last_time)
                self.fps = 0.1 * instant_fps + 0.9 * self.fps
            last_time = current_time

            # Calculate frame time difference (for debugging sync)
            time_diff_ms = abs(time0 - time1) * 1000

            # Resize for faster processing
            new_w, new_h = 320, 240
            left_small = cv2.resize(frame0, (new_w, new_h))
            right_small = cv2.resize(frame1, (new_w, new_h))

            # Convert to grayscale for disparity
            left_gray = cv2.cvtColor(left_small, cv2.COLOR_BGR2GRAY)
            right_gray = cv2.cvtColor(right_small, cv2.COLOR_BGR2GRAY)

            # Compute disparity map
            disparity = self.stereo.compute(left_gray, right_gray).astype(np.float32) / 16.0

            # Filter and enhance
            disparity[disparity < 0] = 0
            disparity[disparity > 64] = 64
            disp_normalized = np.uint8(disparity * 255 / 64)
            disp_normalized = cv2.equalizeHist(disp_normalized)
            # Invert so closer = higher value = warmer colors
            disp_normalized = 255 - disp_normalized
            disp_color = cv2.applyColorMap(disp_normalized, cv2.COLORMAP_TURBO)

            # Stack horizontally: [Left | Right | Disparity]
            combined = np.hstack([left_small, right_small, disp_color])

            # Add labels
            cv2.putText(combined, "LEFT", (10, 25),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            cv2.putText(combined, "RIGHT", (new_w + 10, 25),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            cv2.putText(combined, "DEPTH", (2 * new_w + 10, 25),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            cv2.putText(combined, f"FPS: {self.fps:.1f} | Sync: {time_diff_ms:.0f}ms",
                        (10, new_h - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)

            # Update web frame
            with self.frame_lock:
                self.current_frame = combined

        cam0.stop()
        cam1.stop()
        print("Capture loop stopped.")

    def run(self):
        """Start web server and capture loop"""
        print("=" * 60)
        print("Stereo Disparity Map (Threaded Capture)")
        print("=" * 60)
        print(f"Left Camera:   {self.cam0_url}")
        print(f"Right Camera:  {self.cam1_url}")
        print(f"Web Port:      {self.port}")
        print("=" * 60)

        # Start capture in background
        capture_thread = threading.Thread(target=self.capture_loop, daemon=True)
        capture_thread.start()

        time.sleep(3)

        print(f"\nOpen in browser: http://localhost:{self.port}")
        print("Press Ctrl+C to stop\n")

        try:
            self.app.run(host='0.0.0.0', port=self.port, debug=False, threaded=True)
        except KeyboardInterrupt:
            print("\nStopping...")
            self.running = False


def main():
    parser = argparse.ArgumentParser(description="Stereo Disparity Map (Threaded)")
    parser.add_argument('--cam0', type=str, default=DEFAULT_CAM0_URL,
                        help=f'Left camera RTSP URL (default: {DEFAULT_CAM0_URL})')
    parser.add_argument('--cam1', type=str, default=DEFAULT_CAM1_URL,
                        help=f'Right camera RTSP URL (default: {DEFAULT_CAM1_URL})')
    parser.add_argument('--port', '-p', type=int, default=DEFAULT_PORT,
                        help=f'Web server port (default: {DEFAULT_PORT})')

    args = parser.parse_args()

    streamer = StereoDisparityStream(
        cam0_url=args.cam0,
        cam1_url=args.cam1,
        port=args.port
    )
    streamer.run()


if __name__ == '__main__':
    main()
