# 🎪 Reachy Mini Entertainment System 🤖

A comprehensive, AI-powered entertainment system for the Reachy Mini robot that will keep kids and adults entertained for hours! This system combines robot movements, vision-based games, AI conversations, and interactive storytelling.

## 🌟 Features

### 🎮 Interactive Games
- **Object Hunt**: Find specific objects using computer vision
- **Simon Says**: Motion-detection enhanced Simon Says game  
- **Color Recognition**: Identify and react to different colors
- **Dance Together**: Interactive dance party with motion detection
- **Emotion Mirroring**: Mirror facial expressions and emotions

### 🧠 AI-Powered Features  
- **Smart Conversations**: Age-appropriate chats with kids and adults
- **Interactive Storytelling**: AI-generated stories with emotional expressions
- **Contextual Responses**: Intelligent reactions based on the situation

### 🤖 Classic Robot Behaviors
- **Wake Up/Sleep**: Smooth transitions between active and rest states
- **Wave Hello**: Friendly greeting gestures
- **Dance Moves**: Various dance routines and movements
- **Emotional Expressions**: Happy, curious, shy, excited states
- **Attention Getting**: Get attention when audience is distracted

### 🎪 Specialized Entertainment
- **Kids Entertainment**: Peek-a-boo, counting games, follow-the-leader
- **Audience Shows**: Crowd-pleasing dances, robot introductions, interactive mirroring
- **Ultimate Sessions**: Full multi-activity entertainment experiences

## 🚀 Quick Start

### Option 1: Command Line Interface

```bash
# Install dependencies (if needed)
pip install flask scipy

# Run basic behaviors
python entertainment_controller.py --sim wave
python entertainment_controller.py --sim dance
python entertainment_controller.py --sim random

# Run enhanced system  
python enhanced_entertainment.py --sim object_hunt
python enhanced_entertainment.py --sim simon_vision
python enhanced_entertainment.py --sim story
python enhanced_entertainment.py --sim ultimate
```

### Option 2: Web Interface (Recommended!)

```bash
# Start the web interface
python entertainment_web.py

# Open browser to http://localhost:8080
# Click buttons to control Reachy's entertainment features!
```

### Option 3: Interactive Mode

```bash
# Interactive command prompt
python entertainment_controller.py --sim
# or 
python enhanced_entertainment.py --sim

# Then type commands like:
# - wake, sleep, wave, dance
# - object_hunt, colors, story
# - ultimate, random_enhanced
```

## 🎯 Available Activities

### 🟢 Basic Activities
| Command | Description | Duration |
|---------|-------------|----------|
| `wake` | Wake up with friendly greeting | 2s |
| `wave` | Wave hello gesture | 3s |
| `dance` | Simple dance routine | 6s |
| `sleep` | Go to sleep peacefully | 2s |
| `random` | Random basic behavior | Varies |

### 🔵 Enhanced Games  
| Command | Description | Duration |
|---------|-------------|----------|
| `object_hunt` | Find specific objects in view | 15s |
| `simon_vision` | Motion-enhanced Simon Says | 60s |
| `colors` | Identify and react to colors | 20s |
| `dance_detect` | Interactive dance party | 45s |
| `emotions` | Mirror emotional expressions | 30s |

### 🟡 AI Features
| Command | Description | Duration |
|---------|-------------|----------|
| `chat_kids` | Kid-friendly conversation | 30s |
| `chat_adults` | Adult-appropriate chat | 30s |
| `story` | Interactive storytelling | 45s |
| `random_enhanced` | Random advanced activity | Varies |

### 🔴 Ultimate Experience  
| Command | Description | Duration |
|---------|-------------|----------|
| `ultimate` | Full entertainment session | 5+ min |

## 🛠️ Technical Details

### System Architecture
```
enhanced_entertainment.py          # Main enhanced system
├── entertainment_controller.py    # Core robot control  
├── entertainment_behaviors.py     # Specialized behaviors
├── entertainment_web.py          # Web interface
└── simple_web_interface.py      # Alternative web UI
```

### Dependencies
- **reachy-mini**: Robot SDK
- **opencv-python**: Computer vision
- **scipy**: Mathematical functions
- **numpy**: Array processing
- **flask**: Web interface
- **asyncio**: Async programming

### Vision System
- Supports both real camera and simulation mode
- Simple OpenCV-based motion detection
- Color analysis and object recognition simulation
- Fallback to simulation if no camera available

### AI Integration
- Mock Ollama integration (easily replaceable with real API)
- Context-aware responses based on audience type
- Story generation with thematic variations
- Extensible conversation system

## 🎨 Customization

### Adding New Games
```python
async def my_custom_game(self) -> bool:
    """Custom entertainment activity"""
    self.logger.info("🎮 Starting my custom game!")
    
    # Your custom robot movements here
    await self.controller.wave_hello()
    await self.controller.dance_simple()
    
    return True

# Add to activity map in enhanced_entertainment.py
```

### Modifying Behaviors
Edit `entertainment_behaviors.py` to customize:
- Movement patterns and timings
- Emotional expressions
- Game rules and responses
- Animation sequences

### Web Interface Styling
Modify `entertainment_web.py` template section to customize:
- Colors and styling
- Button layouts
- Status displays
- Activity descriptions

## 🔧 Configuration

### Simulation vs Real Robot
```python
# Simulation mode (default)
system = EnhancedEntertainmentSystem(use_simulation=True)

# Real robot mode (requires Reachy Mini connection)
system = EnhancedEntertainmentSystem(use_simulation=False)
```

### Camera Settings
```python
# Enable camera features
vision = VisionGamesHandler(use_camera=True)

# Disable camera (simulation only)
vision = VisionGamesHandler(use_camera=False)
```

### Web Interface Port
```python
# Change port in entertainment_web.py
app.run(host='0.0.0.0', port=8080)  # Current setting
```

## 🏃‍♂️ Performance Tips

1. **Simulation Mode**: Faster for testing, no robot required
2. **Camera Disable**: Skip camera initialization if not needed
3. **Background Tasks**: Web interface runs activities in separate threads
4. **Emergency Stop**: Always available for safety
5. **Memory Management**: Automatic cleanup after activities

## 🎪 Entertainment Strategies

### For Kids (5-12 years)
- Start with `peek_a_boo` or `wave`
- Use `simon_vision` for interactive play
- Try `object_hunt` to get them moving
- End with `dance_detect` for high energy

### For Adults & Demos
- Begin with `robot_introduction`  
- Show off `colors` and `story` features
- Demonstrate `chat_adults` capability
- Finish with `ultimate` session

### Mixed Audiences
- Use `attention_getter` to gather everyone
- Run `random_enhanced` for variety
- Try `ultimate` for comprehensive show
- Emergency stop available if needed

## 🐛 Troubleshooting

### Common Issues

**"No robot connected"**: 
- Check `use_simulation=True` for testing
- Verify Reachy Mini is powered and connected

**"Camera not found"**:
- System automatically falls back to simulation
- Check `/dev/video0` exists on Linux systems

**"Web interface not loading"**:
- Try different port (8080, 3000, 8000)
- Check firewall settings
- Verify Flask installation

**"Activity seems stuck"**:
- Use emergency stop button/command
- Check logs for error messages
- Restart the system if needed

### Debug Mode
```bash
# Enable detailed logging
python enhanced_entertainment.py --sim story
# Watch the console output for detailed activity logs
```

## 🎉 Fun Facts

- 🎮 **15+ interactive games** and activities
- 🤖 **30+ unique robot movements** and expressions  
- 👀 **Computer vision integration** for interactive play
- 🧠 **AI conversation system** with context awareness
- 🎪 **Ultimate session** combines multiple activities
- 🌐 **Beautiful web interface** for easy control
- ⚡ **Real-time feedback** and status updates
- 🛡️ **Emergency stop** safety feature
- 📱 **Mobile-friendly** responsive design
- 🎨 **Customizable** and extensible architecture

## 🚀 Next Steps

Want to extend the system? Try:
- Integrating real Ollama API for advanced AI chat
- Adding real computer vision models (YOLO, etc.)
- Creating custom dance choreographies  
- Building mobile app interface
- Adding voice recognition commands
- Creating multiplayer games
- Adding music and sound effects

## 🎊 Have Fun!

This entertainment system is designed to bring joy and wonder to everyone who interacts with Reachy Mini. Whether you're entertaining kids, wowing adults, or just having fun with robotics, there's something here for everyone!

**Remember**: The goal is to have fun and create amazing experiences. Don't be afraid to experiment, customize, and create your own entertainment activities!

---

*🤖 Built with love for the Reachy Mini community! 🎪*