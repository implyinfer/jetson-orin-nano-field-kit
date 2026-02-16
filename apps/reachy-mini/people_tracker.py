#!/usr/bin/env python3
"""
Reachy Mini People Tracker
Detects people using Roboflow inference service and makes Reachy look at and nod to each person.

Official SDK docs: https://huggingface.co/docs/reachy_mini/SDK/installation
"""

import asyncio
import cv2
import logging
import math
import time
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
import numpy as np
import requests
from datetime import datetime, timedelta

try:
    from reachy_mini import ReachyMini
    from reachy_mini.utils import create_head_pose
    REACHY_AVAILABLE = True
except ImportError:
    logging.warning("Reachy Mini SDK not available - running in simulation mode")
    REACHY_AVAILABLE = False

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Configuration settings"""
    
    # Reachy connection
    reachy_host: str = "192.168.1.100"
    reachy_port: int = 50051
    
    # Roboflow inference
    roboflow_host: str = "localhost"
    roboflow_port: int = 9001
    roboflow_model: str = "yolov8n-640"  # or your specific model
    confidence_threshold: float = 0.5
    
    # Camera settings
    camera_device: int = 0
    camera_width: int = 1280
    camera_height: int = 720
    camera_fps: int = 15
    
    # Person tracking
    person_memory_duration: int = 10  # seconds
    min_person_area: int = 5000  # minimum bounding box area
    max_tracking_distance: float = 100.0  # pixels
    
    # Reachy behavior
    look_duration: float = 2.0  # seconds to look at person
    nod_after_look: bool = True
    max_head_yaw: float = 45.0  # degrees
    max_head_pitch: float = 30.0  # degrees
    movement_smoothness: float = 1.5  # seconds for smooth movement
    
    # Safety and performance
    detection_interval: float = 0.2  # seconds between detections
    max_concurrent_actions: int = 1
    enable_safety_limits: bool = True
    
    class Config:
        env_file = ".env"


@dataclass
class Person:
    """Represents a detected person"""
    id: int
    center_x: float
    center_y: float
    bbox: Tuple[int, int, int, int]  # x, y, width, height
    confidence: float
    first_seen: datetime
    last_seen: datetime
    acknowledged: bool = False
    look_count: int = 0


class PersonTracker:
    """Tracks people across frames and assigns persistent IDs"""
    
    def __init__(self, max_distance: float = 100.0, memory_duration: int = 10):
        self.people: Dict[int, Person] = {}
        self.next_id = 1
        self.max_distance = max_distance
        self.memory_duration = memory_duration
    
    def update(self, detections: List[Dict]) -> List[Person]:
        """Update tracking with new detections"""
        current_time = datetime.now()
        
        # Filter for person detections only
        person_detections = [
            d for d in detections 
            if d.get('class', '').lower() in ['person', 'people'] 
            and d.get('confidence', 0) > 0.5
        ]
        
        # Calculate centers for new detections
        new_centers = []
        for det in person_detections:
            x, y, w, h = det['x'], det['y'], det['width'], det['height']
            center_x = x + w / 2
            center_y = y + h / 2
            new_centers.append((center_x, center_y, det))
        
        # Match detections to existing people
        matched_ids = set()
        unmatched_detections = []
        
        for center_x, center_y, det in new_centers:
            best_match_id = None
            best_distance = float('inf')
            
            for person_id, person in self.people.items():
                if person_id in matched_ids:
                    continue
                    
                # Calculate distance from last known position
                distance = math.sqrt(
                    (center_x - person.center_x) ** 2 + 
                    (center_y - person.center_y) ** 2
                )
                
                if distance < self.max_distance and distance < best_distance:
                    best_distance = distance
                    best_match_id = person_id
            
            if best_match_id is not None:
                # Update existing person
                person = self.people[best_match_id]
                person.center_x = center_x
                person.center_y = center_y
                person.bbox = (det['x'], det['y'], det['width'], det['height'])
                person.confidence = det['confidence']
                person.last_seen = current_time
                matched_ids.add(best_match_id)
            else:
                unmatched_detections.append((center_x, center_y, det))
        
        # Create new people for unmatched detections
        for center_x, center_y, det in unmatched_detections:
            person = Person(
                id=self.next_id,
                center_x=center_x,
                center_y=center_y,
                bbox=(det['x'], det['y'], det['width'], det['height']),
                confidence=det['confidence'],
                first_seen=current_time,
                last_seen=current_time
            )
            self.people[self.next_id] = person
            self.next_id += 1
        
        # Remove old people
        cutoff_time = current_time - timedelta(seconds=self.memory_duration)
        expired_ids = [
            person_id for person_id, person in self.people.items()
            if person.last_seen < cutoff_time
        ]
        for person_id in expired_ids:
            del self.people[person_id]
        
        return list(self.people.values())
    
    def get_unacknowledged_people(self) -> List[Person]:
        """Get people who haven't been acknowledged yet"""
        return [person for person in self.people.values() if not person.acknowledged]


class ReachyPeopleTracker:
    """Main application class"""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.reachy = None
        self.person_tracker = PersonTracker(
            max_distance=settings.max_tracking_distance,
            memory_duration=settings.person_memory_duration
        )
        
        # Camera setup
        self.cap = None
        self.camera_center_x = settings.camera_width // 2
        self.camera_center_y = settings.camera_height // 2
        
        # Behavior state
        self.is_performing_action = False
        self.action_queue = asyncio.Queue()
        self.last_detection_time = 0
        
        # Initialize connections
        self.setup_camera()
        if REACHY_AVAILABLE:
            self.setup_reachy()
    
    def setup_camera(self):
        """Initialize camera"""
        try:
            self.cap = cv2.VideoCapture(self.settings.camera_device)
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.settings.camera_width)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.settings.camera_height)
            self.cap.set(cv2.CAP_PROP_FPS, self.settings.camera_fps)
            
            if not self.cap.isOpened():
                raise RuntimeError(f"Failed to open camera {self.settings.camera_device}")
                
            logging.info(f"Camera initialized: {self.settings.camera_width}x{self.settings.camera_height}")
            
        except Exception as e:
            logging.error(f"Camera setup failed: {e}")
            raise
    
    def setup_reachy(self):
        """Initialize Reachy connection"""
        try:
            self.reachy = ReachyMini(self.settings.reachy_host)
            self.reachy.wake_up()
            logging.info(f"Connected to Reachy Mini at {self.settings.reachy_host}")

            if self.settings.enable_safety_limits:
                self.configure_safety()

        except Exception as e:
            logging.error(f"Reachy connection failed: {e}")
            self.reachy = None

    def configure_safety(self):
        """Configure safety limits for Reachy"""
        if not self.reachy:
            return

        # ReachyMini SDK handles safety internally
        logging.info("Safety limits configured (using ReachyMini defaults)")
    
    def detect_people(self, frame: np.ndarray) -> List[Dict]:
        """Send frame to Roboflow inference service"""
        try:
            # Encode frame as JPEG
            _, img_encoded = cv2.imencode('.jpg', frame)
            
            # Send to Roboflow inference
            url = f"http://{self.settings.roboflow_host}:{self.settings.roboflow_port}/infer/{self.settings.roboflow_model}"
            
            response = requests.post(
                url,
                files={"image": img_encoded.tobytes()},
                data={"confidence": self.settings.confidence_threshold},
                timeout=5.0
            )
            
            if response.status_code == 200:
                result = response.json()
                predictions = result.get('predictions', [])
                
                # Filter for people and minimum area
                people_detections = []
                for pred in predictions:
                    if pred.get('class', '').lower() in ['person', 'people']:
                        area = pred.get('width', 0) * pred.get('height', 0)
                        if area >= self.settings.min_person_area:
                            people_detections.append(pred)
                
                return people_detections
            else:
                logging.warning(f"Roboflow inference failed: {response.status_code}")
                return []
                
        except Exception as e:
            logging.error(f"Detection failed: {e}")
            return []
    
    def calculate_head_angles(self, person: Person) -> Tuple[float, float]:
        """Calculate head angles to look at person"""
        # Calculate relative position from camera center
        rel_x = person.center_x - self.camera_center_x
        rel_y = person.center_y - self.camera_center_y
        
        # Convert to angles (simplified mapping)
        # These values may need calibration based on camera FOV and mounting
        yaw_angle = (rel_x / self.camera_center_x) * self.settings.max_head_yaw
        pitch_angle = -(rel_y / self.camera_center_y) * self.settings.max_head_pitch
        
        # Clamp angles to safe ranges
        yaw_angle = max(-self.settings.max_head_yaw, min(self.settings.max_head_yaw, yaw_angle))
        pitch_angle = max(-self.settings.max_head_pitch, min(self.settings.max_head_pitch, pitch_angle))
        
        return yaw_angle, pitch_angle
    
    async def look_at_person(self, person: Person):
        """Make Reachy look at and nod to a person"""
        if not self.reachy or self.is_performing_action:
            return

        self.is_performing_action = True

        try:
            # Calculate head angles
            yaw_angle, pitch_angle = self.calculate_head_angles(person)

            logging.info(f"Looking at person {person.id} at ({person.center_x}, {person.center_y}) - "
                        f"angles: yaw={yaw_angle:.1f}°, pitch={pitch_angle:.1f}°")

            # Look at person using ReachyMini SDK
            # x = yaw (left/right), z = pitch (up/down in mm space)
            self.reachy.goto_target(
                head=create_head_pose(x=yaw_angle, z=-pitch_angle, degrees=True, mm=True),
                duration=self.settings.movement_smoothness
            )

            # Hold the look
            await asyncio.sleep(self.settings.look_duration)

            # Nod if enabled
            if self.settings.nod_after_look:
                await self.nod_at_person(yaw_angle, pitch_angle)

            # Mark person as acknowledged
            person.acknowledged = True
            person.look_count += 1

            logging.info(f"Acknowledged person {person.id}")

        except Exception as e:
            logging.error(f"Failed to look at person {person.id}: {e}")
        finally:
            self.is_performing_action = False
    
    async def nod_at_person(self, base_yaw: float, base_pitch: float):
        """Perform nodding gesture while looking at person"""
        try:
            # Small nod motion
            nod_amplitude = 10.0  # degrees/mm

            # Nod down
            self.reachy.goto_target(
                head=create_head_pose(x=base_yaw, z=-(base_pitch + nod_amplitude), degrees=True, mm=True),
                duration=0.4
            )
            await asyncio.sleep(0.45)

            # Nod up
            self.reachy.goto_target(
                head=create_head_pose(x=base_yaw, z=-(base_pitch - nod_amplitude), degrees=True, mm=True),
                duration=0.4
            )
            await asyncio.sleep(0.45)

            # Return to looking position
            self.reachy.goto_target(
                head=create_head_pose(x=base_yaw, z=-base_pitch, degrees=True, mm=True),
                duration=0.4
            )
            await asyncio.sleep(0.45)

            # Small pause
            await asyncio.sleep(0.3)

            # Second nod for emphasis
            self.reachy.goto_target(
                head=create_head_pose(x=base_yaw, z=-(base_pitch + nod_amplitude), degrees=True, mm=True),
                duration=0.3
            )
            await asyncio.sleep(0.35)

            self.reachy.goto_target(
                head=create_head_pose(x=base_yaw, z=-base_pitch, degrees=True, mm=True),
                duration=0.3
            )
            await asyncio.sleep(0.35)

        except Exception as e:
            logging.error(f"Nodding failed: {e}")
    
    async def return_to_neutral(self):
        """Return head to neutral position"""
        if not self.reachy or self.is_performing_action:
            return

        try:
            self.reachy.goto_target(
                head=create_head_pose(x=0, z=0, roll=0, degrees=True, mm=True),
                duration=1.0
            )
            await asyncio.sleep(1.1)

        except Exception as e:
            logging.error(f"Failed to return to neutral: {e}")
    
    def draw_detections(self, frame: np.ndarray, people: List[Person]) -> np.ndarray:
        """Draw detection overlays on frame"""
        display_frame = frame.copy()
        
        for person in people:
            x, y, w, h = person.bbox
            
            # Choose color based on acknowledgment status
            color = (0, 255, 0) if person.acknowledged else (0, 0, 255)  # Green if acked, Red if not
            
            # Draw bounding box
            cv2.rectangle(display_frame, (x, y), (x + w, y + h), color, 2)
            
            # Draw center point
            center_x, center_y = int(person.center_x), int(person.center_y)
            cv2.circle(display_frame, (center_x, center_y), 5, color, -1)
            
            # Draw info text
            info_text = f"Person {person.id} (conf: {person.confidence:.2f})"
            if person.acknowledged:
                info_text += " ✓"
            
            cv2.putText(display_frame, info_text, (x, y - 10), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
            
            # Draw look count
            cv2.putText(display_frame, f"Looks: {person.look_count}", (x, y + h + 20),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)
        
        # Draw camera center reference
        cv2.circle(display_frame, (self.camera_center_x, self.camera_center_y), 10, (255, 255, 255), 2)
        cv2.putText(display_frame, "Center", (self.camera_center_x + 15, self.camera_center_y), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        return display_frame
    
    async def run(self):
        """Main detection and tracking loop"""
        logging.info("Starting people tracking system...")
        
        try:
            while True:
                current_time = time.time()
                
                # Throttle detection rate
                if current_time - self.last_detection_time < self.settings.detection_interval:
                    await asyncio.sleep(0.01)
                    continue
                
                # Capture frame
                ret, frame = self.cap.read()
                if not ret:
                    logging.warning("Failed to capture frame")
                    continue
                
                # Detect people
                detections = self.detect_people(frame)
                
                # Update tracking
                people = self.person_tracker.update(detections)
                
                # Find people who need acknowledgment
                unacknowledged = self.person_tracker.get_unacknowledged_people()
                
                # Process new people (look at them)
                if unacknowledged and not self.is_performing_action:
                    # Sort by confidence and choose the best one
                    best_person = max(unacknowledged, key=lambda p: p.confidence)
                    await self.look_at_person(best_person)
                
                # Display frame with annotations
                display_frame = self.draw_detections(frame, people)
                cv2.imshow("Reachy People Tracker", display_frame)
                
                # Handle key presses
                key = cv2.waitKey(1) & 0xFF
                if key == ord('q'):
                    break
                elif key == ord('r'):
                    # Reset tracking
                    self.person_tracker = PersonTracker(
                        max_distance=self.settings.max_tracking_distance,
                        memory_duration=self.settings.person_memory_duration
                    )
                    logging.info("Reset person tracking")
                elif key == ord('n'):
                    # Return to neutral
                    await self.return_to_neutral()
                
                self.last_detection_time = current_time
                
                # Status logging
                if len(people) > 0:
                    acknowledged_count = sum(1 for p in people if p.acknowledged)
                    logging.debug(f"Tracking {len(people)} people, {acknowledged_count} acknowledged")
        
        except KeyboardInterrupt:
            logging.info("Shutting down...")
        finally:
            await self.cleanup()
    
    async def cleanup(self):
        """Clean up resources"""
        if self.cap:
            self.cap.release()

        cv2.destroyAllWindows()

        if self.reachy:
            try:
                await self.return_to_neutral()
                self.reachy.sleep()
            except:
                pass


async def main():
    """Main application entry point"""
    settings = Settings()
    
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s"
    )
    
    logging.info("Starting Reachy People Tracker")
    logging.info(f"Roboflow inference: {settings.roboflow_host}:{settings.roboflow_port}")
    logging.info(f"Reachy connection: {settings.reachy_host}:{settings.reachy_port}")
    
    tracker = ReachyPeopleTracker(settings)
    await tracker.run()


if __name__ == "__main__":
    asyncio.run(main())