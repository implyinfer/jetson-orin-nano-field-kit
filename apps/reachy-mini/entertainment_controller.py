#!/usr/bin/env python3
"""
Simplified Reachy Mini Entertainment Controller
A streamlined interface for entertaining interactions with the Reachy Mini robot.
"""

import asyncio
import logging
import random
import time
from typing import Optional, List, Dict, Any
from enum import Enum

import numpy as np
from scipy.spatial.transform import Rotation as R

try:
    from reachy_mini import ReachyMini
    REACHY_AVAILABLE = True
except ImportError:
    logging.warning("Reachy Mini SDK not available")
    REACHY_AVAILABLE = False


class EmotionState(Enum):
    """Robot emotional states for entertainment"""
    NEUTRAL = "neutral"
    HAPPY = "happy"
    CURIOUS = "curious"
    SLEEPY = "sleepy"
    EXCITED = "excited"
    SHY = "shy"


class EntertainmentController:
    """Simplified controller for Reachy Mini entertainment behaviors"""
    
    def __init__(self, use_simulation: bool = not REACHY_AVAILABLE):
        """Initialize the entertainment controller
        
        Args:
            use_simulation: If True, runs without real robot connection
        """
        self.logger = logging.getLogger(__name__)
        self.use_simulation = use_simulation
        self.robot: Optional[ReachyMini] = None
        self.current_emotion = EmotionState.NEUTRAL
        self.is_performing = False
        
        # Initialize robot connection
        if not use_simulation and REACHY_AVAILABLE:
            try:
                self.robot = ReachyMini(use_sim=False)
                self.logger.info("Connected to Reachy Mini robot")
            except Exception as e:
                self.logger.error(f"Failed to connect to robot: {e}")
                self.use_simulation = True
        else:
            self.logger.info("Running in simulation mode")
        
        # Initialize advanced behavior modules
        try:
            from entertainment_behaviors import KidFriendlyBehaviors, AudienceEntertainment
            self.kid_behaviors = KidFriendlyBehaviors(self)
            self.audience_behaviors = AudienceEntertainment(self)
        except ImportError:
            self.logger.warning("Advanced behaviors not available")
            self.kid_behaviors = None
            self.audience_behaviors = None
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.robot:
            self.robot.__exit__(exc_type, exc_val, exc_tb)
    
    async def wake_up(self) -> bool:
        """Wake up the robot with a friendly greeting"""
        try:
            self.logger.info("Waking up Reachy Mini...")
            if not self.use_simulation and self.robot:
                self.robot.wake_up()
            else:
                await asyncio.sleep(2)  # Simulate wake up time
            
            self.current_emotion = EmotionState.HAPPY
            return True
        except Exception as e:
            self.logger.error(f"Wake up failed: {e}")
            return False
    
    async def go_to_sleep(self) -> bool:
        """Put the robot to sleep"""
        try:
            self.logger.info("Putting Reachy Mini to sleep...")
            if not self.use_simulation and self.robot:
                self.robot.goto_sleep()
            else:
                await asyncio.sleep(2)  # Simulate sleep time
            
            self.current_emotion = EmotionState.SLEEPY
            return True
        except Exception as e:
            self.logger.error(f"Go to sleep failed: {e}")
            return False
    
    async def wave_hello(self) -> bool:
        """Perform a friendly wave gesture"""
        try:
            self.logger.info("Waving hello...")
            self.is_performing = True
            
            if not self.use_simulation and self.robot:
                # Create wave motion with head and antennas
                base_pose = np.eye(4)
                
                # Wave sequence: tilt head and move antennas
                for i in range(3):
                    # Tilt head slightly
                    tilt_angle = 15 * (1 if i % 2 == 0 else -1)
                    pose = base_pose.copy()
                    pose[:3, :3] = R.from_euler('z', tilt_angle, degrees=True).as_matrix()
                    
                    # Move antennas in wave pattern
                    antenna_pos = [0.5 * (1 if i % 2 == 0 else -1), -0.5 * (1 if i % 2 == 0 else -1)]
                    
                    self.robot.goto_target(head=pose, antennas=antenna_pos, duration=0.8)
                    await asyncio.sleep(0.8)
                
                # Return to neutral
                self.robot.goto_target(head=base_pose, antennas=[0.0, 0.0], duration=1.0)
            else:
                await asyncio.sleep(3)  # Simulate wave duration
            
            self.current_emotion = EmotionState.HAPPY
            return True
        except Exception as e:
            self.logger.error(f"Wave hello failed: {e}")
            return False
        finally:
            self.is_performing = False
    
    async def look_around_curious(self) -> bool:
        """Look around curiously like exploring the environment"""
        try:
            self.logger.info("Looking around curiously...")
            self.is_performing = True
            
            if not self.use_simulation and self.robot:
                # Look at different points in the environment
                look_points = [
                    (0.3, 0.2, 0.1),   # Right
                    (0.3, -0.2, 0.1),  # Left  
                    (0.3, 0.0, 0.2),   # Up
                    (0.3, 0.0, -0.1),  # Down
                    (0.3, 0.0, 0.0),   # Center
                ]
                
                for point in look_points:
                    self.robot.look_at_world(*point, duration=1.5)
                    # Move antennas to show interest
                    antenna_pos = [random.uniform(-0.3, 0.3), random.uniform(-0.3, 0.3)]
                    self.robot.set_target(antennas=antenna_pos)
                    await asyncio.sleep(1.8)
            else:
                await asyncio.sleep(8)  # Simulate looking duration
            
            self.current_emotion = EmotionState.CURIOUS
            return True
        except Exception as e:
            self.logger.error(f"Look around failed: {e}")
            return False
        finally:
            self.is_performing = False
    
    async def nod_yes(self) -> bool:
        """Perform a nodding gesture"""
        try:
            self.logger.info("Nodding yes...")
            self.is_performing = True
            
            if not self.use_simulation and self.robot:
                base_pose = np.eye(4)
                
                # Nod sequence
                for i in range(3):
                    # Nod down
                    pose_down = base_pose.copy()
                    pose_down[:3, :3] = R.from_euler('y', -20, degrees=True).as_matrix()
                    self.robot.goto_target(head=pose_down, duration=0.4)
                    await asyncio.sleep(0.4)
                    
                    # Nod up
                    pose_up = base_pose.copy()
                    pose_up[:3, :3] = R.from_euler('y', 10, degrees=True).as_matrix()
                    self.robot.goto_target(head=pose_up, duration=0.4)
                    await asyncio.sleep(0.4)
                
                # Return to neutral
                self.robot.goto_target(head=base_pose, duration=0.5)
            else:
                await asyncio.sleep(2.5)
            
            self.current_emotion = EmotionState.HAPPY
            return True
        except Exception as e:
            self.logger.error(f"Nod yes failed: {e}")
            return False
        finally:
            self.is_performing = False
    
    async def shake_head_no(self) -> bool:
        """Perform a head shaking gesture"""
        try:
            self.logger.info("Shaking head no...")
            self.is_performing = True
            
            if not self.use_simulation and self.robot:
                base_pose = np.eye(4)
                
                # Shake sequence
                for i in range(3):
                    # Turn left
                    pose_left = base_pose.copy()
                    pose_left[:3, :3] = R.from_euler('z', -30, degrees=True).as_matrix()
                    self.robot.goto_target(head=pose_left, duration=0.3)
                    await asyncio.sleep(0.3)
                    
                    # Turn right
                    pose_right = base_pose.copy()
                    pose_right[:3, :3] = R.from_euler('z', 30, degrees=True).as_matrix()
                    self.robot.goto_target(head=pose_right, duration=0.3)
                    await asyncio.sleep(0.3)
                
                # Return to neutral
                self.robot.goto_target(head=base_pose, duration=0.5)
            else:
                await asyncio.sleep(2.3)
            
            return True
        except Exception as e:
            self.logger.error(f"Shake head no failed: {e}")
            return False
        finally:
            self.is_performing = False
    
    async def dance_simple(self) -> bool:
        """Perform a simple dance routine"""
        try:
            self.logger.info("Dancing...")
            self.is_performing = True
            
            if not self.use_simulation and self.robot:
                base_pose = np.eye(4)
                
                # Dance moves
                moves = [
                    # Tilt left with antennas
                    (R.from_euler('xyz', [0, 0, -20], degrees=True).as_matrix(), [0.8, -0.8]),
                    # Tilt right with antennas  
                    (R.from_euler('xyz', [0, 0, 20], degrees=True).as_matrix(), [-0.8, 0.8]),
                    # Bob up and down
                    (R.from_euler('xyz', [15, 0, 0], degrees=True).as_matrix(), [0.5, 0.5]),
                    (R.from_euler('xyz', [-15, 0, 0], degrees=True).as_matrix(), [-0.5, -0.5]),
                ]
                
                # Perform dance sequence twice
                for cycle in range(2):
                    for rotation_matrix, antennas in moves:
                        pose = base_pose.copy()
                        pose[:3, :3] = rotation_matrix
                        self.robot.goto_target(head=pose, antennas=antennas, duration=0.6)
                        await asyncio.sleep(0.6)
                
                # Return to neutral
                self.robot.goto_target(head=base_pose, antennas=[0.0, 0.0], duration=1.0)
            else:
                await asyncio.sleep(6)
            
            self.current_emotion = EmotionState.EXCITED
            return True
        except Exception as e:
            self.logger.error(f"Dance failed: {e}")
            return False
        finally:
            self.is_performing = False
    
    async def be_shy(self) -> bool:
        """Display shy behavior by looking down and moving antennas inward"""
        try:
            self.logger.info("Being shy...")
            self.is_performing = True
            
            if not self.use_simulation and self.robot:
                # Shy pose: look down, antennas close together
                base_pose = np.eye(4)
                shy_pose = base_pose.copy()
                shy_pose[:3, :3] = R.from_euler('y', -30, degrees=True).as_matrix()
                
                # Move to shy position
                self.robot.goto_target(head=shy_pose, antennas=[0.2, -0.2], duration=2.0)
                await asyncio.sleep(3.0)
                
                # Peek up slightly
                peek_pose = base_pose.copy()
                peek_pose[:3, :3] = R.from_euler('y', -10, degrees=True).as_matrix()
                self.robot.goto_target(head=peek_pose, duration=1.0)
                await asyncio.sleep(2.0)
                
                # Return to neutral gradually
                self.robot.goto_target(head=base_pose, antennas=[0.0, 0.0], duration=2.0)
            else:
                await asyncio.sleep(5)
            
            self.current_emotion = EmotionState.SHY
            return True
        except Exception as e:
            self.logger.error(f"Be shy failed: {e}")
            return False
        finally:
            self.is_performing = False
    
    async def random_entertainment(self) -> bool:
        """Perform a random entertainment behavior"""
        behaviors = [
            self.wave_hello,
            self.look_around_curious,
            self.nod_yes,
            self.shake_head_no,
            self.dance_simple,
            self.be_shy
        ]
        
        # Add kid and audience behaviors if available
        if self.kid_behaviors:
            behaviors.extend([
                self.kid_behaviors.peek_a_boo,
                self.kid_behaviors.attention_getter,
                self.kid_behaviors.story_time_expressions
            ])
        
        if self.audience_behaviors:
            behaviors.extend([
                self.audience_behaviors.crowd_pleaser_dance,
                self.audience_behaviors.interactive_mirror
            ])
        
        chosen_behavior = random.choice(behaviors)
        return await chosen_behavior()
    
    # Kid-friendly behavior shortcuts
    async def peek_a_boo(self) -> bool:
        """Play peek-a-boo game"""
        if self.kid_behaviors:
            return await self.kid_behaviors.peek_a_boo()
        return False
    
    async def follow_the_leader(self) -> bool:
        """Demonstrate movements for kids to copy"""
        if self.kid_behaviors:
            return await self.kid_behaviors.follow_the_leader()
        return False
    
    async def counting_game(self) -> bool:
        """Count from 1 to 5 with movements"""
        if self.kid_behaviors:
            return await self.kid_behaviors.counting_game()
        return False
    
    async def simon_says_demo(self) -> bool:
        """Demonstrate Simon Says game"""
        if self.kid_behaviors:
            return await self.kid_behaviors.simon_says_demo()
        return False
    
    async def story_time_expressions(self) -> bool:
        """Show different emotions for storytelling"""
        if self.kid_behaviors:
            return await self.kid_behaviors.story_time_expressions()
        return False
    
    async def attention_getter(self) -> bool:
        """Get attention when kids are distracted"""
        if self.kid_behaviors:
            return await self.kid_behaviors.attention_getter()
        return False
    
    # Audience entertainment shortcuts
    async def robot_introduction(self) -> bool:
        """Introduce the robot to an audience"""
        if self.audience_behaviors:
            return await self.audience_behaviors.robot_introduction()
        return False
    
    async def crowd_pleaser_dance(self) -> bool:
        """Entertaining dance routine for crowds"""
        if self.audience_behaviors:
            return await self.audience_behaviors.crowd_pleaser_dance()
        return False
    
    async def interactive_mirror(self) -> bool:
        """Mirror movements as if copying the audience"""
        if self.audience_behaviors:
            return await self.audience_behaviors.interactive_mirror()
        return False
    
    def get_status(self) -> Dict[str, Any]:
        """Get current status of the entertainment controller"""
        basic_behaviors = [
            "wake_up", "go_to_sleep", "wave_hello", "look_around_curious",
            "nod_yes", "shake_head_no", "dance_simple", "be_shy", "random_entertainment"
        ]
        
        kid_behaviors = []
        audience_behaviors = []
        
        if self.kid_behaviors:
            kid_behaviors = [
                "peek_a_boo", "follow_the_leader", "counting_game", 
                "simon_says_demo", "story_time_expressions", "attention_getter"
            ]
        
        if self.audience_behaviors:
            audience_behaviors = [
                "robot_introduction", "crowd_pleaser_dance", "interactive_mirror"
            ]
        
        return {
            "simulation_mode": self.use_simulation,
            "robot_connected": self.robot is not None,
            "current_emotion": self.current_emotion.value,
            "is_performing": self.is_performing,
            "available_behaviors": {
                "basic": basic_behaviors,
                "kid_friendly": kid_behaviors,
                "audience": audience_behaviors
            }
        }
    
    async def emergency_stop(self) -> bool:
        """Emergency stop - return to neutral position immediately"""
        try:
            self.logger.warning("Emergency stop activated")
            self.is_performing = False
            
            if not self.use_simulation and self.robot:
                # Set to neutral pose immediately
                neutral_pose = np.eye(4)
                self.robot.set_target(head=neutral_pose, antennas=[0.0, 0.0])
            
            self.current_emotion = EmotionState.NEUTRAL
            return True
        except Exception as e:
            self.logger.error(f"Emergency stop failed: {e}")
            return False


# Simple CLI for testing entertainment behaviors
async def main():
    """Simple CLI for testing entertainment behaviors"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Reachy Mini Entertainment Controller")
    parser.add_argument("--sim", action="store_true", help="Run in simulation mode")
    parser.add_argument("behavior", nargs="?", help="Behavior to perform", 
                       choices=["wake", "sleep", "wave", "curious", "nod", "shake", "dance", "shy", "random"])
    
    args = parser.parse_args()
    
    # Setup logging
    logging.basicConfig(level=logging.INFO)
    
    # Create controller
    controller = EntertainmentController(use_simulation=args.sim)
    
    try:
        if args.behavior:
            behavior_map = {
                "wake": controller.wake_up,
                "sleep": controller.go_to_sleep, 
                "wave": controller.wave_hello,
                "curious": controller.look_around_curious,
                "nod": controller.nod_yes,
                "shake": controller.shake_head_no,
                "dance": controller.dance_simple,
                "shy": controller.be_shy,
                "random": controller.random_entertainment
            }
            
            behavior_func = behavior_map.get(args.behavior)
            if behavior_func:
                success = await behavior_func()
                print(f"Behavior {'succeeded' if success else 'failed'}")
            else:
                print(f"Unknown behavior: {args.behavior}")
        else:
            # Interactive mode
            print("Reachy Mini Entertainment Controller")
            print("Status:", controller.get_status())
            print("Available commands: wake, sleep, wave, curious, nod, shake, dance, shy, random, quit")
            
            while True:
                try:
                    command = input("\nEnter command: ").strip().lower()
                    if command == "quit":
                        break
                    elif command in ["wake", "sleep", "wave", "curious", "nod", "shake", "dance", "shy", "random"]:
                        behavior_map = {
                            "wake": controller.wake_up,
                            "sleep": controller.go_to_sleep,
                            "wave": controller.wave_hello,
                            "curious": controller.look_around_curious,
                            "nod": controller.nod_yes,
                            "shake": controller.shake_head_no,
                            "dance": controller.dance_simple,
                            "shy": controller.be_shy,
                            "random": controller.random_entertainment
                        }
                        
                        print(f"Executing {command}...")
                        success = await behavior_map[command]()
                        print(f"Result: {'Success' if success else 'Failed'}")
                    elif command == "status":
                        print(controller.get_status())
                    else:
                        print("Unknown command")
                except KeyboardInterrupt:
                    await controller.emergency_stop()
                    break
                except Exception as e:
                    print(f"Error: {e}")
                    
    finally:
        controller.__exit__(None, None, None)


if __name__ == "__main__":
    asyncio.run(main())