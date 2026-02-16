#!/usr/bin/env python3
"""
Simple Web Interface for Reachy Mini Entertainment
A minimalist web interface to trigger entertainment behaviors.
"""

import asyncio
import logging
from pathlib import Path
from typing import Dict, Any

import uvicorn
from fastapi import FastAPI, Request, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel

from entertainment_controller import EntertainmentController, EmotionState


class BehaviorRequest(BaseModel):
    behavior: str


class SimpleWebInterface:
    """Simple web interface for entertainment control"""
    
    def __init__(self, host: str = "0.0.0.0", port: int = 8090, use_simulation: bool = False):
        self.host = host
        self.port = port
        self.controller = EntertainmentController(use_simulation=use_simulation)
        
        # Setup FastAPI
        self.app = FastAPI(title="Reachy Mini Entertainment", version="1.0.0")
        
        # Setup templates and static files
        templates_dir = Path(__file__).parent / "templates"
        static_dir = Path(__file__).parent / "static"
        
        if templates_dir.exists():
            self.templates = Jinja2Templates(directory=str(templates_dir))
        if static_dir.exists():
            self.app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
        
        self.setup_routes()
    
    def setup_routes(self):
        """Setup web routes"""
        
        @self.app.get("/", response_class=HTMLResponse)
        async def dashboard(request: Request):
            """Main dashboard page"""
            if hasattr(self, 'templates'):
                return self.templates.TemplateResponse("simple_dashboard.html", {
                    "request": request,
                    "status": self.controller.get_status()
                })
            else:
                # Fallback HTML if templates not available
                return HTMLResponse(self._get_fallback_html())
        
        @self.app.get("/api/status")
        async def get_status():
            """Get controller status"""
            return self.controller.get_status()
        
        @self.app.post("/api/behavior")
        async def execute_behavior(request: BehaviorRequest):
            """Execute a specific behavior"""
            try:
                behavior_map = {
                    "wake_up": self.controller.wake_up,
                    "go_to_sleep": self.controller.go_to_sleep,
                    "wave_hello": self.controller.wave_hello,
                    "look_around_curious": self.controller.look_around_curious,
                    "nod_yes": self.controller.nod_yes,
                    "shake_head_no": self.controller.shake_head_no,
                    "dance_simple": self.controller.dance_simple,
                    "be_shy": self.controller.be_shy,
                    "random_entertainment": self.controller.random_entertainment,
                    # Kid-friendly behaviors
                    "peek_a_boo": self.controller.peek_a_boo,
                    "follow_the_leader": self.controller.follow_the_leader,
                    "counting_game": self.controller.counting_game,
                    "simon_says_demo": self.controller.simon_says_demo,
                    "story_time_expressions": self.controller.story_time_expressions,
                    "attention_getter": self.controller.attention_getter,
                    # Audience behaviors
                    "robot_introduction": self.controller.robot_introduction,
                    "crowd_pleaser_dance": self.controller.crowd_pleaser_dance,
                    "interactive_mirror": self.controller.interactive_mirror
                }
                
                if request.behavior not in behavior_map:
                    raise HTTPException(status_code=400, detail=f"Unknown behavior: {request.behavior}")
                
                if self.controller.is_performing:
                    raise HTTPException(status_code=409, detail="Robot is already performing another behavior")
                
                success = await behavior_map[request.behavior]()
                
                return {
                    "success": success,
                    "behavior": request.behavior,
                    "status": self.controller.get_status()
                }
                
            except Exception as e:
                logging.error(f"Behavior execution failed: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.post("/api/emergency_stop")
        async def emergency_stop():
            """Emergency stop"""
            try:
                success = await self.controller.emergency_stop()
                return {
                    "success": success,
                    "status": self.controller.get_status()
                }
            except Exception as e:
                logging.error(f"Emergency stop failed: {e}")
                raise HTTPException(status_code=500, detail=str(e))
    
    def _get_fallback_html(self) -> str:
        """Fallback HTML when templates are not available"""
        status = self.controller.get_status()
        emotion_color = {
            "neutral": "#6b7280",
            "happy": "#10b981", 
            "curious": "#3b82f6",
            "sleepy": "#6366f1",
            "excited": "#f59e0b",
            "shy": "#ec4899"
        }.get(status["current_emotion"], "#6b7280")
        
        return f"""
<!DOCTYPE html>
<html>
<head>
    <title>Reachy Mini Entertainment</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body {{ font-family: Arial, sans-serif; margin: 0; padding: 20px; background-color: #f3f4f6; }}
        .container {{ max-width: 800px; margin: 0 auto; background-color: white; border-radius: 8px; padding: 30px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
        .header {{ text-align: center; margin-bottom: 30px; }}
        .status {{ background-color: #f9fafb; padding: 20px; border-radius: 6px; margin-bottom: 30px; }}
        .emotion {{ display: inline-block; padding: 5px 15px; background-color: {emotion_color}; color: white; border-radius: 20px; font-size: 14px; }}
        .behavior-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin-bottom: 30px; }}
        .behavior-btn {{ padding: 15px; background-color: #3b82f6; color: white; border: none; border-radius: 6px; cursor: pointer; font-size: 16px; transition: background-color 0.2s; }}
        .behavior-btn:hover {{ background-color: #2563eb; }}
        .behavior-btn:disabled {{ background-color: #9ca3af; cursor: not-allowed; }}
        .emergency-btn {{ width: 100%; padding: 15px; background-color: #dc2626; color: white; border: none; border-radius: 6px; cursor: pointer; font-size: 18px; font-weight: bold; }}
        .emergency-btn:hover {{ background-color: #b91c1c; }}
        .result {{ margin-top: 20px; padding: 10px; border-radius: 4px; }}
        .success {{ background-color: #d1fae5; color: #065f46; }}
        .error {{ background-color: #fef2f2; color: #991b1b; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🤖 Reachy Mini Entertainment</h1>
            <p>Simple controls for entertaining with your Reachy Mini robot</p>
        </div>
        
        <div class="status">
            <h3>Robot Status</h3>
            <p><strong>Mode:</strong> {"Simulation" if status["simulation_mode"] else "Real Robot"}</p>
            <p><strong>Connected:</strong> {"Yes" if status["robot_connected"] else "No"}</p>
            <p><strong>Emotion:</strong> <span class="emotion">{status["current_emotion"].title()}</span></p>
            <p><strong>Performing:</strong> {"Yes" if status["is_performing"] else "No"}</p>
        </div>
        
        <div style="margin-bottom: 20px;">
            <h3>Basic Behaviors</h3>
            <div class="behavior-grid">
                <button class="behavior-btn" onclick="executeBehavior('wake_up')">🌅 Wake Up</button>
                <button class="behavior-btn" onclick="executeBehavior('wave_hello')">👋 Wave Hello</button>
                <button class="behavior-btn" onclick="executeBehavior('nod_yes')">✅ Nod Yes</button>
                <button class="behavior-btn" onclick="executeBehavior('shake_head_no')">❌ Shake No</button>
                <button class="behavior-btn" onclick="executeBehavior('look_around_curious')">👀 Look Around</button>
                <button class="behavior-btn" onclick="executeBehavior('dance_simple')">💃 Dance</button>
                <button class="behavior-btn" onclick="executeBehavior('be_shy')">🙈 Be Shy</button>
                <button class="behavior-btn" onclick="executeBehavior('go_to_sleep')">😴 Sleep</button>
            </div>
        </div>
        
        <div style="margin-bottom: 20px;">
            <h3>🧸 Kid-Friendly Games</h3>
            <div class="behavior-grid">
                <button class="behavior-btn" onclick="executeBehavior('peek_a_boo')">👀 Peek-a-Boo</button>
                <button class="behavior-btn" onclick="executeBehavior('follow_the_leader')">🚶 Follow Leader</button>
                <button class="behavior-btn" onclick="executeBehavior('counting_game')">🔢 Count 1-5</button>
                <button class="behavior-btn" onclick="executeBehavior('simon_says_demo')">👂 Simon Says</button>
                <button class="behavior-btn" onclick="executeBehavior('story_time_expressions')">📚 Story Faces</button>
                <button class="behavior-btn" onclick="executeBehavior('attention_getter')">📢 Hey Look!</button>
            </div>
        </div>
        
        <div style="margin-bottom: 20px;">
            <h3>🎭 Audience Entertainment</h3>
            <div class="behavior-grid">
                <button class="behavior-btn" onclick="executeBehavior('robot_introduction')">🤝 Introduction</button>
                <button class="behavior-btn" onclick="executeBehavior('crowd_pleaser_dance')">🕺 Crowd Dance</button>
                <button class="behavior-btn" onclick="executeBehavior('interactive_mirror')">🪞 Mirror Game</button>
                <button class="behavior-btn" onclick="executeBehavior('random_entertainment')">🎲 Random Fun</button>
            </div>
        </div>
        
        <button class="emergency-btn" onclick="emergencyStop()">🛑 EMERGENCY STOP</button>
        
        <div id="result"></div>
    </div>
    
    <script>
        async function executeBehavior(behavior) {{
            const buttons = document.querySelectorAll('button');
            buttons.forEach(btn => btn.disabled = true);
            
            showResult('Executing ' + behavior.replace('_', ' ') + '...', 'info');
            
            try {{
                const response = await fetch('/api/behavior', {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify({{ behavior: behavior }})
                }});
                
                const data = await response.json();
                
                if (data.success) {{
                    showResult('✅ Behavior completed successfully!', 'success');
                }} else {{
                    showResult('❌ Behavior failed to complete', 'error');
                }}
                
                // Refresh page to update status
                setTimeout(() => location.reload(), 2000);
                
            }} catch (error) {{
                showResult('❌ Error: ' + error.message, 'error');
            }} finally {{
                buttons.forEach(btn => btn.disabled = false);
            }}
        }}
        
        async function emergencyStop() {{
            try {{
                const response = await fetch('/api/emergency_stop', {{ method: 'POST' }});
                const data = await response.json();
                
                showResult('🛑 Emergency stop ' + (data.success ? 'activated' : 'failed'), 
                          data.success ? 'success' : 'error');
                
                setTimeout(() => location.reload(), 1000);
            }} catch (error) {{
                showResult('❌ Emergency stop error: ' + error.message, 'error');
            }}
        }}
        
        function showResult(message, type) {{
            const resultDiv = document.getElementById('result');
            resultDiv.textContent = message;
            resultDiv.className = 'result ' + type;
        }}
        
        // Auto-refresh status every 30 seconds
        setInterval(() => {{
            if (!document.querySelector('button:disabled')) {{
                location.reload();
            }}
        }}, 30000);
    </script>
</body>
</html>
        """
    
    def run(self):
        """Run the web interface"""
        logging.info(f"Starting Reachy Mini Entertainment Web Interface on {self.host}:{self.port}")
        uvicorn.run(self.app, host=self.host, port=self.port, log_level="info")


async def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Reachy Mini Entertainment Web Interface")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8090, help="Port to bind to")
    parser.add_argument("--sim", action="store_true", help="Run in simulation mode")
    
    args = parser.parse_args()
    
    # Setup logging
    logging.basicConfig(level=logging.INFO)
    
    # Create and run web interface
    interface = SimpleWebInterface(host=args.host, port=args.port, use_simulation=args.sim)
    interface.run()


if __name__ == "__main__":
    asyncio.run(main())