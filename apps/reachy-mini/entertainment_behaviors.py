#!/usr/bin/env python3
"""
Advanced Entertainment Behaviors for Reachy Mini
Special behaviors designed to entertain kids and audiences.
"""

import asyncio
import logging
import random
import time
from typing import Optional, List, Dict, Any, Tuple

import numpy as np
from scipy.spatial.transform import Rotation as R

try:
    from reachy_mini import ReachyMini
    REACHY_AVAILABLE = True
except ImportError:
    REACHY_AVAILABLE = False


class KidFriendlyBehaviors:
    """Collection of kid-friendly entertainment behaviors"""
    
    def __init__(self, controller):
        self.controller = controller
        self.robot = controller.robot
        self.logger = logging.getLogger(__name__)
    
    async def peek_a_boo(self) -> bool:
        """Play peek-a-boo game with kids"""
        try:
            self.logger.info("Playing peek-a-boo...")
            
            if not self.controller.use_simulation and self.robot:
                base_pose = np.eye(4)
                
                # "Where are you?" - look around searching
                for _ in range(2):
                    # Look left
                    look_left = base_pose.copy()
                    look_left[:3, :3] = R.from_euler('z', -45, degrees=True).as_matrix()
                    self.robot.goto_target(head=look_left, antennas=[0.5, -0.5], duration=0.8)
                    await asyncio.sleep(1.0)
                    
                    # Look right
                    look_right = base_pose.copy() 
                    look_right[:3, :3] = R.from_euler('z', 45, degrees=True).as_matrix()
                    self.robot.goto_target(head=look_right, antennas=[-0.5, 0.5], duration=0.8)
                    await asyncio.sleep(1.0)
                
                # Hide behind "hands" (antennas forward)
                hide_pose = base_pose.copy()
                hide_pose[:3, :3] = R.from_euler('y', -15, degrees=True).as_matrix()
                self.robot.goto_target(head=hide_pose, antennas=[1.0, 1.0], duration=1.0)
                await asyncio.sleep(2.0)
                
                # PEEK-A-BOO! (sudden reveal with excited movement)
                reveal_pose = base_pose.copy()
                reveal_pose[:3, :3] = R.from_euler('y', 10, degrees=True).as_matrix()
                self.robot.goto_target(head=reveal_pose, antennas=[-1.2, 1.2], duration=0.3)
                await asyncio.sleep(0.5)
                
                # Excited wiggles
                for i in range(4):
                    wiggle_angle = 15 * (1 if i % 2 == 0 else -1)
                    wiggle_pose = base_pose.copy()
                    wiggle_pose[:3, :3] = R.from_euler('z', wiggle_angle, degrees=True).as_matrix()
                    antenna_pos = [0.8 * (1 if i % 2 == 0 else -1), 0.8 * (-1 if i % 2 == 0 else 1)]
                    self.robot.goto_target(head=wiggle_pose, antennas=antenna_pos, duration=0.3)
                    await asyncio.sleep(0.3)
                
                # Return to happy neutral
                self.robot.goto_target(head=base_pose, antennas=[0.0, 0.0], duration=1.0)
            else:
                await asyncio.sleep(8)  # Simulate full sequence
            
            return True
        except Exception as e:
            self.logger.error(f"Peek-a-boo failed: {e}")
            return False
    
    async def follow_the_leader(self) -> bool:
        """Demonstrate various movements for kids to copy"""
        try:
            self.logger.info("Starting follow the leader...")
            
            if not self.controller.use_simulation and self.robot:
                base_pose = np.eye(4)
                
                # Simple movements for kids to follow
                moves = [
                    # Touch your nose (look down)
                    (R.from_euler('y', -30, degrees=True).as_matrix(), [0.3, -0.3], "Touch your nose!"),
                    # Look up at the sky
                    (R.from_euler('y', 20, degrees=True).as_matrix(), [0.5, 0.5], "Look at the sky!"),
                    # Turn your head left
                    (R.from_euler('z', -40, degrees=True).as_matrix(), [-0.8, 0.2], "Turn left!"),
                    # Turn your head right  
                    (R.from_euler('z', 40, degrees=True).as_matrix(), [0.2, -0.8], "Turn right!"),
                    # Wiggle like me!
                    (R.from_euler('xyz', [10, 0, -20], degrees=True).as_matrix(), [0.7, -0.7], "Wiggle!"),
                ]
                
                for rotation_matrix, antennas, instruction in moves:
                    pose = base_pose.copy()
                    pose[:3, :3] = rotation_matrix
                    
                    # Move to position
                    self.robot.goto_target(head=pose, antennas=antennas, duration=1.0)
                    await asyncio.sleep(2.0)  # Hold for kids to copy
                    
                    # Return to center briefly
                    self.robot.goto_target(head=base_pose, antennas=[0.0, 0.0], duration=0.8)
                    await asyncio.sleep(1.0)
                
                # Final celebration
                for i in range(3):
                    celebrate_pose = base_pose.copy()
                    celebrate_pose[:3, :3] = R.from_euler('z', 20 * (1 if i % 2 == 0 else -1), degrees=True).as_matrix()
                    self.robot.goto_target(head=celebrate_pose, antennas=[1.0, 1.0], duration=0.4)
                    await asyncio.sleep(0.4)
                    
                self.robot.goto_target(head=base_pose, antennas=[0.0, 0.0], duration=1.0)
            else:
                await asyncio.sleep(12)
            
            return True
        except Exception as e:
            self.logger.error(f"Follow the leader failed: {e}")
            return False
    
    async def counting_game(self) -> bool:
        """Count from 1 to 5 with head movements"""
        try:
            self.logger.info("Starting counting game...")
            
            if not self.controller.use_simulation and self.robot:
                base_pose = np.eye(4)
                
                # Count 1 to 5 with distinct poses
                counting_poses = [
                    # 1 - Point up
                    (R.from_euler('y', 25, degrees=True).as_matrix(), [0.2, 0.2]),
                    # 2 - Look left and right (two movements) 
                    (R.from_euler('z', -30, degrees=True).as_matrix(), [-0.5, 0.5]),
                    # 3 - Three nods
                    (R.from_euler('y', -15, degrees=True).as_matrix(), [0.4, -0.4]),
                    # 4 - Four corners (up, down, left, right indication)
                    (R.from_euler('xyz', [15, 0, 30], degrees=True).as_matrix(), [0.6, -0.3]),
                    # 5 - Big celebration 
                    (R.from_euler('xyz', [10, 0, -25], degrees=True).as_matrix(), [1.0, 1.0])
                ]
                
                for count, (pose_matrix, antennas) in enumerate(counting_poses, 1):
                    # Announce number with movement
                    pose = base_pose.copy()
                    pose[:3, :3] = pose_matrix
                    
                    if count == 2:  # Special case for "2" - two movements
                        # Left
                        left_pose = base_pose.copy()
                        left_pose[:3, :3] = R.from_euler('z', -30, degrees=True).as_matrix()
                        self.robot.goto_target(head=left_pose, antennas=[-0.5, 0.5], duration=0.6)
                        await asyncio.sleep(0.8)
                        # Right
                        right_pose = base_pose.copy()
                        right_pose[:3, :3] = R.from_euler('z', 30, degrees=True).as_matrix()
                        self.robot.goto_target(head=right_pose, antennas=[0.5, -0.5], duration=0.6)
                        await asyncio.sleep(0.8)
                    elif count == 3:  # Three nods for "3"
                        for _ in range(3):
                            nod_pose = base_pose.copy()
                            nod_pose[:3, :3] = R.from_euler('y', -20, degrees=True).as_matrix()
                            self.robot.goto_target(head=nod_pose, antennas=antennas, duration=0.4)
                            await asyncio.sleep(0.4)
                            self.robot.goto_target(head=base_pose, antennas=[0.0, 0.0], duration=0.3)
                            await asyncio.sleep(0.3)
                    elif count == 5:  # Big celebration for "5"
                        for _ in range(5):
                            party_pose = base_pose.copy()
                            party_angle = random.uniform(-20, 20)
                            party_pose[:3, :3] = R.from_euler('z', party_angle, degrees=True).as_matrix()
                            party_antennas = [random.uniform(-1.0, 1.0), random.uniform(-1.0, 1.0)]
                            self.robot.goto_target(head=party_pose, antennas=party_antennas, duration=0.3)
                            await asyncio.sleep(0.3)
                    else:
                        # Standard pose
                        self.robot.goto_target(head=pose, antennas=antennas, duration=1.0)
                        await asyncio.sleep(1.5)
                    
                    # Brief pause between numbers
                    self.robot.goto_target(head=base_pose, antennas=[0.0, 0.0], duration=0.5)
                    await asyncio.sleep(0.7)
                
            else:
                await asyncio.sleep(15)
            
            return True
        except Exception as e:
            self.logger.error(f"Counting game failed: {e}")
            return False
    
    async def simon_says_demo(self) -> bool:
        """Demonstrate Simon Says commands for interactive play"""
        try:
            self.logger.info("Starting Simon Says demo...")
            
            if not self.controller.use_simulation and self.robot:
                base_pose = np.eye(4)
                
                # Simon Says commands with clear movements
                commands = [
                    # "Simon says touch your head" 
                    (R.from_euler('y', -10, degrees=True).as_matrix(), [0.1, -0.1], True),
                    # "Simon says look up"
                    (R.from_euler('y', 30, degrees=True).as_matrix(), [0.3, 0.3], True),
                    # "Put your hands down" (NOT Simon says - should be ignored)
                    (R.from_euler('y', 0, degrees=True).as_matrix(), [-0.8, -0.8], False),
                    # "Simon says wave hello"
                    (R.from_euler('z', 20, degrees=True).as_matrix(), [0.8, -0.8], True),
                    # "Turn around" (NOT Simon says)
                    (R.from_euler('z', -45, degrees=True).as_matrix(), [0.0, 0.0], False)
                ]
                
                for pose_matrix, antennas, is_simon_says in commands:
                    pose = base_pose.copy()
                    pose[:3, :3] = pose_matrix
                    
                    if is_simon_says:
                        # Execute the command enthusiastically
                        self.robot.goto_target(head=pose, antennas=antennas, duration=1.0)
                        await asyncio.sleep(2.0)
                        
                        # Show approval with a little wiggle
                        approve_pose = base_pose.copy()
                        approve_pose[:3, :3] = R.from_euler('z', 10, degrees=True).as_matrix()
                        self.robot.goto_target(head=approve_pose, antennas=[0.5, 0.5], duration=0.3)
                        await asyncio.sleep(0.5)
                    else:
                        # Don't do the command - stay neutral but show "no"
                        shake_left = base_pose.copy()
                        shake_left[:3, :3] = R.from_euler('z', -15, degrees=True).as_matrix()
                        self.robot.goto_target(head=shake_left, antennas=[-0.3, 0.3], duration=0.4)
                        await asyncio.sleep(0.4)
                        
                        shake_right = base_pose.copy()
                        shake_right[:3, :3] = R.from_euler('z', 15, degrees=True).as_matrix()
                        self.robot.goto_target(head=shake_right, antennas=[0.3, -0.3], duration=0.4)
                        await asyncio.sleep(0.4)
                    
                    # Return to neutral
                    self.robot.goto_target(head=base_pose, antennas=[0.0, 0.0], duration=0.8)
                    await asyncio.sleep(1.0)
                
            else:
                await asyncio.sleep(18)
            
            return True
        except Exception as e:
            self.logger.error(f"Simon Says demo failed: {e}")
            return False
    
    async def story_time_expressions(self) -> bool:
        """Demonstrate different emotions for storytelling"""
        try:
            self.logger.info("Showing story time expressions...")
            
            if not self.controller.use_simulation and self.robot:
                base_pose = np.eye(4)
                
                # Different emotional expressions for stories
                expressions = [
                    # Happy
                    (R.from_euler('y', 15, degrees=True).as_matrix(), [0.6, 0.6], "Happy"),
                    # Sad  
                    (R.from_euler('y', -25, degrees=True).as_matrix(), [0.1, 0.1], "Sad"),
                    # Surprised
                    (R.from_euler('y', 20, degrees=True).as_matrix(), [1.0, 1.0], "Surprised"),
                    # Angry
                    (R.from_euler('xyz', [5, 0, -10], degrees=True).as_matrix(), [-0.8, -0.8], "Angry"),
                    # Confused
                    (R.from_euler('z', 25, degrees=True).as_matrix(), [0.3, -0.7], "Confused"),
                    # Excited
                    (R.from_euler('xyz', [15, 5, 15], degrees=True).as_matrix(), [1.2, -1.2], "Excited")
                ]
                
                for pose_matrix, antennas, emotion in expressions:
                    pose = base_pose.copy()
                    pose[:3, :3] = pose_matrix
                    
                    # Move to emotional pose
                    self.robot.goto_target(head=pose, antennas=antennas, duration=1.2)
                    
                    # Hold expression with slight movement to make it more alive
                    if emotion == "Excited":
                        # Extra wiggles for excited
                        for _ in range(3):
                            wiggle_pose = pose.copy()
                            wiggle_offset = R.from_euler('z', random.uniform(-10, 10), degrees=True).as_matrix()
                            wiggle_pose[:3, :3] = wiggle_pose[:3, :3] @ wiggle_offset
                            wiggle_antennas = [a + random.uniform(-0.2, 0.2) for a in antennas]
                            self.robot.goto_target(head=wiggle_pose, antennas=wiggle_antennas, duration=0.3)
                            await asyncio.sleep(0.3)
                    elif emotion == "Confused":
                        # Little head tilts for confusion
                        for tilt in [-15, 15, -10]:
                            tilt_pose = base_pose.copy()
                            tilt_pose[:3, :3] = R.from_euler('z', 25 + tilt, degrees=True).as_matrix()
                            self.robot.goto_target(head=tilt_pose, antennas=antennas, duration=0.4)
                            await asyncio.sleep(0.5)
                    else:
                        await asyncio.sleep(2.0)
                    
                    # Brief neutral between expressions
                    self.robot.goto_target(head=base_pose, antennas=[0.0, 0.0], duration=0.8)
                    await asyncio.sleep(0.5)
                
            else:
                await asyncio.sleep(20)
            
            return True
        except Exception as e:
            self.logger.error(f"Story time expressions failed: {e}")
            return False
    
    async def attention_getter(self) -> bool:
        """Get attention when kids are distracted"""
        try:
            self.logger.info("Getting attention...")
            
            if not self.controller.use_simulation and self.robot:
                base_pose = np.eye(4)
                
                # Big attention-getting movements
                # Phase 1: Big wave
                for _ in range(2):
                    wave_pose = base_pose.copy()
                    wave_pose[:3, :3] = R.from_euler('xyz', [20, 10, 30], degrees=True).as_matrix()
                    self.robot.goto_target(head=wave_pose, antennas=[1.2, -0.3], duration=0.4)
                    await asyncio.sleep(0.4)
                    
                    wave_pose2 = base_pose.copy()
                    wave_pose2[:3, :3] = R.from_euler('xyz', [20, 10, -30], degrees=True).as_matrix()  
                    self.robot.goto_target(head=wave_pose2, antennas=[-0.3, 1.2], duration=0.4)
                    await asyncio.sleep(0.4)
                
                # Phase 2: Look left and right (like calling "hey!")
                for direction in [-50, 50, -30, 30]:
                    look_pose = base_pose.copy()
                    look_pose[:3, :3] = R.from_euler('z', direction, degrees=True).as_matrix()
                    antenna_pos = [0.8 if direction > 0 else -0.8, -0.8 if direction > 0 else 0.8]
                    self.robot.goto_target(head=look_pose, antennas=antenna_pos, duration=0.5)
                    await asyncio.sleep(0.6)
                
                # Phase 3: Excited bouncing
                for i in range(4):
                    bounce_pose = base_pose.copy()
                    bounce_y = 20 if i % 2 == 0 else -10
                    bounce_pose[:3, :3] = R.from_euler('y', bounce_y, degrees=True).as_matrix()
                    bounce_antennas = [0.8, 0.8] if i % 2 == 0 else [-0.5, -0.5]
                    self.robot.goto_target(head=bounce_pose, antennas=bounce_antennas, duration=0.3)
                    await asyncio.sleep(0.3)
                
                # Final pose - friendly and ready
                ready_pose = base_pose.copy()
                ready_pose[:3, :3] = R.from_euler('y', 10, degrees=True).as_matrix()
                self.robot.goto_target(head=ready_pose, antennas=[0.3, 0.3], duration=1.0)
                await asyncio.sleep(1.0)
                
            else:
                await asyncio.sleep(8)
            
            return True
        except Exception as e:
            self.logger.error(f"Attention getter failed: {e}")
            return False


class AudienceEntertainment:
    """Entertainment behaviors for general audiences"""
    
    def __init__(self, controller):
        self.controller = controller
        self.robot = controller.robot
        self.logger = logging.getLogger(__name__)
    
    async def robot_introduction(self) -> bool:
        """Introduce the robot to an audience"""
        try:
            self.logger.info("Performing robot introduction...")
            
            if not self.controller.use_simulation and self.robot:
                base_pose = np.eye(4)
                
                # Greeting wave
                greeting_pose = base_pose.copy()
                greeting_pose[:3, :3] = R.from_euler('xyz', [10, 5, 25], degrees=True).as_matrix()
                self.robot.goto_target(head=greeting_pose, antennas=[0.8, -0.5], duration=1.5)
                await asyncio.sleep(2.0)
                
                # Look around at audience
                look_points = [
                    (30, [0.6, 0.3]),   # Right side
                    (-30, [-0.3, 0.6]), # Left side
                    (0, [0.4, 0.4])     # Center
                ]
                
                for angle, antennas in look_points:
                    look_pose = base_pose.copy()
                    look_pose[:3, :3] = R.from_euler('z', angle, degrees=True).as_matrix()
                    self.robot.goto_target(head=look_pose, antennas=antennas, duration=1.0)
                    await asyncio.sleep(1.5)
                
                # Friendly bow
                bow_pose = base_pose.copy()
                bow_pose[:3, :3] = R.from_euler('y', -25, degrees=True).as_matrix()
                self.robot.goto_target(head=bow_pose, antennas=[0.1, 0.1], duration=1.5)
                await asyncio.sleep(2.0)
                
                # Back to neutral with happy antennas
                self.robot.goto_target(head=base_pose, antennas=[0.5, 0.5], duration=1.0)
                
            else:
                await asyncio.sleep(10)
            
            return True
        except Exception as e:
            self.logger.error(f"Robot introduction failed: {e}")
            return False
    
    async def crowd_pleaser_dance(self) -> bool:
        """Entertaining dance routine for crowds"""
        try:
            self.logger.info("Performing crowd pleaser dance...")
            
            if not self.controller.use_simulation and self.robot:
                base_pose = np.eye(4)
                
                # Upbeat dance sequence
                dance_moves = [
                    # Move 1: Side to side sway
                    (R.from_euler('xyz', [5, 0, -25], degrees=True).as_matrix(), [0.9, -0.3]),
                    (R.from_euler('xyz', [5, 0, 25], degrees=True).as_matrix(), [-0.3, 0.9]),
                    # Move 2: Up and down bob
                    (R.from_euler('xyz', [25, 0, 0], degrees=True).as_matrix(), [0.7, 0.7]),
                    (R.from_euler('xyz', [-15, 0, 0], degrees=True).as_matrix(), [-0.4, -0.4]),
                    # Move 3: Twist and shout
                    (R.from_euler('xyz', [10, 15, -20], degrees=True).as_matrix(), [1.1, -0.8]),
                    (R.from_euler('xyz', [10, -15, 20], degrees=True).as_matrix(), [-0.8, 1.1]),
                    # Move 4: Figure 8 head movement
                    (R.from_euler('xyz', [0, 10, 30], degrees=True).as_matrix(), [0.6, 0.2]),
                    (R.from_euler('xyz', [0, -10, -30], degrees=True).as_matrix(), [0.2, 0.6]),
                ]
                
                # Perform dance sequence twice for full effect
                for round_num in range(2):
                    for i, (rotation_matrix, antennas) in enumerate(dance_moves):
                        pose = base_pose.copy()
                        pose[:3, :3] = rotation_matrix
                        
                        # Vary timing for rhythm
                        duration = 0.4 if i % 2 == 0 else 0.6
                        self.robot.goto_target(head=pose, antennas=antennas, duration=duration)
                        await asyncio.sleep(duration + 0.1)
                
                # Grand finale spin (if possible with head constraints)
                for spin_angle in range(0, 360, 45):
                    if spin_angle > 180:  # Don't overrotate
                        spin_angle = 360 - spin_angle
                    finale_pose = base_pose.copy()
                    finale_pose[:3, :3] = R.from_euler('z', min(spin_angle, 45), degrees=True).as_matrix()
                    finale_antennas = [1.0 * np.cos(np.radians(spin_angle * 2)), 
                                     1.0 * np.sin(np.radians(spin_angle * 2))]
                    self.robot.goto_target(head=finale_pose, antennas=finale_antennas, duration=0.2)
                    await asyncio.sleep(0.25)
                
                # Final pose
                final_pose = base_pose.copy()
                final_pose[:3, :3] = R.from_euler('y', 15, degrees=True).as_matrix()
                self.robot.goto_target(head=final_pose, antennas=[0.8, 0.8], duration=1.0)
                
            else:
                await asyncio.sleep(15)
            
            return True
        except Exception as e:
            self.logger.error(f"Crowd pleaser dance failed: {e}")
            return False
    
    async def interactive_mirror(self) -> bool:
        """Mirror movements as if copying the audience"""
        try:
            self.logger.info("Starting interactive mirror mode...")
            
            if not self.controller.use_simulation and self.robot:
                base_pose = np.eye(4)
                
                # Simulate different "mirrored" movements
                mirror_moves = [
                    # "Person waves" - robot waves back
                    (R.from_euler('z', 30, degrees=True).as_matrix(), [0.8, -0.5], "Wave back"),
                    # "Person nods" - robot nods 
                    (R.from_euler('y', -20, degrees=True).as_matrix(), [0.2, 0.2], "Nod back"),
                    # "Person tilts head" - robot tilts opposite way (mirror)
                    (R.from_euler('z', -25, degrees=True).as_matrix(), [0.4, -0.4], "Mirror tilt"),
                    # "Person raises hand" - robot raises antennas
                    (R.from_euler('y', 10, degrees=True).as_matrix(), [1.0, 1.0], "Raise antennas"),
                    # "Person looks around" - robot looks around
                    (R.from_euler('z', 40, degrees=True).as_matrix(), [0.7, 0.1], "Look around"),
                ]
                
                for pose_matrix, antennas, action in mirror_moves:
                    # Small delay as if "seeing" the person's movement
                    await asyncio.sleep(0.8)
                    
                    pose = base_pose.copy()
                    pose[:3, :3] = pose_matrix
                    
                    # Perform the mirrored movement
                    self.robot.goto_target(head=pose, antennas=antennas, duration=1.0)
                    await asyncio.sleep(2.0)
                    
                    # Return to neutral briefly
                    self.robot.goto_target(head=base_pose, antennas=[0.0, 0.0], duration=0.8)
                    await asyncio.sleep(1.0)
                
                # Final acknowledgment 
                thanks_pose = base_pose.copy()
                thanks_pose[:3, :3] = R.from_euler('y', -15, degrees=True).as_matrix()
                self.robot.goto_target(head=thanks_pose, antennas=[0.3, 0.3], duration=1.0)
                
            else:
                await asyncio.sleep(12)
            
            return True
        except Exception as e:
            self.logger.error(f"Interactive mirror failed: {e}")
            return False