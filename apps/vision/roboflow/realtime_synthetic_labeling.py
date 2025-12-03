#!/usr/bin/env python3
"""
Real-time Synthetic Labeling Tool
Generates synthetic training data using Fal.ai image editing models from a live camera stream.

Usage:
    python3 realtime_synethic_labeling.py [OPTIONS]

Env:
    FAL_KEY: Your Fal.ai API key
"""

import argparse
import base64
import cv2
import datetime
import io
import json
import os
import sys
import threading
import time
import numpy as np
from PIL import Image

try:
    from dotenv import load_dotenv
    # Load .env from the script's directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    env_path = os.path.join(script_dir, '.env')
    load_dotenv(env_path)
except ImportError:
    print("Warning: python-dotenv not installed. Install with: pip install python-dotenv")
    print("Continuing without .env file support...")

try:
    from flask import Flask, Response, render_template_string, request, jsonify
except ImportError:
    print("Error: Missing required package 'flask'. Install with: pip install flask")
    sys.exit(1)

try:
    import fal_client
except ImportError:
    print("Error: Missing required package 'fal-client'. Install with: pip install fal-client")
    sys.exit(1)

# Get FAL_KEY from environment - fal_client reads from FAL_KEY env var automatically
FAL_KEY = os.getenv('FAL_KEY')
if not FAL_KEY:
    print("Warning: FAL_KEY not found in environment variables.")
    print("Set it in .env file or export FAL_KEY environment variable.")
    print("The script will continue but Fal.ai API calls may fail.")
else:
    print("Fal.ai API key loaded successfully.")

# Default configuration
DEFAULT_RTSP_URL = "rtsp://127.0.0.1:8554/cam0"
DEFAULT_PORT = 5003
DEFAULT_MODEL = "fal-ai/nano-banana-pro/edit"
DEFAULT_PROMPT = "make all the people in this image wear an orange construction hardhat. Keep the original image, only add the hardhats"
SAVE_DIR = "data/synthetic_labeled"


class ThreadedCamera:
    """
    Threaded camera capture - reads frames in background thread.
    Copied from run_roboflow_web_stream.py to ensure consistency.
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


class SyntheticLabelingApp:
    def __init__(self, rtsp_url, port, model_id, prompt):
        self.rtsp_url = rtsp_url
        self.port = port
        self.model_id = model_id
        self.current_prompt = prompt
        
        # State
        self.camera = None
        self.current_frame = None # The live frame
        self.captured_frame = None # The frame used for generation
        self.generated_image_data = None # Base64 or URL of generated image
        self.last_generation_time = 0
        self.is_generating = False
        self.generation_interval = 10 # seconds
        self.auto_generate = False  # Disabled - use manual generation only
        self.trigger_generation = False  # Flag for manual trigger
        
        self.lock = threading.Lock()
        
        # Ensure save directory exists
        os.makedirs(SAVE_DIR, exist_ok=True)
        
        # Flask app
        self.app = Flask(__name__)
        self._setup_routes()

    def _setup_routes(self):
        @self.app.route('/')
        def index():
            return render_template_string(self._get_html_template(), 
                                        prompt=self.current_prompt,
                                        interval=self.generation_interval)

        @self.app.route('/video_feed')
        def video_feed():
            return Response(self._generate_frames(),
                          mimetype='multipart/x-mixed-replace; boundary=frame')

        @self.app.route('/generated_feed')
        def generated_feed():
            """Returns the latest generated image as JSON"""
            with self.lock:
                return jsonify({
                    'image': self.generated_image_data,
                    'is_generating': self.is_generating,
                    'timestamp': self.last_generation_time
                })

        @self.app.route('/api/prompt', methods=['POST'])
        def update_prompt():
            data = request.json
            new_prompt = data.get('prompt')
            if new_prompt:
                with self.lock:
                    self.current_prompt = new_prompt
                    # Trigger immediate regeneration if possible
                    self.last_generation_time = 0 
                return jsonify({'status': 'ok', 'prompt': self.current_prompt})
            return jsonify({'status': 'error', 'message': 'No prompt provided'}), 400

        @self.app.route('/api/save', methods=['POST'])
        def save_image():
            with self.lock:
                if self.generated_image_data and self.captured_frame is not None:
                    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                    
                    # Save Generated Image
                    # If it's a URL (from fal), we might need to fetch it, but fal-client result usually gives URL
                    # For simplicity in this script, we'll assume the frontend sends the base64 or we handle the URL.
                    # Actually, let's handle saving locally since we have the data.
                    
                    try:
                        # Decode generated image if it's base64 data URI
                        if self.generated_image_data.startswith('data:image'):
                            header, encoded = self.generated_image_data.split(",", 1)
                            data = base64.b64decode(encoded)
                            ext = "jpg" if "jpeg" in header else "png"
                        else:
                            # Handle URL or other format if needed, for now assume base64 from our conversion
                            return jsonify({'status': 'error', 'message': 'Invalid image data format'}), 400

                        # Save generated
                        gen_filename = f"{SAVE_DIR}/gen_{timestamp}.{ext}"
                        with open(gen_filename, "wb") as f:
                            f.write(data)
                            
                        # Save original frame
                        orig_filename = f"{SAVE_DIR}/orig_{timestamp}.jpg"
                        cv2.imwrite(orig_filename, self.captured_frame)
                        
                        # Save metadata
                        meta = {
                            'prompt': self.current_prompt,
                            'original_image': orig_filename,
                            'generated_image': gen_filename,
                            'timestamp': timestamp,
                            'model': self.model_id
                        }
                        with open(f"{SAVE_DIR}/meta_{timestamp}.json", "w") as f:
                            json.dump(meta, f, indent=2)
                            
                        return jsonify({'status': 'saved', 'files': [gen_filename, orig_filename]})
                    except Exception as e:
                        print(f"Error saving: {e}")
                        return jsonify({'status': 'error', 'message': str(e)}), 500
                        
            return jsonify({'status': 'error', 'message': 'No image to save'}), 400

        @self.app.route('/api/discard', methods=['POST'])
        def discard_image():
            # Clear the current generated image
            with self.lock:
                self.generated_image_data = None
            return jsonify({'status': 'discarded'})

        @self.app.route('/api/generate', methods=['POST'])
        def trigger_generate():
            """Manually trigger a new generation"""
            with self.lock:
                if self.is_generating:
                    return jsonify({'status': 'error', 'message': 'Generation already in progress'}), 400
                self.trigger_generation = True
            return jsonify({'status': 'ok', 'message': 'Generation triggered'})

    def _generate_frames(self):
        while True:
            frame = None
            if self.camera and self.camera.connected:
                ret, cam_frame, _ = self.camera.read()
                if ret:
                    frame = cam_frame
                    with self.lock:
                        self.current_frame = frame

            if frame is None:
                with self.lock:
                    if self.current_frame is not None:
                         frame = self.current_frame.copy()
                    else:
                        frame = np.zeros((480, 640, 3), dtype=np.uint8)
                        cv2.putText(frame, "Waiting for stream...", (50, 240),
                                    cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)

            ret, buffer = cv2.imencode('.jpg', frame)
            if not ret:
                time.sleep(0.1)
                continue

            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
            time.sleep(0.05)

    def _encode_image_to_base64(self, cv2_img):
        is_success, buffer = cv2.imencode(".jpg", cv2_img)
        if is_success:
            return "data:image/jpeg;base64," + base64.b64encode(buffer).decode('utf-8')
        return None

    def generation_loop(self):
        print("Starting generation loop (manual trigger mode)...")
        while True:
            if not self.camera or not self.camera.connected:
                time.sleep(1)
                continue

            should_generate = False

            with self.lock:
                # Check for manual trigger or auto-generate (if enabled)
                if self.trigger_generation and not self.is_generating:
                    should_generate = True
                    self.trigger_generation = False
                elif self.auto_generate and not self.is_generating:
                    now = time.time()
                    if now - self.last_generation_time >= self.generation_interval:
                        should_generate = True

            if should_generate:
                # Capture state for generation
                captured_frame = None
                prompt = ""
                with self.lock:
                    self.is_generating = True
                    ret, frame, _ = self.camera.read()
                    if ret:
                        self.captured_frame = frame.copy()
                        captured_frame = frame.copy()
                        prompt = self.current_prompt

                if captured_frame is not None:
                    print(f"Generating image with prompt: {prompt[:30]}...")
                    try:
                        # Convert to base64 data URI for Fal
                        image_data_uri = self._encode_image_to_base64(captured_frame)

                        # Call Fal API - expects image_urls as an array
                        result = fal_client.submit(
                            self.model_id,
                            arguments={
                                "image_urls": [image_data_uri],
                                "prompt": prompt
                            }
                        )
                        
                        # The result structure depends on the model, but usually it's result['images'][0]['url']
                        # For edit models, it might be slightly different, let's assume standard response
                        response = result.get()
                        if 'images' in response and len(response['images']) > 0:
                            generated_url = response['images'][0]['url']
                            
                            # For this app, we want to display it easily without CORS issues from Fal URLs sometimes
                            # Or just use the URL. Let's store the URL. 
                            # But wait, to save it later we need to download it.
                            # For now, let's store the URL and let the frontend display it.
                            # When saving, we might need to fetch it. 
                            # However, fal results are often public URLs. 
                            # Optimization: Download it now to base64 so we have it for saving even if URL expires?
                            # Let's just use the URL for display and download for save.
                            
                            # Actually, for "data:image" consistency in save_image, let's fetch it if it's a URL.
                            # Or, to keep it simple, assume the generated_image_data IS the URL for display, 
                            # and we handle download in save_image. 
                            # BUT my save_image logic above assumed base64. Let's stick to base64 for generated_image_data
                            # to make the frontend self-contained.
                            
                            # Let's try to keep it as URL for display speed, but fetch for save?
                            # No, let's consistency use base64 if possible, or handle both.
                            # Let's stick to the URL for generated_image_data and update save_image to handle URL.
                            
                            self.generated_image_data = generated_url
                            print("Generation successful")
                        else:
                            print("Fal returned no images:", response)
                            
                    except Exception as e:
                        print(f"Generation failed: {e}")
                    
                with self.lock:
                    self.is_generating = False
                    self.last_generation_time = time.time()
            
            time.sleep(0.5)

    def _get_html_template(self):
        return """
<!DOCTYPE html>
<html>
<head>
    <title>Synthetic Data Labeler</title>
    <style>
        body { background: #1a1a1a; color: white; font-family: sans-serif; padding: 20px; }
        .container { display: flex; gap: 20px; flex-wrap: wrap; }
        .panel { flex: 1; min-width: 400px; background: #2a2a2a; padding: 15px; border-radius: 8px; }
        img { width: 100%; border-radius: 4px; }
        .controls { margin-top: 20px; padding: 15px; background: #333; border-radius: 8px; }
        textarea { width: 100%; height: 80px; background: #444; color: white; border: 1px solid #555; padding: 8px; margin-bottom: 10px; }
        button { padding: 10px 20px; cursor: pointer; border: none; border-radius: 4px; font-weight: bold; }
        .btn-save { background: #2ecc71; color: white; }
        .btn-discard { background: #e74c3c; color: white; }
        .btn-update { background: #3498db; color: white; }
        .btn-generate { background: #9b59b6; color: white; }
        .btn-generate:disabled { background: #666; cursor: not-allowed; }
        .status { margin-top: 10px; color: #aaa; font-size: 0.9em; }
        .loading { color: #f39c12; display: none; }
    </style>
</head>
<body>
    <h1>Synthetic Data Labeler</h1>
    
    <div class="container">
        <div class="panel">
            <h3>Live Stream</h3>
            <img src="/video_feed" alt="Live Feed">
        </div>
        
        <div class="panel">
            <h3>Generated Synthetic Data</h3>
            <div id="generated-container">
                <img id="generated-image" src="//:0" alt="Waiting for generation..." style="display:none">
                <div id="placeholder" style="height: 300px; display:flex; align-items:center; justify-content:center; background:#222; color:#666;">
                    Waiting for next generation...
                </div>
            </div>
            <div class="loading" id="generating-indicator">Generating...</div>
        </div>
    </div>

    <div class="controls">
        <h3>Control Panel</h3>
        <div>
            <label>Prompt:</label>
            <textarea id="prompt-input">{{ prompt }}</textarea>
            <button class="btn-update" onclick="updatePrompt()">Update Prompt</button>
            <button class="btn-generate" id="generate-btn" onclick="generateImage()">Generate Image</button>
        </div>
        
        <div style="margin-top: 20px; border-top: 1px solid #555; padding-top: 20px;">
            <p>Decide on the generated image:</p>
            <button class="btn-save" onclick="saveImage()">YES - Save to Dataset</button>
            <button class="btn-discard" onclick="discardImage()">NO - Discard</button>
        </div>
        <div id="status-msg" class="status"></div>
    </div>

    <script>
        let currentImageUrl = "";

        function updateStatus(msg, isError=false) {
            const el = document.getElementById('status-msg');
            el.textContent = msg;
            el.style.color = isError ? '#e74c3c' : '#aaa';
            setTimeout(() => el.textContent = '', 5000);
        }

        async function pollGenerated() {
            try {
                const res = await fetch('/generated_feed');
                const data = await res.json();
                
                const img = document.getElementById('generated-image');
                const placeholder = document.getElementById('placeholder');
                const indicator = document.getElementById('generating-indicator');
                
                const generateBtn = document.getElementById('generate-btn');
                if (data.is_generating) {
                    indicator.style.display = 'block';
                    generateBtn.disabled = true;
                    generateBtn.textContent = 'Generating...';
                } else {
                    indicator.style.display = 'none';
                    generateBtn.disabled = false;
                    generateBtn.textContent = 'Generate Image';
                }

                if (data.image && data.image !== currentImageUrl) {
                    currentImageUrl = data.image;
                    img.src = data.image;
                    img.style.display = 'block';
                    placeholder.style.display = 'none';
                }
            } catch (e) {
                console.error("Polling error", e);
            }
        }

        setInterval(pollGenerated, 1000);

        async function updatePrompt() {
            const prompt = document.getElementById('prompt-input').value;
            try {
                const res = await fetch('/api/prompt', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({prompt})
                });
                const data = await res.json();
                updateStatus('Prompt updated.');
            } catch (e) {
                updateStatus('Error updating prompt', true);
            }
        }

        async function generateImage() {
            try {
                const res = await fetch('/api/generate', { method: 'POST' });
                const data = await res.json();
                if (data.status === 'ok') {
                    updateStatus('Generation started...');
                } else {
                    updateStatus('Error: ' + data.message, true);
                }
            } catch (e) {
                updateStatus('Error triggering generation', true);
            }
        }

        async function saveImage() {
            try {
                // If using URL, we might need to proxy or handle in backend.
                // The backend save endpoint handles the current state.
                const res = await fetch('/api/save', { method: 'POST' });
                const data = await res.json();
                if (data.status === 'saved') {
                    updateStatus('Image saved to dataset!');
                } else {
                    updateStatus('Error: ' + data.message, true);
                }
            } catch (e) {
                updateStatus('Error saving image', true);
            }
        }

        async function discardImage() {
            try {
                await fetch('/api/discard', { method: 'POST' });
                updateStatus('Image discarded. waiting for next...');
                document.getElementById('generated-image').style.display = 'none';
                document.getElementById('placeholder').style.display = 'flex';
                currentImageUrl = "";
            } catch (e) {
                updateStatus('Error discarding', true);
            }
        }
    </script>
</body>
</html>
        """

    def run(self):
        print(f"Starting Synthetic Labeling App on port {self.port}")
        print(f"RTSP: {self.rtsp_url}")
        print(f"Model: {self.model_id}")
        
        # Start camera
        self.camera = ThreadedCamera(self.rtsp_url)
        self.camera.start()
        
        # Start background generation loop
        gen_thread = threading.Thread(target=self.generation_loop, daemon=True)
        gen_thread.start()
        
        # Start background camera reader for the main thread/preview (optional, Flask handles it)
        # We need to keep the main camera loop updated.
        # The video_feed route pulls from self.camera.read() directly, but we need to update self.current_frame
        # for the generator loop to pick up. 
        # Actually, ThreadedCamera updates its internal frame. We need to read it.
        # The generation loop reads it. The video_feed reads it.
        
        # Wait for camera
        print("Waiting for camera...")
        while not self.camera.connected:
            time.sleep(0.5)
            
        # Run Flask
        # Note: debug=True breaks background threads sometimes due to reloader
        self.app.run(host='0.0.0.0', port=self.port, debug=False, threaded=True)


def main():
    parser = argparse.ArgumentParser(description="Roboflow/Fal.ai Synthetic Labeling")
    parser.add_argument('--port', type=int, default=DEFAULT_PORT)
    parser.add_argument('--rtsp', type=str, default=DEFAULT_RTSP_URL)
    parser.add_argument('--model', type=str, default=DEFAULT_MODEL)
    parser.add_argument('--prompt', type=str, default=DEFAULT_PROMPT)
    
    args = parser.parse_args()
    
    app = SyntheticLabelingApp(args.rtsp, args.port, args.model, args.prompt)
    app.run()

if __name__ == "__main__":
    main()

