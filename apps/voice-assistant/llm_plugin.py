"""LLM (Large Language Model) plugin implementations"""

import logging
import os

from livekit.plugins import openai

logger = logging.getLogger("jetson-orin-nano-field-kit-voice-assistant")


def get_llm_plugin(use_local: bool = False):
    """
    Get the appropriate LLM plugin based on availability.
    
    Args:
        use_local: If True, force use of local model even if cloud is available
    
    Returns:
        LLM plugin instance or string identifier
    """
    if use_local:
        logger.info("Using local Ollama LLM")
        return openai.LLM.with_ollama(
            model="qwen3:1.7b",
            base_url="http://localhost:11434/v1"
        )

    return "openai/gpt-4.1-mini"

