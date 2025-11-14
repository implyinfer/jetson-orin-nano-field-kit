"""STT (Speech-to-Text) plugin implementations"""

import io
import logging
import os
import tempfile
import wave
from typing import Optional, Dict

from livekit.agents import stt, utils
from faster_whisper import WhisperModel

logger = logging.getLogger("jetson-orin-nano-field-kit-voice-assistant")

class FasterWhisperSTT(stt.STT):
    """Local STT implementation using faster_whisper"""
    
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


def get_stt_plugin(use_local: bool = False):
    """
    Get the appropriate STT plugin based on availability.
    
    Args:
        use_local: If True, force use of local model even if cloud is available
    
    Returns:
        STT plugin instance
    """
    if use_local:
        logger.info("Using local FasterWhisper STT")
        return FasterWhisperSTT(
            model_size="distil-small.en",
            device="cuda",
            compute_type="float16",
            language="en",
            beam_size=5
        )
    else: 
        return "assemblyai/universal-streaming"

