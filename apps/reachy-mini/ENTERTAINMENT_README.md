# Reachy Mini Entertainment System

A simplified entertainment control system designed to keep kids and audiences entertained using the Reachy Mini robot.

## Features

### 🧸 Kid-Friendly Games
Perfect for engaging children with interactive and educational behaviors:

- **Peek-a-Boo** - Classic hide-and-seek game with expressive movements
- **Follow the Leader** - Robot demonstrates movements for kids to copy
- **Count 1-5** - Educational counting game with distinct poses for each number
- **Simon Says Demo** - Demonstrates proper Simon Says gameplay
- **Story Faces** - Shows different emotions for storytelling (happy, sad, surprised, etc.)
- **Hey Look!** - Attention-getting behavior when kids get distracted

### 🎭 Audience Entertainment  
Engaging performances for crowds and general audiences:

- **Robot Introduction** - Friendly self-introduction with waves and bows
- **Crowd Pleaser Dance** - Upbeat dance routine with varied movements
- **Mirror Game** - Interactive behavior that mimics audience movements

### 🤖 Basic Behaviors
Core robot interactions suitable for all ages:

- **Wake Up** - Energetic startup routine
- **Wave Hello** - Friendly greeting gesture
- **Nod Yes/Shake No** - Response gestures
- **Look Around** - Curious environmental exploration
- **Simple Dance** - Basic rhythmic movements
- **Be Shy** - Cute bashful behavior
- **Go to Sleep** - Gentle shutdown routine

## Quick Start

### Command Line Interface
```bash
# Run in simulation mode (no robot required)
python entertainment_controller.py --sim

# Run with real robot
python entertainment_controller.py

# Execute specific behavior
python entertainment_controller.py wave
python entertainment_controller.py peek_a_boo
```

### Web Interface
```bash
# Start web interface (default port 8090)
python simple_web_interface.py --sim

# Custom host/port
python simple_web_interface.py --host 0.0.0.0 --port 8090

# Then visit http://localhost:8090
```

### Programmatic Usage
```python
from entertainment_controller import EntertainmentController

# Create controller
controller = EntertainmentController(use_simulation=True)

# Execute behaviors
await controller.peek_a_boo()
await controller.dance_simple()
await controller.attention_getter()

# Emergency stop
await controller.emergency_stop()
```

## Behavior Categories

### Educational & Interactive
- **Counting Game**: Teaches numbers 1-5 with distinct movements
- **Simon Says**: Demonstrates command following vs. ignoring
- **Follow the Leader**: Encourages physical activity and mimicry

### Emotional & Expressive
- **Story Faces**: Shows 6 different emotions for storytelling
- **Peek-a-Boo**: Creates surprise and delight
- **Be Shy**: Demonstrates relatable emotions

### Performance & Entertainment
- **Crowd Pleaser Dance**: Full routine for audience engagement  
- **Robot Introduction**: Professional presentation behavior
- **Mirror Game**: Interactive audience participation

## Safety Features

- **Emergency Stop**: Immediately returns robot to neutral position
- **Movement Constraints**: All movements stay within safe joint limits
- **Timeout Protection**: Prevents runaway behaviors
- **Simulation Mode**: Full testing without hardware

## Technical Details

### Architecture
- **EntertainmentController**: Main control class with basic behaviors
- **KidFriendlyBehaviors**: Specialized games for children
- **AudienceEntertainment**: Performance behaviors for crowds
- **SimpleWebInterface**: Web-based control dashboard

### Movement Design
- Uses smooth interpolation for natural motion
- Combines head pose and antenna movements
- Incorporates realistic timing and pauses
- Expressive gestures matched to behavior context

### Emotion System
Robot tracks emotional states that influence behavior:
- **Neutral**: Default calm state
- **Happy**: Energetic positive movements  
- **Curious**: Investigative head movements
- **Excited**: Quick animated gestures
- **Sleepy**: Slow downward movements
- **Shy**: Withdrawn protective poses

## Integration with Jetson Field Kit

This entertainment system integrates seamlessly with the Jetson Orin Nano Field Kit:

- **Unique Port**: Uses port 8090 to avoid conflicts
- **Hotspot Compatible**: Works with field kit's WiFi hotspot
- **Low Resource**: Optimized for edge deployment
- **Logging**: Compatible with field kit monitoring
- **Offline Operation**: No internet required

## Customization

### Adding New Behaviors
```python
async def my_custom_behavior(self) -> bool:
    """Custom entertainment behavior"""
    try:
        if not self.use_simulation and self.robot:
            # Define custom movements
            custom_pose = np.eye(4)
            custom_pose[:3, :3] = R.from_euler('y', 20, degrees=True).as_matrix()
            
            self.robot.goto_target(
                head=custom_pose, 
                antennas=[0.5, -0.5], 
                duration=1.0
            )
            await asyncio.sleep(1.5)
        
        return True
    except Exception as e:
        self.logger.error(f"Custom behavior failed: {e}")
        return False
```

### Modifying Timing
Adjust `duration` and `await asyncio.sleep()` values to change behavior speed:
- Faster: Reduce durations for energetic feel
- Slower: Increase durations for calm interactions

### Emotion Responses
Behaviors automatically set appropriate emotional states that persist until the next behavior.

## Use Cases

### 🏫 Educational Settings
- **Math Class**: Counting game for number learning
- **Drama Class**: Story faces for emotion recognition  
- **PE Class**: Follow the leader for physical activity

### 🎪 Entertainment Venues
- **Museums**: Robot introduction for visitors
- **Parties**: Crowd pleaser dance for groups
- **Interactive Exhibits**: Mirror game for participation

### 🏠 Home Use
- **Babysitting**: Peek-a-boo and attention getter
- **Playtime**: Simon Says and follow the leader
- **Bedtime**: Gentle sleep routine

## Troubleshooting

### Robot Not Moving
- Check robot connection status in web interface
- Verify Reachy Mini is powered and connected
- Try emergency stop, then wake up

### Behaviors Not Working
- Ensure no other behavior is currently running
- Check for error messages in console output
- Restart in simulation mode to test logic

### Web Interface Issues  
- Verify port 8090 is not blocked by firewall
- Check browser developer console for errors
- Try different browser (WebRTC support needed for video)

## Performance Tips

- Use simulation mode for development and testing
- Emergency stop cancels current behavior immediately
- Random entertainment adds variety automatically
- Group similar behaviors in sequence for smooth transitions

## License

Part of the Jetson Orin Nano Field Kit project - see main LICENSE file.