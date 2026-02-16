#!/usr/bin/env python3
"""
Audio System for Reachy Mini Entertainment
Provides text-to-speech capabilities with pleasant voices for storytelling
"""

import asyncio
import logging
import threading
import time
import tempfile
import os
import numpy as np
import wave
from typing import Optional, Dict, Any
import pyttsx3
import pygame
from elevenlabs import VoiceSettings
from elevenlabs.client import ElevenLabs

try:
    from reachy_mini import ReachyMini
    REACHY_AVAILABLE = True
except ImportError:
    REACHY_AVAILABLE = False


class TTSEngine:
    """Text-to-Speech engine with voice customization using Eleven Labs for natural speech"""
    
    def __init__(self, api_key: str = "sk_329b52cca86917437ef4055f992f73224db215255b605214", 
                 use_reachy_audio: bool = False):
        self.logger = logging.getLogger(__name__)
        self.engine: Optional[pyttsx3.Engine] = None
        self.elevenlabs_client: Optional[ElevenLabs] = None
        self.reachy_mini: Optional[ReachyMini] = None
        self.is_speaking = False
        self.speech_lock = threading.Lock()
        self.use_elevenlabs = True
        self.use_reachy_audio = use_reachy_audio and REACHY_AVAILABLE
        self.api_key = api_key
        
        # Initialize audio system
        if self.use_reachy_audio:
            self._init_reachy_audio()
        else:
            self._init_pygame_audio()
        
        # Initialize TTS engines
        self._init_elevenlabs()
        self._init_engine()  # Fallback pyttsx3 engine
    
    def _init_reachy_audio(self):
        """Initialize Reachy Mini native audio system"""
        try:
            if REACHY_AVAILABLE:
                self.reachy_mini = ReachyMini(media_backend="default")
                self.reachy_mini.media.start_playing()
                self.logger.info("🤖 Reachy Mini native audio system initialized")
            else:
                self.logger.warning("Reachy Mini not available, falling back to pygame")
                self.use_reachy_audio = False
                self._init_pygame_audio()
        except Exception as e:
            self.logger.error(f"Failed to initialize Reachy audio: {e}")
            self.use_reachy_audio = False
            self._init_pygame_audio()
    
    def _init_pygame_audio(self):
        """Initialize pygame mixer for audio fallback"""
        try:
            pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=1024)
            self.logger.info("Audio system initialized (pygame fallback)")
        except Exception as e:
            self.logger.error(f"Failed to initialize audio: {e}")
    
    def _init_elevenlabs(self):
        """Initialize Eleven Labs TTS client"""
        try:
            self.elevenlabs_client = ElevenLabs(api_key=self.api_key)
            # Test connection and get available voices
            voices = self.elevenlabs_client.voices.get_all()
            
            # Use George - Warm, Captivating Storyteller (perfect for fairytales)
            # Will try June again once subscription upgrade propagates
            self.selected_voice_id = "3NCpLcGW5vNnR78Ytkew"  # June - Narrative & Story
            
            # Verify the voice exists and get its name
            voice_found = False
            selected_voice_name = "Unknown"
            for voice in voices.voices:
                if voice.voice_id == self.selected_voice_id:
                    voice_found = True
                    selected_voice_name = voice.name
                    break
            
            if voice_found:
                self.logger.info(f"🎤 Using specified ElevenLabs voice: {selected_voice_name} (ID: {self.selected_voice_id})")
            else:
                self.logger.warning(f"⚠️ Specified voice ID {self.selected_voice_id} not found in voice list, using as-is")
                # Still try to use the provided ID in case it's valid but not in the list
            
            self.logger.info("✨ Eleven Labs TTS initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Eleven Labs TTS: {e}")
            self.elevenlabs_client = None
            self.use_elevenlabs = False
            self.logger.warning("🔄 Falling back to pyttsx3 TTS")
        
    def _init_engine(self):
        """Initialize and configure the TTS engine"""
        try:
            self.engine = pyttsx3.init()
            
            # Get available voices
            voices = self.engine.getProperty('voices')
            
            # Configure voice settings
            self._configure_voice(voices)
            
            self.logger.info("TTS engine initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize TTS engine: {e}")
            self.engine = None
    
    def _configure_voice(self, voices):
        """Configure voice for natural, engaging storytelling from Reachy"""
        if not voices:
            self.logger.warning("No voices available")
            return
            
        # Find the most natural, kid-friendly voice
        preferred_voice = None
        voice_priority = []
        
        for voice in voices:
            voice_info = f"ID: {voice.id}, Name: {getattr(voice, 'name', 'Unknown')}"
            self.logger.debug(f"Available voice: {voice_info}")
            
            voice_name = getattr(voice, 'name', '').lower()
            voice_id = voice.id.lower()
            
            # Priority ranking for natural storytelling voices
            priority = 0
            
            # Best voices for storytelling (warm, clear, expressive)
            if any(keyword in voice_name for keyword in ['samantha', 'karen', 'tessa', 'moira']):
                priority = 100
            elif any(keyword in voice_name for keyword in ['alex', 'daniel', 'tom']):
                priority = 90
            elif 'female' in voice_name or 'woman' in voice_name:
                priority = 80
            elif any(keyword in voice_name for keyword in ['natural', 'enhanced', 'premium']):
                priority = 70
            elif 'english' in voice_name and 'us' in voice_name:
                priority = 60
            elif 'english' in voice_name:
                priority = 50
            elif not ('compact' in voice_name or 'novelty' in voice_name):
                priority = 30
            
            # Prefer non-compact voices for better quality
            if 'compact' not in voice_name and 'novelty' not in voice_name:
                priority += 10
                
            voice_priority.append((priority, voice, voice_name))
        
        # Sort by priority and select best voice
        voice_priority.sort(key=lambda x: x[0], reverse=True)
        
        if voice_priority:
            preferred_voice = voice_priority[0][1]
            voice_name = voice_priority[0][2]
            self.logger.info(f"🎤 Selected optimal voice for Reachy: {voice_name} (priority: {voice_priority[0][0]})")
        
        # Set the voice
        if preferred_voice:
            self.engine.setProperty('voice', preferred_voice.id)
        else:
            # Fallback to first available
            self.engine.setProperty('voice', voices[0].id)
            self.logger.info(f"Using fallback voice: {getattr(voices[0], 'name', voices[0].id)}")
        
        # Configure for natural, engaging speech from Reachy
        # Slightly slower rate for clarity and dramatic effect
        self.engine.setProperty('rate', 145)  # Slower for better storytelling
        
        # Full volume - Reachy should speak clearly!
        self.engine.setProperty('volume', 1.0)
    
    def get_voice_info(self) -> Dict[str, Any]:
        """Get current voice configuration"""
        info = {
            "engine": "Eleven Labs" if self.use_elevenlabs and self.elevenlabs_client else "pyttsx3",
            "is_natural": self.use_elevenlabs and self.elevenlabs_client is not None
        }
        
        if self.use_elevenlabs and self.elevenlabs_client:
            try:
                voices = self.elevenlabs_client.voices.get_all()
                current_voice = next((v for v in voices.voices if v.voice_id == self.selected_voice_id), None)
                info.update({
                    "current_voice": current_voice.name if current_voice else "Unknown",
                    "voice_id": self.selected_voice_id,
                    "available_voices": len(voices.voices)
                })
            except Exception as e:
                info["error"] = str(e)
        elif self.engine:
            try:
                voices = self.engine.getProperty('voices')
                current_voice_id = self.engine.getProperty('voice')
                current_voice = next((v for v in voices if v.id == current_voice_id), None)
                
                info.update({
                    "current_voice": getattr(current_voice, 'name', 'Unknown') if current_voice else 'Unknown',
                    "rate": self.engine.getProperty('rate'),
                    "volume": self.engine.getProperty('volume'),
                    "available_voices": len(voices) if voices else 0
                })
            except Exception as e:
                info["error"] = str(e)
        else:
            info["error"] = "No TTS engine available"
            
        return info
    
    def set_voice_settings(self, rate: Optional[int] = None, volume: Optional[float] = None):
        """Adjust voice settings"""
        if not self.engine:
            return
        
        try:
            if rate is not None:
                # Rate should be between 50-300 words per minute
                rate = max(50, min(300, rate))
                self.engine.setProperty('rate', rate)
                self.logger.info(f"Speech rate set to {rate} WPM")
            
            if volume is not None:
                # Volume should be between 0.0 and 1.0
                volume = max(0.0, min(1.0, volume))
                self.engine.setProperty('volume', volume)
                self.logger.info(f"Speech volume set to {volume}")
                
        except Exception as e:
            self.logger.error(f"Failed to set voice settings: {e}")
    
    async def speak_async(self, text: str, interrupt: bool = False, emotion: str = "neutral") -> bool:
        """Speak text asynchronously using Eleven Labs or fallback TTS"""
        if not text.strip():
            return False
        
        # Stop current speech if interrupting
        if interrupt and self.is_speaking:
            self.stop_speaking()
        
        # Wait if currently speaking and not interrupting
        if self.is_speaking and not interrupt:
            return False
        
        # Use Eleven Labs if available, otherwise fallback to pyttsx3
        if self.use_elevenlabs and self.elevenlabs_client:
            return await self._speak_elevenlabs_async(text, emotion)
        elif self.engine:
            return await self._speak_pyttsx3_async(text)
        else:
            return False
    
    async def _speak_elevenlabs_async(self, text: str, emotion: str = "neutral") -> bool:
        """Speak using Eleven Labs TTS with enhanced natural voice"""
        def speak_in_thread():
            with self.speech_lock:
                try:
                    self.is_speaking = True
                    self.logger.debug(f"🎤 Speaking with Eleven Labs: {text[:50]}...")
                    
                    # Configure voice settings for emotion
                    voice_settings = self._get_elevenlabs_voice_settings(emotion)
                    
                    # Generate audio
                    audio_generator = self.elevenlabs_client.text_to_speech.convert(
                        voice_id=self.selected_voice_id,
                        text=text,
                        voice_settings=voice_settings,
                        model_id="eleven_multilingual_v2"  # High quality model
                    )
                    
                    # Collect all audio data
                    audio_data = b""
                    for chunk in audio_generator:
                        audio_data += chunk
                    
                    # Play audio using appropriate method
                    if self.use_reachy_audio and self.reachy_mini:
                        self._play_audio_reachy_sync(audio_data)
                    else:
                        self._play_audio_pygame_sync(audio_data)
                    
                    self.logger.debug("✨ Eleven Labs speech completed")
                    
                except Exception as e:
                    self.logger.error(f"Eleven Labs TTS error: {e}")
                    # Try fallback to pyttsx3
                    if self.engine:
                        self.logger.info("🔄 Falling back to pyttsx3")
                        try:
                            self.engine.say(text)
                            self.engine.runAndWait()
                        except Exception as fallback_error:
                            self.logger.error(f"Fallback TTS error: {fallback_error}")
                finally:
                    self.is_speaking = False
        
        # Run in separate thread to avoid blocking
        thread = threading.Thread(target=speak_in_thread, daemon=True)
        thread.start()
        
        # Wait a moment for speech to start
        await asyncio.sleep(0.2)
        return True
    
    async def _speak_pyttsx3_async(self, text: str) -> bool:
        """Fallback pyttsx3 speech"""
        def speak_in_thread():
            with self.speech_lock:
                try:
                    self.is_speaking = True
                    self.logger.debug(f"Speaking with pyttsx3: {text[:50]}...")
                    self.engine.say(text)
                    self.engine.runAndWait()
                    self.logger.debug("Speech completed")
                except Exception as e:
                    self.logger.error(f"pyttsx3 TTS error: {e}")
                finally:
                    self.is_speaking = False
        
        # Run in separate thread to avoid blocking
        thread = threading.Thread(target=speak_in_thread, daemon=True)
        thread.start()
        
        # Wait a moment for speech to start
        await asyncio.sleep(0.1)
        return True
    
    def _get_elevenlabs_voice_settings(self, emotion: str) -> VoiceSettings:
        """Get optimized ElevenLabs voice settings for dramatic movie-like storytelling"""
        # Enhanced settings for dramatic, cinematic narration
        # Lower stability for more dynamic, expressive delivery
        
        emotion_settings = {
            "excited": VoiceSettings(
                stability=0.3,      # More dynamic for dramatic excitement
                similarity_boost=0.85,  # Good voice consistency with variation
                style=0.8,          # High styling for cinematic drama
                use_speaker_boost=True
            ),
            "happy": VoiceSettings(
                stability=0.4,      # Warm but dramatic
                similarity_boost=0.9,
                style=0.7,          # Expressive and engaging
                use_speaker_boost=True
            ),
            "curious": VoiceSettings(
                stability=0.5,      # Thoughtful but with character
                similarity_boost=0.9,  # Consistent narration
                style=0.6,          # Moderate drama for mystery
                use_speaker_boost=True
            ),
            "surprised": VoiceSettings(
                stability=0.2,      # Very dynamic for dramatic surprise
                similarity_boost=0.8,  # Allow more variation for effect
                style=0.9,          # Maximum expressiveness
                use_speaker_boost=True
            ),
            "neutral": VoiceSettings(
                stability=0.4,      # Dramatic baseline for movie narrator
                similarity_boost=0.85, # Good consistency with character
                style=0.6,          # Cinematic storytelling style
                use_speaker_boost=True
            ),
            "dramatic": VoiceSettings(
                stability=0.2,      # Very expressive for maximum drama
                similarity_boost=0.8,  # Allow character variation
                style=0.9,          # Maximum cinematic style
                use_speaker_boost=True
            )
        }
        
        return emotion_settings.get(emotion, emotion_settings["neutral"])
    
    def _play_audio_reachy_sync(self, audio_data: bytes):
        """Play audio using Reachy Mini native audio system (synchronous)"""
        try:
            # Save audio to temporary file for format conversion
            with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as temp_file:
                temp_path = temp_file.name
                temp_file.write(audio_data)
            
            # Convert MP3 to WAV format for Reachy (16kHz, float32)
            wav_data = self._convert_mp3_to_reachy_format(temp_path)
            
            # Push audio samples to Reachy
            if wav_data is not None:
                self.reachy_mini.media.push_audio_sample(wav_data)
                
                # Calculate playback duration and wait
                sample_rate = self.reachy_mini.media.get_output_audio_samplerate()
                duration = len(wav_data) / sample_rate
                time.sleep(duration)  # Synchronous sleep
            
            # Clean up temporary file
            try:
                os.unlink(temp_path)
            except:
                pass
                
        except Exception as e:
            self.logger.error(f"Reachy audio playback error: {e}")
            # Fallback to pygame
            self._play_audio_pygame_sync(audio_data)
    
    def _play_audio_pygame_sync(self, audio_data: bytes):
        """Play audio using pygame as fallback (synchronous)"""
        try:
            # Save audio to temporary file
            with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as temp_file:
                temp_path = temp_file.name
                temp_file.write(audio_data)
            
            # Play audio using pygame
            pygame.mixer.music.load(temp_path)
            pygame.mixer.music.set_volume(1.0)  # Maximum volume
            pygame.mixer.music.play()
            
            # Wait for playback to complete
            while pygame.mixer.music.get_busy():
                time.sleep(0.1)
            
            # Clean up temporary file
            try:
                os.unlink(temp_path)
            except:
                pass
        except Exception as e:
            self.logger.error(f"Pygame audio playback error: {e}")
    
    async def _play_audio_reachy(self, audio_data: bytes):
        """Play audio using Reachy Mini native audio system"""
        try:
            # Save audio to temporary file for format conversion
            with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as temp_file:
                temp_path = temp_file.name
                temp_file.write(audio_data)
            
            # Convert MP3 to WAV format for Reachy (16kHz, float32)
            wav_data = self._convert_mp3_to_reachy_format(temp_path)
            
            # Push audio samples to Reachy
            if wav_data is not None:
                self.reachy_mini.media.push_audio_sample(wav_data)
                
                # Calculate playback duration and wait
                sample_rate = self.reachy_mini.media.get_output_audio_samplerate()
                duration = len(wav_data) / sample_rate
                await asyncio.sleep(duration)
            
            # Clean up temporary file
            try:
                os.unlink(temp_path)
            except:
                pass
                
        except Exception as e:
            self.logger.error(f"Reachy audio playback error: {e}")
            # Fallback to pygame
            await self._play_audio_pygame(audio_data)
    
    async def _play_audio_pygame(self, audio_data: bytes):
        """Play audio using pygame as fallback"""
        try:
            # Save audio to temporary file
            with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as temp_file:
                temp_path = temp_file.name
                temp_file.write(audio_data)
            
            # Play audio using pygame
            pygame.mixer.music.load(temp_path)
            pygame.mixer.music.set_volume(1.0)  # Maximum volume
            pygame.mixer.music.play()
            
            # Wait for playback to complete
            while pygame.mixer.music.get_busy():
                await asyncio.sleep(0.1)
            
            # Clean up temporary file
            try:
                os.unlink(temp_path)
            except:
                pass
        except Exception as e:
            self.logger.error(f"Pygame audio playback error: {e}")
    
    def _convert_mp3_to_reachy_format(self, mp3_path: str) -> Optional[np.ndarray]:
        """Convert MP3 audio to Reachy Mini format (16kHz, float32)"""
        try:
            import librosa
            
            # Load MP3 file and resample to 16kHz
            audio_data, original_sr = librosa.load(mp3_path, sr=16000, mono=False)
            
            # Ensure we have the right shape for Reachy
            if audio_data.ndim == 1:
                # Convert mono to stereo if needed
                audio_data = np.stack([audio_data, audio_data], axis=-1)
            elif audio_data.ndim == 2 and audio_data.shape[0] == 2:
                # Transpose if channels are first dimension
                audio_data = audio_data.T
            
            # Ensure float32 format
            audio_data = audio_data.astype(np.float32)
            
            return audio_data
            
        except ImportError:
            self.logger.warning("librosa not available for audio conversion, using pygame fallback")
            return None
        except Exception as e:
            self.logger.error(f"Audio conversion error: {e}")
            return None
    
    def stop_speaking(self):
        """Stop current speech"""
        try:
            # Stop pygame music if playing
            if pygame.mixer.music.get_busy():
                pygame.mixer.music.stop()
            
            # Stop pyttsx3 if available
            if self.engine and self.is_speaking:
                self.engine.stop()
            
            # Note: Reachy audio is non-blocking and cannot be stopped mid-playback
            # This is a limitation of the push_audio_sample method
            
            self.is_speaking = False
            self.logger.info("Speech stopped")
        except Exception as e:
            self.logger.error(f"Failed to stop speech: {e}")
    
    async def wait_for_speech_completion(self, timeout: float = 10.0):
        """Wait for current speech to complete"""
        start_time = time.time()
        while self.is_speaking and (time.time() - start_time) < timeout:
            await asyncio.sleep(0.1)
    
    def cleanup(self):
        """Clean up resources"""
        self.stop_speaking()
        if self.engine:
            try:
                self.engine.stop()
            except:
                pass
        
        if self.use_reachy_audio and self.reachy_mini:
            try:
                self.reachy_mini.media.stop_playing()
            except:
                pass
        
        try:
            pygame.mixer.quit()
        except:
            pass


class AudioStorytellingSystem:
    """Enhanced storytelling system with audio narration"""
    
    def __init__(self, use_reachy_audio: bool = False):
        self.logger = logging.getLogger(__name__)
        self.tts = TTSEngine(use_reachy_audio=use_reachy_audio)
        self.story_paused = False
        self.use_reachy_audio = use_reachy_audio
        
    async def narrate_story_part(self, text: str, emotion: str = "neutral", 
                                pause_before: float = 0.0, pause_after: float = 1.0) -> bool:
        """Narrate a single story part with appropriate timing"""
        
        # Pause before speaking
        if pause_before > 0:
            await asyncio.sleep(pause_before)
        
        # Clean and optimize text for speech using best practices
        clean_text = self._clean_text_for_speech(text)
        
        # Add emotional context for ElevenLabs if using that engine
        if self.tts.use_elevenlabs and self.tts.elevenlabs_client:
            clean_text = self._add_emotional_context_for_elevenlabs(clean_text, emotion)
        else:
            # Adjust voice settings for pyttsx3 fallback
            self._adjust_voice_for_emotion(emotion)
        
        # Speak the text
        success = await self.tts.speak_async(clean_text, emotion=emotion)
        
        if success:
            # Wait for speech to complete
            await self.tts.wait_for_speech_completion()
            
            # Pause after speaking
            if pause_after > 0:
                await asyncio.sleep(pause_after)
        
        return success
    
    async def speak_with_emotion(self, text: str, emotion: str = "neutral", 
                               pause_before: float = 0.0, pause_after: float = 1.0) -> bool:
        """Alias for narrate_story_part for compatibility"""
        return await self.narrate_story_part(text, emotion, pause_before, pause_after)
    
    def _clean_text_for_speech(self, text: str) -> str:
        """Clean and enhance text for natural Reachy speech synthesis using ElevenLabs best practices"""
        
        # Remove emojis and replace with expressive words for natural speech
        emoji_replacements = {
            '🌟': ' sparkling star ',
            '✨': ', with magical sparkles, ',
            '🎉': ' celebration ',
            '💖': ' with lots of love ',
            '🌈': ' beautiful rainbow ',
            '🚀': ' rocket ship ',
            '🌊': ' ocean waves ',
            '🐙': ' friendly octopus ',
            '🎪': '',  # Remove, already implied by context
            '📚': '',  # Remove, already implied
            '🎭': '',  # Remove, already implied
            '🎤': '',  # Remove, already implied
        }
        
        clean_text = text
        for emoji, replacement in emoji_replacements.items():
            clean_text = clean_text.replace(emoji, replacement)
        
        # Normalize text for better TTS (ElevenLabs best practice)
        text_normalizations = {
            # Expand abbreviations
            ' Dr.': ' Doctor',
            ' Mr.': ' Mister',
            ' Mrs.': ' Missus',
            ' Ms.': ' Miss',
            ' etc.': ' etcetera',
            
            # Convert numbers to words (for smaller numbers)
            ' 1 ': ' one ',
            ' 2 ': ' two ',
            ' 3 ': ' three ',
            ' 4 ': ' four ',
            ' 5 ': ' five ',
            ' 6 ': ' six ',
            ' 7 ': ' seven ',
            ' 8 ': ' eight ',
            ' 9 ': ' nine ',
            ' 10 ': ' ten ',
            
            # Improve character descriptions with emotional context
            'Reachy': 'our friend Reachy',
            'little robot': 'sweet little robot',
        }
        
        # Apply text normalizations
        for original, replacement in text_normalizations.items():
            clean_text = clean_text.replace(original, replacement)
        
        # Remove extra spaces and clean up
        clean_text = ' '.join(clean_text.split())
        
        # Use ElevenLabs recommended punctuation for natural rhythm
        clean_text = clean_text.replace('. ', '... ')     # Natural pauses between sentences
        clean_text = clean_text.replace('! ', '! ')       # Keep excitement natural
        clean_text = clean_text.replace(', ', '... ')     # Brief pause at commas
        clean_text = clean_text.replace('....', '...')    # Normalize ellipses
        
        return clean_text
        
    def _add_emotional_context_for_elevenlabs(self, text: str, emotion: str) -> str:
        """Clean text for natural ElevenLabs speech without audio tags"""
        
        # ElevenLabs processes emotion through voice settings, not text tags
        # Just return clean text without any audio markup tags
        return text
    
    def _adjust_voice_for_emotion(self, emotion: str):
        """Adjust voice parameters based on emotion for more natural Reachy speech"""
        emotion_settings = {
            "excited": {"rate": 165, "volume": 1.0},      # Faster but not too fast
            "happy": {"rate": 155, "volume": 1.0},        # Warm and pleasant
            "curious": {"rate": 140, "volume": 0.95},     # Slower, thoughtful
            "surprised": {"rate": 175, "volume": 1.0},    # Quick but clear
            "neutral": {"rate": 145, "volume": 1.0}       # Standard Reachy voice
        }
        
        settings = emotion_settings.get(emotion, emotion_settings["neutral"])
        self.tts.set_voice_settings(rate=settings["rate"], volume=settings["volume"])
    
    async def tell_complete_story(self, story_parts: list, emotions: list = None) -> bool:
        """Tell a complete story with audio narration and proper pacing"""
        
        if not story_parts:
            return False
        
        self.logger.info(f"🎤 Starting audio storytelling with {len(story_parts)} parts")
        
        # Default emotions if not provided
        if not emotions:
            emotions = ["curious", "happy", "excited", "surprised"] * (len(story_parts) // 4 + 1)
        
        try:
            for i, story_part in enumerate(story_parts):
                if self.story_paused:
                    break
                
                emotion = emotions[i % len(emotions)]
                
                # Vary pause timing for dramatic effect
                pause_before = 0.3 if i > 0 else 0.0
                pause_after = 2.0 if i < len(story_parts) - 1 else 1.0
                
                # Special timing for dramatic moments
                if "oh no" in story_part.lower() or "suddenly" in story_part.lower():
                    pause_before = 1.0
                    pause_after = 2.5
                elif story_part.endswith("!"):
                    pause_after = 2.2
                
                # Narrate the story part
                success = await self.narrate_story_part(
                    story_part, 
                    emotion=emotion,
                    pause_before=pause_before, 
                    pause_after=pause_after
                )
                
                if not success:
                    self.logger.warning(f"Failed to narrate part {i+1}")
                    # Continue with visual storytelling only
                    await asyncio.sleep(3)  # Give time to read
            
            self.logger.info("🎊 Audio storytelling completed!")
            return True
            
        except Exception as e:
            self.logger.error(f"Audio storytelling failed: {e}")
            return False
    
    def pause_story(self):
        """Pause the current story"""
        self.story_paused = True
        self.tts.stop_speaking()
        self.logger.info("Story paused")
    
    def resume_story(self):
        """Resume the paused story"""
        self.story_paused = False
        self.logger.info("Story resumed")
    
    def stop_story(self):
        """Stop the current story"""
        self.story_paused = True
        self.tts.stop_speaking()
        self.logger.info("Story stopped")
    
    def get_audio_status(self) -> Dict[str, Any]:
        """Get current audio system status"""
        return {
            "is_speaking": self.tts.is_speaking,
            "story_paused": self.story_paused,
            "voice_info": self.tts.get_voice_info()
        }
    
    def cleanup(self):
        """Clean up audio resources"""
        self.stop_story()
        self.tts.cleanup()


# Simple test function
async def test_audio_system():
    """Test the audio storytelling system"""
    print("🎤 Testing Audio Storytelling System")
    
    audio_system = AudioStorytellingSystem()
    
    # Test basic speech
    print("Testing basic speech...")
    await audio_system.narrate_story_part("Hello! Welcome to our audio storytelling test!", "happy")
    
    # Test a mini story
    mini_story = [
        "Once upon a time, there was a little robot named Reachy.",
        "Reachy loved to tell stories to children!",
        "With a magical voice, Reachy could bring any tale to life.",
        "And everyone lived happily ever after!"
    ]
    
    print("Testing complete story narration...")
    await audio_system.tell_complete_story(mini_story)
    
    print("Audio system test completed!")
    audio_system.cleanup()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(test_audio_system())