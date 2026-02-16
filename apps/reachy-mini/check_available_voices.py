#!/usr/bin/env python3
"""
Check available ElevenLabs voices for the current subscription
"""

from elevenlabs.client import ElevenLabs

def check_voices():
    client = ElevenLabs(api_key="sk_329b52cca86917437ef4055f992f73224db215255b605214")
    
    print("🎤 Checking available ElevenLabs voices...")
    
    try:
        voices = client.voices.get_all()
        print(f"\n✅ Found {len(voices.voices)} available voices:\n")
        
        for i, voice in enumerate(voices.voices):
            print(f"{i+1:2d}. {voice.name:<25} (ID: {voice.voice_id})")
            if hasattr(voice, 'labels'):
                labels = getattr(voice, 'labels', {})
                if labels:
                    print(f"     Labels: {labels}")
            print()
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    check_voices()