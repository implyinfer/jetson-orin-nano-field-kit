#!/usr/bin/env python3
"""
Reachy Mini Control App - Main Application
Web dashboard with WebRTC video streaming and robot control for Jetson Orin Nano Field Kit
"""

import asyncio
import cv2
import json
import logging
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set
import uuid

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
from pydantic_settings import BaseSettings
import numpy as np

from aiortc import RTCPeerConnection, RTCSessionDescription, VideoStreamTrack
from aiortc.contrib.media import MediaPlayer
import av

try:
    from reachy_sdk import ReachySDK
    from reachy_sdk.trajectory import goto
    REACHY_AVAILABLE = True
except ImportError:
    logging.warning("Reachy SDK not available - running in simulation mode")
    REACHY_AVAILABLE = False


class Settings(BaseSettings):
    """Application settings from environment variables"""
    
    # Reachy connection
    reachy_host: str = "192.168.1.100"
    reachy_port: int = 50051
    reachy_timeout: int = 10
    
    # Web server
    web_port: int = 8080
    web_host: str = "0.0.0.0"
    debug: bool = False
    
    # WebRTC
    webrtc_port: int = 8081
    video_resolution: str = "1280x720"
    video_fps: int = 30
    video_codec: str = "h264"
    hardware_acceleration: bool = True
    
    # Camera
    camera_device: int = 0
    camera_format: str = "mjpeg"
    use_reachy_cameras: bool = True
    
    # Robot control
    safety_limits: bool = True
    max_joint_velocity: float = 50.0
    max_torque_limit: float = 0.8
    auto_compliance: bool = True
    idle_timeout: int = 30
    
    # Entertainment
    enable_macros: bool = True
    macro_timeout: int = 60
    available_macros: str = "wave,dance,look_around,nod,shake_head,point,celebrate"
    
    # System
    enable_monitoring: bool = True
    monitoring_interval: int = 5
    log_level: str = "INFO"
    
    class Config:
        env_file = ".env"


class ReachyCamera(VideoStreamTrack):
    """
    Custom video track for Reachy camera or USB camera
    """
    
    def __init__(self, device: int = 0, resolution: str = "1280x720", fps: int = 30):
        super().__init__()
        self.device = device
        self.fps = fps
        
        # Parse resolution
        width, height = map(int, resolution.split('x'))
        self.width = width
        self.height = height
        
        # Initialize camera
        self.cap = cv2.VideoCapture(device)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        self.cap.set(cv2.CAP_PROP_FPS, fps)
        
        if not self.cap.isOpened():
            raise RuntimeError(f"Failed to open camera device {device}")
        
        logging.info(f"Camera initialized: {width}x{height} @ {fps}fps")
    
    async def recv(self):
        pts, time_base = await self.next_timestamp()
        
        ret, frame = self.cap.read()
        if not ret:
            logging.warning("Failed to read frame from camera")
            # Return a black frame if camera fails
            frame = np.zeros((self.height, self.width, 3), dtype=np.uint8)
        
        # Convert BGR to RGB for WebRTC
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # Create av.VideoFrame
        av_frame = av.VideoFrame.from_ndarray(frame, format="rgb24")
        av_frame.pts = pts
        av_frame.time_base = time_base
        
        return av_frame
    
    def __del__(self):
        if hasattr(self, 'cap') and self.cap.isOpened():
            self.cap.release()


class ReachyController:
    """
    Reachy robot controller with safety features
    """
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.reachy = None
        self.connected = False
        self.last_activity = time.time()
        self.executing_macro = False
        
        if REACHY_AVAILABLE:
            self.connect()
        else:
            logging.warning("Reachy SDK not available - using mock controller")
    
    def connect(self):
        """Connect to Reachy robot"""
        try:
            self.reachy = ReachySDK(
                host=self.settings.reachy_host,
                port=self.settings.reachy_port
            )
            self.connected = True
            logging.info(f"Connected to Reachy at {self.settings.reachy_host}:{self.settings.reachy_port}")
            
            # Enable safety features
            if self.settings.safety_limits:
                self.configure_safety()
                
        except Exception as e:
            logging.error(f"Failed to connect to Reachy: {e}")
            self.connected = False
    
    def configure_safety(self):
        """Configure safety limits"""
        if not self.connected:
            return
            
        try:
            # Set torque limits for all joints
            for joint_name in self.reachy.joints:
                joint = getattr(self.reachy, joint_name)
                joint.torque_limit = self.settings.max_torque_limit
                
            logging.info("Safety limits configured")
        except Exception as e:
            logging.error(f"Failed to configure safety: {e}")
    
    def update_activity(self):
        """Update last activity timestamp"""
        self.last_activity = time.time()
    
    def check_idle_compliance(self):
        """Enable compliance if robot is idle"""
        if not self.connected or not self.settings.auto_compliance:
            return
            
        if time.time() - self.last_activity > self.settings.idle_timeout:
            try:
                # Enable compliance for all joints
                for joint_name in self.reachy.joints:
                    joint = getattr(self.reachy, joint_name)
                    joint.compliant = True
                logging.debug("Enabled compliance due to inactivity")
            except Exception as e:
                logging.error(f"Failed to enable compliance: {e}")
    
    async def execute_macro(self, macro_name: str) -> bool:
        """Execute entertainment macro"""
        if not self.connected or self.executing_macro:
            return False
        
        if macro_name not in self.settings.available_macros.split(','):
            logging.warning(f"Unknown macro: {macro_name}")
            return False
        
        self.executing_macro = True
        self.update_activity()
        
        try:
            # Disable compliance
            for joint_name in self.reachy.joints:
                joint = getattr(self.reachy, joint_name)
                joint.compliant = False
            
            # Execute macro based on name
            if macro_name == "wave":
                await self._macro_wave()
            elif macro_name == "dance":
                await self._macro_dance()
            elif macro_name == "look_around":
                await self._macro_look_around()
            elif macro_name == "nod":
                await self._macro_nod()
            elif macro_name == "shake_head":
                await self._macro_shake_head()
            elif macro_name == "point":
                await self._macro_point()
            elif macro_name == "celebrate":
                await self._macro_celebrate()
            else:
                logging.warning(f"Macro not implemented: {macro_name}")
                return False
            
            logging.info(f"Executed macro: {macro_name}")
            return True
            
        except Exception as e:
            logging.error(f"Failed to execute macro {macro_name}: {e}")
            return False
        finally:
            self.executing_macro = False
    
    async def _macro_wave(self):
        """Wave gesture"""
        if not self.connected:
            return
            
        # Simple wave motion
        await goto(
            goal_positions={
                "r_shoulder_pitch": -30,
                "r_shoulder_roll": -45,
                "r_elbow_pitch": -90,
            },
            duration=1.0,
            interpolation_mode="minimum_jerk"
        )
        
        # Wave motion
        for _ in range(3):
            await goto(
                goal_positions={"r_elbow_pitch": -60},
                duration=0.5,
                interpolation_mode="minimum_jerk"
            )
            await goto(
                goal_positions={"r_elbow_pitch": -120},
                duration=0.5,
                interpolation_mode="minimum_jerk"
            )
        
        # Return to neutral
        await goto(
            goal_positions={
                "r_shoulder_pitch": 0,
                "r_shoulder_roll": 0,
                "r_elbow_pitch": 0,
            },
            duration=1.0,
            interpolation_mode="minimum_jerk"
        )
    
    async def _macro_nod(self):
        """Nod gesture"""
        if not self.connected:
            return
            
        for _ in range(2):
            await goto(
                goal_positions={"neck_pitch": 15},
                duration=0.5,
                interpolation_mode="minimum_jerk"
            )
            await goto(
                goal_positions={"neck_pitch": -15},
                duration=0.5,
                interpolation_mode="minimum_jerk"
            )
        
        await goto(
            goal_positions={"neck_pitch": 0},
            duration=0.5,
            interpolation_mode="minimum_jerk"
        )
    
    async def _macro_shake_head(self):
        """Shake head gesture"""
        if not self.connected:
            return
            
        for _ in range(2):
            await goto(
                goal_positions={"neck_yaw": 30},
                duration=0.4,
                interpolation_mode="minimum_jerk"
            )
            await goto(
                goal_positions={"neck_yaw": -30},
                duration=0.4,
                interpolation_mode="minimum_jerk"
            )
        
        await goto(
            goal_positions={"neck_yaw": 0},
            duration=0.4,
            interpolation_mode="minimum_jerk"
        )
    
    async def _macro_look_around(self):
        """Look around gesture"""
        if not self.connected:
            return
            
        positions = [
            {"neck_yaw": 45, "neck_pitch": 10},
            {"neck_yaw": -45, "neck_pitch": 10},
            {"neck_yaw": 0, "neck_pitch": -20},
            {"neck_yaw": 0, "neck_pitch": 0},
        ]
        
        for pos in positions:
            await goto(
                goal_positions=pos,
                duration=1.0,
                interpolation_mode="minimum_jerk"
            )
            await asyncio.sleep(0.5)
    
    async def _macro_point(self):
        """Point gesture"""
        if not self.connected:
            return
            
        await goto(
            goal_positions={
                "r_shoulder_pitch": -45,
                "r_shoulder_roll": -20,
                "r_elbow_pitch": 0,
                "neck_yaw": 20,
                "neck_pitch": -10,
            },
            duration=1.5,
            interpolation_mode="minimum_jerk"
        )
        
        await asyncio.sleep(2.0)
        
        await goto(
            goal_positions={
                "r_shoulder_pitch": 0,
                "r_shoulder_roll": 0,
                "r_elbow_pitch": 0,
                "neck_yaw": 0,
                "neck_pitch": 0,
            },
            duration=1.5,
            interpolation_mode="minimum_jerk"
        )
    
    async def _macro_dance(self):
        """Simple dance routine"""
        if not self.connected:
            return
            
        moves = [
            {"r_shoulder_pitch": -30, "l_shoulder_pitch": 30, "neck_yaw": 20},
            {"r_shoulder_pitch": 30, "l_shoulder_pitch": -30, "neck_yaw": -20},
            {"r_shoulder_roll": -45, "l_shoulder_roll": 45, "neck_pitch": 10},
            {"r_shoulder_roll": 45, "l_shoulder_roll": -45, "neck_pitch": -10},
        ]
        
        for move in moves * 2:
            await goto(
                goal_positions=move,
                duration=0.8,
                interpolation_mode="minimum_jerk"
            )
            await asyncio.sleep(0.2)
        
        # Return to neutral
        await goto(
            goal_positions={joint: 0 for joint in move.keys()},
            duration=1.0,
            interpolation_mode="minimum_jerk"
        )
    
    async def _macro_celebrate(self):
        """Celebration gesture"""
        if not self.connected:
            return
            
        # Raise both arms
        await goto(
            goal_positions={
                "r_shoulder_pitch": -90,
                "l_shoulder_pitch": -90,
                "r_shoulder_roll": -30,
                "l_shoulder_roll": 30,
                "neck_pitch": -20,
            },
            duration=1.0,
            interpolation_mode="minimum_jerk"
        )
        
        await asyncio.sleep(1.0)
        
        # Celebration wave
        for _ in range(4):
            await goto(
                goal_positions={
                    "r_shoulder_roll": -60,
                    "l_shoulder_roll": 60,
                },
                duration=0.3,
                interpolation_mode="minimum_jerk"
            )
            await goto(
                goal_positions={
                    "r_shoulder_roll": -30,
                    "l_shoulder_roll": 30,
                },
                duration=0.3,
                interpolation_mode="minimum_jerk"
            )
        
        # Return to neutral
        await goto(
            goal_positions={
                "r_shoulder_pitch": 0,
                "l_shoulder_pitch": 0,
                "r_shoulder_roll": 0,
                "l_shoulder_roll": 0,
                "neck_pitch": 0,
            },
            duration=1.5,
            interpolation_mode="minimum_jerk"
        )


# API Models
class MacroRequest(BaseModel):
    name: str

class MacroResponse(BaseModel):
    success: bool
    message: str


# Global variables
settings = Settings()
reachy_controller = ReachyController(settings)
pcs: Set[RTCPeerConnection] = set()
camera_track: Optional[ReachyCamera] = None

# Initialize FastAPI app
app = FastAPI(title="Reachy Mini Control Dashboard", version="1.0.0")

# Setup templates and static files
templates_dir = Path(__file__).parent / "templates"
static_dir = Path(__file__).parent / "static"
templates_dir.mkdir(exist_ok=True)
static_dir.mkdir(exist_ok=True)

templates = Jinja2Templates(directory=str(templates_dir))
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


@app.on_event("startup")
async def startup_event():
    """Initialize camera and start monitoring tasks"""
    global camera_track
    
    try:
        # Initialize camera
        camera_track = ReachyCamera(
            device=settings.camera_device,
            resolution=settings.video_resolution,
            fps=settings.video_fps
        )
        logging.info("Camera track initialized")
        
        # Start monitoring task
        if settings.enable_monitoring:
            asyncio.create_task(monitoring_task())
            
    except Exception as e:
        logging.error(f"Failed to initialize camera: {e}")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup resources"""
    # Close all peer connections
    coros = [pc.close() for pc in pcs]
    await asyncio.gather(*coros, return_exceptions=True)
    pcs.clear()
    
    # Cleanup camera
    if camera_track:
        del camera_track


async def monitoring_task():
    """Background task for system monitoring and robot compliance"""
    while True:
        try:
            # Check robot idle compliance
            reachy_controller.check_idle_compliance()
            
            # Add system monitoring here if needed
            
        except Exception as e:
            logging.error(f"Monitoring task error: {e}")
        
        await asyncio.sleep(settings.monitoring_interval)


@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Main dashboard page"""
    context = {
        "request": request,
        "title": "Reachy Mini Control Dashboard",
        "connected": reachy_controller.connected,
        "macros": settings.available_macros.split(','),
        "webrtc_port": settings.webrtc_port,
    }
    return templates.TemplateResponse("dashboard.html", context)


@app.get("/api/status")
async def get_status():
    """Get system and robot status"""
    return JSONResponse({
        "timestamp": datetime.now().isoformat(),
        "robot_connected": reachy_controller.connected,
        "executing_macro": reachy_controller.executing_macro,
        "camera_active": camera_track is not None,
        "active_connections": len(pcs),
        "settings": {
            "safety_limits": settings.safety_limits,
            "macros_enabled": settings.enable_macros,
            "auto_compliance": settings.auto_compliance,
        }
    })


@app.post("/api/macro", response_model=MacroResponse)
async def execute_macro(request: MacroRequest):
    """Execute a robot macro"""
    if not settings.enable_macros:
        raise HTTPException(status_code=403, detail="Macros are disabled")
    
    if reachy_controller.executing_macro:
        raise HTTPException(status_code=409, detail="Another macro is currently executing")
    
    success = await reachy_controller.execute_macro(request.name)
    
    if success:
        return MacroResponse(success=True, message=f"Macro '{request.name}' executed successfully")
    else:
        return MacroResponse(success=False, message=f"Failed to execute macro '{request.name}'")


@app.post("/api/webrtc/offer")
async def webrtc_offer(request: Request):
    """Handle WebRTC offer and create answer"""
    if not camera_track:
        raise HTTPException(status_code=503, detail="Camera not available")
    
    params = await request.json()
    offer = RTCSessionDescription(sdp=params["sdp"], type=params["type"])
    
    pc = RTCPeerConnection()
    pcs.add(pc)
    
    @pc.on("connectionstatechange")
    async def on_connectionstatechange():
        logging.info(f"WebRTC connection state: {pc.connectionState}")
        if pc.connectionState == "closed":
            pcs.discard(pc)
    
    # Add video track
    pc.addTrack(camera_track)
    
    # Set remote description and create answer
    await pc.setRemoteDescription(offer)
    answer = await pc.createAnswer()
    await pc.setLocalDescription(answer)
    
    return JSONResponse({
        "sdp": pc.localDescription.sdp,
        "type": pc.localDescription.type
    })


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time communication"""
    await websocket.accept()
    
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            
            if message["type"] == "ping":
                await websocket.send_text(json.dumps({"type": "pong"}))
            elif message["type"] == "macro":
                if settings.enable_macros and not reachy_controller.executing_macro:
                    macro_name = message.get("name")
                    success = await reachy_controller.execute_macro(macro_name)
                    await websocket.send_text(json.dumps({
                        "type": "macro_result",
                        "success": success,
                        "macro": macro_name
                    }))
            
    except WebSocketDisconnect:
        logging.info("WebSocket client disconnected")
    except Exception as e:
        logging.error(f"WebSocket error: {e}")


if __name__ == "__main__":
    # Setup logging
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    # Create logs directory
    logs_dir = Path(__file__).parent / "logs"
    logs_dir.mkdir(exist_ok=True)
    
    logging.info("Starting Reachy Mini Control Dashboard")
    logging.info(f"Web server: http://{settings.web_host}:{settings.web_port}")
    logging.info(f"WebRTC port: {settings.webrtc_port}")
    logging.info(f"Robot connection: {settings.reachy_host}:{settings.reachy_port}")
    
    # Run the application
    uvicorn.run(
        "main:app",
        host=settings.web_host,
        port=settings.web_port,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    )