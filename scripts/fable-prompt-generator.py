#!/usr/bin/env python3
"""
Gullah Geechee Biz — Fable 5 Prompt Library
Generates video prompts for Fable 5 based on ad generator output.
Each prompt produces 15-30 second footage for social media trailers.
"""

import json, os, random
from pathlib import Path
from datetime import datetime

HOME = Path.home()
ADS_DIR = HOME / "generated-ads"
PROMPTS_DIR = HOME / "fable-prompts"
PROMPTS_DIR.mkdir(parents=True, exist_ok=True)

# Fable 5 scene templates for each content type
SCENE_TEMPLATES = {
    "self-help": [
        {
            "scene": "opening",
            "prompt": "Aerial drone shot gliding over Lowcountry marsh at golden hour, tall grass swaying in breeze, warm amber light reflecting on slow-moving water, cinematic 4K, no text, no words"
        },
        {
            "scene": "mid",
            "prompt": "Slow push-in on an old oak tree draped in Spanish moss, dappled sunlight filtering through leaves, peaceful and timeless, cinematic 24fps, no text"
        },
        {
            "scene": "closing",
            "prompt": "Sunset over the Atlantic Ocean from a Sea Island beach, waves gently rolling in, golden light on the water, calm and reflective, cinematic, no text"
        }
    ],
    "business": [
        {
            "scene": "opening",
            "prompt": "Slow pan across historic Penn Center campus on St. Helena Island, live oaks framing the shot, warm afternoon light, cinematic 4K, no text"
        },
        {
            "scene": "mid",
            "prompt": "Close-up of hands weaving a sweetgrass basket, natural light, detailed texture of the grass, traditional craft in progress, cinematic, no text"
        },
        {
            "scene": "closing",
            "prompt": "Wide shot of a Gullah Geechee community gathering, people talking and laughing, warm sunlight, authentic and joyful, cinematic, no text"
        }
    ],
    "cooking": [
        {
            "scene": "opening",
            "prompt": "Close-up of fresh okra being sliced on a wooden cutting board, natural kitchen light, vibrant green colors, cinematic macro shot, no text"
        },
        {
            "scene": "mid",
            "prompt": "Cast iron skillet with simmering red rice, steam rising, rich red-orange color, wooden spoon stirring slowly, warm kitchen lighting, cinematic, no text"
        },
        {
            "scene": "closing",
            "prompt": "Plated dish being placed on a rustic wooden table, garnished with fresh herbs, steam still rising, warm inviting atmosphere, cinematic, no text"
        }
    ],
    "recipe": [
        {
            "scene": "opening",
            "prompt": "Fresh ingredients arranged on a weathered wooden table, natural light from a window, vibrant colors, rustic kitchen aesthetic, cinematic, no text"
        },
        {
            "scene": "mid",
            "prompt": "Hands preparing food in a traditional way, close-up of the cooking process, steam and sizzle, warm kitchen lighting, cinematic, no text"
        },
        {
            "scene": "closing",
            "prompt": "Final dish on the table, steam rising, garnished beautifully, warm golden light, inviting and delicious, cinematic, no text"
        }
    ],
    "bundle": [
        {
            "scene": "opening",
            "prompt": "Aerial shot of a Gullah Geechee community along the coast, marsh and ocean meeting, golden hour light, cinematic 4K, no text"
        },
        {
            "scene": "mid",
            "prompt": "Slow montage of cultural elements: sweetgrass basket, cast iron cooking, live oaks, marsh grass, warm light throughout, cinematic, no text"
        },
        {
            "scene": "closing",
            "prompt": "Sunset over the water, golden and peaceful, a single sweetgrass basket silhouetted against the sky, cinematic, no text"
        }
    ]
}

# Text overlay templates for DaVinci
TEXT_OVERLAYS = {
    "self-help": [
        {"text": "Carry the resilience of generations.", "duration": 3, "position": "center"},
        {"text": "Your heritage is your strength.", "duration": 3, "position": "center"},
        {"text": "Gullah Geechee wisdom for daily living.", "duration": 3, "position": "bottom"}
    ],
    "business": [
        {"text": "Build something that honors your roots.", "duration": 3, "position": "center"},
        {"text": "The Gullah Geechee way of business.", "duration": 3, "position": "center"},
        {"text": "From heritage to hustle.", "duration": 3, "position": "bottom"}
    ],
    "cooking": [
        {"text": "Taste the Lowcountry.", "duration": 3, "position": "center"},
        {"text": "Recipes passed down for generations.", "duration": 3, "position": "center"},
        {"text": "From our kitchen to yours.", "duration": 3, "position": "bottom"}
    ],
    "recipe": [
        {"text": "Learn to make it yourself.", "duration": 3, "position": "center"},
        {"text": "Authentic Gullah Geechee cooking.", "duration": 3, "position": "center"},
        {"text": "Get the full recipe.", "duration": 2, "position": "bottom"}
    ],
    "bundle": [
        {"text": "100 ebooks. One culture.", "duration": 3, "position": "center"},
        {"text": "The complete Gullah Geechee library.", "duration": 3, "position": "center"},
        {"text": "Start reading today.", "duration": 2, "position": "bottom"}
    ]
}

# CTA overlays (final card)
CTA_OVERLAYS = {
    "self-help": "gullahgeecheebiz.com/ebooks/",
    "business": "gullahgeecheebiz.com/ebooks/",
    "cooking": "gullahgeecheebiz.com/recipes/",
    "recipe": "gullahgeecheebiz.com/recipes/",
    "bundle": "gullahgeecheebiz.com/ebooks/"
}

def generate_video_prompt(ad_data):
    """Generate a complete Fable 5 video prompt from ad data."""
    ad_type = ad_data.get("type", ad_data.get("category", "general"))
    category = ad_data.get("category", ad_data.get("type", "general"))
    
    # Map to scene template key
    scene_key = category if category in SCENE_TEMPLATES else "bundle"
    if scene_key not in SCENE_TEMPLATES:
        scene_key = "bundle"
    
    scenes = SCENE_TEMPLATES[scene_key]
    text_overlays = TEXT_OVERLAYS.get(scene_key, TEXT_OVERLAYS["bundle"])
    cta = CTA_OVERLAYS.get(scene_key, "gullahgeecheebiz.com")
    
    # Build the full video spec
    video_spec = {
        "title": ad_data.get("title", "Gullah Geechee Biz"),
        "duration_seconds": 15,
        "aspect_ratio": "9:16",
        "format": "vertical",
        "scenes": [],
        "text_overlays": [],
        "cta_card": {
            "text": cta,
            "duration": 2,
            "background": "navy",
            "text_color": "gold"
        },
        "audio": {
            "style": "soft_instrumental",
            "mood": "warm_uplifting"
        }
    }
    
    # Add scenes
    for i, scene in enumerate(scenes):
        video_spec["scenes"].append({
            "scene_number": i + 1,
            "duration": 5,
            "prompt": scene["prompt"],
            "transition": "crossfade" if i > 0 else "none"
        })
    
    # Add text overlays (distribute across scenes)
    for i, overlay in enumerate(text_overlays):
        if i < len(scenes):
            video_spec["text_overlays"].append({
                "scene": i + 1,
                "text": overlay["text"],
                "duration": overlay["duration"],
                "position": overlay["position"],
                "font": "Georgia",
                "color": "gold",
                "size": "large"
            })
    
    return video_spec

def generate_batch(count=4):
    """Generate a batch of Fable 5 video prompts."""
    # Load latest ads
    ad_files = sorted(ADS_DIR.glob("*.json"))
    if not ad_files:
        print("No ads found. Run ad-generator.py first.")
        return []
    
    # Load the most recent campaign or individual ads
    ads = []
    for f in ad_files[-10:]:
        try:
            with open(f) as fh:
                ad = json.load(fh)
                ads.append(ad)
        except:
            continue
    
    if not ads:
        return []
    
    # Pick diverse ads
    selected = random.sample(ads, min(count, len(ads)))
    
    videos = []
    for ad in selected:
        spec = generate_video_prompt(ad)
        videos.append(spec)
    
    return videos

def save_prompts(videos):
    """Save video prompts to disk."""
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    filepath = PROMPTS_DIR / f"fable-batch-{timestamp}.json"
    
    with open(filepath, "w") as f:
        json.dump({
            "batch": timestamp,
            "count": len(videos),
            "videos": videos
        }, f, indent=2)
    
    return filepath

def main():
    print("🎬 Gullah Geechee Biz — Fable 5 Prompt Generator")
    print()
    
    videos = generate_batch(4)
    if not videos:
        print("   No ads available. Run ad-generator.py first.")
        return
    
    filepath = save_prompts(videos)
    
    print(f"   Generated {len(videos)} video prompts:")
    for v in videos:
        print(f"\n  {'='*50}")
        print(f"  🎥 {v['title']}")
        print(f"  {'='*50}")
        print(f"     Duration: {v['duration_seconds']}s")
        print(f"     Format: {v['aspect_ratio']} {v['format']}")
        print(f"     Scenes: {len(v['scenes'])}")
        for s in v['scenes']:
            print(f"       Scene {s['scene_number']}: {s['prompt'][:60]}...")
        print(f"     Text overlays: {len(v['text_overlays'])}")
        for t in v['text_overlays']:
            print(f"       \"{t['text']}\" ({t['duration']}s, {t['position']})")
        print(f"     CTA: {v['cta_card']['text']}")
    
    print(f"\n   📁 Saved to: {filepath}")
    print(f"   🎬 Ready for Fable 5 import")

if __name__ == "__main__":
    main()
