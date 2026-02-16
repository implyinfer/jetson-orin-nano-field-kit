#!/usr/bin/env python3
"""
Quick test to verify Reachy audio integration is working
"""

import asyncio
from audio_system import AudioStorytellingSystem

async def test_audio_routing():
    print("🎤 Testing Reachy Audio Integration")
    
    # Test with Reachy audio enabled
    print("Initializing with Reachy audio enabled...")
    audio_system = AudioStorytellingSystem(use_reachy_audio=True)
    
    # Check if Reachy audio is actually being used
    if audio_system.tts.use_reachy_audio:
        print("✅ Audio will route through Reachy speakers!")
    else:
        print("⚠️ Using fallback audio (laptop speakers)")
    
    print(f"Voice engine: {audio_system.tts.get_voice_info()['engine']}")
    
    # Test short phrase
    print("Speaking test phrase through Reachy...")
    await audio_system.speak_with_emotion(
        "Hello! This audio should come from Reachy's speakers, not your laptop.",
        emotion="happy",
        pause_after=1.0
    )
    
    print("🎊 Audio test completed!")

if __name__ == "__main__":
    asyncio.run(test_audio_routing())