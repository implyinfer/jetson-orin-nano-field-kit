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

# Set low-latency FFMPEG options for RTSP capture before any VideoCapture is created
os.environ['OPENCV_FFMPEG_CAPTURE_OPTIONS'] = 'rtsp_transport;tcp|fflags;nobuffer|flags;low_delay|framedrop;1'

try:
    from inference_sdk import InferenceHTTPClient
    import supervision as sv
    from flask import Flask, Response, render_template_string, jsonify
except ImportError as e:
    print(f"Error: Missing required package - {e}")
    print("Install with: pip install inference-sdk supervision flask")
    sys.exit(1)

# Optional IMU support
try:
    from icm20948 import ThreadedIMU
    IMU_AVAILABLE = True
    print("IMU module loaded successfully")
except ImportError as e:
    IMU_AVAILABLE = False
    print(f"IMU module not available: {e}")


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
            # Open capture with FFMPEG backend (low-latency options set via environment variable)
            cap = cv2.VideoCapture(self.rtsp_url, cv2.CAP_FFMPEG)
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

    def __init__(self, model_id, rtsp_url, confidence=0.5, port=5000, inference_server=None, enable_imu=True):
        """
        Initialize inference with web streaming

        Args:
            model_id: Model ID (e.g., yolov11n-640, rfdetr-small)
            rtsp_url: RTSP stream URL
            confidence: Detection confidence threshold (0.0-1.0)
            port: Web server port
            inference_server: URL of inference server (e.g., http://localhost:9001)
            enable_imu: Enable IMU sensor data overlay (default: True)
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

        # IMU sensor
        self.imu = None
        self.imu_available = False
        print(f"IMU init: enable_imu={enable_imu}, IMU_AVAILABLE={IMU_AVAILABLE}")
        if enable_imu and IMU_AVAILABLE:
            try:
                print("Creating ThreadedIMU...")
                self.imu = ThreadedIMU()
                print("Starting IMU...")
                if self.imu.start():
                    self.imu_available = True
                    print("IMU sensor initialized successfully")
                else:
                    print("IMU sensor start() returned False")
                    self.imu = None
            except Exception as e:
                import traceback
                print(f"Failed to initialize IMU: {e}")
                traceback.print_exc()
                self.imu = None
        else:
            print(f"IMU skipped: enable_imu={enable_imu}, IMU_AVAILABLE={IMU_AVAILABLE}")

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
                <script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
                <style>
                    * {
                        margin: 0;
                        padding: 0;
                        box-sizing: border-box;
                    }
                    html, body {
                        width: 100%;
                        height: 100%;
                        overflow: hidden;
                        background-color: #000;
                    }
                    .video-container {
                        position: relative;
                        width: 100vw;
                        height: 100vh;
                    }
                    img {
                        width: 100%;
                        height: 100%;
                        object-fit: contain;
                        display: block;
                    }
                    .overlay {
                        position: absolute;
                        top: 10px;
                        right: 10px;
                        background-color: rgba(0, 0, 0, 0.7);
                        color: #fff;
                        padding: 10px 15px;
                        border-radius: 6px;
                        font-family: 'Courier New', monospace;
                        font-size: 14px;
                    }
                    .overlay .model-name {
                        font-weight: bold;
                        color: #00ff00;
                        margin-bottom: 5px;
                    }
                    .imu-container {
                        position: absolute;
                        bottom: 15px;
                        right: 15px;
                        width: 220px;
                        height: 280px;
                        background: linear-gradient(145deg, rgba(20, 25, 35, 0.9), rgba(10, 15, 25, 0.95));
                        border-radius: 12px;
                        border: 1px solid rgba(100, 200, 255, 0.3);
                        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.5), inset 0 1px 0 rgba(255,255,255,0.1);
                        overflow: hidden;
                    }
                    .imu-header {
                        padding: 10px 12px 8px;
                        border-bottom: 1px solid rgba(100, 200, 255, 0.2);
                        background: rgba(0, 150, 255, 0.1);
                    }
                    .imu-title {
                        font-family: 'Segoe UI', Arial, sans-serif;
                        font-size: 11px;
                        font-weight: 600;
                        color: #64c8ff;
                        text-transform: uppercase;
                        letter-spacing: 1.5px;
                    }
                    #imu-canvas {
                        width: 100%;
                        height: 160px;
                        display: block;
                    }
                    .imu-data {
                        padding: 8px 12px;
                        font-family: 'SF Mono', 'Consolas', monospace;
                        font-size: 11px;
                        display: grid;
                        grid-template-columns: repeat(3, 1fr);
                        gap: 4px;
                        background: rgba(0, 0, 0, 0.3);
                    }
                    .imu-axis {
                        text-align: center;
                        padding: 4px;
                        border-radius: 4px;
                        background: rgba(255, 255, 255, 0.03);
                    }
                    .imu-axis-label {
                        font-size: 9px;
                        color: #888;
                        text-transform: uppercase;
                        letter-spacing: 1px;
                    }
                    .imu-axis-value {
                        font-size: 13px;
                        font-weight: bold;
                        margin-top: 2px;
                    }
                    .roll-color { color: #ff6b6b; }
                    .pitch-color { color: #4ecdc4; }
                    .yaw-color { color: #ffe66d; }
                    .imu-unavailable {
                        display: none;
                    }
                    .calibrate-btn {
                        position: absolute;
                        bottom: 8px;
                        left: 50%;
                        transform: translateX(-50%);
                        background: rgba(100, 200, 255, 0.2);
                        border: 1px solid rgba(100, 200, 255, 0.4);
                        color: #64c8ff;
                        padding: 4px 12px;
                        border-radius: 4px;
                        font-size: 9px;
                        font-family: 'Segoe UI', Arial, sans-serif;
                        text-transform: uppercase;
                        letter-spacing: 1px;
                        cursor: pointer;
                        transition: all 0.2s;
                    }
                    .calibrate-btn:hover {
                        background: rgba(100, 200, 255, 0.3);
                        border-color: rgba(100, 200, 255, 0.6);
                    }
                    .calibrate-btn:active {
                        transform: translateX(-50%) scale(0.95);
                    }
                    .imu-status {
                        position: absolute;
                        top: 8px;
                        right: 10px;
                        font-size: 8px;
                        color: #4a4a4a;
                    }
                    .imu-status.calibrated {
                        color: #4ecdc4;
                    }
                </style>
            </head>
            <body>
                <div class="video-container">
                    <img src="{{ url_for('video_feed') }}" alt="Live Stream">
                    <div class="overlay">
                        <div class="model-name">{{ model_id }}</div>
                    </div>
                    <div class="imu-container {% if not imu_available %}imu-unavailable{% endif %}" id="imu-container">
                        <div class="imu-header">
                            <div class="imu-title">9-DOF IMU Orientation</div>
                            <div class="imu-status" id="imu-status">NOT CALIBRATED</div>
                        </div>
                        <canvas id="imu-canvas"></canvas>
                        <div class="imu-data">
                            <div class="imu-axis">
                                <div class="imu-axis-label">Roll</div>
                                <div class="imu-axis-value roll-color" id="imu-roll">0.0°</div>
                            </div>
                            <div class="imu-axis">
                                <div class="imu-axis-label">Pitch</div>
                                <div class="imu-axis-value pitch-color" id="imu-pitch">0.0°</div>
                            </div>
                            <div class="imu-axis">
                                <div class="imu-axis-label">Yaw</div>
                                <div class="imu-axis-value yaw-color" id="imu-yaw">0.0°</div>
                            </div>
                        </div>
                        <button class="calibrate-btn" id="calibrate-btn" onclick="calibrateIMU()">Reset Level</button>
                    </div>
                </div>
                {% if imu_available %}
                <script>
                    // Three.js IMU Visualization
                    let scene, camera, renderer, deviceGroup, gyroRings;
                    let targetRoll = 0, targetPitch = 0, targetYaw = 0;
                    let currentRoll = 0, currentPitch = 0, currentYaw = 0;
                    let isCalibrated = false;

                    function calibrateIMU() {
                        fetch('/api/imu/calibrate', { method: 'POST' })
                            .then(response => response.json())
                            .then(data => {
                                if (data.success) {
                                    isCalibrated = true;
                                    const status = document.getElementById('imu-status');
                                    status.textContent = 'CALIBRATED';
                                    status.classList.add('calibrated');
                                    // Reset current positions for smooth transition
                                    currentRoll = 0;
                                    currentPitch = 0;
                                    currentYaw = 0;
                                }
                            })
                            .catch(err => console.error('Calibration error:', err));
                    }

                    function initThreeJS() {
                        const canvas = document.getElementById('imu-canvas');
                        const width = canvas.clientWidth;
                        const height = canvas.clientHeight;

                        // Scene
                        scene = new THREE.Scene();

                        // Camera - positioned to view device from front-right, slightly above
                        // This shows the cameras facing away (toward -Z) as if device is on table in front of you
                        camera = new THREE.PerspectiveCamera(40, width / height, 0.1, 1000);
                        camera.position.set(2.5, 1.8, 3.5);
                        camera.lookAt(0, 0, 0);

                        // Renderer
                        renderer = new THREE.WebGLRenderer({ canvas: canvas, alpha: true, antialias: true });
                        renderer.setSize(width, height);
                        renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));

                        // Lighting
                        const ambientLight = new THREE.AmbientLight(0x404050, 0.5);
                        scene.add(ambientLight);

                        const directionalLight = new THREE.DirectionalLight(0xffffff, 0.8);
                        directionalLight.position.set(5, 5, 5);
                        scene.add(directionalLight);

                        const backLight = new THREE.DirectionalLight(0x4080ff, 0.3);
                        backLight.position.set(-3, 2, -3);
                        scene.add(backLight);

                        // Device group (will rotate with IMU)
                        deviceGroup = new THREE.Group();
                        scene.add(deviceGroup);

                        // Create Jetson-like device body
                        const bodyGeom = new THREE.BoxGeometry(1.4, 0.25, 1.0);
                        const bodyMat = new THREE.MeshPhongMaterial({
                            color: 0x1a1a1a,
                            specular: 0x333333,
                            shininess: 30
                        });
                        const body = new THREE.Mesh(bodyGeom, bodyMat);
                        deviceGroup.add(body);

                        // Green PCB accent
                        const pcbGeom = new THREE.BoxGeometry(1.35, 0.02, 0.95);
                        const pcbMat = new THREE.MeshPhongMaterial({
                            color: 0x1b5e20,
                            specular: 0x2e7d32,
                            shininess: 50
                        });
                        const pcb = new THREE.Mesh(pcbGeom, pcbMat);
                        pcb.position.y = 0.13;
                        deviceGroup.add(pcb);

                        // Heatsink fins
                        const finMat = new THREE.MeshPhongMaterial({
                            color: 0x37474f,
                            specular: 0x607d8b,
                            shininess: 60
                        });
                        for (let i = -4; i <= 4; i++) {
                            const finGeom = new THREE.BoxGeometry(0.8, 0.15, 0.03);
                            const fin = new THREE.Mesh(finGeom, finMat);
                            fin.position.set(0.1, 0.2, i * 0.1);
                            deviceGroup.add(fin);
                        }

                        // Dual IMX219 Cameras
                        const camMat = new THREE.MeshPhongMaterial({
                            color: 0x263238,
                            specular: 0x455a64,
                            shininess: 40
                        });
                        const lensMat = new THREE.MeshPhongMaterial({
                            color: 0x0d47a1,
                            specular: 0x42a5f5,
                            shininess: 100,
                            transparent: true,
                            opacity: 0.9
                        });

                        // Camera positions (front of device)
                        [-0.35, 0.35].forEach(x => {
                            // Camera housing
                            const camBody = new THREE.Mesh(
                                new THREE.BoxGeometry(0.2, 0.15, 0.12),
                                camMat
                            );
                            camBody.position.set(x, 0.2, -0.56);
                            deviceGroup.add(camBody);

                            // Lens
                            const lens = new THREE.Mesh(
                                new THREE.CylinderGeometry(0.05, 0.06, 0.08, 16),
                                lensMat
                            );
                            lens.rotation.x = Math.PI / 2;
                            lens.position.set(x, 0.2, -0.64);
                            deviceGroup.add(lens);

                            // Lens ring
                            const ringGeom = new THREE.TorusGeometry(0.055, 0.01, 8, 24);
                            const ringMat = new THREE.MeshPhongMaterial({ color: 0x212121 });
                            const ring = new THREE.Mesh(ringGeom, ringMat);
                            ring.rotation.x = Math.PI / 2;
                            ring.position.set(x, 0.2, -0.68);
                            deviceGroup.add(ring);
                        });

                        // NVIDIA logo placeholder (green glow)
                        const logoGeom = new THREE.PlaneGeometry(0.3, 0.1);
                        const logoMat = new THREE.MeshBasicMaterial({
                            color: 0x76b900,
                            transparent: true,
                            opacity: 0.8
                        });
                        const logo = new THREE.Mesh(logoGeom, logoMat);
                        logo.rotation.x = -Math.PI / 2;
                        logo.position.set(-0.4, 0.14, 0.3);
                        deviceGroup.add(logo);

                        // Create gyroscopic rings
                        gyroRings = new THREE.Group();
                        scene.add(gyroRings);

                        // Outer ring (Yaw - Yellow)
                        const ring1Geom = new THREE.TorusGeometry(1.6, 0.015, 16, 64);
                        const ring1Mat = new THREE.MeshBasicMaterial({
                            color: 0xffe66d,
                            transparent: true,
                            opacity: 0.6
                        });
                        const ring1 = new THREE.Mesh(ring1Geom, ring1Mat);
                        gyroRings.add(ring1);

                        // Middle ring (Pitch - Cyan)
                        const ring2Geom = new THREE.TorusGeometry(1.4, 0.015, 16, 64);
                        const ring2Mat = new THREE.MeshBasicMaterial({
                            color: 0x4ecdc4,
                            transparent: true,
                            opacity: 0.6
                        });
                        const ring2 = new THREE.Mesh(ring2Geom, ring2Mat);
                        ring2.rotation.y = Math.PI / 2;
                        gyroRings.add(ring2);

                        // Inner ring (Roll - Red)
                        const ring3Geom = new THREE.TorusGeometry(1.2, 0.015, 16, 64);
                        const ring3Mat = new THREE.MeshBasicMaterial({
                            color: 0xff6b6b,
                            transparent: true,
                            opacity: 0.6
                        });
                        const ring3 = new THREE.Mesh(ring3Geom, ring3Mat);
                        ring3.rotation.x = Math.PI / 2;
                        gyroRings.add(ring3);

                        // Axis lines
                        const axisLen = 1.8;
                        const axisMat = {
                            x: new THREE.LineBasicMaterial({ color: 0xff6b6b, transparent: true, opacity: 0.4 }),
                            y: new THREE.LineBasicMaterial({ color: 0x4ecdc4, transparent: true, opacity: 0.4 }),
                            z: new THREE.LineBasicMaterial({ color: 0xffe66d, transparent: true, opacity: 0.4 })
                        };

                        // X axis (Roll)
                        const xGeom = new THREE.BufferGeometry().setFromPoints([
                            new THREE.Vector3(-axisLen, 0, 0),
                            new THREE.Vector3(axisLen, 0, 0)
                        ]);
                        scene.add(new THREE.Line(xGeom, axisMat.x));

                        // Y axis (Pitch)
                        const yGeom = new THREE.BufferGeometry().setFromPoints([
                            new THREE.Vector3(0, -axisLen, 0),
                            new THREE.Vector3(0, axisLen, 0)
                        ]);
                        scene.add(new THREE.Line(yGeom, axisMat.y));

                        // Z axis (Yaw)
                        const zGeom = new THREE.BufferGeometry().setFromPoints([
                            new THREE.Vector3(0, 0, -axisLen),
                            new THREE.Vector3(0, 0, axisLen)
                        ]);
                        scene.add(new THREE.Line(zGeom, axisMat.z));

                        // Grid helper (subtle)
                        const gridHelper = new THREE.GridHelper(4, 20, 0x2a2a3a, 0x1a1a2a);
                        gridHelper.position.y = -1;
                        scene.add(gridHelper);

                        animate();
                    }

                    function animate() {
                        requestAnimationFrame(animate);

                        // Smooth interpolation
                        const smoothing = 0.15;
                        currentRoll += (targetRoll - currentRoll) * smoothing;
                        currentPitch += (targetPitch - currentPitch) * smoothing;
                        currentYaw += (targetYaw - currentYaw) * smoothing;

                        // Apply rotation to device (convert degrees to radians)
                        deviceGroup.rotation.z = currentRoll * Math.PI / 180;
                        deviceGroup.rotation.x = currentPitch * Math.PI / 180;
                        deviceGroup.rotation.y = currentYaw * Math.PI / 180;

                        // Animate gyro rings subtly
                        const time = Date.now() * 0.001;
                        gyroRings.children[0].rotation.z = time * 0.1;
                        gyroRings.children[1].rotation.z = time * 0.15;
                        gyroRings.children[2].rotation.y = time * 0.12;

                        renderer.render(scene, camera);
                    }

                    function updateIMU() {
                        fetch('/api/imu')
                            .then(response => response.json())
                            .then(data => {
                                if (data.available) {
                                    targetRoll = data.roll;
                                    targetPitch = data.pitch;
                                    targetYaw = data.yaw;

                                    document.getElementById('imu-roll').textContent = data.roll.toFixed(1) + '°';
                                    document.getElementById('imu-pitch').textContent = data.pitch.toFixed(1) + '°';
                                    document.getElementById('imu-yaw').textContent = data.yaw.toFixed(1) + '°';

                                    // Update calibration status display
                                    if (data.calibrated && !isCalibrated) {
                                        isCalibrated = true;
                                        const status = document.getElementById('imu-status');
                                        status.textContent = 'CALIBRATED';
                                        status.classList.add('calibrated');
                                    }
                                }
                            })
                            .catch(err => console.error('IMU fetch error:', err));
                    }

                    // Initialize
                    window.addEventListener('load', () => {
                        initThreeJS();
                        // Auto-calibrate on first load after a short delay to let IMU stabilize
                        setTimeout(() => {
                            calibrateIMU();
                        }, 500);
                        setInterval(updateIMU, 50);
                        updateIMU();
                    });
                </script>
                {% endif %}
            </body>
            </html>
            """
            return render_template_string(
                html,
                model_id=self.model_id,
                imu_available=self.imu_available
            )

        # Store initial IMU offset for calibration
        self._imu_offset = {'roll': 0, 'pitch': 0, 'yaw': 0}
        self._imu_calibrated = False

        @self.app.route('/api/imu')
        def get_imu_data():
            """API endpoint for IMU data"""
            if self.imu_available and self.imu:
                angles = self.imu.get_angles()
                # Apply calibration offset
                return jsonify({
                    'available': True,
                    'roll': angles.roll - self._imu_offset['roll'],
                    'pitch': angles.pitch - self._imu_offset['pitch'],
                    'yaw': angles.yaw - self._imu_offset['yaw'],
                    'calibrated': self._imu_calibrated
                })
            else:
                return jsonify({
                    'available': False,
                    'roll': 0,
                    'pitch': 0,
                    'yaw': 0,
                    'calibrated': False
                })

        @self.app.route('/api/imu/calibrate', methods=['POST'])
        def calibrate_imu():
            """Calibrate IMU - set current position as zero reference"""
            if self.imu_available and self.imu:
                angles = self.imu.get_angles()
                self._imu_offset = {
                    'roll': angles.roll,
                    'pitch': angles.pitch,
                    'yaw': angles.yaw
                }
                self._imu_calibrated = True
                return jsonify({'success': True, 'offset': self._imu_offset})
            return jsonify({'success': False})

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

            ret, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 90])
            if not ret:
                continue

            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
            # Minimal sleep to prevent CPU spinning while maintaining low latency
            time.sleep(0.001)

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
        print(f"IMU Sensor:          {'Available' if self.imu_available else 'Not available'}")
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
            if self.imu:
                self.imu.stop()
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
    parser.add_argument('--no-imu', action='store_true',
                        help='Disable IMU sensor overlay')

    args = parser.parse_args()

    if not 0.0 <= args.confidence <= 1.0:
        print(f"Error: Confidence must be between 0.0 and 1.0 (got {args.confidence})")
        sys.exit(1)

    web_stream = WebStreamInference(
        model_id=args.model,
        rtsp_url=args.rtsp_url,
        confidence=args.confidence,
        port=args.port,
        inference_server=args.inference_server,
        enable_imu=not args.no_imu
    )

    web_stream.run()


if __name__ == '__main__':
    main()
