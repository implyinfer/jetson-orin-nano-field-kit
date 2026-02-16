# Reachy Mini Control Dashboard

A web-based control dashboard for Reachy Mini robot with live video streaming and entertainment macros, optimized for the Jetson Orin Nano Field Kit.

## Features

- **Live Video Streaming**: WebRTC-based low-latency video stream from robot cameras
- **Entertainment Macros**: Pre-programmed gestures and movements for audience engagement
- **Safety Systems**: Built-in safety limits, emergency stop, and auto-compliance
- **Web Dashboard**: Real-time control interface accessible from any device on the network
- **System Monitoring**: Robot status, connection health, and performance metrics
- **Hotspot Integration**: Works with Jetson Field Kit's hotspot for remote access

## Quick Start

1. **Install Dependencies**
   ```bash
   cd apps/reachy-mini
   pip install -r requirements.txt
   ```

2. **Configure Environment**
   ```bash
   cp .env.example .env
   # Edit .env with your Reachy's IP address and settings
   ```

3. **Run the Application**
   ```bash
   python main.py
   ```

4. **Access Dashboard**
   - Open `http://<jetson-ip>:8080` in any browser
   - Connect to the Field Kit's hotspot for remote access

## Configuration

Key environment variables in `.env`:

- `REACHY_HOST`: IP address of your Reachy Mini (default: 192.168.1.100)
- `WEB_PORT`: Dashboard port (default: 8080)  
- `WEBRTC_PORT`: Video streaming port (default: 8081)
- `SAFETY_LIMITS`: Enable safety systems (default: true)
- `ENABLE_MACROS`: Allow entertainment macros (default: true)

## Entertainment Macros

Available audience-friendly gestures:

- **Wave**: Friendly greeting gesture
- **Dance**: Simple rhythmic movement sequence
- **Look Around**: Curious head movements
- **Nod**: Affirmative head gesture  
- **Shake Head**: Negative head gesture
- **Point**: Directional pointing gesture
- **Celebrate**: Victory celebration with raised arms

## Safety Features

- **Joint Limits**: Configurable velocity and torque limits
- **Emergency Stop**: Immediate halt of all movements
- **Auto-Compliance**: Automatic relaxation during inactivity
- **Timeout Protection**: Prevents runaway motions
- **Connection Monitoring**: Graceful handling of network issues

## WebRTC Streaming

- **Low Latency**: ~50ms typical latency for local network
- **Hardware Acceleration**: Uses Jetson's video encoders when available
- **Multiple Viewers**: Supports multiple simultaneous connections
- **Adaptive Quality**: Adjusts to network conditions

## API Endpoints

- `GET /`: Main dashboard interface
- `GET /api/status`: System and robot status
- `POST /api/macro`: Execute entertainment macro
- `POST /api/webrtc/offer`: WebRTC connection setup
- `WS /ws`: Real-time WebSocket communication

## Development

For development mode:

```bash
# Enable debug mode in .env
DEBUG=true

# Run with hot reload
uvicorn main:app --reload --host 0.0.0.0 --port 8080
```

## Integration with Field Kit

This app integrates with the Jetson Orin Nano Field Kit infrastructure:

- Uses unique ports to avoid conflicts with other services
- Supports the field kit's hotspot for remote access
- Follows the project's logging and monitoring patterns
- Compatible with the existing MediaMTX setup if needed

## Troubleshooting

**Robot Connection Issues:**
- Verify Reachy is powered on and connected to network
- Check IP address in `.env` file
- Ensure firewall allows connections on port 50051

**Video Stream Issues:**
- Verify camera device index in `.env`
- Check camera permissions and hardware connection
- Try different video resolution/format settings

**Web Dashboard Issues:**
- Ensure port 8080 is not blocked by firewall
- Check browser console for JavaScript errors
- Try different browsers (WebRTC support required)

## Hardware Requirements

- NVIDIA Jetson Orin Nano (or compatible)
- USB camera or Reachy's built-in cameras
- Network connection to Reachy Mini
- Sufficient power supply for sustained operation

## License

Part of the Jetson Orin Nano Field Kit project - see main LICENSE file.