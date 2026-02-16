#!/usr/bin/env python3
"""
Quick test script to demonstrate all the amazing story themes!
"""

import asyncio
import logging
from enhanced_entertainment import EnhancedEntertainmentSystem

async def test_all_stories():
    """Test each story theme"""
    print("🎪 Testing All Story Themes! 🎪\n")
    
    system = EnhancedEntertainmentSystem(use_simulation=True)
    await system.initialize()
    
    themes = ["adventure", "friendship", "magic", "space", "ocean"]
    
    for theme in themes:
        print(f"\n{'='*50}")
        print(f"📚 TESTING {theme.upper()} STORY")
        print(f"{'='*50}")
        
        # Get story parts
        story_parts = await system.chat.generate_story(theme)
        
        print(f"🎭 Story Theme: {theme.title()}")
        print(f"📖 Number of story parts: {len(story_parts)}")
        print("\n✨ Story Preview:")
        
        for i, part in enumerate(story_parts[:3]):  # Show first 3 parts
            print(f"   {i+1}. {part}")
        
        if len(story_parts) > 3:
            print(f"   ... and {len(story_parts) - 3} more exciting parts!")
        
        print(f"\n🎉 Final part: {story_parts[-1]}")
    
    print(f"\n{'='*50}")
    print("🎊 All Stories Ready for Entertainment! 🎊")
    print("Run 'python enhanced_entertainment.py --sim story' to experience them!")
    print(f"{'='*50}")

if __name__ == "__main__":
    logging.basicConfig(level=logging.WARNING)  # Quiet mode
    asyncio.run(test_all_stories())