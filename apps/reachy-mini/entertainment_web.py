#!/usr/bin/env python3
"""
Simple Web Interface for Reachy Mini Entertainment System
Easy-to-use web control panel for all the fun features!
"""

import asyncio
import logging
import json
from pathlib import Path
from flask import Flask, render_template, request, jsonify
from threading import Thread
from enhanced_entertainment import EnhancedEntertainmentSystem

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Global entertainment system
entertainment_system = None
current_activity = "None"
activity_status = "Ready"

app = Flask(__name__)

def create_templates():
    """Create simple HTML templates"""
    templates_dir = Path("templates")
    templates_dir.mkdir(exist_ok=True)
    
    # Main interface template
    template_html = """
<!DOCTYPE html>
<html>
<head>
    <title>🤖 Reachy Mini Entertainment System 🎪</title>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body {
            font-family: 'Comic Sans MS', cursive, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            margin: 0;
            padding: 20px;
            color: white;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
        }
        .header {
            text-align: center;
            margin-bottom: 30px;
        }
        .header h1 {
            font-size: 3em;
            margin: 10px 0;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.5);
        }
        .status-panel {
            background: rgba(255,255,255,0.1);
            border-radius: 15px;
            padding: 20px;
            margin-bottom: 30px;
            backdrop-filter: blur(10px);
        }
        .games-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        .game-card {
            background: rgba(255,255,255,0.15);
            border-radius: 15px;
            padding: 20px;
            text-align: center;
            backdrop-filter: blur(10px);
            transition: transform 0.3s ease, box-shadow 0.3s ease;
            border: 1px solid rgba(255,255,255,0.2);
        }
        .game-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 10px 25px rgba(0,0,0,0.3);
        }
        .game-card h3 {
            margin-top: 0;
            font-size: 1.5em;
        }
        .game-button {
            background: linear-gradient(45deg, #ff6b6b, #ee5a24);
            border: none;
            border-radius: 25px;
            padding: 12px 25px;
            color: white;
            font-size: 16px;
            font-weight: bold;
            cursor: pointer;
            transition: all 0.3s ease;
            margin: 5px;
        }
        .game-button:hover {
            transform: scale(1.05);
            box-shadow: 0 5px 15px rgba(0,0,0,0.3);
        }
        .game-button:active {
            transform: scale(0.95);
        }
        .basic-button {
            background: linear-gradient(45deg, #4ecdc4, #44a08d);
        }
        .enhanced-button {
            background: linear-gradient(45deg, #f093fb, #f5576c);
        }
        .ultimate-button {
            background: linear-gradient(45deg, #ffd89b, #19547b);
            font-size: 18px;
            padding: 15px 30px;
        }
        .log-panel {
            background: rgba(0,0,0,0.3);
            border-radius: 15px;
            padding: 20px;
            height: 200px;
            overflow-y: scroll;
            font-family: monospace;
            font-size: 14px;
        }
        .emergency-stop {
            background: linear-gradient(45deg, #e74c3c, #c0392b) !important;
            font-size: 20px;
            padding: 15px 30px;
            width: 100%;
            margin-bottom: 20px;
        }
        .status-good { color: #2ecc71; }
        .status-busy { color: #f39c12; }
        .status-error { color: #e74c3c; }
        .emoji { font-size: 1.5em; margin-right: 10px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🤖 Reachy Mini Entertainment System 🎪</h1>
            <p>Welcome to the most fun robot in the world!</p>
        </div>

        <div class="status-panel">
            <h2>🔧 System Status</h2>
            <p><strong>Current Activity:</strong> <span id="current-activity">{{ current_activity }}</span></p>
            <p><strong>Status:</strong> <span id="activity-status" class="status-good">{{ activity_status }}</span></p>
            <button class="game-button emergency-stop" onclick="emergencyStop()">
                🛑 EMERGENCY STOP
            </button>
        </div>

        <div class="games-grid">
            <!-- Basic Behaviors -->
            <div class="game-card">
                <h3>🌟 Basic Behaviors</h3>
                <p>Simple and classic robot moves</p>
                <button class="game-button basic-button" onclick="runActivity('wake')">
                    <span class="emoji">☀️</span>Wake Up
                </button>
                <button class="game-button basic-button" onclick="runActivity('wave')">
                    <span class="emoji">👋</span>Wave Hello
                </button>
                <button class="game-button basic-button" onclick="runActivity('dance')">
                    <span class="emoji">💃</span>Dance
                </button>
                <button class="game-button basic-button" onclick="runActivity('sleep')">
                    <span class="emoji">😴</span>Sleep
                </button>
            </div>

            <!-- Vision Games -->
            <div class="game-card">
                <h3>👁️ Vision Games</h3>
                <p>Interactive games using camera vision</p>
                <button class="game-button enhanced-button" onclick="runActivity('object_hunt')">
                    <span class="emoji">🔍</span>Object Hunt
                </button>
                <button class="game-button enhanced-button" onclick="runActivity('simon_vision')">
                    <span class="emoji">🎮</span>Simon Says
                </button>
                <button class="game-button enhanced-button" onclick="runActivity('colors')">
                    <span class="emoji">🎨</span>Color Game
                </button>
                <button class="game-button enhanced-button" onclick="runActivity('dance_detect')">
                    <span class="emoji">🕺</span>Dance Together
                </button>
            </div>

            <!-- AI Conversations -->
            <div class="game-card">
                <h3>🧠 AI Conversations</h3>
                <p>Smart talks and storytelling</p>
                <button class="game-button enhanced-button" onclick="runActivity('chat_kids')">
                    <span class="emoji">🧒</span>Chat with Kids
                </button>
                <button class="game-button enhanced-button" onclick="runActivity('chat_adults')">
                    <span class="emoji">👥</span>Chat with Adults
                </button>
                <button class="game-button enhanced-button" onclick="runActivity('story')">
                    <span class="emoji">📚</span>Tell Story
                </button>
            </div>

            <!-- Random Fun -->
            <div class="game-card">
                <h3>🎲 Random Fun</h3>
                <p>Let Reachy surprise you!</p>
                <button class="game-button enhanced-button" onclick="runActivity('random_enhanced')">
                    <span class="emoji">🎲</span>Random Game
                </button>
                <button class="game-button enhanced-button" onclick="runActivity('emotions')">
                    <span class="emoji">😊</span>Emotion Mirror
                </button>
                <button class="game-button ultimate-button" onclick="runActivity('ultimate')">
                    <span class="emoji">🎊</span>ULTIMATE SESSION
                </button>
            </div>
        </div>

        <div class="log-panel">
            <h3>📋 Activity Log</h3>
            <div id="activity-log">
                <p>System ready! Choose an activity to start the fun! 🚀</p>
            </div>
        </div>
    </div>

    <script>
        let logCount = 0;
        
        function updateStatus() {
            fetch('/status')
                .then(response => response.json())
                .then(data => {
                    document.getElementById('current-activity').textContent = data.current_activity;
                    const statusElement = document.getElementById('activity-status');
                    statusElement.textContent = data.activity_status;
                    
                    // Update status color
                    statusElement.className = '';
                    if (data.activity_status === 'Running') {
                        statusElement.classList.add('status-busy');
                    } else if (data.activity_status === 'Error') {
                        statusElement.classList.add('status-error');
                    } else {
                        statusElement.classList.add('status-good');
                    }
                    
                    // Update log if there are new messages
                    if (data.logs && data.logs.length > 0) {
                        const logDiv = document.getElementById('activity-log');
                        data.logs.forEach(log => {
                            const p = document.createElement('p');
                            p.textContent = log;
                            logDiv.appendChild(p);
                        });
                        logDiv.scrollTop = logDiv.scrollHeight;
                    }
                })
                .catch(err => console.error('Status update failed:', err));
        }
        
        function runActivity(activity) {
            addLog(`🚀 Starting ${activity}...`);
            
            fetch('/run', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({activity: activity})
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    addLog(`✅ ${activity} started successfully!`);
                } else {
                    addLog(`❌ Failed to start ${activity}: ${data.error}`);
                }
            })
            .catch(err => {
                addLog(`💥 Error running ${activity}: ${err}`);
            });
        }
        
        function emergencyStop() {
            addLog('🛑 EMERGENCY STOP ACTIVATED!');
            
            fetch('/emergency_stop', {method: 'POST'})
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        addLog('✅ Emergency stop successful');
                    } else {
                        addLog('❌ Emergency stop failed');
                    }
                })
                .catch(err => addLog(`💥 Emergency stop error: ${err}`));
        }
        
        function addLog(message) {
            const logDiv = document.getElementById('activity-log');
            const p = document.createElement('p');
            const timestamp = new Date().toLocaleTimeString();
            p.textContent = `[${timestamp}] ${message}`;
            logDiv.appendChild(p);
            logDiv.scrollTop = logDiv.scrollHeight;
        }
        
        // Update status every 2 seconds
        setInterval(updateStatus, 2000);
        updateStatus(); // Initial update
    </script>
</body>
</html>
    """
    
    with open(templates_dir / "index.html", "w") as f:
        f.write(template_html)

@app.route('/')
def index():
    """Main interface page"""
    return render_template('index.html', 
                         current_activity=current_activity,
                         activity_status=activity_status)

@app.route('/status')
def status():
    """Get current system status"""
    global entertainment_system, current_activity, activity_status
    
    logs = []  # Could implement log collection here
    
    return jsonify({
        'current_activity': current_activity,
        'activity_status': activity_status,
        'system_ready': entertainment_system is not None,
        'logs': logs
    })

@app.route('/run', methods=['POST'])
def run_activity():
    """Run a specific entertainment activity"""
    global entertainment_system, current_activity, activity_status
    
    try:
        data = request.json
        activity = data.get('activity')
        
        if not entertainment_system:
            return jsonify({'success': False, 'error': 'System not initialized'})
        
        current_activity = activity
        activity_status = "Running"
        
        # Map activity names to methods
        activity_map = {
            # Basic behaviors
            'wake': entertainment_system.controller.wake_up,
            'sleep': entertainment_system.controller.go_to_sleep,
            'wave': entertainment_system.controller.wave_hello,
            'dance': entertainment_system.controller.dance_simple,
            
            # Enhanced games
            'object_hunt': entertainment_system.object_hunt_game,
            'simon_vision': entertainment_system.simon_says_vision,
            'colors': entertainment_system.color_recognition_game,
            'chat_kids': lambda: entertainment_system.smart_conversation("kids"),
            'chat_adults': lambda: entertainment_system.smart_conversation("adults"),
            'story': entertainment_system.ai_storytelling,
            'dance_detect': entertainment_system.dance_along_with_detection,
            'emotions': entertainment_system.emotion_mirroring_game,
            'random_enhanced': entertainment_system.play_random_enhanced_game,
            'ultimate': entertainment_system.ultimate_entertainment_session
        }
        
        activity_func = activity_map.get(activity)
        if not activity_func:
            activity_status = "Error"
            return jsonify({'success': False, 'error': f'Unknown activity: {activity}'})
        
        # Run activity in background thread
        def run_bg():
            global activity_status, current_activity
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                result = loop.run_until_complete(activity_func())
                activity_status = "Completed" if result else "Failed"
                current_activity = "None"
                loop.close()
            except Exception as e:
                logging.error(f"Activity {activity} failed: {e}")
                activity_status = "Error"
                current_activity = "None"
        
        thread = Thread(target=run_bg, daemon=True)
        thread.start()
        
        return jsonify({'success': True})
        
    except Exception as e:
        logging.error(f"Run activity error: {e}")
        activity_status = "Error"
        return jsonify({'success': False, 'error': str(e)})

@app.route('/emergency_stop', methods=['POST'])
def emergency_stop():
    """Emergency stop all activities"""
    global entertainment_system, current_activity, activity_status
    
    try:
        if entertainment_system:
            # Run emergency stop in background
            def stop_bg():
                global activity_status, current_activity
                try:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    loop.run_until_complete(entertainment_system.controller.emergency_stop())
                    activity_status = "Stopped"
                    current_activity = "None"
                    loop.close()
                except Exception as e:
                    logging.error(f"Emergency stop failed: {e}")
                    activity_status = "Error"
            
            thread = Thread(target=stop_bg, daemon=True)
            thread.start()
            
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'error': 'System not initialized'})
            
    except Exception as e:
        logging.error(f"Emergency stop error: {e}")
        return jsonify({'success': False, 'error': str(e)})

async def init_system():
    """Initialize the entertainment system"""
    global entertainment_system, activity_status
    
    try:
        entertainment_system = EnhancedEntertainmentSystem(use_simulation=True)
        await entertainment_system.initialize()
        activity_status = "Ready"
        logging.info("Entertainment system initialized successfully!")
    except Exception as e:
        logging.error(f"Failed to initialize entertainment system: {e}")
        activity_status = "Error"

def main():
    """Run the web interface"""
    logging.info("🎪 Starting Reachy Mini Entertainment Web Interface!")
    
    # Create templates
    create_templates()
    
    # Initialize system
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(init_system())
    loop.close()
    
    # Start web server
    logging.info("🌐 Web interface available at: http://localhost:8080")
    logging.info("🎮 Use the web interface to control Reachy's entertainment features!")
    
    app.run(host='0.0.0.0', port=8080, debug=False, threaded=True)

if __name__ == "__main__":
    main()