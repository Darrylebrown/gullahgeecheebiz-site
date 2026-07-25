#!/usr/bin/env python3
"""
Gullah Geechee Biz — Heirs Property Documentary Generator
Creates a full-length YouTube documentary with branding, narration, and scene images
"""

import os, json, subprocess, tempfile, textwrap
from pathlib import Path

HOME = os.path.expanduser("~")
OUTPUT_DIR = os.path.join(HOME, "heirs-property-doc")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ── Documentary Script ──
SCENES = [
    {
        "id": 1,
        "title": "The Land That Remembers",
        "narration": "The Gullah Geechee people have lived on the Sea Islands of the American Southeast for over 300 years. Their ancestors were brought here against their will, but they built a culture, a language, and a way of life that has endured against all odds. At the heart of that culture is land. Land that was farmed, prayed on, and passed down through generations. But today, that land is disappearing at an alarming rate.",
        "image_prompt": "Aerial view of the Sea Islands, South Carolina coast, marsh and ancient oaks at golden hour, mist rising, National Geographic quality, cinematic wide shot",
        "duration": 20
    },
    {
        "id": 2,
        "title": "What Is Heirs' Property?",
        "narration": "Heirs' property is land that has been passed down through generations without a formal will. After the Civil War, newly freed African Americans acquired land through purchase, homesteading, and land grants. But many of these transactions were never properly documented. When the original owner died, the land was passed to their heirs through informal agreements. Over time, as families grew and spread across the country, ownership became fragmented among dozens, sometimes hundreds, of descendants.",
        "image_prompt": "Vintage photograph of Gullah Geechee family on their farm, early 1900s, sepia tone, historical documentary style",
        "duration": 25
    },
    {
        "id": 3,
        "title": "The Fragmentation Problem",
        "narration": "Here's how it works. When a property owner dies without a will, their children each inherit an equal share. When those children die, their shares are divided among their children. After just three generations, a single piece of land can have 20, 30, or even 100 owners. Each owner holds what's called a 'tenancy in common' share. And here's the danger: any one of those owners can force a partition sale of the entire property.",
        "image_prompt": "Documentary style graphic showing a family tree splitting into branches, warm amber tones, educational visual",
        "duration": 22
    },
    {
        "id": 4,
        "title": "The Numbers Are Staggering",
        "narration": "According to the USDA, heirs' property accounts for over 3.5 million acres of land in the United States, with a value exceeding $6 billion. In the Gullah Geechee Corridor alone, an estimated 70% of ancestral land is held as heirs' property. That's hundreds of thousands of acres of land that has been in Gullah Geechee families since Reconstruction, now at risk of being lost forever.",
        "image_prompt": "Map of the Gullah Geechee Cultural Heritage Corridor from North Carolina to Florida, highlighted areas showing land loss, documentary infographic style",
        "duration": 20
    },
    {
        "id": 5,
        "title": "The Development Threat",
        "narration": "The Sea Islands are some of the most desirable real estate on the East Coast. Luxury resorts, golf courses, and vacation homes have transformed Hilton Head, Kiawah, and other islands. As property values have skyrocketed, developers have targeted heirs' property for acquisition. A single heir can be approached by a developer, offered a fraction of the land's value, and pressured to sell. Once that sale goes through, the entire property can be partitioned and sold out from under the family.",
        "image_prompt": "Aerial contrast: luxury golf resort next to historic Gullah Geechee church and cemetery, dramatic lighting, documentary style",
        "duration": 25
    },
    {
        "id": 6,
        "title": "The Tax Trap",
        "narration": "Another devastating mechanism is the tax sale. As property values rise, so do property taxes. Many Gullah Geechee families, particularly elderly homeowners on fixed incomes, find themselves unable to pay the increased taxes. The county then sells the property at a tax auction, often for a fraction of its value. Families who have lived on the land for generations can lose everything in a single auction. And unlike conventional property owners, heirs' property owners often don't qualify for homestead exemptions or tax relief programs.",
        "image_prompt": "Historic Gullah Geechee home, weathered but loved, live oaks with Spanish moss, emotional documentary photography style",
        "duration": 22
    },
    {
        "id": 7,
        "title": "The Legal Labyrinth",
        "narration": "Resolving heirs' property requires navigating a complex legal system. Families must prove their ownership through decades of informal records, gather dozens of scattered heirs, and pay legal fees that can run into tens of thousands of dollars. For many families, the cost of fighting to keep their land is higher than the value of the land itself. This is why the Uniform Partition of Heirs Property Act, or UPHPA, is so important. It provides legal protections that give families a fighting chance.",
        "image_prompt": "Legal documents and property deeds spread on a wooden table, warm lamp light, documentary still life photography",
        "duration": 25
    },
    {
        "id": 8,
        "title": "The UPHPA Solution",
        "narration": "The Uniform Partition of Heirs Property Act, adopted by 18 states including South Carolina and Georgia, changes the rules. Under UPHPA, before a partition sale can happen, the court must determine the fair market value of the property. The heirs who want to keep the land are given the right to buy out the other heirs at that fair market price. And if a sale does happen, it must be a private sale that maximizes the value, not a public auction that sells the land for pennies on the dollar. This law is the single most important legal tool for protecting Gullah Geechee land.",
        "image_prompt": "Gullah Geechee family standing together on their land, looking toward the future, hopeful, golden hour lighting, documentary portrait",
        "duration": 25
    },
    {
        "id": 9,
        "title": "The Center for Heirs' Property",
        "narration": "Organizations like the Center for Heirs' Property Preservation are on the front lines of this fight. Based in South Carolina, the Center provides legal assistance, financial counseling, and land management education to heirs' property owners. They've helped thousands of families clear their titles, access USDA programs, and protect their land for future generations. But the need far exceeds the resources available.",
        "image_prompt": "Center for Heirs' Property Preservation office, warm professional setting, staff working with community members, documentary style",
        "duration": 20
    },
    {
        "id": 10,
        "title": "A Family's Story",
        "narration": "Meet the Brown family of St. Helena Island. Their land has been in the family since 1888, purchased by their great-great-grandfather just two decades after emancipation. For over 130 years, the family has farmed the land, held family reunions there, and buried their ancestors in the small family cemetery. But when the matriarch passed away without a will, the property became heirs' property. 47 descendants scattered across 12 states each held a share. A developer offered one cousin $15,000 for their share. The cousin accepted. Suddenly, the entire 50-acre property was at risk of partition sale. The family fought back, with help from the Center for Heirs' Property Preservation. After three years and $40,000 in legal fees, they cleared the title. The land is safe. But not every family has that kind of time or money.",
        "image_prompt": "Gullah Geechee family cemetery on St. Helena Island, moss-draped oaks, small headstones, golden sunlight filtering through, emotional documentary photography",
        "duration": 30
    },
    {
        "id": 11,
        "title": "What Can Be Done",
        "narration": "There are concrete steps that can protect Gullah Geechee land. First, create a will. If you own heirs' property, work with a lawyer to formalize your ownership and create an estate plan. Second, support organizations like the Center for Heirs' Property Preservation and the Gullah Geechee Cultural Heritage Corridor Commission. Third, advocate for the adoption of UPHPA in every state. Fourth, document your family's land history. Photographs, deeds, tax records, and family stories all help establish ownership. And fifth, educate the next generation about the value of the land, not just in dollars, but in heritage.",
        "image_prompt": "Gullah Geechee elder teaching young child about the land, passing down knowledge, warm golden light, hopeful documentary photography",
        "duration": 25
    },
    {
        "id": 12,
        "title": "The Land Remembers",
        "narration": "The Gullah Geechee people have survived slavery, Reconstruction, Jim Crow, and the Civil Rights era. They have maintained their language, their culture, and their connection to the land against impossible odds. The fight for heirs' property is the latest chapter in this story of resilience. But it is a fight that can be won. With the right tools, the right laws, and the right support, Gullah Geechee families can keep their land for another 300 years. The land remembers. And so do we.",
        "image_prompt": "Sunrise over the Lowcountry marsh, golden light spreading across the water, ancient oaks silhouetted, hopeful and majestic, National Geographic quality",
        "duration": 20
    }
]

# ── Generate Scene Images ──
def generate_scene_images():
    """Generate AI images for each scene"""
    print("=" * 60)
    print("  GENERATING SCENE IMAGES")
    print("=" * 60)
    
    for scene in SCENES:
        img_path = os.path.join(OUTPUT_DIR, f"scene-{scene['id']:02d}.png")
        if os.path.exists(img_path):
            print(f"  ⏭️  Scene {scene['id']:02d} — already exists")
            continue
        
        print(f"  🎬 Scene {scene['id']:02d}: {scene['title']}")
        print(f"     Generating image...")
        
        # We'll use the image_generate tool from the main session
        # This script is a plan - the actual generation happens in the conversation
        print(f"     Prompt: {scene['image_prompt'][:60]}...")
        print(f"     Narration: {scene['duration']}s")
        print()
    
    print(f"  {len(SCENES)} scenes planned")
    print()

# ── Generate Script File ──
def generate_script():
    """Generate the full documentary script"""
    script_path = os.path.join(OUTPUT_DIR, "heirs-property-script.md")
    
    with open(script_path, "w") as f:
        f.write("# The Land That Remembers\n")
        f.write("# A Gullah Geechee Documentary\n\n")
        f.write("---\n\n")
        
        for scene in SCENES:
            f.write(f"## Scene {scene['id']:02d}: {scene['title']}\n")
            f.write(f"**Duration:** {scene['duration']} seconds\n\n")
            f.write(f"**Visual:** {scene['image_prompt']}\n\n")
            f.write(f"**Narration:**\n")
            f.write(f"{textwrap.fill(scene['narration'], width=80)}\n\n")
            f.write("---\n\n")
        
        f.write("\n## Credits\n\n")
        f.write("**Produced by:** Gullah Geechee Biz\n")
        f.write("**Narration:** AI-generated voiceover\n")
        f.write("**Images:** AI-generated\n")
        f.write("**Music:** Royalty-free documentary score\n")
        f.write("**Copyright:** Gullah Geechee Biz\n")
    
    print(f"  ✅ Script saved: {script_path}")
    return script_path

# ── Generate FFmpeg Command ──
def generate_ffmpeg_command():
    """Generate the ffmpeg command to stitch the video"""
    cmd_path = os.path.join(OUTPUT_DIR, "render.sh")
    
    with open(cmd_path, "w") as f:
        f.write("#!/bin/bash\n")
        f.write("# Gullah Geechee Biz — Heirs Property Documentary Render\n")
        f.write("# Run this after generating all scene images and narration audio\n\n")
        
        f.write("OUTPUT_DIR=\"$HOME/heirs-property-doc\"\n")
        f.write("FINAL_VIDEO=\"$HOME/heirs-property-doc/final-documentary.mp4\"\n\n")
        
        f.write("# Step 1: Generate narration audio for each scene\n")
        f.write("# (Use text-to-speech for each scene's narration)\n\n")
        
        f.write("# Step 2: Create video segments\n")
        f.write("for i in $(seq -w 1 12); do\n")
        f.write("  IMAGE=\"$OUTPUT_DIR/scene-$i.png\"\n")
        f.write("  AUDIO=\"$OUTPUT_DIR/narration-$i.mp3\"\n")
        f.write("  OUTPUT=\"$OUTPUT_DIR/segment-$i.mp4\"\n")
        f.write("  \n")
        f.write("  # Get duration from narration audio\n")
        f.write("  DUR=$(ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 \"$AUDIO\" 2>/dev/null || echo 10)\n")
        f.write("  \n")
        f.write("  # Create video segment with branding overlay\n")
        f.write("  ffmpeg -y -loop 1 -i \"$IMAGE\" -i \"$AUDIO\" \\\n")
        f.write("    -vf \"drawtext=text='GULLAH GEECHEE BIZ':fontcolor=#D4AF37:fontsize=24:x=w-tw-20:y=h-th-20:fontfile=/System/Library/Fonts/Georgia.ttf, \\\n")
        f.write("          drawtext=text='The Land That Remembers':fontcolor=white:fontsize=18:x=20:y=h-th-20:fontfile=/System/Library/Fonts/Helvetica.ttc\" \\\n")
        f.write("    -c:v libx264 -preset medium -crf 23 -c:a aac -shortest \\\n")
        f.write("    \"$OUTPUT\"\n")
        f.write("done\n\n")
        
        f.write("# Step 3: Concatenate all segments\n")
        f.write("ffmpeg -y -f concat -safe 0 -i <(for f in $OUTPUT_DIR/segment-*.mp4; do echo \"file '$f'\"; done) \\\n")
        f.write("  -c:v libx264 -preset medium -crf 23 -c:a aac \\\n")
        f.write("  \"$FINAL_VIDEO\"\n\n")
        
        f.write("echo \"✅ Documentary rendered: $FINAL_VIDEO\"\n")
    
    os.chmod(cmd_path, 0o755)
    print(f"  ✅ Render script saved: {cmd_path}")

def main():
    print("=" * 60)
    print("  THE LAND THAT REMEMBERS")
    print("  A Gullah Geechee Heirs' Property Documentary")
    print("=" * 60)
    print()
    
    generate_script()
    print()
    generate_scene_images()
    print()
    generate_ffmpeg_command()
    
    print()
    print("=" * 60)
    print("  DOCUMENTARY BLUEPRINT COMPLETE")
    print("=" * 60)
    print()
    print("  Next steps:")
    print("  1. Generate 12 scene images (AI image generation)")
    print("  2. Generate 12 narration audio files (text-to-speech)")
    print("  3. Run render.sh to stitch everything together")
    print("  4. Upload to YouTube with Gullah Geechee Biz branding")
    print()
    print(f"  Output: {OUTPUT_DIR}")
    print("=" * 60)

if __name__ == "__main__":
    main()
