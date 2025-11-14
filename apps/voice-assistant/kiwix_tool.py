"""Kiwix ZIM search tool for offline Wikipedia access"""

import asyncio
import logging
import re
import socket
from typing import Optional
from urllib.parse import quote
from urllib.request import urlopen

from livekit.agents.llm import function_tool
from livekit.agents.voice import RunContext
from pydantic import Field, Annotated

logger = logging.getLogger("jetson-orin-nano-field-kit-voice-assistant")

# Kiwix configuration
KIWIX_PORT = 8080
KIWIX_HOST = "box.local"  # or "localhost" if running locally
MAX_OUTPUT_LENGTH = 2000  # characters


def check_port_available(host: str, port: int, timeout: float = 1.0) -> bool:
    """Check if a port is available/accessible"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except Exception:
        return False


def is_kiwix_available() -> bool:
    """Check if Kiwix service is available on the configured port"""
    return check_port_available(KIWIX_HOST, KIWIX_PORT)


def create_kiwix_search_tool():
    """
    Create the Kiwix search tool function.
    This should be added as a method to the agent class if Kiwix is available.
    
    Returns:
        Function for Kiwix search, or None if service is unavailable
    """
    if not is_kiwix_available():
        logger.info(f"Kiwix service not available on {KIWIX_HOST}:{KIWIX_PORT}")
        return None
    
    logger.info(f"Kiwix service detected on {KIWIX_HOST}:{KIWIX_PORT}")
    
    async def search_kiwix_impl(
        context: RunContext,
        query: Annotated[str, Field(description="The search query to look up in Kiwix Wikipedia")]
    ) -> str:
        """
        Search the local Kiwix Wikipedia instance for information.
        Kiwix provides offline access to Wikipedia-like content.
        
        Args:
            query: The search term or question to look up (e.g., 'pizza', 'quantum physics', 'London')
        """
        # LED: Yellow - Processing
        # TODO: GPIO.set_led_color("yellow")
        
        logger.info(f"Kiwix search request: {query}")
        
        try:
            # Construct the search URL
            search_url = f"http://{KIWIX_HOST}:{KIWIX_PORT}/search?pattern={quote(query)}"
            
            # Make the HTTP request with timeout
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: urlopen(search_url, timeout=10).read().decode('utf-8')
            )
            
            # Parse and extract relevant information from the HTML response
            # Kiwix returns HTML, so we need to extract text content
            # Remove HTML tags and get text content
            text_content = re.sub(r'<[^>]+>', ' ', response)
            # Clean up whitespace
            text_content = ' '.join(text_content.split())
            
            # Truncate if too long
            if len(text_content) > MAX_OUTPUT_LENGTH:
                text_content = text_content[:MAX_OUTPUT_LENGTH] + "... (truncated)"
            
            if not text_content or len(text_content.strip()) < 10:
                return f"No results found for '{query}' in Kiwix Wikipedia."
            
            logger.info("Kiwix search completed successfully")
            
            # LED: Green - Success
            # TODO: GPIO.set_led_color("green")
            await asyncio.sleep(0.1)
            # LED: Green - Stay active
            # TODO: GPIO.set_led_color("green")
            
            return text_content
            
        except Exception as e:
            logger.error(f"Error searching Kiwix: {e}")
            # LED: Red - Error
            # TODO: GPIO.set_led_color("red")   
            await asyncio.sleep(0.5)
            # LED: Green - Stay active
            # TODO: GPIO.set_led_color("green")
            
            return f"Error searching Kiwix: {str(e)}"
    
    # Decorate with function_tool to make it a tool
    return function_tool()(search_kiwix_impl)

