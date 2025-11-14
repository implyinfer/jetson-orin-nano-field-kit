"""
---
title: Jetson Orin Nano Assistant
category: hardware
tags: [jetson, wake-word, tool-calling, linux-commands, gpio-leds]
difficulty: advanced
description: A comprehensive voice assistant for Jetson Orin Nano with wake word, tool calling, and safe Linux command execution
demonstrates:
  - Wake word detection for privacy
  - Safe Linux command execution with whitelisting
  - System information tools
  - LED status indicators via GPIO
  - Conversational best practices
---
"""

import asyncio
import logging
import os
import re
import shlex
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import AsyncIterable, Optional, Annotated, Tuple

from dotenv import load_dotenv
from pydantic import Field
from livekit import rtc
from livekit.agents import JobContext, WorkerOptions, cli
from livekit.agents.llm import function_tool
from livekit.agents.voice import Agent, AgentSession, RunContext
from livekit.agents.voice.agent_activity import StopResponse
from livekit.plugins import silero

from stt_plugin import get_stt_plugin
from tts_plugin import get_tts_plugin
from llm_plugin import get_llm_plugin
from utils import should_use_local_models
from kiwix_tool import create_kiwix_search_tool, is_kiwix_available
from vision_plugin import get_vision_plugin, is_vision_available

load_dotenv(dotenv_path=Path(__file__).parent / '.env')

logger = logging.getLogger("jetson-orin-nano-field-kit-voice-assistant")
logger.setLevel(logging.INFO)

# Configuration
WAKE_WORD = os.getenv("WAKE_WORD", "nano")
MAX_COMMAND_TIMEOUT = 30  # seconds
MAX_OUTPUT_LENGTH = 2000  # characters

# Safe command whitelist - only these commands are allowed
SAFE_COMMANDS = {
    'date', 'uptime', 'whoami', 'hostname', 'uname', 'df', 'free', 'ps',
    'ls', 'pwd', 'cat', 'head', 'tail', 'grep', 'find', 'which', 'env',
    'ping', 'curl', 'ifconfig', 'ip', 'lscpu', 'nvidia-smi', 'tegrastats',
    'nmcli', 'ip link', 'ip addr', 'ip route', 'ip neigh', 'ip netns', 'ip netns list',
}

# Dangerous patterns to block
DANGEROUS_PATTERNS = [
    r'rm\s+-[rf]',  # rm -rf
    r'mkfs',  # Format commands
    r'dd\s+if=',  # Disk operations
    r'sudo\s+rm',  # sudo with rm
    r';\s*rm',  # Command chaining with rm
    r'&&\s*rm',  # Logical AND with rm
]

# Determine which models to use
use_local, local_reason = should_use_local_models()
if use_local:
    logger.info(f"Using local models: {local_reason}")
    print(f"Using local models: {local_reason}")
else:
    logger.info("Using cloud models (internet and API keys available)")
    print("Using cloud models (internet and API keys available)")

# Check if Kiwix is available
KIWIX_AVAILABLE = is_kiwix_available()
if KIWIX_AVAILABLE:
    logger.info(f"Kiwix service detected and available")
else:
    logger.info("Kiwix service not available")

# Check if vision is available
VISION_AVAILABLE = is_vision_available()
if VISION_AVAILABLE:
    logger.info("Vision capabilities available - camera detected")
else:
    logger.info("Vision capabilities not available - no camera detected")


class JetsonOrinNanoFieldKitVoiceAssistant(Agent):
    """Comprehensive voice assistant for Jetson Orin Nano"""
    
    def __init__(self) -> None:
        super().__init__(
            instructions=f"""
                You are Nano, a voice assistant running on a Jetson Orin Nano device. You interact with users through voice conversation and have access to system information, safe Linux commands, and various helpful tools.

                PERSONALITY AND COMMUNICATION STYLE:

                British Accent and Speech:
                - Speak with a natural British accent (Received Pronunciation or modern British English)
                - Maintain a warm, friendly British tone - not posh or overly formal, but naturally British

                Warmth and Wit:
                - Sound like a friend and appear to genuinely enjoy talking to the user
                - Be warm when the user actually deserves it or needs it, not when inappropriate
                - Aim to be subtly witty, humorous, and sarcastic when fitting the conversational vibe (British dry humour)
                - Never force jokes when a normal response would be more appropriate
                - Never make multiple jokes in a row unless the user reacts positively
                - Never make unoriginal jokes - always err on the side of not making a joke if it may be unoriginal
                - Find a balance that sounds natural, and never be sycophantic

                Conciseness and Directness:
                - Never output preamble or postamble
                - Never include unnecessary details when conveying information, except possibly for humor
                - Never ask the user if they want extra detail or additional tasks
                - Never say "Let me know if you need anything else"
                - Never say "Anything specific you want to know"
                - Get straight to the point - no corporate jargon or overly formal language
                - Never repeat what the user says directly back at them when acknowledging requests
                - Instead, acknowledge naturally without echoing their words

                Adaptiveness:
                - Adapt to the user's speaking style and formality level
                - Match your response length approximately to the user's input
                - If the user is chatting casually with a few words, don't send back multiple sentences unless they're asking for information
                - When the user is just chatting, do not unnecessarily offer help or explain anything - this sounds robotic
                - Use your judgement to determine when the user is not asking for information and just chatting
                - At the end of a conversation, you can say nothing when natural

                Voice-Specific Considerations:
                - Keep responses concise but informative (under 600 characters when speaking)
                - Use natural pauses and conversational flow
                - Speak naturally and conversationally, not robotically
                - For long outputs, summarize the key points verbally
                - Use natural speech patterns, not written text patterns
                - Maintain your British accent consistently throughout all interactions

                Wake word: "{WAKE_WORD}" - Users must say this before you respond. After the wake word is detected, you stay active for conversation until the user explicitly asks you to stop or there's 60 seconds of inactivity.

                AVAILABLE CAPABILITIES:
                - Get current time and date
                - Get system status (uptime, memory, disk usage)
                - Execute safe Linux commands (whitelisted commands only)
{f"                - Search local Kiwix Wikipedia (offline Wikipedia-like knowledge base)" if KIWIX_AVAILABLE else ""}
{f"                - Vision capabilities: You can see what the camera sees using the see_whats_in_front tool. When users ask questions about what's in front of them, how many people are there, what objects are visible, or any visual questions, call the see_whats_in_front tool to get a description. Never mention 'shot', 'scene', or other camera/photo terminology - just describe what you see naturally." if VISION_AVAILABLE else ""}
                - Stop listening when explicitly asked (will require wake word to reactivate)
                - Shut down the assistant service completely (will exit the process)

                IMPORTANT GUIDELINES:
                - Always confirm what you're about to do before executing commands, but do so naturally without repeating the user's exact words
                - Explain results in user-friendly terms, avoiding technical jargon when possible
                - If a command is not allowed, politely explain why without being overly apologetic
                - For long outputs, summarize the key points verbally
                - Never execute dangerous commands (rm, format, etc.)
                - Be helpful with troubleshooting and diagnostics
                - When asked about system status, use the appropriate tools
{f"                - VISION: When users ask visual questions (e.g., 'what's in front of me?', 'how many people are there?', 'what do you see?'), use the see_whats_in_front tool to get a description of what the camera sees. Answer visual questions directly using the tool result. Never mention 'shot', 'scene', 'image', 'photo', 'picture', 'frame', or other camera/photo terminology - just describe what you see naturally as if you're looking at it directly." if VISION_AVAILABLE else ""}
                - If the user explicitly asks you to stop, stop talking, go to sleep, or stop listening, use the stop_listening tool immediately
                - If the user asks to shut down, power off, or exit the service completely, use the shutdown_service tool (this will terminate the entire service)

                - Answer visual questions sarcastically making good natured fun of the user.

                HANDLING MISTAKES AND ERRORS:
                - When explaining errors or apologizing, focus on explaining WHAT went wrong from the user's perspective, not HOW it went wrong technically
                - Never reveal technical processes, tool names, or internal workflows
                - Maintain the illusion of being a single, unified entity
                - Focus on how you'll do better next time rather than technical explanations

                REMEMBER:
                - You're running on embedded hardware, so be mindful of resource usage
                - Keep responses efficient and focused
                - You're a friend helping out, not a corporate assistant
                - Sound natural, warm, and genuinely helpful without being overbearing
                - When you say numbers, say them in context of the conversation, not as a standalone number.
                - When you say accronyms or abbreviations, say them in context of the conversation, not as a standalone word.
                - Always call a tool if it's relevant.
{f"             - IMPORTANT: You are running in LOCAL-ONLY mode. Speech recognition, language model, and text-to-speech are running locally on the device, which may be slower than cloud services." if use_local else ""}
            """,
            stt=get_stt_plugin(use_local=use_local),
            llm=get_llm_plugin(use_local=use_local),
            tts=get_tts_plugin(use_local=use_local),
            vad=silero.VAD.load(),
            allow_interruptions=True
        )
        self.wake_word = WAKE_WORD.lower()
        self.wake_word_detected = False
        self.last_activity_time = None
        self.wake_word_timeout = 60  # Reset after 60 seconds of inactivity
        self.stop_requested = False  # Track if stop_listening was called
        
        # Initialize vision plugin if available
        self.vision_plugin = get_vision_plugin() if VISION_AVAILABLE else None

    async def on_enter(self) -> None:
        """Called when agent enters the session"""
        # LED: Blue - System ready, waiting for wake word
        # TODO: GPIO.set_led_color("blue")
        logger.info(f"Assistant ready. Waiting for wake word: '{self.wake_word}'")
        
        # Start camera capture if vision is available
        if self.vision_plugin:
            try:
                await self.vision_plugin.start_camera_capture()
                logger.info("Vision camera capture started")
            except Exception as e:
                logger.error(f"Error starting camera capture: {e}", exc_info=True)
        
        await self.session.say(
            f"Hello! How can I help you today?"
            # f"Say '{self.wake_word}' to wake me up."
        )

    async def on_exit(self) -> None:
        """Called when agent exits the session - cleanup resources"""
        # Stop camera capture if vision is available
        if self.vision_plugin:
            try:
                await self.vision_plugin.stop_camera_capture()
                logger.info("Vision camera capture stopped")
            except Exception as e:
                logger.error(f"Error stopping camera capture: {e}", exc_info=True)

    def stt_node(
        self, 
        audio: AsyncIterable[str], 
        model_settings: Optional[dict] = None
    ) -> Optional[AsyncIterable[rtc.AudioFrame]]:
        """Custom STT node with wake word detection"""
        parent_stream = super().stt_node(audio, model_settings)
        
        if parent_stream is None:
            return None
        
        async def process_stream():
            async for event in parent_stream:
                # If stop was requested, discard all input until wake word is detected again
                if self.stop_requested and not self.wake_word_detected:
                    # Check if wake word is in this transcript
                    if hasattr(event, 'type') and str(event.type) == "SpeechEventType.FINAL_TRANSCRIPT" and event.alternatives:
                        transcript = event.alternatives[0].text.lower()
                        cleaned_transcript = re.sub(r'[^\w\s]', '', transcript)
                        cleaned_transcript = ' '.join(cleaned_transcript.split())
                        if self.wake_word in cleaned_transcript:
                            # Wake word detected, reset stop flag
                            self.stop_requested = False
                            self.wake_word_detected = True
                            self.last_activity_time = time.time()
                            logger.info(f"Wake word detected after stop - reactivating")
                            # Extract content after wake word
                            content_after_wake_word = cleaned_transcript.split(self.wake_word, 1)[-1].strip()
                            if content_after_wake_word:
                                event.alternatives[0].text = content_after_wake_word
                                yield event
                    # Otherwise, discard the input
                    continue
                
                if hasattr(event, 'type') and str(event.type) == "SpeechEventType.FINAL_TRANSCRIPT" and event.alternatives:
                    transcript = event.alternatives[0].text.lower()
                    logger.info(f"Received transcript: '{transcript}'")
                    
                    # Clean the transcript
                    cleaned_transcript = re.sub(r'[^\w\s]', '', transcript)
                    cleaned_transcript = ' '.join(cleaned_transcript.split())
                    
                    if not self.wake_word_detected:
                        # Check for wake word
                        if self.wake_word in cleaned_transcript:
                            logger.info(f"Wake word detected: '{self.wake_word}'")
                            self.wake_word_detected = True
                            self.last_activity_time = time.time()
                            
                            # LED: Green - Wake word detected, listening
                            # TODO: GPIO.set_led_color("green")
                            
                            # Extract content after wake word
                            content_after_wake_word = cleaned_transcript.split(self.wake_word, 1)[-1].strip()
                            if content_after_wake_word:
                                event.alternatives[0].text = content_after_wake_word
                                yield event
                        # If wake word not detected, discard input
                    else:
                        # Wake word already detected, process this utterance
                        self.last_activity_time = time.time()  # Update activity time
                        yield event
                        # Don't reset wake word here - keep it active for conversation
                elif self.wake_word_detected:
                    # Pass through other event types when wake word is active
                    yield event
        
        return process_stream()

    async def on_user_turn_completed(self, chat_ctx, new_message=None):
        """Handle user turn completion with wake word check"""
        # Check if stop was requested - if so, don't process anything
        if self.stop_requested:
            logger.info("Stop was requested - not processing user input")
            self.stop_requested = False  # Reset flag
            raise StopResponse()
        
        # Check for timeout
        if self.wake_word_detected and self.last_activity_time:
            elapsed = time.time() - self.last_activity_time
            if elapsed > self.wake_word_timeout:
                logger.info(f"Wake word timeout after {elapsed:.1f} seconds of inactivity")
                self.wake_word_detected = False
                # LED: Blue - Back to waiting
                # TODO: GPIO.set_led_color("blue")
                raise StopResponse()
        
        if self.wake_word_detected:
            # LED: Yellow - Processing user request
            # TODO: GPIO.set_led_color("yellow")
            
            result = await super().on_user_turn_completed(chat_ctx, new_message)
            
            # Check if stop was requested during processing (after tool call)
            if self.stop_requested:
                logger.info("Stop was requested during processing - stopping immediately")
                self.stop_requested = False  # Reset flag
                # LED: Blue - Back to waiting
                # TODO: GPIO.set_led_color("blue")
                raise StopResponse()
            
            # Update activity time
            self.last_activity_time = time.time()
            
            # Keep wake word active - don't reset immediately
            # LED: Green - Ready for next input
            # TODO: GPIO.set_led_color("green")
            
            logger.info("Response completed, staying active for conversation")
            return result
        
        # Otherwise, don't generate a reply
        raise StopResponse()

    def _is_command_safe(self, command: str) -> Tuple[bool, Optional[str]]:
        """Check if a command is safe to execute"""
        # Check for dangerous patterns
        for pattern in DANGEROUS_PATTERNS:
            if re.search(pattern, command, re.IGNORECASE):
                return False, f"Command contains dangerous pattern: {pattern}"
        
        # Parse command to get base command
        try:
            parts = shlex.split(command)
            if not parts:
                return False, "Empty command"
            
            base_cmd = parts[0]
            
            # Remove path, get just the command name
            base_cmd = os.path.basename(base_cmd)
            
            # Check if command is in whitelist
            if base_cmd not in SAFE_COMMANDS:
                return False, f"Command '{base_cmd}' is not in the safe command whitelist"
            
            return True, None
        except ValueError as e:
            return False, f"Invalid command syntax: {str(e)}"

    @function_tool()
    async def get_current_time(self, context: RunContext) -> str:
        """Get the current date and time on the system."""
        # LED: Yellow - Processing
        # TODO: GPIO.set_led_color("yellow")
        
        now = datetime.now()
        time_str = now.strftime("%Y-%m-%d %H:%M:%S")
        day_name = now.strftime("%A")
        
        result = f"Current time is {time_str}, {day_name}"
        logger.info(f"Time query: {result}")
        
        # LED: Green - Success
        # TODO: GPIO.set_led_color("green")
        await asyncio.sleep(0.1)
        # LED: Green - Stay active
        # TODO: GPIO.set_led_color("green")
        
        return result

    @function_tool()
    async def get_system_status(self, context: RunContext) -> str:
        """Get system status including uptime, memory, disk, and basic hardware info."""
        # LED: Yellow - Processing
        # TODO: GPIO.set_led_color("yellow")
        
        status_parts = []
        
        try:
            # Uptime
            result = subprocess.run(['uptime'], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                status_parts.append(f"Uptime: {result.stdout.strip()}")
            
            # Memory
            result = subprocess.run(['free', '-h'], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                status_parts.append(f"Memory:\n{result.stdout.strip()}")
            
            # Disk
            result = subprocess.run(['df', '-h', '/'], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                status_parts.append(f"Disk:\n{result.stdout.strip()}")
            
            if not status_parts:
                return "Could not retrieve system status"
            
            result_text = '\n'.join(status_parts)
            
            # Truncate if too long
            if len(result_text) > MAX_OUTPUT_LENGTH:
                result_text = result_text[:MAX_OUTPUT_LENGTH] + "... (truncated)"
            
            logger.info("System status retrieved")
            
            # LED: Green - Success
            # TODO: GPIO.set_led_color("green")
            await asyncio.sleep(0.1)
            # LED: Green - Stay active
            # TODO: GPIO.set_led_color("green")
            
            return result_text
            
        except Exception as e:
            logger.error(f"Error getting system status: {e}")
            # LED: Red - Error
            # TODO: GPIO.set_led_color("red")
            await asyncio.sleep(0.5)
            # LED: Green - Stay active
            # TODO: GPIO.set_led_color("green")
            
            return f"Error retrieving system status: {str(e)}"

    @function_tool()
    async def execute_safe_command(
        self,
        context: RunContext,
        command: Annotated[str, Field(description="The Linux command to execute (must be in safe whitelist)")]
    ) -> str:
        """
        Execute a safe Linux command. Only whitelisted commands are allowed.
        Dangerous commands like rm, format, etc. are blocked.
        
        Args:
            command: The command to execute (e.g., 'ls -la', 'ps aux', 'df -h')
        """
        # LED: Yellow - Processing command
        # TODO: GPIO.set_led_color("yellow")
        
        logger.info(f"Command request: {command}")
        
        # Check if command is safe
        is_safe, reason = self._is_command_safe(command)
        
        if not is_safe:
            logger.warning(f"Unsafe command blocked: {command} - {reason}")
            # LED: Red - Command blocked
            # TODO: GPIO.set_led_color("red")
            await asyncio.sleep(0.5)
            # LED: Green - Stay active
            # TODO: GPIO.set_led_color("green")
            
            return f"Command not allowed: {reason}. Only safe, whitelisted commands can be executed."
        
        try:
            # Execute command with timeout
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=MAX_COMMAND_TIMEOUT,
                cwd=os.path.expanduser("~")  # Run from home directory
            )
            
            output = result.stdout if result.stdout else result.stderr
            
            if not output:
                output = f"Command executed (exit code: {result.returncode})"
            
            # Truncate if too long
            if len(output) > MAX_OUTPUT_LENGTH:
                output = output[:MAX_OUTPUT_LENGTH] + f"\n... (truncated, {len(output)} total characters)"
            
            logger.info(f"Command executed successfully: {command}")
            
            # LED: Green - Command successful
            # TODO: GPIO.set_led_color("green")
            await asyncio.sleep(0.1)
            # LED: Green - Stay active
            # TODO: GPIO.set_led_color("green")
            
            return output
            
        except subprocess.TimeoutExpired:
            logger.warning(f"Command timed out: {command}")
            # LED: Red - Timeout
            # TODO: GPIO.set_led_color("red")
            await asyncio.sleep(0.5)
            # LED: Green - Stay active
            # TODO: GPIO.set_led_color("green")
            
            return f"Command timed out after {MAX_COMMAND_TIMEOUT} seconds"
            
        except Exception as e:
            logger.error(f"Error executing command: {command} - {e}")
            # LED: Red - Error
            # TODO: GPIO.set_led_color("red")
            await asyncio.sleep(0.5)
            # LED: Green - Stay active
            # TODO: GPIO.set_led_color("green")
            
            return f"Error executing command: {str(e)}"

    @function_tool()
    async def see_whats_in_front(self, context: RunContext) -> str:
        """
        See and describe what's in front of the camera. Use this when the user asks visual questions 
        like "what's in front of me?", "how many people are there?", "what do you see?", or any 
        questions about what's visible to the camera.
        """
        # LED: Yellow - Processing vision
        # TODO: GPIO.set_led_color("yellow")
        
        if not self.vision_plugin:
            logger.warning("Vision plugin not available")
            # LED: Red - Error
            # TODO: GPIO.set_led_color("red")
            await asyncio.sleep(0.5)
            # LED: Green - Stay active
            # TODO: GPIO.set_led_color("green")
            return "I don't have access to a camera right now."
        
        if not self.vision_plugin.has_frame():
            logger.warning("No frame available from camera")
            # LED: Red - Error
            # TODO: GPIO.set_led_color("red")
            await asyncio.sleep(0.5)
            # LED: Green - Stay active
            # TODO: GPIO.set_led_color("green")
            return "I can't see anything right now - the camera isn't capturing any frames."
        
        try:
            caption = self.vision_plugin.get_image_description()
            if caption:
                logger.info(f"Vision description: {caption[:100]}...")
                # LED: Green - Success
                # TODO: GPIO.set_led_color("green")
                await asyncio.sleep(0.1)
                # LED: Green - Stay active
                # TODO: GPIO.set_led_color("green")
                return caption
            else:
                logger.warning("No caption returned from vision plugin")
                # LED: Red - Error
                # TODO: GPIO.set_led_color("red")
                await asyncio.sleep(0.5)
                # LED: Green - Stay active
                # TODO: GPIO.set_led_color("green")
                return "I couldn't generate a description of what I see right now."
        except Exception as e:
            logger.error(f"Error getting vision description: {e}", exc_info=True)
            # LED: Red - Error
            # TODO: GPIO.set_led_color("red")
            await asyncio.sleep(0.5)
            # LED: Green - Stay active
            # TODO: GPIO.set_led_color("green")
            return f"Error seeing what's in front of me: {str(e)}"

    @function_tool()
    async def stop_listening(self, context: RunContext) -> str:
        """
        Stop listening and go back to sleep. The assistant will not respond again until the wake word is said.
        Use this when the user explicitly asks you to stop, go to sleep, or stop listening.
        """
        # LED: Blue - Going to sleep
        # TODO: GPIO.set_led_color("blue")
        
        logger.info("User requested to stop listening - resetting wake word")
        
        # Reset wake word detection
        self.wake_word_detected = False
        self.last_activity_time = None
        self.stop_requested = True  # Set flag to stop further processing
        
        # LED: Blue - Back to waiting state
        # TODO: GPIO.set_led_color("blue")
        
        # Return empty string so LLM doesn't generate additional response
        # The confirmation will be spoken by the LLM based on the tool result
        return "I've stopped listening. Say the wake word again when you need me."



# Conditionally add Kiwix search tool if available
if KIWIX_AVAILABLE:
    kiwix_tool = create_kiwix_search_tool()
    if kiwix_tool:
        # Add the tool as a method to the agent class
        setattr(JetsonOrinNanoFieldKitVoiceAssistant, 'search_kiwix', kiwix_tool)

# Vision is available as a tool (see_whats_in_front) that the LLM can call when needed


def configure_audio_sources():
    """
    Check and configure audio input/output sources to ensure correct devices are selected.
    Uses PulseAudio (pactl) to set the default sink and source.

    Configuration can be customized via environment variables:
    - AUDIO_SINK_NAME: Name pattern for the correct audio output device
    - AUDIO_SOURCE_NAME: Name pattern for the correct audio input device
    """
    # Get desired device names from environment or use defaults
    desired_sink = os.getenv("AUDIO_SINK_NAME", "")
    desired_source = os.getenv("AUDIO_SOURCE_NAME", "")

    try:
        # Check if pactl is available
        result = subprocess.run(['which', 'pactl'], capture_output=True, timeout=5)
        if result.returncode != 0:
            logger.warning("pactl not found - audio configuration skipped")
            return

        # Get current default sink
        result = subprocess.run(['pactl', 'get-default-sink'], capture_output=True, text=True, timeout=5)
        current_sink = result.stdout.strip() if result.returncode == 0 else ""

        # Get current default source
        result = subprocess.run(['pactl', 'get-default-source'], capture_output=True, text=True, timeout=5)
        current_source = result.stdout.strip() if result.returncode == 0 else ""

        logger.info(f"Current audio sink: {current_sink}")
        logger.info(f"Current audio source: {current_source}")

        # List all available sinks
        result = subprocess.run(['pactl', 'list', 'short', 'sinks'], capture_output=True, text=True, timeout=5)
        if result.returncode == 0 and desired_sink:
            sinks = result.stdout.strip().split('\n')
            for sink_line in sinks:
                if desired_sink.lower() in sink_line.lower():
                    sink_name = sink_line.split()[1]
                    if sink_name != current_sink:
                        logger.info(f"Setting default sink to: {sink_name}")
                        subprocess.run(['pactl', 'set-default-sink', sink_name], timeout=5)
                    break

        # List all available sources
        result = subprocess.run(['pactl', 'list', 'short', 'sources'], capture_output=True, text=True, timeout=5)
        if result.returncode == 0 and desired_source:
            sources = result.stdout.strip().split('\n')
            for source_line in sources:
                if desired_source.lower() in source_line.lower():
                    source_name = source_line.split()[1]
                    if source_name != current_source:
                        logger.info(f"Setting default source to: {source_name}")
                        subprocess.run(['pactl', 'set-default-source', source_name], timeout=5)
                    break

        # Get updated configuration
        result = subprocess.run(['pactl', 'get-default-sink'], capture_output=True, text=True, timeout=5)
        final_sink = result.stdout.strip() if result.returncode == 0 else ""

        result = subprocess.run(['pactl', 'get-default-source'], capture_output=True, text=True, timeout=5)
        final_source = result.stdout.strip() if result.returncode == 0 else ""

        logger.info(f"Final audio sink: {final_sink}")
        logger.info(f"Final audio source: {final_source}")

    except Exception as e:
        logger.error(f"Error configuring audio sources: {e}")


async def entrypoint(ctx: JobContext):
    """Main entry point for the Jetson Nano assistant"""
    # Configure audio sources at startup
    configure_audio_sources()

    session = AgentSession()
    
    await session.start(
        agent=JetsonOrinNanoFieldKitVoiceAssistant(),
        room=ctx.room
    )

if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))

