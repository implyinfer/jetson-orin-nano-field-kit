#!/usr/bin/env python3
"""
Roboflow Real-time Inference with Web Browser Streaming

This script runs real-time object detection using Roboflow inference server
and streams the annotated video to a web browser via HTTP/MJPEG.

Usage:
    python3 run_roboflow_web_stream.py [OPTIONS]

Examples:
    # Use default settings
    python3 run_roboflow_web_stream.py

    # Specify custom port and model
    python3 run_roboflow_web_stream.py --port 5001 --model yolov11n-640

    # Use specific model and RTSP URL
    python3 run_roboflow_web_stream.py --model rfdetr-small --rtsp-url rtsp://127.0.0.1:8554/cam0
"""

import argparse
import os
import sys
import threading
import time
import cv2
import numpy as np

try:
    from inference_sdk import InferenceHTTPClient
    import supervision as sv
    from flask import Flask, Response, render_template_string
except ImportError as e:
    print(f"Error: Missing required package - {e}")
    print("Install with: pip install inference-sdk supervision flask")
    sys.exit(1)


# Default configuration
DEFAULT_MODEL = "yolov11n-640"
DEFAULT_RTSP_URL = "rtsp://127.0.0.1:8554/cam0"
DEFAULT_CONFIDENCE = 0.5
DEFAULT_PORT = 5000
DEFAULT_INFERENCE_SERVER = "http://localhost:9001"


class ThreadedCamera:
    """
    Threaded camera capture - reads frames in background thread.
    Decouples frame capture from processing to prevent buffer overflow.
    """

    def __init__(self, rtsp_url):
        self.rtsp_url = rtsp_url
        self.frame = None
        self.frame_time = 0
        self.lock = threading.Lock()
        self.running = False
        self.connected = False
        self.thread = None

    def start(self):
        """Start the capture thread"""
        self.running = True
        self.thread = threading.Thread(target=self._capture_loop, daemon=True)
        self.thread.start()
        return self

    def _capture_loop(self):
        """Background thread that continuously reads frames"""
        while self.running:
            # Open capture with FFMPEG and TCP transport
            cap = cv2.VideoCapture(
                self.rtsp_url + "?rtsp_transport=tcp",
                cv2.CAP_FFMPEG
            )
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

            if not cap.isOpened():
                print(f"Error: Could not open stream: {self.rtsp_url}")
                time.sleep(2)
                continue

            self.connected = True
            print("Camera connected (threaded capture)")

            consecutive_failures = 0
            while self.running and consecutive_failures < 10:
                # Grab to skip buffered frames, then read latest
                cap.grab()
                ret, frame = cap.read()

                if ret and frame is not None:
                    with self.lock:
                        self.frame = frame
                        self.frame_time = time.time()
                    consecutive_failures = 0
                else:
                    consecutive_failures += 1
                    time.sleep(0.01)

            cap.release()
            self.connected = False
            if self.running:
                print("Camera disconnected, reconnecting...")
                time.sleep(1)

    def read(self):
        """Read the latest frame (thread-safe, non-blocking)"""
        with self.lock:
            if self.frame is not None:
                return True, self.frame.copy(), self.frame_time
            return False, None, 0

    def stop(self):
        """Stop the capture thread"""
        self.running = False
        if self.thread is not None:
            self.thread.join(timeout=2)


class WebStreamInference:
    """Roboflow inference with web streaming using InferenceHTTPClient"""

    def __init__(self, model_id, rtsp_url, confidence=0.5, port=5000, inference_server=None):
        """
        Initialize inference with web streaming

        Args:
            model_id: Model ID (e.g., yolov11n-640, rfdetr-small)
            rtsp_url: RTSP stream URL
            confidence: Detection confidence threshold (0.0-1.0)
            port: Web server port
            inference_server: URL of inference server (e.g., http://localhost:9001)
        """
        self.model_id = model_id
        self.rtsp_url = rtsp_url
        self.confidence = confidence
        self.port = port
        self.inference_server = inference_server or DEFAULT_INFERENCE_SERVER

        # Initialize inference client
        self.client = InferenceHTTPClient(api_url=self.inference_server)

        # Thread-safe frame storage
        self.current_frame = None
        self.frame_lock = threading.Lock()

        # Control flag
        self.running = False

        # FPS and latency monitoring
        self.fps = 0.0
        self.fps_alpha = 0.1
        self.latency_ms = 0.0

        # Annotators
        self.box_annotator = sv.BoxAnnotator()
        self.label_annotator = sv.LabelAnnotator()

        # Flask app
        self.app = Flask(__name__)
        self._setup_routes()

    def _setup_routes(self):
        """Setup Flask routes"""

        @self.app.route('/')
        def index():
            """Render the main page"""
            html = """
            <!DOCTYPE html>
            <html>
            <head>
                <title>Roboflow Live Stream</title>
                <style>
                    body {
                        margin: 0;
                        padding: 20px;
                        background-color: #1a1a1a;
                        color: #ffffff;
                        font-family: Arial, sans-serif;
                        display: flex;
                        flex-direction: column;
                        align-items: center;
                    }
                    h1 { margin-bottom: 20px; }
                    .video-container {
                        max-width: 100%;
                        border: 2px solid #333;
                        border-radius: 8px;
                        overflow: hidden;
                        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
                    }
                    img { width: 100%; height: auto; display: block; }
                    .info {
                        margin-top: 20px;
                        padding: 15px;
                        background-color: #2a2a2a;
                        border-radius: 8px;
                        max-width: 800px;
                    }
                    .info p { margin: 5px 0; }
                    .status {
                        display: inline-block;
                        width: 10px;
                        height: 10px;
                        border-radius: 50%;
                        background-color: #00ff00;
                        margin-right: 5px;
                        animation: pulse 2s infinite;
                    }
                    @keyframes pulse {
                        0%, 100% { opacity: 1; }
                        50% { opacity: 0.3; }
                    }
                </style>
            </head>
            <body>
                <h1>Roboflow Live Object Detection</h1>
                <div class="video-container">
                    <img src="{{ url_for('video_feed') }}" alt="Live Stream">
                </div>
                <div class="info">
                    <p><span class="status"></span> <strong>Status:</strong> Streaming</p>
                    <p><strong>Model:</strong> {{ model_id }}</p>
                    <p><strong>Inference Server:</strong> {{ inference_server }}</p>
                    <p><strong>Stream:</strong> {{ rtsp_url }}</p>
                    <p><strong>Confidence:</strong> {{ confidence }}</p>
                </div>
            </body>
            </html>
            """
            return render_template_string(
                html,
                model_id=self.model_id,
                rtsp_url=self.rtsp_url,
                confidence=self.confidence,
                inference_server=self.inference_server
            )

        @self.app.route('/video_feed')
        def video_feed():
            """Stream video frames as MJPEG"""
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
                    frame = np.zeros((480, 640, 3), dtype=np.uint8)
                    cv2.putText(frame, "Waiting for stream...", (160, 240),
                                cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)

            ret, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
            if not ret:
                continue

            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
            time.sleep(0.01)

    def inference_loop(self):
        """Main inference loop - reads frames and runs inference"""
        print("\nStarting inference loop...")
        print(f"Connecting to RTSP stream: {self.rtsp_url}")

        # Use threaded camera capture to decouple from inference
        camera = ThreadedCamera(self.rtsp_url)
        camera.start()

        # Wait for camera to connect
        print("Waiting for camera connection...")
        timeout = 10
        start = time.time()
        while time.time() - start < timeout:
            if camera.connected:
                break
            time.sleep(0.5)
        else:
            print(f"Error: Timeout waiting for RTSP stream: {self.rtsp_url}")
            camera.stop()
            return

        print(f"Using inference server: {self.inference_server}")
        print(f"Model: {self.model_id}")

        last_time = time.time()
        self.running = True

        while self.running:
            # Read latest frame from threaded camera (non-blocking)
            ret, frame, frame_time = camera.read()

            if not ret or frame is None:
                time.sleep(0.01)
                continue

            frame_start = time.time()

            try:
                # Run inference using HTTP client
                result = self.client.infer(frame, model_id=self.model_id)

                # Calculate FPS and latency
                current_time = time.time()
                if current_time - last_time > 0:
                    instant_fps = 1.0 / (current_time - last_time)
                    self.fps = self.fps_alpha * instant_fps + (1 - self.fps_alpha) * self.fps
                last_time = current_time

                # Measure pipeline latency (frame capture + inference)
                self.latency_ms = (current_time - frame_start) * 1000

                # Get detections
                detections = sv.Detections.from_inference(result)

                # Filter by confidence
                if len(detections) > 0:
                    detections = detections[detections.confidence >= self.confidence]

                # Annotate frame
                annotated = self.box_annotator.annotate(scene=frame.copy(), detections=detections)

                if len(detections) > 0:
                    labels = [
                        f"{class_name} {conf:.2f}"
                        for class_name, conf in zip(detections['class_name'], detections.confidence)
                    ]
                    annotated = self.label_annotator.annotate(scene=annotated, detections=detections, labels=labels)

                # Add FPS, latency, and detection count
                cv2.putText(annotated, f"FPS: {self.fps:.1f}", (10, 30),
                            cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                cv2.putText(annotated, f"Latency: {self.latency_ms:.0f}ms", (10, 70),
                            cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                cv2.putText(annotated, f"Detections: {len(detections)}", (10, 110),
                            cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

                # Update current frame
                with self.frame_lock:
                    self.current_frame = annotated

            except Exception as e:
                print(f"Inference error: {e}")
                time.sleep(0.1)

        camera.stop()
        print("Inference loop stopped.")

    def run(self):
        """Start the web server and inference loop"""
        print("=" * 70)
        print("Roboflow Web Stream Inference (GPU Accelerated)")
        print("=" * 70)
        print(f"Model:               {self.model_id}")
        print(f"RTSP Stream:         {self.rtsp_url}")
        print(f"Confidence:          {self.confidence}")
        print(f"Web Server Port:     {self.port}")
        print(f"Inference Server:    {self.inference_server}")
        print("=" * 70)

        # Start inference loop in background thread
        inference_thread = threading.Thread(target=self.inference_loop, daemon=True)
        inference_thread.start()

        # Give inference time to initialize
        time.sleep(2)

        # Start Flask web server
        print("\n" + "=" * 70)
        print("Web server starting...")
        print(f"Open in browser: http://localhost:{self.port}")
        print("Press Ctrl+C to stop")
        print("=" * 70 + "\n")

        try:
            self.app.run(host='0.0.0.0', port=self.port, debug=False, threaded=True)
        except KeyboardInterrupt:
            print("\n\nStopping...")
            self.running = False
            print("Stopped.")


def main():
    parser = argparse.ArgumentParser(
        description="Run Roboflow inference with web browser streaming (GPU accelerated)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s
  %(prog)s --model rfdetr-small
  %(prog)s --model yolov11n-640 --confidence 0.7
  %(prog)s --rtsp-url rtsp://127.0.0.1:8554/cam0 --port 8080

Available Models (cached locally):
  yolov11n-640  - YOLOv11 Nano 640x640 (fast)
  rfdetr-small  - RF-DETR Small (accurate)
        """
    )

    parser.add_argument('--model', '-m', type=str, default=DEFAULT_MODEL,
                        help=f'Model ID (default: {DEFAULT_MODEL})')
    parser.add_argument('--rtsp-url', '-u', type=str, default=DEFAULT_RTSP_URL,
                        help=f'RTSP stream URL (default: {DEFAULT_RTSP_URL})')
    parser.add_argument('--confidence', '-c', type=float, default=DEFAULT_CONFIDENCE,
                        help=f'Confidence threshold 0.0-1.0 (default: {DEFAULT_CONFIDENCE})')
    parser.add_argument('--port', '-p', type=int, default=DEFAULT_PORT,
                        help=f'Web server port (default: {DEFAULT_PORT})')
    parser.add_argument('--inference-server', '-s', type=str, default=DEFAULT_INFERENCE_SERVER,
                        help=f'Inference server URL (default: {DEFAULT_INFERENCE_SERVER})')

    args = parser.parse_args()

    if not 0.0 <= args.confidence <= 1.0:
        print(f"Error: Confidence must be between 0.0 and 1.0 (got {args.confidence})")
        sys.exit(1)

    web_stream = WebStreamInference(
        model_id=args.model,
        rtsp_url=args.rtsp_url,
        confidence=args.confidence,
        port=args.port,
        inference_server=args.inference_server
    )

    web_stream.run()


if __name__ == '__main__':
    main()
