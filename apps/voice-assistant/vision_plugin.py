"""Vision plugin for camera-based vision capabilities using Moondream"""

import asyncio
import logging
import os
from pathlib import Path
from typing import Optional

import cv2
import moondream as md
from PIL import Image

logger = logging.getLogger("jetson-orin-nano-field-kit-voice-assistant")


def is_camera_available() -> bool:
    """
    Check if a camera is available on the system.
    
    Returns:
        True if camera is available, False otherwise
    """
    try:
        # Try to open the default camera device
        camera_device = os.getenv("CAMERA_DEVICE", "/dev/video0")
        
        # For Jetson with IMX219, check if nvarguscamerasrc is available
        sensor_id = int(os.getenv("CAMERA_SENSOR_ID", "0"))
        
        # Try to create a GStreamer pipeline to test camera availability
        gstreamer_pipeline = (
            f"nvarguscamerasrc sensor-id={sensor_id} ! "
            f"video/x-raw(memory:NVMM), width=1280, height=720, "
            f"format=NV12, framerate=30/1 ! "
            f"nvvidconv ! video/x-raw, format=BGRx ! "
            f"videoconvert ! video/x-raw, format=BGR ! appsink"
        )
        
        cap = cv2.VideoCapture(gstreamer_pipeline, cv2.CAP_GSTREAMER)
        if cap.isOpened():
            ret, _ = cap.read()
            cap.release()
            if ret:
                logger.info(f"Camera available at sensor-id={sensor_id}")
                return True
        
        # Fallback: try standard V4L2 device
        cap = cv2.VideoCapture(camera_device)
        if cap.isOpened():
            ret, _ = cap.read()
            cap.release()
            if ret:
                logger.info(f"Camera available at {camera_device}")
                return True
        
        logger.warning("No camera detected")
        return False
    except Exception as e:
        logger.warning(f"Error checking camera availability: {e}")
        return False


class VisionPlugin:
    """Vision plugin for capturing and processing camera frames with Moondream"""
    
    def __init__(self):
        self._latest_frame: Optional[Image.Image] = None
        self._camera_task: Optional[asyncio.Task] = None
        self._camera_running = False
        self._md_model = None
        
        # Camera configuration
        self._camera_device = os.getenv("CAMERA_DEVICE", "/dev/video0")
        self._camera_width = int(os.getenv("CAMERA_WIDTH", "1280"))
        self._camera_height = int(os.getenv("CAMERA_HEIGHT", "720"))
        self._camera_fps = int(os.getenv("CAMERA_FPS", "30"))
        self._camera_sensor_id = int(os.getenv("CAMERA_SENSOR_ID", "0"))
        
        # Initialize Moondream model
        try:
            api_key = os.getenv("MOONDREAM_API_KEY")
            if api_key:
                self._md_model = md.vl(api_key=api_key)
                logger.info("Moondream model initialized with API key")
            else:
                # Try to use local model if available
                try:
                    self._md_model = md.vl()
                    logger.info("Moondream model initialized locally")
                except Exception as e:
                    logger.warning(f"Could not initialize Moondream model: {e}")
        except Exception as e:
            logger.error(f"Error initializing Moondream: {e}")
    
    async def start_camera_capture(self):
        """Start capturing frames from the local camera"""
        if self._camera_running:
            logger.warning("Camera capture already running")
            return
        
        if not is_camera_available():
            logger.warning("Camera not available, cannot start capture")
            return
        
        self._camera_running = True
        self._camera_task = asyncio.create_task(self._capture_local_camera())
        logger.info("Started camera capture")
    
    async def stop_camera_capture(self):
        """Stop capturing frames from the camera"""
        self._camera_running = False
        if self._camera_task:
            self._camera_task.cancel()
            try:
                await self._camera_task
            except asyncio.CancelledError:
                pass
            self._camera_task = None
        logger.info("Stopped camera capture")
    
    async def _capture_local_camera(self):
        """
        Capture frames from a local camera device (e.g. IMX219 CSI camera on Jetson),
        convert to PIL.Image, and store as the latest frame for Moondream.
        """
        # For Jetson with IMX219 CSI camera, use GStreamer pipeline
        gstreamer_pipeline = (
            f"nvarguscamerasrc sensor-id={self._camera_sensor_id} ! "
            f"video/x-raw(memory:NVMM), width={self._camera_width}, height={self._camera_height}, "
            f"format=NV12, framerate={self._camera_fps}/1 ! "
            f"nvvidconv ! video/x-raw, format=BGRx ! "
            f"videoconvert ! video/x-raw, format=BGR ! appsink"
        )
        
        logger.info("Starting local camera capture with GStreamer pipeline")
        logger.debug("Pipeline: %s", gstreamer_pipeline)
        
        # Use OpenCV with GStreamer backend
        cap = cv2.VideoCapture(gstreamer_pipeline, cv2.CAP_GSTREAMER)
        
        if not cap.isOpened():
            logger.error("Could not open camera with GStreamer pipeline")
            logger.error("Falling back to standard V4L2 device")
            # Fallback to standard device
            cap = cv2.VideoCapture(self._camera_device)
            if not cap.isOpened():
                logger.error(f"Could not open camera at {self._camera_device}")
                self._camera_running = False
                return
        
        loop = asyncio.get_running_loop()
        try:
            while self._camera_running:
                # Offload blocking read to thread pool
                ret, frame = await loop.run_in_executor(None, cap.read)
                if not ret or frame is None:
                    logger.warning("Failed to read frame from camera")
                    await asyncio.sleep(0.1)
                    continue
                
                # OpenCV -> BGR numpy array -> RGB PIL image
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                image = Image.fromarray(rgb)
                
                # Only keep the most recent frame
                self._latest_frame = image
                
                # Capture at ~2 fps (only need latest frame when user speaks)
                await asyncio.sleep(0.5)
        
        except asyncio.CancelledError:
            logger.info("Local camera capture cancelled")
        except Exception as e:
            logger.error(f"Error in camera capture: {e}", exc_info=True)
        finally:
            cap.release()
            self._camera_running = False
            logger.info("Local camera capture stopped")
    
    def get_image_description(self) -> Optional[str]:
        """
        Get a description of the latest captured frame using Moondream.
        
        Returns:
            Description string if available, None otherwise
        """
        if self._latest_frame is None:
            logger.warning("No frame available for description")
            return None
        
        if self._md_model is None:
            logger.warning("Moondream model not initialized")
            return None
        
        try:
            logger.info("Sending frame to Moondream for captioning...")
            response = self._md_model.caption(self._latest_frame)
            caption = response.get("caption")
            
            if caption:
                logger.info(f"Received caption: {caption}")
                return caption
            else:
                logger.warning(f"No caption in Moondream response: {response}")
                return None
        except Exception as exc:
            logger.error(f"Error getting image description from Moondream: {exc}", exc_info=True)
            return None
    
    def has_frame(self) -> bool:
        """Check if a frame is currently available"""
        return self._latest_frame is not None
    
    def is_available(self) -> bool:
        """Check if vision is available (camera and model)"""
        return self._camera_running and self._md_model is not None


# Global instance
_vision_plugin: Optional[VisionPlugin] = None


def get_vision_plugin() -> Optional[VisionPlugin]:
    """Get or create the vision plugin instance"""
    global _vision_plugin
    
    if _vision_plugin is None:
        if is_camera_available():
            _vision_plugin = VisionPlugin()
        else:
            logger.info("Vision plugin not available - no camera detected")
    
    return _vision_plugin


def is_vision_available() -> bool:
    """Check if vision capabilities are available"""
    return is_camera_available()

