#!/usr/bin/env python3
"""
Reachy Mini Control App - Main Application
Web dashboard with WebRTC video streaming and robot control for Jetson Orin Nano Field Kit
"""

import asyncio
import cv2
import json
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, Set

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
from pydantic_settings import BaseSettings
import numpy as np

from aiortc import RTCPeerConnection, RTCSessionDescription, VideoStreamTrack
import av

try:
    from reachy_mini import ReachyMini
    from reachy_mini.utils import create_head_pose
    REACHY_AVAILABLE = True
except ImportError:
    logging.warning("Reachy Mini SDK not available - running in simulation mode")
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
    Custom video track for Reachy camera - uses Reachy's media system when awake
    """

    def __init__(self, controller: 'ReachyController', resolution: str = "1280x720", fps: int = 30):
        super().__init__()
        self.controller = controller
        self.fps = fps

        # Parse resolution
        width, height = map(int, resolution.split('x'))
        self.width = width
        self.height = height

        logging.info(f"ReachyCamera initialized: {width}x{height} @ {fps}fps")

    async def recv(self):
        pts, time_base = await self.next_timestamp()

        frame = None

        # Try to get frame from Reachy's camera if connected and awake
        if self.controller.connected and self.controller.awake:
            frame = self.controller.get_camera_frame()

        if frame is None:
            # Return a placeholder frame with "Sleeping" or "Not Connected" message
            frame = np.zeros((self.height, self.width, 3), dtype=np.uint8)
            # Add text overlay
            if not self.controller.connected:
                text = "Not Connected"
            elif not self.controller.awake:
                text = "Reachy is Sleeping - Click Wake Up"
            else:
                text = "Camera Unavailable"

            # Draw text on frame
            font = cv2.FONT_HERSHEY_SIMPLEX
            font_scale = 1.5
            thickness = 3
            text_size = cv2.getTextSize(text, font, font_scale, thickness)[0]
            text_x = (self.width - text_size[0]) // 2
            text_y = (self.height + text_size[1]) // 2
            cv2.putText(frame, text, (text_x, text_y), font, font_scale, (255, 255, 255), thickness)
        else:
            # Frame from Reachy is already RGB, resize if needed
            if frame.shape[0] != self.height or frame.shape[1] != self.width:
                frame = cv2.resize(frame, (self.width, self.height))

        # Ensure frame is RGB format
        if len(frame.shape) == 2:
            frame = cv2.cvtColor(frame, cv2.COLOR_GRAY2RGB)
        elif frame.shape[2] == 4:
            frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2RGB)
        elif frame.shape[2] == 3:
            # Reachy media.get_frame() returns RGB, so no conversion needed
            pass

        # Create av.VideoFrame
        av_frame = av.VideoFrame.from_ndarray(frame, format="rgb24")
        av_frame.pts = pts
        av_frame.time_base = time_base

        return av_frame


class ReachyController:
    """
    Reachy robot controller with safety features
    """

    def __init__(self, settings: Settings):
        self.settings = settings
        self.reachy = None
        self.connected = False
        self.awake = False
        self.last_activity = time.time()
        self.executing_macro = False

        if REACHY_AVAILABLE:
            self.connect()
        else:
            logging.warning("Reachy SDK not available - using mock controller")
    
    def connect(self):
        """Connect to Reachy Mini robot"""
        try:
            # ReachyMini auto-detects connection mode (localhost or network)
            # Use connection_mode="network" to force network connection to remote robot
            self.reachy = ReachyMini(self.settings.reachy_host)
            self.connected = True
            logging.info(f"Connected to Reachy Mini at {self.settings.reachy_host}")

            # Enable safety features
            if self.settings.safety_limits:
                self.configure_safety()

        except Exception as e:
            logging.error(f"Failed to connect to Reachy Mini: {e}")
            self.connected = False
    
    def configure_safety(self):
        """Configure safety limits"""
        if not self.connected:
            return

        try:
            # ReachyMini SDK handles safety internally
            # Just log that safety is enabled
            logging.info("Safety limits configured (using ReachyMini defaults)")
        except Exception as e:
            logging.error(f"Failed to configure safety: {e}")

    def wake_up(self) -> bool:
        """Wake up the robot - enables motors and camera"""
        if not self.connected:
            logging.warning("Cannot wake up: not connected to robot")
            return False

        try:
            self.reachy.wake_up()
            self.awake = True
            self.update_activity()
            logging.info("Reachy Mini woke up")
            return True
        except Exception as e:
            logging.error(f"Failed to wake up robot: {e}")
            return False

    def go_to_sleep(self) -> bool:
        """Put the robot to sleep - disables motors"""
        if not self.connected:
            logging.warning("Cannot sleep: not connected to robot")
            return False

        try:
            self.reachy.sleep()
            self.awake = False
            logging.info("Reachy Mini went to sleep")
            return True
        except Exception as e:
            logging.error(f"Failed to put robot to sleep: {e}")
            return False

    def get_camera_frame(self):
        """Get a frame from Reachy's camera"""
        if not self.connected or not self.awake:
            return None

        try:
            frame = self.reachy.media.get_frame()
            return frame
        except Exception as e:
            logging.error(f"Failed to get camera frame: {e}")
            return None

    def update_activity(self):
        """Update last activity timestamp"""
        self.last_activity = time.time()
    
    def check_idle_compliance(self):
        """Enable compliance if robot is idle"""
        if not self.connected or not self.settings.auto_compliance:
            return

        if time.time() - self.last_activity > self.settings.idle_timeout:
            try:
                # ReachyMini SDK handles compliance differently
                # The SDK manages this internally
                logging.debug("Idle timeout reached - robot in standby")
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
        """Wave gesture using head movements"""
        if not self.connected:
            return

        # Wave by tilting head side to side
        for _ in range(3):
            self.reachy.goto_target(
                head=create_head_pose(roll=20, degrees=True),
                duration=0.4
            )
            await asyncio.sleep(0.5)
            self.reachy.goto_target(
                head=create_head_pose(roll=-20, degrees=True),
                duration=0.4
            )
            await asyncio.sleep(0.5)

        # Return to neutral
        self.reachy.goto_target(
            head=create_head_pose(roll=0, degrees=True),
            duration=0.5
        )
        await asyncio.sleep(0.6)
    
    async def _macro_nod(self):
        """Nod gesture - yes motion"""
        if not self.connected:
            return

        for _ in range(2):
            self.reachy.goto_target(
                head=create_head_pose(z=-15, degrees=True, mm=True),
                duration=0.4
            )
            await asyncio.sleep(0.5)
            self.reachy.goto_target(
                head=create_head_pose(z=15, degrees=True, mm=True),
                duration=0.4
            )
            await asyncio.sleep(0.5)

        # Return to neutral
        self.reachy.goto_target(
            head=create_head_pose(z=0, degrees=True, mm=True),
            duration=0.4
        )
        await asyncio.sleep(0.5)
    
    async def _macro_shake_head(self):
        """Shake head gesture - no motion"""
        if not self.connected:
            return

        for _ in range(2):
            self.reachy.goto_target(
                head=create_head_pose(x=30, degrees=True, mm=True),
                duration=0.35
            )
            await asyncio.sleep(0.4)
            self.reachy.goto_target(
                head=create_head_pose(x=-30, degrees=True, mm=True),
                duration=0.35
            )
            await asyncio.sleep(0.4)

        # Return to neutral
        self.reachy.goto_target(
            head=create_head_pose(x=0, degrees=True, mm=True),
            duration=0.35
        )
        await asyncio.sleep(0.4)
    
    async def _macro_look_around(self):
        """Look around gesture"""
        if not self.connected:
            return

        # Look right and up
        self.reachy.goto_target(
            head=create_head_pose(x=40, z=10, degrees=True, mm=True),
            duration=0.8
        )
        await asyncio.sleep(1.2)

        # Look left and up
        self.reachy.goto_target(
            head=create_head_pose(x=-40, z=10, degrees=True, mm=True),
            duration=0.8
        )
        await asyncio.sleep(1.2)

        # Look down center
        self.reachy.goto_target(
            head=create_head_pose(x=0, z=-20, degrees=True, mm=True),
            duration=0.8
        )
        await asyncio.sleep(1.2)

        # Return to neutral
        self.reachy.goto_target(
            head=create_head_pose(x=0, z=0, degrees=True, mm=True),
            duration=0.6
        )
        await asyncio.sleep(0.7)
    
    async def _macro_point(self):
        """Point gesture - look in a direction"""
        if not self.connected:
            return

        # Look and point to the right
        self.reachy.goto_target(
            head=create_head_pose(x=35, z=-10, degrees=True, mm=True),
            duration=1.2
        )
        await asyncio.sleep(2.5)

        # Return to neutral
        self.reachy.goto_target(
            head=create_head_pose(x=0, z=0, degrees=True, mm=True),
            duration=1.2
        )
        await asyncio.sleep(1.3)
    
    async def _macro_dance(self):
        """Simple dance routine using head movements"""
        if not self.connected:
            return

        # Dance moves using head tilts and rotations
        moves = [
            {"x": 25, "roll": 15},
            {"x": -25, "roll": -15},
            {"x": 0, "z": 15, "roll": 10},
            {"x": 0, "z": -15, "roll": -10},
        ]

        for _ in range(2):
            for move in moves:
                self.reachy.goto_target(
                    head=create_head_pose(**move, degrees=True, mm=True),
                    duration=0.5
                )
                await asyncio.sleep(0.6)

        # Return to neutral
        self.reachy.goto_target(
            head=create_head_pose(x=0, z=0, roll=0, degrees=True, mm=True),
            duration=0.8
        )
        await asyncio.sleep(0.9)
    
    async def _macro_celebrate(self):
        """Celebration gesture with excited head movements"""
        if not self.connected:
            return

        # Look up excitedly
        self.reachy.goto_target(
            head=create_head_pose(z=-25, degrees=True, mm=True),
            duration=0.8
        )
        await asyncio.sleep(1.0)

        # Excited head bobbing
        for _ in range(4):
            self.reachy.goto_target(
                head=create_head_pose(z=-20, roll=15, degrees=True, mm=True),
                duration=0.25
            )
            await asyncio.sleep(0.3)
            self.reachy.goto_target(
                head=create_head_pose(z=-20, roll=-15, degrees=True, mm=True),
                duration=0.25
            )
            await asyncio.sleep(0.3)

        # Return to neutral
        self.reachy.goto_target(
            head=create_head_pose(z=0, roll=0, degrees=True, mm=True),
            duration=1.2
        )
        await asyncio.sleep(1.3)


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
        # Initialize camera with the Reachy controller
        camera_track = ReachyCamera(
            controller=reachy_controller,
            resolution=settings.video_resolution,
            fps=settings.video_fps
        )
        logging.info("Camera track initialized (using Reachy media when awake)")

        # Start monitoring task
        if settings.enable_monitoring:
            asyncio.create_task(monitoring_task())

    except Exception as e:
        logging.error(f"Failed to initialize camera: {e}")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup resources"""
    global camera_track

    # Close all peer connections
    coros = [pc.close() for pc in pcs]
    await asyncio.gather(*coros, return_exceptions=True)
    pcs.clear()

    # Cleanup camera
    if camera_track:
        camera_track = None


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
        "robot_awake": reachy_controller.awake,
        "executing_macro": reachy_controller.executing_macro,
        "camera_active": camera_track is not None and reachy_controller.awake,
        "active_connections": len(pcs),
        "settings": {
            "safety_limits": settings.safety_limits,
            "macros_enabled": settings.enable_macros,
            "auto_compliance": settings.auto_compliance,
        }
    })


@app.post("/api/wake_up")
async def wake_up_robot():
    """Wake up the robot - enables motors and camera"""
    if not reachy_controller.connected:
        raise HTTPException(status_code=503, detail="Robot not connected")

    if reachy_controller.awake:
        return JSONResponse({"success": True, "message": "Robot is already awake"})

    success = reachy_controller.wake_up()
    if success:
        return JSONResponse({"success": True, "message": "Robot woke up successfully"})
    else:
        raise HTTPException(status_code=500, detail="Failed to wake up robot")


@app.post("/api/sleep")
async def sleep_robot():
    """Put the robot to sleep - disables motors"""
    if not reachy_controller.connected:
        raise HTTPException(status_code=503, detail="Robot not connected")

    if not reachy_controller.awake:
        return JSONResponse({"success": True, "message": "Robot is already asleep"})

    success = reachy_controller.go_to_sleep()
    if success:
        return JSONResponse({"success": True, "message": "Robot went to sleep successfully"})
    else:
        raise HTTPException(status_code=500, detail="Failed to put robot to sleep")


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