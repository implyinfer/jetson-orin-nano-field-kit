"""Utility functions for the voice assistant"""

import logging
import os
import socket
from typing import Tuple

logger = logging.getLogger("jetson-orin-nano-field-kit-voice-assistant")


def check_internet_connectivity(timeout: int = 3) -> bool:
    """
    Check if internet connectivity is available.
    
    Args:
        timeout: Timeout in seconds for the connection attempt
    
    Returns:
        True if internet is available, False otherwise
    """
    try:
        # Try to connect to a reliable DNS server
        socket.create_connection(("8.8.8.8", 53), timeout=timeout)
        return True
    except OSError:
        try:
            # Fallback: try Google's DNS
            socket.create_connection(("1.1.1.1", 53), timeout=timeout)
            return True
        except OSError:
            return False


def check_api_availability() -> Tuple[bool, bool]:
    """
    Check if cloud API services are available.
    
    Returns:
        Tuple of (has_stt_api, has_tts_api)
    """
    has_stt = bool(os.getenv("ASSEMBLYAI_API_KEY"))
    has_tts = bool(os.getenv("CARTESIA_API_KEY"))
    
    return has_stt, has_tts


def should_use_local_models() -> Tuple[bool, str]:
    """
    Determine if local models should be used.
    
    Returns:
        Tuple of (use_local, reason)
    """
    has_internet = check_internet_connectivity()
    has_stt_api, has_tts_api = check_api_availability()
    
    if not has_internet:
        return True, "No internet connectivity available"
    
    if not (has_stt_api or has_tts_api):
        return True, "No cloud API keys configured"
    
    # Check for LiveKit URL and keys
    livekit_url = os.getenv("LIVEKIT_URL")
    livekit_api_key = os.getenv("LIVEKIT_API_KEY")
    livekit_api_secret = os.getenv("LIVEKIT_API_SECRET")
    
    if not (livekit_url and livekit_api_key and livekit_api_secret):
        return True, "LiveKit credentials not configured"
    
    return False, "Cloud services available"

