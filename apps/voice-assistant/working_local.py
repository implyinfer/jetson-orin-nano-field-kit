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
import io
import logging
import os
import re
import shlex
import subprocess
import tempfile
import time
import wave
from datetime import datetime
from pathlib import Path
from typing import AsyncIterable, Optional, List, Dict, Annotated, Tuple

import numpy as np
from dotenv import load_dotenv
from pydantic import Field
from livekit import rtc
from livekit.agents import JobContext, WorkerOptions, cli, stt, tts, utils
from livekit.agents.llm import function_tool
from livekit.agents.types import DEFAULT_API_CONNECT_OPTIONS
from livekit.agents.voice import Agent, AgentSession, RunContext
from livekit.agents.voice.agent_activity import StopResponse
from livekit.plugins import openai, silero
from faster_whisper import WhisperModel

from piper import PiperVoice, SynthesisConfig

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

print("Loading Whisper model...")

model = WhisperModel("distil-small.en", device="cuda", compute_type="float16")

print(model)

class FasterWhisperSTT(stt.STT):
    """Custom STT implementation using faster_whisper"""
    
    def __init__(
        self,
        model_size: str = "distil-small.en",
        device: str = "cuda",
        compute_type: str = "float16",
        language: Optional[str] = "en",
        beam_size: int = 5
    ):
        super().__init__(
            capabilities=stt.STTCapabilities(streaming=False, interim_results=False)
        )
        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type
        self.language = language
        self.beam_size = beam_size
        self._model = None
        
    def _get_model(self) -> WhisperModel:
        """Lazy load the Whisper model"""
        if self._model is None:
            logger.info(f"Loading Whisper model: {self.model_size} on {self.device}")
            self._model = WhisperModel(
                self.model_size,
                device=self.device,
                compute_type=self.compute_type
            )
        return self._model
    
    async def _recognize_impl(
        self, buffer: utils.AudioBuffer, *, language: str | None = None, conn_options: Optional[Dict] = None
    ) -> stt.SpeechEvent:
        """Recognize speech from audio buffer using faster_whisper"""
        try:
            # Merge frames if needed
            buffer = utils.merge_frames(buffer)
            
            # Convert AudioBuffer to WAV format in memory
            io_buffer = io.BytesIO()
            
            with wave.open(io_buffer, "wb") as wav:
                wav.setnchannels(buffer.num_channels)
                wav.setsampwidth(2)  # 16-bit
                wav.setframerate(buffer.sample_rate)
                wav.writeframes(buffer.data)
            
            # Save to temporary file for faster_whisper
            io_buffer.seek(0)
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_file:
                tmp_file.write(io_buffer.getvalue())
                tmp_path = tmp_file.name
            
            try:
                # Load model and transcribe
                model = self._get_model()
                use_language = language or self.language
                
                segments, info = model.transcribe(
                    tmp_path,
                    beam_size=self.beam_size,
                    language=use_language,
                    condition_on_previous_text=False
                )
                
                # Combine all segments into a single transcript
                transcript_parts = []
                for segment in segments:
                    transcript_parts.append(segment.text)
                
                result_text = " ".join(transcript_parts).strip()
                
                logger.info(f"Transcribed text: {result_text}")
                
                return stt.SpeechEvent(
                    type=stt.SpeechEventType.FINAL_TRANSCRIPT,
                    alternatives=[
                        stt.SpeechData(text=result_text or "", language=use_language or "")
                    ],
                )
            finally:
                # Clean up temporary file
                try:
                    os.unlink(tmp_path)
                except Exception as e:
                    logger.warning(f"Failed to delete temp file {tmp_path}: {e}")
                    
        except Exception as e:
            logger.error(f"Error in faster_whisper STT: {e}")
            return stt.SpeechEvent(
                type=stt.SpeechEventType.FINAL_TRANSCRIPT,
                alternatives=[
                    stt.SpeechData(text="", language=language or self.language or "")
                ],
            )


class PiperTTSPlugin(tts.TTS):
    """Local TTS implementation using Piper"""
    
    def __init__(self, model, speed=1.0, volume=1.0, noise_scale=0.667, noise_w=0.8, use_cuda=False):
        super().__init__(
            capabilities=tts.TTSCapabilities(streaming=False),
            sample_rate=22050,
            num_channels=1
        )
        self._model_name = model
        self.speed = speed
        self.volume = volume
        self.noise_scale = noise_scale
        self.noise_w = noise_w
        # Check if CUDA is actually available before using it
        self.use_cuda = self._check_cuda_available() if use_cuda else False
        self._voice = None
        self._load_voice()

    def _check_cuda_available(self):
        """Check if CUDA is available in onnxruntime"""
        try:
            import onnxruntime as ort
            available_providers = ort.get_available_providers()
            return 'CUDAExecutionProvider' in available_providers
        except Exception:
            return False

    def _load_voice(self):
        # according to the docs if you enable cuda you need onnxruntime-gpu package, read the docs
        if self.use_cuda:
            logger.info("Loading Piper TTS with CUDA support")
        else:
            logger.info("Loading Piper TTS with CPU (CUDA not available)")
        self._voice = PiperVoice.load(self._model_name, use_cuda=self.use_cuda)
        
    def synthesize(self, text, *, conn_options=DEFAULT_API_CONNECT_OPTIONS):
        return PiperApiStream(self, text, conn_options)


class PiperApiStream(tts.ChunkedStream):
    """Stream implementation for Piper TTS"""
    
    def __init__(self, plugin, text, conn_options):
        super().__init__(tts=plugin, input_text=text, conn_options=conn_options)
        self.plugin = plugin

    async def _run(self, output_emitter):
        try:
            config = SynthesisConfig(
                volume=self.plugin.volume,
                length_scale=self.plugin.speed,
                noise_scale=self.plugin.noise_scale,
                noise_w_scale=self.plugin.noise_w,
                normalize_audio=True
            )
            
            loop = asyncio.get_event_loop()
            chunks = await loop.run_in_executor(None, self._synthesize_chunks, config)
            
            # Ensure we always send at least one frame
            if not chunks:
                # Send silence if no chunks
                silence = np.zeros(22050, dtype=np.int16).tobytes()
                chunks = [silence]
            
            # Add a small silence buffer at the end to prevent abrupt cutoffs
            # 0.15 seconds of silence at 22050 Hz = 3307.5 samples ≈ 3308 samples
            buffer_samples = int(22050 * 0.15)  # 0.15 seconds
            silence_buffer = np.zeros(buffer_samples, dtype=np.int16).tobytes()
            chunks.append(silence_buffer)
            
            # Push first frame to output_emitter to start it (prevents "isn't started" error)
            # Then use _event_ch for the rest
            first_frame_sent = False
            for chunk in chunks:
                frame = rtc.AudioFrame(
                    data=chunk,
                    sample_rate=22050,
                    num_channels=1,
                    samples_per_channel=len(chunk) // 2
                )
                # Send through event channel (base class will handle emitter)
                self._event_ch.send_nowait(
                    tts.SynthesizedAudio(
                        request_id="1",
                        segment_id="1",
                        frame=frame
                    )
                )
                # Push first frame to output_emitter to ensure it's started
                if not first_frame_sent:
                    try:
                        output_emitter.push(frame)
                        first_frame_sent = True
                    except RuntimeError:
                        # If push fails, _event_ch should be sufficient
                        pass
                
        except Exception as e:
            logger.error(f"Error in Piper TTS synthesis: {e}")
            try:
                silence = np.zeros(22050, dtype=np.int16).tobytes()
                frame = rtc.AudioFrame(
                    data=silence,
                    sample_rate=22050,
                    num_channels=1,
                    samples_per_channel=22050
                )
                self._event_ch.send_nowait(
                    tts.SynthesizedAudio(
                        request_id="1",
                        segment_id="1",
                        frame=frame
                    )
                )
                # Push to emitter to ensure it's started (prevents error on end_input)
                try:
                    output_emitter.push(frame)
                except RuntimeError:
                    pass  # Ignore if push fails
            except Exception:
                pass  # Ignore if channel is closed

    # this is a not streaming implementation, so if you are reading this, check https://github.com/OHF-Voice/piper1-gpl/blob/main/docs/API_PYTHON.md and PiperVoice.synthesize
    # i will not add streaming support right now
    def _synthesize_chunks(self, config):
        chunks = []
        for chunk in self.plugin._voice.synthesize(self.input_text, syn_config=config):
            audio_data = chunk.audio_int16_bytes
            if chunk.sample_channels == 2:
                audio = np.frombuffer(audio_data, dtype=np.int16)
                audio = audio.reshape(-1, 2).mean(axis=1).astype(np.int16)
                audio_data = audio.tobytes()
            chunks.append(audio_data)
        return chunks


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
                - If the user explicitly asks you to stop, stop talking, go to sleep, or stop listening, use the stop_listening tool immediately
                - If the user asks to shut down, power off, or exit the service completely, use the shutdown_service tool (this will terminate the entire service)

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
                - Always call a tool if it's relevant to the conversation.


                Current Time: {get_current_time()}
            """,
            # stt="assemblyai/universal-streaming",
            stt=FasterWhisperSTT(
                model_size="distil-small.en",
                device="cuda",
                compute_type="float16",
                language="en",
                beam_size=5
            ),
            # ="openai/gpt-4.1-mini",
            
            llm=openai.LLM.with_ollama(
                model="qwen3:1.7b", 
                base_url="http://localhost:11434/v1"
            ),

            # Old TTS example (commented out)
            # tts="cartesia/sonic-2:6f84f4b8-58a2-430c-8c79-688dad597532",
            tts=PiperTTSPlugin(
                model="en_GB-alba-medium.onnx",
                speed=1.2,
                volume=0.8,
                noise_scale=0.5,
                noise_w=0.6,
                use_cuda=True
            ),
            vad=silero.VAD.load(),
            allow_interruptions=True
        )
        self.wake_word = WAKE_WORD.lower()
        self.wake_word_detected = False
        self.last_activity_time = None
        self.wake_word_timeout = 60  # Reset after 60 seconds of inactivity
        self.stop_requested = False  # Track if stop_listening was called

    async def on_enter(self) -> None:
        """Called when agent enters the session"""
        # LED: Blue - System ready, waiting for wake word
        # TODO: GPIO.set_led_color("blue")
        logger.info(f"Assistant ready. Waiting for wake word: '{self.wake_word}'")
        await self.session.say(
            f"Hello! I'm Nano, how can I help you today?"
            # f"Say '{self.wake_word}' to wake me up."
        )

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


async def entrypoint(ctx: JobContext):
    """Main entry point for the Jetson Nano assistant"""
    session = AgentSession()
    
    await session.start(
        agent=JetsonOrinNanoFieldKitVoiceAssistant(),
        room=ctx.room
    )

if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))

