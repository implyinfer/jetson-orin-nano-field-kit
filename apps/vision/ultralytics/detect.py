#!/usr/bin/env python3
"""
YOLO Ultralytics Detection App for Jetson Orin Nano with IMX-219 Camera

This app demonstrates real-time object detection using YOLO Ultralytics
with the IMX-219 CSI camera on the Jetson Orin Nano.
"""

import argparse
import cv2
import logging
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple

import numpy as np
from ultralytics import YOLO

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def get_gstreamer_pipeline(
    sensor_id: int = 0,
    width: int = 1280,
    height: int = 720,
    fps: int = 30,
    flip_method: int = 0
) -> str:
    """
    Create a GStreamer pipeline for IMX-219 camera on Jetson.

    Args:
        sensor_id: Camera sensor ID (default: 0)
        width: Capture width (default: 1280)
        height: Capture height (default: 720)
        fps: Frames per second (default: 30)
        flip_method: Flip method (0=none, 1=counterclockwise, 2=rotate-180,
                                   3=clockwise, 4=horizontal-flip, 5=upper-right-diagonal,
                                   6=vertical-flip, 7=upper-left-diagonal)

    Returns:
        GStreamer pipeline string
    """
    return (
        f"nvarguscamerasrc sensor-id={sensor_id} ! "
        f"video/x-raw(memory:NVMM), width={width}, height={height}, "
        f"format=NV12, framerate={fps}/1 ! "
        f"nvvidconv flip-method={flip_method} ! "
        f"video/x-raw, format=BGRx ! "
        f"videoconvert ! video/x-raw, format=BGR ! appsink"
    )


def setup_camera(args: argparse.Namespace) -> Optional[cv2.VideoCapture]:
    """
    Setup and open the camera with appropriate pipeline.

    Args:
        args: Command line arguments

    Returns:
        OpenCV VideoCapture object or None if failed
    """
    if args.use_gstreamer:
        logger.info("Setting up camera with GStreamer pipeline")
        pipeline = get_gstreamer_pipeline(
            sensor_id=args.sensor_id,
            width=args.width,
            height=args.height,
            fps=args.fps,
            flip_method=args.flip_method
        )
        logger.debug(f"Pipeline: {pipeline}")
        cap = cv2.VideoCapture(pipeline, cv2.CAP_GSTREAMER)
    else:
        logger.info(f"Setting up camera with device: {args.device}")
        cap = cv2.VideoCapture(args.device)
        if cap.isOpened():
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, args.width)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, args.height)
            cap.set(cv2.CAP_PROP_FPS, args.fps)

    if not cap.isOpened():
        logger.error("Failed to open camera")
        return None

    logger.info("Camera opened successfully")
    return cap


def load_model(model_path: str, device: str = 'cuda:0') -> Optional[YOLO]:
    """
    Load YOLO model.

    Args:
        model_path: Path to YOLO model or model name (e.g., 'yolov8n.pt')
        device: Device to run model on (default: 'cuda:0' for GPU)

    Returns:
        YOLO model object or None if failed
    """
    try:
        logger.info(f"Loading YOLO model: {model_path}")
        model = YOLO(model_path)

        # Move model to specified device
        model.to(device)
        logger.info(f"Model loaded successfully on {device}")
        return model
    except Exception as e:
        logger.error(f"Failed to load model: {e}")
        return None


def draw_detections(
    frame: np.ndarray,
    results,
    show_labels: bool = True,
    show_conf: bool = True
) -> np.ndarray:
    """
    Draw detection boxes and labels on frame.

    Args:
        frame: Input frame
        results: YOLO detection results
        show_labels: Whether to show class labels
        show_conf: Whether to show confidence scores

    Returns:
        Annotated frame
    """
    annotated_frame = frame.copy()

    for result in results:
        boxes = result.boxes
        for box in boxes:
            # Get box coordinates
            x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
            x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)

            # Get confidence and class
            conf = float(box.conf[0])
            cls = int(box.cls[0])
            class_name = result.names[cls]

            # Choose color based on class
            color = tuple(int(c) for c in np.random.randint(0, 255, 3, dtype=int))

            # Draw box
            cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), color, 2)

            # Draw label
            if show_labels or show_conf:
                label = ""
                if show_labels:
                    label += class_name
                if show_conf:
                    label += f" {conf:.2f}"

                # Get label size
                (label_width, label_height), baseline = cv2.getTextSize(
                    label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1
                )

                # Draw label background
                cv2.rectangle(
                    annotated_frame,
                    (x1, y1 - label_height - baseline - 5),
                    (x1 + label_width, y1),
                    color,
                    -1
                )

                # Draw label text
                cv2.putText(
                    annotated_frame,
                    label,
                    (x1, y1 - baseline - 2),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.5,
                    (255, 255, 255),
                    1
                )

    return annotated_frame


def print_detection_stats(results, frame_time: float):
    """
    Print detection statistics to console.

    Args:
        results: YOLO detection results
        frame_time: Time taken to process frame (seconds)
    """
    for result in results:
        boxes = result.boxes
        num_detections = len(boxes)

        if num_detections > 0:
            # Count detections by class
            class_counts = {}
            for box in boxes:
                cls = int(box.cls[0])
                class_name = result.names[cls]
                class_counts[class_name] = class_counts.get(class_name, 0) + 1

            logger.info(f"Frame processed in {frame_time*1000:.1f}ms - "
                       f"Detections: {num_detections} - {class_counts}")


def save_frame(frame: np.ndarray, output_dir: Path, prefix: str = "frame"):
    """
    Save frame to output directory.

    Args:
        frame: Frame to save
        output_dir: Output directory
        prefix: Filename prefix
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    filename = output_dir / f"{prefix}_{timestamp}.jpg"
    cv2.imwrite(str(filename), frame)
    logger.info(f"Saved frame to {filename}")


def main():
    """Main detection loop"""
    parser = argparse.ArgumentParser(
        description="YOLO Ultralytics Detection for Jetson Orin Nano with IMX-219"
    )

    # Camera arguments
    parser.add_argument(
        '--device',
        type=str,
        default='/dev/video0',
        help='Camera device (default: /dev/video0)'
    )
    parser.add_argument(
        '--use-gstreamer',
        action='store_true',
        default=True,
        help='Use GStreamer pipeline for IMX-219 (default: True)'
    )
    parser.add_argument(
        '--sensor-id',
        type=int,
        default=0,
        help='Camera sensor ID for GStreamer (default: 0)'
    )
    parser.add_argument(
        '--width',
        type=int,
        default=1280,
        help='Camera width (default: 1280)'
    )
    parser.add_argument(
        '--height',
        type=int,
        default=720,
        help='Camera height (default: 720)'
    )
    parser.add_argument(
        '--fps',
        type=int,
        default=30,
        help='Camera FPS (default: 30)'
    )
    parser.add_argument(
        '--flip-method',
        type=int,
        default=0,
        choices=[0, 1, 2, 3, 4, 5, 6, 7],
        help='Flip method for camera (default: 0=none)'
    )

    # Model arguments
    parser.add_argument(
        '--model',
        type=str,
        default='yolov8n.pt',
        help='YOLO model path or name (default: yolov8n.pt)'
    )
    parser.add_argument(
        '--conf',
        type=float,
        default=0.25,
        help='Confidence threshold (default: 0.25)'
    )
    parser.add_argument(
        '--iou',
        type=float,
        default=0.45,
        help='IoU threshold for NMS (default: 0.45)'
    )
    parser.add_argument(
        '--device-type',
        type=str,
        default='cuda:0',
        choices=['cuda:0', 'cpu'],
        help='Device for inference (default: cuda:0)'
    )

    # Display arguments
    parser.add_argument(
        '--show',
        action='store_true',
        default=False,
        help='Show detection window (default: False)'
    )
    parser.add_argument(
        '--no-labels',
        action='store_true',
        help='Do not show labels on detections'
    )
    parser.add_argument(
        '--no-conf',
        action='store_true',
        help='Do not show confidence scores'
    )

    # Output arguments
    parser.add_argument(
        '--save',
        action='store_true',
        help='Save annotated frames'
    )
    parser.add_argument(
        '--output-dir',
        type=str,
        default='output',
        help='Output directory for saved frames (default: output)'
    )
    parser.add_argument(
        '--save-interval',
        type=int,
        default=30,
        help='Save frame every N frames when detections present (default: 30)'
    )

    # Other arguments
    parser.add_argument(
        '--max-frames',
        type=int,
        default=0,
        help='Maximum frames to process (0=unlimited, default: 0)'
    )
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )

    args = parser.parse_args()

    if args.verbose:
        logger.setLevel(logging.DEBUG)

    # Create output directory if saving
    if args.save:
        output_dir = Path(args.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Saving frames to {output_dir}")

    # Setup camera
    cap = setup_camera(args)
    if cap is None:
        logger.error("Failed to setup camera")
        return 1

    # Load model
    model = load_model(args.model, args.device_type)
    if model is None:
        logger.error("Failed to load model")
        cap.release()
        return 1

    # Main detection loop
    frame_count = 0
    fps_start_time = time.time()
    fps_frame_count = 0
    fps = 0.0

    try:
        logger.info("Starting detection loop (press 'q' to quit)")

        while True:
            # Read frame
            ret, frame = cap.read()
            if not ret:
                logger.warning("Failed to read frame")
                break

            frame_count += 1
            fps_frame_count += 1

            # Run detection
            start_time = time.time()
            results = model(
                frame,
                conf=args.conf,
                iou=args.iou,
                verbose=False
            )
            inference_time = time.time() - start_time

            # Print stats
            print_detection_stats(results, inference_time)

            # Draw detections
            annotated_frame = draw_detections(
                frame,
                results,
                show_labels=not args.no_labels,
                show_conf=not args.no_conf
            )

            # Calculate and display FPS
            if time.time() - fps_start_time >= 1.0:
                fps = fps_frame_count / (time.time() - fps_start_time)
                fps_start_time = time.time()
                fps_frame_count = 0

            # Add FPS text to frame
            cv2.putText(
                annotated_frame,
                f"FPS: {fps:.1f}",
                (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                1,
                (0, 255, 0),
                2
            )

            # Save frame if requested and detections present
            if args.save and len(results[0].boxes) > 0:
                if frame_count % args.save_interval == 0:
                    save_frame(annotated_frame, output_dir)

            # Show frame
            if args.show:
                cv2.imshow('YOLO Detection', annotated_frame)
                key = cv2.waitKey(1) & 0xFF
                if key == ord('q'):
                    logger.info("User requested quit")
                    break

            # Check max frames
            if args.max_frames > 0 and frame_count >= args.max_frames:
                logger.info(f"Reached max frames: {args.max_frames}")
                break

    except KeyboardInterrupt:
        logger.info("Interrupted by user")

    except Exception as e:
        logger.error(f"Error in detection loop: {e}", exc_info=True)
        return 1

    finally:
        # Cleanup
        cap.release()
        if args.show:
            cv2.destroyAllWindows()
        logger.info(f"Processed {frame_count} frames")

    return 0


if __name__ == "__main__":
    sys.exit(main())
