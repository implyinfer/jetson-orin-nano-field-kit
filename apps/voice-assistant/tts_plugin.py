"""TTS (Text-to-Speech) plugin implementations"""

import asyncio
import logging
import os
from typing import Optional

import numpy as np
from livekit import rtc
from livekit.agents import tts
from livekit.agents.types import DEFAULT_API_CONNECT_OPTIONS
from piper import PiperVoice, SynthesisConfig

logger = logging.getLogger("jetson-orin-nano-field-kit-voice-assistant")


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


def get_tts_plugin(use_local: bool = False):
    """
    Get the appropriate TTS plugin based on availability.
    
    Args:
        use_local: If True, force use of local model even if cloud is available
    
    Returns:
        TTS plugin instance
    """
    if use_local:
        logger.info("Using local Piper TTS")
        return PiperTTSPlugin(
            model="en_GB-alba-medium.onnx",
            speed=1.2,
            volume=0.8,
            noise_scale=0.5,
            noise_w=0.6,
            use_cuda=True
        )
    
    # Try to use cloud TTS if available
    try:
        if os.getenv("CARTESIA_API_KEY"):
            logger.info("Using Cartesia cloud TTS")
            # Use string identifier format: "cartesia/sonic-2:voice-id"
            return "cartesia/sonic-2:6f84f4b8-58a2-430c-8c79-688dad597532"
    except Exception as e:
        logger.warning(f"Failed to initialize Cartesia TTS: {e}")
    
    # Fall back to local
    logger.info("Falling back to local Piper TTS")
    return PiperTTSPlugin(
        model="en_GB-alba-medium.onnx",
        speed=1.2,
        volume=0.8,
        noise_scale=0.5,
        noise_w=0.6,
        use_cuda=True
    )

