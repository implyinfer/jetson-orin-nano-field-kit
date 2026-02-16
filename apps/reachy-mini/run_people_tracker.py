#!/usr/bin/env python3
"""
Reachy Mini People Tracker Launcher
Simplified launcher script with built-in configuration and status monitoring
"""

import asyncio
import logging
import os
import sys
from pathlib import Path

# Add current directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

try:
    from people_tracker import ReachyPeopleTracker, Settings
except ImportError as e:
    print(f"Failed to import people_tracker: {e}")
    print("Make sure to install requirements:")
    print("  source venv/bin/activate")
    print("  pip install -r requirements.txt")
    sys.exit(1)


def setup_logging():
    """Setup logging configuration"""
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    logging.basicConfig(
        level=logging.INFO,
        format=log_format,
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler("logs/people_tracker.log")
        ]
    )


def print_banner():
    """Print startup banner"""
    banner = """
    ╔══════════════════════════════════════════════════════════╗
    ║               Reachy Mini People Tracker                ║
    ║          Detects people and makes Reachy greet them     ║
    ╚══════════════════════════════════════════════════════════╝
    """
    print(banner)


def print_usage():
    """Print usage instructions"""
    usage = """
    Usage:
    ------
    python run_people_tracker.py [options]
    
    Options:
        --help, -h          Show this help message
        --config, -c FILE   Use custom configuration file
        --debug, -d         Enable debug logging
        --no-display        Run without video display window
        --simulate          Run in simulation mode (no Reachy connection)
    
    Controls (when display window is active):
        Q                   Quit application  
        R                   Reset person tracking
        N                   Return Reachy head to neutral position
        SPACE               Pause/unpause detection
    
    Environment Variables:
        REACHY_HOST         Reachy robot IP address (default: 192.168.1.100)
        ROBOFLOW_HOST       Roboflow service host (default: localhost)
        ROBOFLOW_PORT       Roboflow service port (default: 9001)
        CAMERA_DEVICE       Camera device index (default: 0)
    
    Example:
        # Basic usage
        python run_people_tracker.py
        
        # With custom Reachy IP
        REACHY_HOST=192.168.1.150 python run_people_tracker.py
        
        # Debug mode with simulation
        python run_people_tracker.py --debug --simulate
    """
    print(usage)


def check_dependencies():
    """Check if required services are available"""
    import requests
    import socket
    
    issues = []
    
    # Check Roboflow inference service
    try:
        response = requests.get("http://localhost:9001/health", timeout=3)
        if response.status_code != 200:
            issues.append("Roboflow inference service not responding correctly")
    except requests.exceptions.RequestException:
        issues.append("Roboflow inference service not accessible on port 9001")
    
    # Check Reachy connection (if not in simulation)
    reachy_host = os.getenv("REACHY_HOST", "192.168.1.100")
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(3)
        result = sock.connect_ex((reachy_host, 50051))
        sock.close()
        if result != 0:
            issues.append(f"Cannot connect to Reachy at {reachy_host}:50051")
    except Exception:
        issues.append(f"Failed to check Reachy connection at {reachy_host}")
    
    return issues


async def main():
    """Main application"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Reachy Mini People Tracker")
    parser.add_argument("--config", "-c", help="Configuration file path")
    parser.add_argument("--debug", "-d", action="store_true", help="Enable debug logging")
    parser.add_argument("--no-display", action="store_true", help="Run without display window")
    parser.add_argument("--simulate", action="store_true", help="Simulation mode")
    parser.add_argument("--help-extended", action="store_true", help="Show extended help")
    
    args = parser.parse_args()
    
    if args.help_extended:
        print_usage()
        return
    
    print_banner()
    
    # Setup logging
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
    
    setup_logging()
    logger = logging.getLogger(__name__)
    
    # Create logs directory
    Path("logs").mkdir(exist_ok=True)
    
    logger.info("Starting Reachy Mini People Tracker")
    
    # Check dependencies
    logger.info("Checking system dependencies...")
    issues = check_dependencies()
    
    if issues and not args.simulate:
        logger.warning("Dependency issues detected:")
        for issue in issues:
            logger.warning(f"  - {issue}")
        
        response = input("Continue anyway? (y/N): ")
        if response.lower() != 'y':
            logger.info("Exiting due to dependency issues")
            return
    
    # Load configuration
    try:
        if args.config:
            os.environ['ENV_FILE'] = args.config
        
        settings = Settings()
        logger.info("Configuration loaded successfully")
        
    except Exception as e:
        logger.error(f"Failed to load configuration: {e}")
        return
    
    # Override settings for command line options
    if args.simulate:
        settings.reachy_host = "simulation"  # Will cause connection to fail gracefully
        logger.info("Running in simulation mode")
    
    # Display configuration
    logger.info("Current configuration:")
    logger.info(f"  Reachy: {settings.reachy_host}:{settings.reachy_port}")
    logger.info(f"  Roboflow: {settings.roboflow_host}:{settings.roboflow_port}")
    logger.info(f"  Camera: device {settings.camera_device} ({settings.camera_width}x{settings.camera_height})")
    logger.info(f"  Detection: {settings.confidence_threshold} confidence, {settings.detection_interval}s interval")
    
    # Create and run tracker
    try:
        tracker = ReachyPeopleTracker(settings)
        
        if args.no_display:
            # Modify tracker to not show display
            import cv2
            original_imshow = cv2.imshow
            cv2.imshow = lambda *args: None  # Disable display
        
        logger.info("People tracker started - monitoring for people...")
        logger.info("Press Ctrl+C to stop")
        
        await tracker.run()
        
    except KeyboardInterrupt:
        logger.info("Shutdown requested by user")
    except Exception as e:
        logger.error(f"Application error: {e}", exc_info=True)
    finally:
        logger.info("People tracker stopped")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nShutdown complete")
    except Exception as e:
        print(f"Fatal error: {e}")
        sys.exit(1)