#!/usr/bin/env python3
"""
Simple Fairytale Storyteller for Reachy Mini
Creates engaging stories with dramatic movements and natural ElevenLabs voice
"""

import asyncio
import logging
from typing import Dict, List, Tuple
from audio_system import AudioStorytellingSystem
from entertainment_controller import EntertainmentController

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

class FairytaleStoryteller:
    """Simple fairytale storyteller with synchronized movements and natural voice"""
    
    def __init__(self, simulation_mode: bool = True, use_reachy_audio: bool = False):
        self.logger = logging.getLogger(__name__)
        self.simulation_mode = simulation_mode
        self.use_reachy_audio = use_reachy_audio
        
        # Initialize audio storytelling system with ElevenLabs and optional Reachy audio
        self.audio_system = AudioStorytellingSystem(use_reachy_audio=use_reachy_audio)
        
        # Initialize Reachy controller for movements
        self.reachy_controller = EntertainmentController()
        
        # Story configuration for dramatic movie-like narration
        self.story_config = {
            "voice_speed": "slow",      # Slow, dramatic pace
            "dramatic_pauses": True,    # Extra pauses for cinematic effect
            "movement_emphasis": True,  # Synchronized dramatic movements
            "emotional_range": "dramatic", # Movie-like dramatic emotions
            "voice_style": "cinematic"  # Deep male narrator voice
        }
        
        self.logger.info("🏰 Fairytale Storyteller initialized")
    
    async def tell_simple_fairytale(self, story_name: str = "The Little Prince"):
        """Tell a simple fairytale with dramatic movements"""
        
        self.logger.info(f"📖 Starting fairytale: {story_name}")
        
        # Get the story and movements
        story_parts = self._get_fairytale_story(story_name)
        
        # Welcome the audience
        await self._welcome_audience()
        
        # Tell the story with movements
        for i, (text, emotion, movement, pause_after) in enumerate(story_parts):
            self.logger.info(f"🎭 Scene {i+1}: {emotion} - {movement}")
            
            # Check if this is a dance/celebration scene that needs continuous narration
            is_dance_scene = any(dance_word in movement.lower() for dance_word in 
                               ['dance', 'celebratory', 'spinning', 'crowd_pleaser'])
            
            if is_dance_scene:
                # For dance scenes: start audio first, then movement during narration
                audio_task = asyncio.create_task(
                    self.audio_system.speak_with_emotion(
                        text=text,
                        emotion=emotion,
                        pause_before=0.5,
                        pause_after=pause_after
                    )
                )
                
                # Small delay then start movement during speech
                await asyncio.sleep(1.0)  # Let narration begin
                movement_task = asyncio.create_task(self._perform_movement(movement, emotion))
                
                # Wait for both to complete
                await audio_task
                await movement_task
            else:
                # For regular scenes: run movement and audio simultaneously
                movement_task = asyncio.create_task(self._perform_movement(movement, emotion))
                audio_task = asyncio.create_task(
                    self.audio_system.speak_with_emotion(
                        text=text,
                        emotion=emotion,
                        pause_before=0.5,
                        pause_after=pause_after
                    )
                )
                
                # Wait for both to complete
                await asyncio.gather(movement_task, audio_task)
            
            # Extra pause between scenes for kids to process
            await asyncio.sleep(1.0)
        
        # Story conclusion
        await self._conclude_story()
        
        self.logger.info("✨ Fairytale completed!")
    
    async def _welcome_audience(self):
        """Welcome the children to storytime"""
        
        welcome_text = """
        Gather 'round, dear friends. You are about to witness... a tale of wonder and friendship.
        A story of a little prince... from a tiny planet far, far away.
        Are you ready... for this extraordinary journey?
        """
        
        # Run welcome gesture and speech simultaneously
        movement_task = asyncio.create_task(self._perform_movement("wave_hello", "happy"))
        audio_task = asyncio.create_task(
            self.audio_system.speak_with_emotion(
                text=welcome_text.strip(),
                emotion="dramatic",
                pause_before=1.0,
                pause_after=3.0
            )
        )
        
        await asyncio.gather(movement_task, audio_task)
    
    async def _conclude_story(self):
        """Conclude the story with a gentle ending"""
        
        conclusion_text = """
        And so ends... our tale of the little prince.
        Remember this lesson, dear friends... 
        What is essential is invisible to the eye... but visible to the heart.
        Until we meet again... may you always see with your heart.
        """
        
        # Run concluding bow and speech simultaneously
        movement_task = asyncio.create_task(self._perform_movement("gentle_bow", "happy"))
        audio_task = asyncio.create_task(
            self.audio_system.speak_with_emotion(
                text=conclusion_text.strip(),
                emotion="dramatic",
                pause_before=1.0,
                pause_after=3.0
            )
        )
        
        await asyncio.gather(movement_task, audio_task)
        
        # Final friendly wave after speech
        await self._perform_movement("wave_goodbye", "happy")
    
    def _get_fairytale_story(self, story_name: str) -> List[Tuple[str, str, str, float]]:
        """Get fairytale story parts with emotions, movements, and timing"""
        
        if story_name == "The Little Prince":
            return [
                (
                    "Once upon a time... on a tiny planet no bigger than a house... there lived a little prince.",
                    "dramatic",
                    "point_up_high", 
                    3.0
                ),
                (
                    "He had golden hair that shone like wheat... and he tended to his beloved rose with the greatest care.",
                    "curious", 
                    "hands_to_heart",
                    3.0
                ),
                (
                    "Every day... he would water his rose... and protect her from the wind... for she was the most beautiful flower in all the universe.",
                    "neutral",
                    "gentle_sway",
                    2.5
                ),
                (
                    "But the little prince felt lonely... his planet was so small... and he yearned to explore the vast cosmos!",
                    "curious",
                    "look_around_worried",
                    3.5
                ),
                (
                    "So one day... he decided to leave his tiny planet... and visit other worlds... to learn about life and friendship.",
                    "excited",
                    "reach_out_adventurous",
                    3.0
                ),
                (
                    "He visited a planet with a king who ruled over nothing... and another with a man who counted the stars!",
                    "surprised",
                    "look_around_curious",
                    3.5
                ),
                (
                    "On each planet... he met grown-ups who had forgotten what truly mattered... who were too busy to see the beauty around them.",
                    "curious",
                    "gentle_disappointment",
                    3.0
                ),
                (
                    "Until finally... he arrived on Earth... where he met a wise fox in the desert.",
                    "happy",
                    "gentle_wave",
                    3.0
                ),
                (
                    "The fox taught him the most important secret of all... 'One sees clearly only with the heart. What is essential is invisible to the eye.'",
                    "dramatic",
                    "hands_to_heart",
                    4.0
                ),
                (
                    "The little prince understood... that his rose was special not because she was perfect... but because she was his.",
                    "happy",
                    "warm_embrace_gesture",
                    3.5
                ),
                (
                    "He realized... that love is not about possessing... but about caring... about responsibility... about connection.",
                    "dramatic",
                    "confident_stance",
                    3.0
                ),
                (
                    "And though he returned to his tiny planet... his heart remained forever connected to all those he had loved.",
                    "dramatic",
                    "hands_to_heart_proud",
                    4.0
                )
            ]
        
        # Default simple story if requested story not found
        return [
            ("Once upon a time, there was a magical adventure waiting to begin!", "happy", "wave_hello", 2.0),
            ("And they all lived happily ever after!", "happy", "celebratory_arms", 2.0)
        ]
    
    async def _perform_movement(self, movement_name: str, emotion: str):
        """Perform dramatic movement synchronized with the story"""
        
        # Map story movements to available Reachy entertainment methods
        movement_map = {
            # Story-specific movements -> Reachy methods
            "point_up_high": "look_around_curious",  # Look up dramatically
            "hands_to_heart": "be_shy",  # Touching gesture
            "gentle_sway": "story_time_expressions",  # Storytelling gestures
            "look_around_worried": "look_around_curious",  # Looking around
            "reach_down_concerned": "look_around_curious",  # Concerned looking
            "chest_puff_brave": "wave_hello",  # Confident gesture
            "arms_spread_shining": "crowd_pleaser_dance",  # Big dramatic gesture
            "spinning_light": "dance_simple",  # Spinning movement
            "gentle_wave": "wave_hello",  # Wave gesture
            "welcome_others": "wave_hello",  # Welcoming wave
            "celebratory_arms": "crowd_pleaser_dance",  # Victory celebration
            "confident_stance": "robot_introduction",  # Confident pose
            "hands_to_heart_proud": "be_shy",  # Heart gesture
            
            # Little Prince movements
            "reach_out_adventurous": "wave_hello",  # Reaching out gesture
            "gentle_disappointment": "look_around_curious",  # Disappointed look
            "warm_embrace_gesture": "be_shy",  # Warm embracing gesture
            
            # Standard movements
            "wave_hello": "wave_hello",
            "wave_goodbye": "wave_hello", 
            "gentle_bow": "be_shy"  # Gentle bow-like gesture
        }
        
        # Get the actual movement method
        reachy_method = movement_map.get(movement_name, "story_time_expressions")
        
        # Execute the movement
        try:
            if self.simulation_mode:
                self.logger.info(f"🎭 [SIMULATION] Reachy performing: {reachy_method} with {emotion} emotion")
                await asyncio.sleep(0.5)  # Simulate movement time
            else:
                # Execute actual Reachy movement
                method = getattr(self.reachy_controller, reachy_method, None)
                if method:
                    self.logger.info(f"🤖 Reachy performing: {reachy_method} for {movement_name}")
                    success = await method()
                    if not success:
                        self.logger.warning(f"Movement {reachy_method} failed, continuing story")
                else:
                    self.logger.warning(f"Method {reachy_method} not found, using default expression")
                    await self.reachy_controller.story_time_expressions()
                
        except Exception as e:
            self.logger.error(f"Movement error: {e}")
            # Continue with story even if movement fails
            pass
    
    async def tell_custom_fairytale(self, title: str, story_parts: List[str]):
        """Tell a custom fairytale provided by the user"""
        
        self.logger.info(f"📖 Starting custom fairytale: {title}")
        
        await self._welcome_audience()
        
        # Convert simple story parts to full story structure
        for i, text in enumerate(story_parts):
            # Assign emotions based on content
            if any(word in text.lower() for word in ['happy', 'joy', 'wonderful', 'magic']):
                emotion = "happy"
                movement = "celebratory_arms"
            elif any(word in text.lower() for word in ['dark', 'scary', 'worried', 'afraid']):
                emotion = "curious"
                movement = "look_around_worried"
            elif any(word in text.lower() for word in ['brave', 'strong', 'courage']):
                emotion = "excited"
                movement = "confident_stance"
            else:
                emotion = "neutral"
                movement = "gentle_sway"
            
            await self._perform_movement(movement, emotion)
            
            await self.audio_system.speak_with_emotion(
                text=text,
                emotion=emotion,
                pause_before=0.5,
                pause_after=2.0 if i == len(story_parts) - 1 else 1.5  # Longer pause at end
            )
        
        await self._conclude_story()

# Test the fairytale storyteller
async def main():
    """Test the fairytale storyteller system"""
    
    print("🏰 Testing Fairytale Storyteller")
    print("Setting up storytelling system...")
    
    # Create storyteller with real Reachy hardware and audio
    storyteller = FairytaleStoryteller(
        simulation_mode=False,    # Use real Reachy hardware
        use_reachy_audio=True    # Audio through Reachy speakers
    )
    
    print("Starting fairytale story...")
    
    # Tell the simple fairytale
    await storyteller.tell_simple_fairytale("The Brave Little Star")
    
    print("✨ Fairytale storytelling test completed!")

if __name__ == "__main__":
    asyncio.run(main())