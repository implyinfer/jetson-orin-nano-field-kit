#!/usr/bin/env python3
"""
Roboflow Real-time Inference with RTSP Stream

This script runs real-time object detection using Roboflow models on an RTSP stream.
Make sure the RTSP server is running first (use start_rtsp_server.py).

Usage:
    python3 run_roboflow_inference.py [OPTIONS]

Examples:
    # Use default settings (localhost RTSP stream)
    python3 run_roboflow_inference.py

    # Specify custom RTSP URL
    python3 run_roboflow_inference.py --rtsp-url rtsp://192.168.1.171:8554/camera

    # Use different model and confidence threshold
    python3 run_roboflow_inference.py --model yolov8n-1280 --confidence 0.7

    # Load settings from .env file
    python3 run_roboflow_inference.py --use-env

Environment Variables (when using --use-env):
    ROBOFLOW_API_KEY: Your Roboflow API key
    RTSP_URL: RTSP stream URL
    MODEL_ALIAS: Model to use (e.g., yolov8n-640)
    CONFIDENCE: Confidence threshold (0.0-1.0)
    DISPLAY: X display (default: :0)
"""

import argparse
import os
import sys

try:
    from inference import InferencePipeline
    from inference.core.interfaces.stream.sinks import render_boxes
    import supervision as sv
except ImportError:
    print("Error: Roboflow inference package not installed")
    print("Install with: pip install inference[yolo] supervision")
    sys.exit(1)


# Model aliases for easier configuration
MODEL_ALIASES = {
    "yolov8n-640": "coco/3",
    "yolov8n-1280": "coco/9",
    "yolov8m-640": "coco/8"
}

# Default configuration
DEFAULT_API_KEY = "5yawNNvJ7gqjlloPoG0w"
DEFAULT_MODEL = "yolov8n-640"
DEFAULT_RTSP_URL = "rtsp://localhost:8554/camera"
DEFAULT_CONFIDENCE = 0.5


class RoboflowInference:
    """Roboflow inference pipeline for RTSP streams"""

    def __init__(self, api_key, model_id, rtsp_url, confidence=0.5):
        """
        Initialize inference pipeline

        Args:
            api_key: Roboflow API key
            model_id: Model ID or alias
            rtsp_url: RTSP stream URL
            confidence: Detection confidence threshold (0.0-1.0)
        """
        self.api_key = api_key
        self.model_id = self._resolve_model_alias(model_id)
        self.rtsp_url = rtsp_url
        self.confidence = confidence
        self.fps_monitor = sv.FPSMonitor()

    @staticmethod
    def _resolve_model_alias(model_id):
        """Resolve model alias to actual model ID"""
        return MODEL_ALIASES.get(model_id, model_id)

    def on_prediction(self, predictions, video_frame):
        """Callback function to render predictions on video frames"""
        render_boxes(
            predictions=predictions,
            video_frame=video_frame,
            fps_monitor=self.fps_monitor,
            display_statistics=True,
        )

    def run(self):
        """Start the inference pipeline"""
        print("=" * 70)
        print("Roboflow Real-time Inference")
        print("=" * 70)
        print(f"Model:               {self.model_id}")
        print(f"RTSP Stream:         {self.rtsp_url}")
        print(f"Confidence:          {self.confidence}")
        print(f"Display:             {os.environ.get('DISPLAY', 'not set')}")
        print("=" * 70)
        print("\nInitializing inference pipeline...")

        try:
            pipeline = InferencePipeline.init(
                model_id=self.model_id,
                video_reference=self.rtsp_url,
                on_prediction=self.on_prediction,
                api_key=self.api_key,
                confidence=self.confidence,
            )

            print("Pipeline initialized successfully!")
            print("\nStarting inference... Press Ctrl+C to stop")
            print("-" * 70)

            pipeline.start()
            pipeline.join()

        except KeyboardInterrupt:
            print("\n\nStopping inference pipeline...")
            pipeline.terminate()
            print("Pipeline stopped.")
        except Exception as e:
            print(f"\nError: {e}")
            print("\nTroubleshooting:")
            print("1. Make sure the RTSP server is running: python3 start_rtsp_server.py")
            print("2. Check that the RTSP URL is correct")
            print("3. Verify your Roboflow API key is valid")
            print(f"4. Test the stream with: ffplay {self.rtsp_url}")
            sys.exit(1)


def load_env_file(env_path='.env'):
    """Load environment variables from .env file"""
    if not os.path.exists(env_path):
        print(f"Warning: {env_path} file not found")
        print("Create one from .env.example: cp .env.example .env")
        return False

    with open(env_path, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ[key.strip()] = value.strip()

    return True


def main():
    parser = argparse.ArgumentParser(
        description="Run Roboflow inference on RTSP stream",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s
  %(prog)s --rtsp-url rtsp://localhost:8554/camera
  %(prog)s --model yolov8n-1280 --confidence 0.7
  %(prog)s --use-env

Available Models:
  yolov8n-640   - YOLOv8 Nano 640x640 (fastest)
  yolov8n-1280  - YOLOv8 Nano 1280x1280 (balanced)
  yolov8m-640   - YOLOv8 Medium 640x640 (more accurate)
  Or use custom model: workspace/version
        """
    )

    parser.add_argument(
        '--api-key', '-k',
        type=str,
        help=f'Roboflow API key (default: use DEFAULT_API_KEY)'
    )

    parser.add_argument(
        '--model', '-m',
        type=str,
        default=DEFAULT_MODEL,
        help=f'Model ID or alias (default: {DEFAULT_MODEL})'
    )

    parser.add_argument(
        '--rtsp-url', '-u',
        type=str,
        default=DEFAULT_RTSP_URL,
        help=f'RTSP stream URL (default: {DEFAULT_RTSP_URL})'
    )

    parser.add_argument(
        '--confidence', '-c',
        type=float,
        default=DEFAULT_CONFIDENCE,
        help=f'Confidence threshold 0.0-1.0 (default: {DEFAULT_CONFIDENCE})'
    )

    parser.add_argument(
        '--use-env',
        action='store_true',
        help='Load configuration from .env file'
    )

    parser.add_argument(
        '--display', '-d',
        type=str,
        help='X display to use (default: :0)'
    )

    args = parser.parse_args()

    # Load .env file if requested
    if args.use_env:
        load_env_file()

    # Set display environment variable
    display = args.display or os.environ.get('DISPLAY', ':0')
    os.environ['DISPLAY'] = display

    # Get configuration from args or environment
    api_key = args.api_key or os.environ.get('ROBOFLOW_API_KEY', DEFAULT_API_KEY)
    model = os.environ.get('MODEL_ALIAS', args.model)
    rtsp_url = os.environ.get('RTSP_URL', args.rtsp_url)
    confidence = float(os.environ.get('CONFIDENCE', args.confidence))

    # Validate confidence
    if not 0.0 <= confidence <= 1.0:
        print(f"Error: Confidence must be between 0.0 and 1.0 (got {confidence})")
        sys.exit(1)

    # Create and run inference
    inference = RoboflowInference(
        api_key=api_key,
        model_id=model,
        rtsp_url=rtsp_url,
        confidence=confidence
    )

    inference.run()


if __name__ == '__main__':
    main()
