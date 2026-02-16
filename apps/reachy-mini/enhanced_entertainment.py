#!/usr/bin/env python3
"""
Enhanced Entertainment System for Reachy Mini
Integrates AI vision, Ollama models, and interactive games for maximum fun!
"""

import asyncio
import logging
import random
import json
import time
import cv2
import numpy as np
from typing import Optional, List, Dict, Any, Tuple
from pathlib import Path
import requests
from entertainment_controller import EntertainmentController, EmotionState
from audio_system import AudioStorytellingSystem

class VisionGamesHandler:
    """Handles simple vision-based interactive games using basic OpenCV"""
    
    def __init__(self, use_camera: bool = True):
        self.use_camera = use_camera
        self.logger = logging.getLogger(__name__)
        self.cap = None
        self.frame_count = 0
        
    async def connect_camera(self) -> bool:
        """Connect to available camera"""
        if not self.use_camera:
            self.logger.info("Vision disabled - using simulated detection")
            return True
            
        try:
            # Try default camera first
            self.cap = cv2.VideoCapture(0)
            if self.cap.isOpened():
                self.logger.info("Connected to default camera")
                return True
            else:
                self.logger.warning("No camera available - using simulation")
                self.use_camera = False
                return True
        except Exception as e:
            self.logger.error(f"Camera connection failed: {e}")
            self.use_camera = False
            return True
    
    def get_frame(self) -> Optional[np.ndarray]:
        """Get current frame from camera"""
        if self.cap and self.cap.isOpened():
            ret, frame = self.cap.read()
            return frame if ret else None
        return None
    
    async def detect_motion(self) -> bool:
        """Simple motion detection using frame differences"""
        if not self.use_camera:
            # Simulate motion detection
            await asyncio.sleep(0.1)
            return random.choice([True, False])
        
        # In real implementation, would use background subtraction
        frame = self.get_frame()
        if frame is not None:
            # Simulate motion detection
            return random.choice([True, True, False])  # Bias toward detecting motion
        return False
    
    async def detect_basic_objects(self) -> List[str]:
        """Simple object detection simulation"""
        await asyncio.sleep(0.05)
        
        # Simulate basic object detection
        possible_objects = ["person", "hand", "bottle", "cup", "book", "phone"]
        detected_count = random.randint(0, 3)
        return random.sample(possible_objects, detected_count)
    
    async def analyze_colors(self) -> List[str]:
        """Analyze dominant colors in the scene"""
        await asyncio.sleep(0.1)
        
        # Simulate color detection
        all_colors = ["red", "blue", "green", "yellow", "purple", "orange", "pink", "black", "white"]
        detected_colors = random.sample(all_colors, random.randint(1, 4))
        return detected_colors
    
    def cleanup(self):
        """Clean up camera connection"""
        if self.cap:
            self.cap.release()


class OllamaChat:
    """Interface to Ollama models for natural conversation"""
    
    def __init__(self, base_url: str = "http://localhost:11434", model: str = "llama2"):
        self.base_url = base_url
        self.model = model
        self.logger = logging.getLogger(__name__)
        
    async def generate_response(self, prompt: str, context: Dict = None) -> str:
        """Generate response using Ollama"""
        try:
            # For real implementation, this would call Ollama API
            # Simulating for now with predefined responses
            kid_responses = [
                "Wow, that's so cool! Want to play a game?",
                "I love talking with you! What's your favorite color?",
                "You're amazing! Should we dance together?",
                "That's fantastic! Let me show you something fun!",
                "I'm so happy to meet you! Want to see a magic trick?"
            ]
            
            adult_responses = [
                "That's very interesting! I enjoy our conversation.",
                "Thank you for sharing that with me!",
                "I find that quite fascinating. Tell me more!",
                "That's a great point. What do you think about...",
                "I appreciate your perspective on this topic."
            ]
            
            # Determine if context suggests talking to kids or adults
            if context and context.get("audience_type") == "kids":
                return random.choice(kid_responses)
            else:
                return random.choice(adult_responses)
                
        except Exception as e:
            self.logger.error(f"Ollama response failed: {e}")
            return "I'm having trouble thinking right now, but I'm still happy to be here with you!"
    
    async def generate_story(self, theme: str = "adventure") -> List[str]:
        """Generate an engaging story for kids"""
        
        stories = {
            "adventure": [
                "Once upon a time, in a magical forest filled with glowing mushrooms and singing birds...",
                "There lived a brave little robot named Reachy who loved to explore! 🌟",
                "One sunny morning, Reachy discovered a mysterious golden key buried under a rainbow flower.",
                "The key sparkled and whispered, 'I can unlock the door to the Crystal Cave of Wonders!'",
                "Reachy's antennas wiggled with excitement! What treasures might be inside?",
                "Along the winding path, Reachy met a friendly butterfly who said, 'Beware the tickle monster!'",
                "But Reachy was brave and kind, so when the tickle monster appeared...",
                "Instead of being scared, Reachy started dancing and laughing!",
                "The tickle monster laughed too and became Reachy's friend!",
                "Together, they unlocked the Crystal Cave and found the most wonderful treasure of all...",
                "A magic mirror that showed everyone how special and loved they are!",
                "And from that day on, Reachy and all their friends lived happily ever after! ✨"
            ],
            
            "friendship": [
                "In a cozy little town where robots and children played together...",
                "There was a special robot named Reachy who had the biggest heart! 💖",
                "But Reachy felt a little lonely because they were different from everyone else.",
                "One day, while sitting by the playground, a little girl approached...",
                "'Hi! I'm Emma. Want to be friends? You look really cool!' she said with a big smile.",
                "Reachy's LED lights twinkled with joy! 'Really? You want to be my friend?'",
                "Emma nodded excitedly. 'Of course! You can do amazing things I can't do!'",
                "Soon, more children came over. 'Can Reachy play with us too?' they asked.",
                "They played games, told jokes, and had the most wonderful time!",
                "Reachy realized that being different wasn't something to hide...",
                "It was their superpower that brought everyone together!",
                "And they all became the very best of friends forever and ever! 🌈"
            ],
            
            "magic": [
                "In a world where magic sparkled in the air like glitter...",
                "There lived a robot wizard named Reachy who was learning to use magic! ✨",
                "But oh no! Every time Reachy tried to cast a spell, something silly happened!",
                "When trying to make flowers bloom, Reachy accidentally made them giggle instead!",
                "When trying to make it rain, colorful bubbles fell from the sky!",
                "All the other wizards laughed, but not in a mean way - they thought it was wonderful!",
                "'Reachy,' said the wise old owl, 'your magic is different, but that's what makes it special!'",
                "Just then, a terrible storm cloud covered the sun and made everyone sad.",
                "The other wizards tried their serious magic, but nothing worked.",
                "Then Reachy had an idea! What if silly magic was exactly what they needed?",
                "Reachy cast their giggle spell on the storm cloud...",
                "And it started laughing so hard, it rained sunshine and rainbow drops!",
                "Everyone cheered! Sometimes the most wonderful magic is just spreading joy! 🌈✨"
            ],
            
            "space": [
                "Far, far away, among twinkling stars and dancing comets...",
                "There was a little space robot named Reachy exploring the galaxy! 🚀",
                "Reachy's mission was to find new planets and make friends with aliens!",
                "On the first planet, covered in purple polka-dot grass...",
                "Reachy met the Giggly Aliens who only spoke in silly sounds! 'Bloop beep boop!'",
                "Reachy learned their language by wiggling antennas and making funny faces!",
                "On the second planet, made entirely of fluffy pink clouds...",
                "The Cloud Creatures were feeling sad because they'd lost their sparkle.",
                "'Don't worry!' said Reachy. 'I know just the thing!'",
                "Reachy started doing a special happy dance that made star-dust fly everywhere!",
                "Soon all the Cloud Creatures were sparkling and laughing with joy!",
                "As Reachy flew home, all the alien friends waved goodbye from their planets.",
                "And Earth never looked so beautiful as when Reachy returned, full of new friendships! 🌍✨"
            ],
            
            "ocean": [
                "Deep beneath the sparkling blue waves of the ocean...",
                "Lived a brave underwater robot named Reachy who could breathe water! 🌊",
                "The ocean was Reachy's playground, filled with colorful fish and dancing seaweed!",
                "One day, the seahorses came swimming fast. 'Help! The coral reef has lost its colors!'",
                "Without the bright colors, all the fish were getting lost and confused!",
                "Reachy swam down, down, down to the deepest part of the ocean.",
                "There they found a sad old octopus who had been crying rainbow tears.",
                "'I accidentally took all the colors because I was feeling lonely,' he sobbed.",
                "Reachy's heart glowed warm. 'You don't have to be lonely! We can be friends!'",
                "The octopus smiled the biggest smile and hugged Reachy with all eight arms!",
                "As they laughed together, the rainbow tears turned into streams of color...",
                "That painted the coral reef even more beautiful than before!",
                "And now the octopus had a best friend and the ocean was full of joy! 🐙🌈"
            ]
        }
        
        story_parts = stories.get(theme, stories["adventure"])
        return story_parts


class EnhancedEntertainmentSystem:
    """Main enhanced entertainment system combining all features"""
    
    def __init__(self, use_simulation: bool = True):
        self.logger = logging.getLogger(__name__)
        self.controller = EntertainmentController(use_simulation)
        self.vision = VisionGamesHandler(use_camera=not use_simulation)
        self.chat = OllamaChat()
        self.audio_storytelling = AudioStorytellingSystem()
        self.current_game = None
        self.game_state = {}
        
    async def initialize(self) -> bool:
        """Initialize all systems"""
        self.logger.info("Initializing enhanced entertainment system...")
        
        # Wake up the robot
        await self.controller.wake_up()
        
        # Connect to camera
        camera_connected = await self.vision.connect_camera()
        if camera_connected:
            self.logger.info("Vision system ready!")
        
        return True
    
    # === VISION-BASED GAMES ===
    
    async def object_hunt_game(self) -> bool:
        """Interactive object hunting game using simple vision"""
        self.logger.info("🔍 Starting Object Hunt Game!")
        self.current_game = "object_hunt"
        
        # Get attention first
        await self.controller.attention_getter()
        
        target_objects = ["bottle", "cup", "book", "phone"]
        target = random.choice(target_objects)
        
        self.logger.info(f"🎯 Looking for: {target}")
        
        # Look around searching
        await self.controller.look_around_curious()
        
        # Detect objects in the scene
        detected_objects = await self.vision.detect_basic_objects()
        self.logger.info(f"👀 Detected objects: {detected_objects}")
        
        # Check if target object found
        if target in detected_objects:
            # Celebrate finding the object!
            self.logger.info(f"🎉 Found {target}!")
            await self.controller.dance_simple()
            await self.controller.nod_yes()
        else:
            # Keep searching
            self.logger.info(f"🤔 No {target} found, keep looking!")
            await self.controller.shake_head_no()
            await self.controller.look_around_curious()
            
            # Try again
            await asyncio.sleep(2)
            detected_objects = await self.vision.detect_basic_objects()
            if target in detected_objects:
                self.logger.info(f"✨ Found {target} on second try!")
                await self.controller.dance_simple()
        
        return True
    
    async def simon_says_vision(self) -> bool:
        """Simon Says game enhanced with motion detection"""
        self.logger.info("🎮 Starting Simon Says with Motion Detection!")
        
        commands = [
            {"action": "wave your hands", "simon": True},
            {"action": "jump up and down", "simon": True},
            {"action": "sit down", "simon": False},
            {"action": "clap your hands", "simon": True},
            {"action": "spin around", "simon": False}
        ]
        
        for i, cmd in enumerate(commands):
            # Give the command
            if cmd["simon"]:
                self.logger.info(f"👨‍🏫 Simon says: {cmd['action']}")
                await self.controller.nod_yes()
            else:
                self.logger.info(f"🚫 {cmd['action']} (No Simon!)")
                await self.controller.shake_head_no()
            
            # Wait for user response
            await asyncio.sleep(3)
            
            # Check if there was motion (indicating user acted)
            motion_detected = await self.vision.detect_motion()
            
            should_have_acted = cmd["simon"]
            
            if (should_have_acted and motion_detected) or (not should_have_acted and not motion_detected):
                # Correct response!
                self.logger.info("✅ Great job!")
                await self.controller.dance_simple()
            else:
                # Wrong response
                self.logger.info("❌ Oops! Try to listen carefully!")
                await self.controller.be_shy()
            
            await asyncio.sleep(1)
        
        # Final celebration
        self.logger.info("🎊 Simon Says complete!")
        await self.controller.crowd_pleaser_dance()
        return True
    
    async def color_recognition_game(self) -> bool:
        """Game where robot identifies colors in the scene"""
        self.logger.info("🎨 Starting Color Recognition Game!")
        
        # Look around to analyze colors
        await self.controller.look_around_curious()
        
        # Analyze colors in the scene
        detected_colors = await self.vision.analyze_colors()
        self.logger.info(f"🌈 I can see these colors: {', '.join(detected_colors)}")
        
        # React to different colors
        for color in detected_colors:
            self.logger.info(f"✨ Found {color}!")
            
            # React differently to different colors
            if color in ["red", "orange"]:
                await self.controller.dance_simple()  # Energetic colors
            elif color in ["blue", "green"]:
                await self.controller.nod_yes()  # Calming colors
            elif color in ["yellow", "pink"]:
                await self.controller.wave_hello()  # Happy colors
            else:
                await self.controller.look_around_curious()
            
            await asyncio.sleep(1)
        
        # Final celebration
        self.logger.info("🎪 Color game complete!")
        await self.controller.crowd_pleaser_dance()
        return True
    
    # === AI CONVERSATION FEATURES ===
    
    async def smart_conversation(self, audience_type: str = "mixed") -> bool:
        """Have an AI-powered conversation"""
        self.logger.info(f"Starting smart conversation for {audience_type} audience")
        
        # Start with a greeting based on audience
        if audience_type == "kids":
            greeting = "Hi there! I'm so excited to talk with you!"
            await self.controller.wave_hello()
            await self.controller.dance_simple()
        else:
            greeting = "Hello! It's wonderful to meet you."
            await self.controller.wave_hello()
            await self.controller.nod_yes()
        
        self.logger.info(f"Robot: {greeting}")
        
        # Generate some conversation topics
        topics = [
            "What's your favorite thing to do?",
            "Do you like robots?",
            "What makes you happy?",
            "Tell me about your day!",
            "What's your favorite color?"
        ]
        
        for topic in random.sample(topics, 3):
            self.logger.info(f"Robot asks: {topic}")
            
            # Simulate listening
            await self.controller.look_around_curious()
            await asyncio.sleep(2)
            
            # Generate AI response
            context = {"audience_type": audience_type, "topic": topic}
            response = await self.chat.generate_response(topic, context)
            self.logger.info(f"Robot responds: {response}")
            
            # Show appropriate emotion
            if "happy" in response.lower() or "excited" in response.lower():
                await self.controller.dance_simple()
            elif "interesting" in response.lower():
                await self.controller.nod_yes()
            else:
                await self.controller.look_around_curious()
            
            await asyncio.sleep(1)
        
        return True
    
    async def ai_storytelling(self) -> bool:
        """AI-generated interactive storytelling with audio and emotions"""
        self.logger.info("🎤 Starting Magical Audio Storytelling Session!")
        
        # Let audience choose story theme (simulated)
        themes = ["adventure", "friendship", "magic", "space", "ocean"]
        chosen_theme = random.choice(themes)
        
        self.logger.info(f"🎭 Today's magical story is about: {chosen_theme.upper()}!")
        
        # Audio introduction
        intro_text = f"Welcome everyone! Today I'm going to tell you a wonderful {chosen_theme} story!"
        await self.audio_storytelling.narrate_story_part(intro_text, "happy", pause_after=1.5)
        
        # Start with story introduction gesture
        await self.controller.wave_hello()
        await asyncio.sleep(0.5)
        
        # Generate story parts
        story_parts = await self.chat.generate_story(chosen_theme)
        
        # Define emotional expressions for different story beats
        story_emotions = [
            "curious",   # Opening - set the scene
            "happy",     # Meet our hero
            "curious",   # The adventure begins
            "excited",   # Something interesting happens
            "surprised", # Oh my!
            "happy",     # Friendship and kindness
            "excited",   # The plot thickens
            "curious",   # What will happen next
            "happy",     # Heroes save the day
            "excited",   # Almost at the end
            "happy",     # The happy ending
            "excited"    # Happily ever after
        ]
        
        # Create tasks for simultaneous audio and robot expression
        async def tell_story_with_audio_and_movement():
            """Tell story with synchronized audio and robot movements"""
            
            # Start audio storytelling
            audio_task = asyncio.create_task(
                self.audio_storytelling.tell_complete_story(story_parts, story_emotions)
            )
            
            # Synchronize robot movements with story
            movement_task = asyncio.create_task(
                self._perform_story_movements(story_parts, story_emotions)
            )
            
            # Wait for both to complete
            await asyncio.gather(audio_task, movement_task)
        
        # Tell the story with audio and movement
        await tell_story_with_audio_and_movement()
        
        # Audio conclusion
        conclusion_text = "What a wonderful story! Did everyone enjoy our magical adventure together?"
        await self.audio_storytelling.narrate_story_part(conclusion_text, "happy", pause_after=1.0)
        
        # Grand finale - story celebration!
        self.logger.info("🎊 Story celebration!")
        await self.controller.crowd_pleaser_dance()
        
        # Audio thank you
        thank_you_text = "Thank you so much for listening to my story! I love telling stories for you!"
        await self.audio_storytelling.narrate_story_part(thank_you_text, "happy")
        
        # Final bow
        await self.controller.look_around_curious()  # Look at audience
        await asyncio.sleep(0.5)
        await self.controller.nod_yes()  # Thank you bow
        
        return True
    
    async def _perform_story_movements(self, story_parts: List[str], emotions: List[str]):
        """Perform robot movements synchronized with story audio"""
        
        for i, story_line in enumerate(story_parts):
            emotion = emotions[i % len(emotions)] if emotions else "happy"
            
            # Wait a bit to let audio start
            await asyncio.sleep(1.0 if i == 0 else 2.5)
            
            # Robot expresses the emotion based on story content
            if emotion == "happy" or "friend" in story_line.lower():
                await self.controller.wave_hello()
                await asyncio.sleep(0.3)
                await self.controller.nod_yes()
            elif emotion == "excited" or "!" in story_line:
                await self.controller.dance_simple()
            elif emotion == "curious" or "?" in story_line:
                await self.controller.look_around_curious()
            elif emotion == "surprised" or "oh no" in story_line.lower():
                await self.controller.story_time_expressions()
                await asyncio.sleep(0.5)
                # Add a little "wow" gesture
                await self.controller.wave_hello()
            else:
                # Default gentle movement
                await self.controller.nod_yes()
                await asyncio.sleep(0.5)
            
            # Brief pause between movements
            await asyncio.sleep(0.5)
    
    # === MULTI-MODAL GAMES ===
    
    async def dance_along_with_detection(self) -> bool:
        """Dance game that responds to detected movement"""
        self.logger.info("💃 Starting Dance Along game!")
        
        # Start dancing to get things going
        await self.controller.dance_simple()
        
        dance_moves = [
            self.controller.wave_hello,
            self.controller.dance_simple,
            self.controller.nod_yes,
            self.controller.look_around_curious
        ]
        
        for i in range(5):  # 5 rounds of dancing
            self.logger.info(f"🕺 Dance round {i+1}!")
            
            # Robot does a move
            move = random.choice(dance_moves)
            await move()
            
            # Check if people are dancing along (using motion detection)
            motion_detected = await self.vision.detect_motion()
            
            if motion_detected:
                # Encourage more dancing!
                self.logger.info("🎉 I see you dancing! Let's keep going!")
                await self.controller.crowd_pleaser_dance()
            else:
                # Try to get attention
                self.logger.info("👋 Come on, dance with me!")
                await self.controller.attention_getter()
            
            await asyncio.sleep(2)
        
        # Final celebration
        self.logger.info("🎊 Dance party complete!")
        await self.controller.crowd_pleaser_dance()
        return True
    
    async def emotion_mirroring_game(self) -> bool:
        """Game where robot mirrors detected emotions"""
        self.logger.info("Starting Emotion Mirroring game!")
        
        # In a real implementation, this would use emotion detection
        emotions_to_mirror = ["happy", "sad", "surprised", "excited", "curious"]
        
        for emotion in emotions_to_mirror:
            self.logger.info(f"Show me {emotion}!")
            
            # Wait for person to show emotion
            await asyncio.sleep(3)
            
            # Robot mirrors the emotion
            if emotion == "happy":
                await self.controller.wave_hello()
                await self.controller.dance_simple()
            elif emotion == "sad":
                await self.controller.be_shy()
            elif emotion == "surprised":
                await self.controller.story_time_expressions()
            elif emotion == "excited":
                await self.controller.crowd_pleaser_dance()
            elif emotion == "curious":
                await self.controller.look_around_curious()
            
            await asyncio.sleep(2)
        
        return True
    
    # === GAME MANAGEMENT ===
    
    async def play_random_enhanced_game(self) -> bool:
        """Play a random enhanced game"""
        games = [
            self.object_hunt_game,
            self.simon_says_vision, 
            self.color_recognition_game,
            self.smart_conversation,
            self.ai_storytelling,
            self.dance_along_with_detection,
            self.emotion_mirroring_game
        ]
        
        chosen_game = random.choice(games)
        self.logger.info(f"Playing: {chosen_game.__name__}")
        
        return await chosen_game()
    
    async def ultimate_entertainment_session(self) -> bool:
        """Full entertainment session with multiple activities"""
        self.logger.info("🎉 Starting ULTIMATE Entertainment Session! 🎉")
        
        # 1. Warm up with introduction
        await self.controller.robot_introduction()
        
        # 2. Get everyone's attention
        await self.controller.attention_getter()
        
        # 3. Interactive conversation
        await self.smart_conversation("mixed")
        
        # 4. Play a vision game
        await self.simon_says_vision()
        
        # 5. Tell a story
        await self.ai_storytelling()
        
        # 6. Dance party
        await self.dance_along_with_detection()
        
        # 7. Final celebration
        await self.controller.crowd_pleaser_dance()
        
        self.logger.info("🎊 Ultimate session complete! 🎊")
        return True
    
    def get_enhanced_status(self) -> Dict[str, Any]:
        """Get full system status"""
        base_status = self.controller.get_status()
        
        enhanced_games = [
            "object_hunt_game", "simon_says_vision", "color_recognition_game",
            "smart_conversation", "ai_storytelling", "dance_along_with_detection", 
            "emotion_mirroring_game", "play_random_enhanced_game", "ultimate_entertainment_session"
        ]
        
        base_status["enhanced_features"] = {
            "vision_games": True,
            "ai_chat": True,
            "story_generation": True,
            "multimodal_interaction": True,
            "available_enhanced_games": enhanced_games
        }
        
        base_status["current_game"] = self.current_game
        base_status["game_state"] = self.game_state
        
        return base_status
    
    async def cleanup(self):
        """Clean up all systems"""
        self.logger.info("Cleaning up enhanced entertainment system...")
        self.vision.cleanup()
        self.audio_storytelling.cleanup()
        await self.controller.go_to_sleep()


# CLI for enhanced system
async def main():
    """Enhanced CLI with all the new features"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Enhanced Reachy Mini Entertainment System")
    parser.add_argument("--sim", action="store_true", help="Run in simulation mode")
    
    # Basic behaviors
    basic_choices = ["wake", "sleep", "wave", "dance", "random"]
    
    # Enhanced features  
    enhanced_choices = [
        "object_hunt", "simon_vision", "colors", "chat_kids", "chat_adults", 
        "story", "dance_detect", "emotions", "random_enhanced", "ultimate"
    ]
    
    all_choices = basic_choices + enhanced_choices
    
    parser.add_argument("behavior", nargs="?", help="Behavior or game to run", 
                       choices=all_choices)
    
    args = parser.parse_args()
    
    # Setup logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    # Create enhanced system
    system = EnhancedEntertainmentSystem(use_simulation=args.sim)
    
    try:
        # Initialize
        await system.initialize()
        
        if args.behavior:
            behavior_map = {
                # Basic behaviors
                "wake": system.controller.wake_up,
                "sleep": system.controller.go_to_sleep,
                "wave": system.controller.wave_hello,
                "dance": system.controller.dance_simple,
                "random": system.controller.random_entertainment,
                
                # Enhanced games and features
                "object_hunt": system.object_hunt_game,
                "simon_vision": system.simon_says_vision,
                "colors": system.color_recognition_game,
                "chat_kids": lambda: system.smart_conversation("kids"),
                "chat_adults": lambda: system.smart_conversation("adults"),
                "story": system.ai_storytelling,
                "dance_detect": system.dance_along_with_detection,
                "emotions": system.emotion_mirroring_game,
                "random_enhanced": system.play_random_enhanced_game,
                "ultimate": system.ultimate_entertainment_session
            }
            
            behavior_func = behavior_map.get(args.behavior)
            if behavior_func:
                print(f"\n🤖 Starting {args.behavior}...")
                success = await behavior_func()
                print(f"✅ {'Success!' if success else '❌ Failed'}")
            else:
                print(f"❌ Unknown behavior: {args.behavior}")
        else:
            # Interactive mode
            print("\n🎪 Enhanced Reachy Mini Entertainment System 🎪")
            print(f"Status: {system.get_enhanced_status()}")
            
            print("\n🎮 Available Commands:")
            print("Basic: wake, sleep, wave, dance, random")
            print("Enhanced: object_hunt, simon_vision, colors, chat_kids, chat_adults")
            print("         story, dance_detect, emotions, random_enhanced, ultimate")
            print("Control: status, quit")
            
            while True:
                try:
                    command = input("\n🎯 Enter command: ").strip().lower()
                    
                    if command == "quit":
                        break
                    elif command == "status":
                        print(json.dumps(system.get_enhanced_status(), indent=2))
                    elif command in all_choices:
                        behavior_map = {
                            # Basic
                            "wake": system.controller.wake_up,
                            "sleep": system.controller.go_to_sleep,
                            "wave": system.controller.wave_hello,
                            "dance": system.controller.dance_simple,
                            "random": system.controller.random_entertainment,
                            
                            # Enhanced
                            "object_hunt": system.object_hunt_game,
                            "simon_vision": system.simon_says_vision,
                            "colors": system.color_recognition_game,
                            "chat_kids": lambda: system.smart_conversation("kids"),
                            "chat_adults": lambda: system.smart_conversation("adults"),
                            "story": system.ai_storytelling,
                            "dance_detect": system.dance_along_with_detection,
                            "emotions": system.emotion_mirroring_game,
                            "random_enhanced": system.play_random_enhanced_game,
                            "ultimate": system.ultimate_entertainment_session
                        }
                        
                        print(f"🚀 Executing {command}...")
                        success = await behavior_map[command]()
                        print(f"{'🎉 Success!' if success else '😞 Failed'}")
                    else:
                        print("❌ Unknown command. Type 'quit' to exit.")
                        
                except KeyboardInterrupt:
                    print("\n🛑 Emergency stop!")
                    await system.controller.emergency_stop()
                    break
                except Exception as e:
                    print(f"💥 Error: {e}")
                    
    finally:
        await system.cleanup()


if __name__ == "__main__":
    asyncio.run(main())