#!/usr/bin/env python3
"""
GGB Agent Opus — One-command faceless video generator for Gullah Geechee Biz.

Turns any topic into a polished 60-second vertical video with:
  - AI-generated scene images (via FAL/FLUX)
  - Voiceover narration (via edge-tts)
  - Brand-styled text overlays (navy + gold)
  - Background music
  - Brand outro

Usage:
  python3 ggb-agent-opus.py "Gullah Geechee sweetgrass baskets: 300 years of art"
  python3 ggb-agent-opus.py "The story of the Sea Islands" --duration 45
  python3 ggb-agent-opus.py "Heirs' property explained" --output my-video.mp4
"""

import argparse
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

# ─── Paths ───────────────────────────────────────────────────────────────────
ROOT = Path(__file__).parent.resolve()
SCENES_DIR = ROOT / "scenes"
OUTPUT_DIR = ROOT / "output"
ASSETS_DIR = ROOT / "assets"
os.makedirs(SCENES_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(ASSETS_DIR, exist_ok=True)

# ─── Brand Constants ─────────────────────────────────────────────────────────
NAVY_HEX = "#0A1628"
NAVY_RGB = (10, 22, 40)
GOLD_HEX = "#C9A84C"
GOLD_RGB = (201, 168, 76)
WHITE_HEX = "#FFFFFF"
FONT_PATH = "/System/Library/Fonts/Helvetica.ttc"
FONT_BOLD = "/System/Library/Fonts/Helvetica-Bold.ttf"

# ─── Scene Template ──────────────────────────────────────────────────────────
SCENE_COUNT = 6  # 6 scenes × ~10s each = ~60s video

# ─── Helpers ─────────────────────────────────────────────────────────────────

def log(msg):
    print(f"  🎬 {msg}")

def run_ffmpeg(args, desc="ffmpeg"):
    """Run ffmpeg with error handling."""
    env = os.environ.copy()
    env["PATH"] = f"{os.path.expanduser('~/homebrew/bin')}:{env.get('PATH', '')}"
    result = subprocess.run(args, capture_output=True, text=True, env=env)
    if result.returncode != 0:
        print(f"  ⚠️  {desc} warning: {result.stderr[-200:]}")
    return result

def get_ollama_response(prompt, model="hermes3:latest"):
    """Get a response from local Ollama."""
    import urllib.request
    import urllib.error

    data = json.dumps({
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0.7, "num_predict": 2000}
    }).encode()

    req = urllib.request.Request(
        "http://127.0.0.1:11434/api/generate",
        data=data,
        headers={"Content-Type": "application/json"}
    )

    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            result = json.loads(resp.read())
            return result.get("response", "")
    except Exception as e:
        log(f"Ollama error: {e}")
        return ""

# ─── Scene Writer ─────────────────────────────────────────────────────────────

def write_scenes(topic, duration=60):
    """Generate scene descriptions, narration, and image prompts from a topic."""
    scene_time = duration // SCENE_COUNT

    prompt = f"""Create {SCENE_COUNT} scenes for a {duration}-second faceless video about: {topic}

Return ONLY a JSON array. Each scene has: duration (seconds), narration (1 sentence), image_prompt (visual description), text_overlay (3-5 words).

Rules:
- Final scene text_overlay: "gullahgeecheebiz.com"
- Final scene narration includes "Gullah Geechee Biz"
- No people's faces visible in image_prompt
- Gullah Geechee cultural context

Example format:
[{{"duration":10,"narration":"...","image_prompt":"...","text_overlay":"..."}}]"""

    response = get_ollama_response(prompt)
    if not response or len(response) < 50:
        log("Ollama response too short. Using fallback scenes.")
        return fallback_scenes(topic, scene_time)

    # Extract JSON from response
    try:
        # Find JSON array in response
        start = response.find("[")
        end = response.rfind("]") + 1
        if start >= 0 and end > start:
            json_str = response[start:end]
            scenes = json.loads(json_str)
            # Validate
            for s in scenes:
                if not all(k in s for k in ["duration", "narration", "image_prompt", "text_overlay"]):
                    raise ValueError("Missing required fields")
            return scenes
    except (json.JSONDecodeError, ValueError) as e:
        log(f"Scene parsing error: {e}")
        return fallback_scenes(topic, scene_time)

def fallback_scenes(topic, scene_time):
    """Fallback scenes when Ollama is unavailable."""
    return [
        {
            "duration": scene_time,
            "narration": f"The story of {topic} begins here, on the Sea Islands of the Lowcountry.",
            "image_prompt": f"Golden sunset over Lowcountry marsh. Spanish moss on ancient oaks. {topic}. Cinematic wide shot. No people. Warm amber light.",
            "text_overlay": "The Land"
        },
        {
            "duration": scene_time,
            "narration": "For over 300 years, Gullah Geechee people have carried this culture forward.",
            "image_prompt": f"Hands weaving sweetgrass basket. Traditional craft. Warm sunlight. Shallow depth of field. {topic}.",
            "text_overlay": "300 Years"
        },
        {
            "duration": scene_time,
            "narration": "Every story, every song, every tradition passed down through generations.",
            "image_prompt": f"Ancient live oak with moss. Twilight sky. Deep blues and purples. {topic}. Moody cinematic atmosphere.",
            "text_overlay": "Our Stories"
        },
        {
            "duration": scene_time,
            "narration": "Now we write our own history. Publish our own truth.",
            "image_prompt": f"Open book with warm golden light. Dark navy background. Pages glowing. {topic}. Elegant literary atmosphere.",
            "text_overlay": "Our Voice"
        },
        {
            "duration": scene_time,
            "narration": "Gullah Geechee Biz. Culture. Books. Story.",
            "image_prompt": f"Gold metallic GGB emblem on navy background. Wrought iron border. Luxury brand aesthetic. {topic}.",
            "text_overlay": "GULLAH GEECHEE BIZ"
        },
        {
            "duration": scene_time,
            "narration": f"Discover more about {topic} at Gullah Geechee Biz.",
            "image_prompt": f"Navy background with gold accents. Gullah Geechee Biz branding. Elegant typography. {topic}.",
            "text_overlay": "gullahgeecheebiz.com"
        }
    ]

# ─── Voiceover ───────────────────────────────────────────────────────────────

def generate_voiceover(scenes, output_path):
    """Generate voiceover audio using edge-tts."""
    # Combine all narration into one script
    full_script = " ".join(s["narration"] for s in scenes)

    log("Generating voiceover...")
    result = subprocess.run([
        sys.executable, "-m", "edge_tts",
        "--text", full_script,
        "--voice", "en-US-GuyNeural",
        "--write-media", str(output_path)
    ], capture_output=True, text=True, timeout=120)

    if result.returncode != 0:
        log(f"TTS error: {result.stderr}")
        return False
    return True

# ─── Image Generation ────────────────────────────────────────────────────────

def generate_image(prompt, output_path):
    """Generate an image using FAL/FLUX via the Hermes tool.
    
    Falls back to creating a styled placeholder if FAL is unavailable.
    """
    # Try using the Hermes image_generate tool via subprocess
    # Since we can't call Hermes tools directly from Python, we use FAL API
    fal_key = os.environ.get("FAL_KEY")
    
    if fal_key:
        try:
            import urllib.request
            data = json.dumps({
                "prompt": prompt,
                "aspect_ratio": "9:16",
                "num_images": 1
            }).encode()
            req = urllib.request.Request(
                "https://fal.run/fal-ai/flux/dev",
                data=data,
                headers={
                    "Authorization": f"Key {fal_key}",
                    "Content-Type": "application/json"
                }
            )
            with urllib.request.urlopen(req, timeout=60) as resp:
                result = json.loads(resp.read())
                image_url = result.get("images", [{}])[0].get("url", "")
                if image_url:
                    # Download the image
                    urllib.request.urlretrieve(image_url, output_path)
                    return True
        except Exception as e:
            log(f"FAL API error: {e}")
    
    # Fallback: create a styled placeholder
    log("Creating styled placeholder (no FAL key available)...")
    try:
        from PIL import Image, ImageDraw, ImageFont
        img = Image.new("RGB", (1080, 1920), NAVY_RGB)
        draw = ImageDraw.Draw(img)
        
        # Try to load font
        try:
            font = ImageFont.truetype(FONT_PATH, 36)
            title_font = ImageFont.truetype(FONT_PATH, 48)
        except:
            font = ImageFont.load_default()
            title_font = font
        
        # Draw gold accent line
        draw.rectangle([(200, 800), (880, 805)], fill=GOLD_RGB)
        
        # Draw scene description
        lines = prompt.split(". ")
        y = 850
        for line in lines[:4]:
            bbox = draw.textbbox((0, 0), line[:60], font=font)
            tw = bbox[2] - bbox[0]
            draw.text(((1080 - tw) // 2, y), line[:60], fill=GOLD_RGB, font=font)
            y += 50
        
        # Draw bottom gold line
        draw.rectangle([(200, y + 50), (880, y + 55)], fill=GOLD_RGB)
        
        img.save(output_path)
        return True
    except ImportError:
        log("Pillow not available for fallback images")
        return False

# ─── Video Builder ───────────────────────────────────────────────────────────

def build_video(scenes, voiceover_path, output_path):
    """Assemble scenes + voiceover into final video."""
    log("Building video...")
    
    workdir = Path(tempfile.mkdtemp())
    clip_files = []
    
    for i, scene in enumerate(scenes):
        num = i + 1
        img_path = SCENES_DIR / f"scene{num}.png"
        clip_path = workdir / f"clip{num}.mp4"
        dur = scene["duration"]
        text = scene["text_overlay"]
        
        if not img_path.exists():
            log(f"Scene {num} image missing, creating placeholder")
            create_placeholder_image(img_path, text)
        
        # Build ffmpeg command with text overlay
        # Use sharp + SVG for premium gold serif text
        try:
            frame_path = workdir / f"frame{num}.png"
            
            # Call Node.js overlay script for premium text
            subprocess.run([
                "node", str(ROOT / "overlay.mjs"),
                str(img_path), text, str(frame_path)
            ], capture_output=True, text=True, timeout=30)
            
            if not frame_path.exists():
                raise Exception("Overlay failed, falling back to Pillow")
            
            # Create video clip from frame + audio segment
            # Extract audio segment
            seg_path = workdir / f"seg{num}.mp3"
            run_ffmpeg([
                "ffmpeg", "-y",
                "-i", str(voiceover_path),
                "-ss", str(sum(s["duration"] for s in scenes[:i])),
                "-t", str(dur),
                "-c:a", "libmp3lame", "-b:a", "48k", "-ar", "24000", "-ac", "1",
                str(seg_path)
            ], f"audio seg {num}")
            
            # Create video clip
            run_ffmpeg([
                "ffmpeg", "-y",
                "-loop", "1", "-i", str(frame_path),
                "-i", str(seg_path),
                "-c:v", "libx264", "-preset", "fast", "-crf", "23",
                "-c:a", "aac", "-b:a", "128k",
                "-t", str(dur), "-pix_fmt", "yuv420p",
                str(clip_path)
            ], f"clip {num}")
            
            clip_files.append(clip_path)
            log(f"Scene {num}/{len(scenes)}: {text}")
            
        except Exception as e:
            log(f"Sharp overlay failed ({e}), falling back to Pillow...")
            # Fallback: Pillow text overlay
            try:
                from PIL import Image, ImageDraw, ImageFont
                img = Image.open(img_path).convert("RGB").resize((1080, 1920), Image.LANCZOS)
                draw = ImageDraw.Draw(img)
                
                # Semi-transparent bar at bottom
                bar_y = 1700
                bar_h = 180
                overlay = Image.new("RGBA", (1080, bar_h), (0, 0, 0, 180))
                img.paste(overlay, (0, bar_y), overlay)
                
                # Gold accent line above text
                gold_line = Image.new("RGBA", (200, 3), (201, 168, 76, 255))
                img.paste(gold_line, ((1080 - 200) // 2, bar_y + 15), gold_line)
                
                # Text
                try:
                    font = ImageFont.truetype(FONT_PATH, 48)
                except:
                    font = ImageFont.load_default()
                
                bbox = draw.textbbox((0, 0), text, font=font)
                tw = bbox[2] - bbox[0]
                th = bbox[3] - bbox[1]
                tx = (1080 - tw) // 2
                ty = bar_y + (bar_h - th) // 2
                draw.text((tx, ty), text, fill=(255, 255, 255), font=font)
                
                # Save frame
                frame_path = workdir / f"frame{num}.png"
                img.save(frame_path)
                
                # Create video clip from frame + audio segment
                seg_path = workdir / f"seg{num}.mp3"
                run_ffmpeg([
                    "ffmpeg", "-y",
                    "-i", str(voiceover_path),
                    "-ss", str(sum(s["duration"] for s in scenes[:i])),
                    "-t", str(dur),
                    "-c:a", "libmp3lame", "-b:a", "48k", "-ar", "24000", "-ac", "1",
                    str(seg_path)
                ], f"audio seg {num}")
                
                run_ffmpeg([
                    "ffmpeg", "-y",
                    "-loop", "1", "-i", str(frame_path),
                    "-i", str(seg_path),
                    "-c:v", "libx264", "-preset", "fast", "-crf", "23",
                    "-c:a", "aac", "-b:a", "128k",
                    "-t", str(dur), "-pix_fmt", "yuv420p",
                    str(clip_path)
                ], f"clip {num}")
                
                clip_files.append(clip_path)
                log(f"Scene {num}/{len(scenes)}: {text}")
            except Exception as e2:
                log(f"Scene {num} error: {e2}")
                continue
    
    if not clip_files:
        log("No clips generated!")
        return False
    
    # Concatenate all clips
    concat_file = workdir / "concat.txt"
    with open(concat_file, "w") as f:
        for clip in clip_files:
            f.write(f"file '{clip}'\n")
    
    # First pass: concatenate clips
    temp_video = workdir / "temp_combined.mp4"
    run_ffmpeg([
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0",
        "-i", str(concat_file),
        "-c", "copy",
        str(temp_video)
    ], "concat pass")
    
    # Second pass: mix in background music
    bg_music = ASSETS_DIR / "ambient_mixed.mp3"
    if bg_music.exists():
        log("Adding background music...")
        run_ffmpeg([
            "ffmpeg", "-y",
            "-i", str(temp_video),
            "-i", str(bg_music),
            "-filter_complex", "[1:a]volume=0.12[bg];[0:a][bg]amix=inputs=2:duration=first:weights=1 0.3[a]",
            "-map", "0:v", "-map", "[a]",
            "-c:v", "copy",
            "-c:a", "aac", "-b:a", "128k",
            "-shortest",
            str(output_path)
        ], "music mix")
    else:
        # Just copy the temp
        import shutil
        shutil.copy2(temp_video, output_path)
    
    if output_path.exists():
        size_mb = output_path.stat().st_size / 1024 / 1024
        log(f"Video complete: {output_path.name} ({size_mb:.1f} MB)")
        return True
    return False

def create_placeholder_image(path, text):
    """Create a brand-styled placeholder image."""
    try:
        from PIL import Image, ImageDraw, ImageFont
        img = Image.new("RGB", (1080, 1920), NAVY_RGB)
        draw = ImageDraw.Draw(img)
        
        # Gold border
        draw.rectangle([(40, 40), (1040, 1880)], outline=GOLD_RGB, width=3)
        
        # Wrought-iron corner accents (simple)
        for cx, cy in [(40, 40), (1040, 40), (40, 1880), (1040, 1880)]:
            draw.arc([cx-30, cy-30, cx+30, cy+30], 0, 360, fill=GOLD_RGB, width=3)
        
        # Text
        try:
            font = ImageFont.truetype(FONT_PATH, 42)
        except:
            font = ImageFont.load_default()
        
        bbox = draw.textbbox((0, 0), text, font=font)
        tw = bbox[2] - bbox[0]
        draw.text(((1080 - tw) // 2, 900), text, fill=GOLD_RGB, font=font)
        
        img.save(path)
    except ImportError:
        # Create a minimal PNG
        with open(path, "wb") as f:
            f.write(b"")
    return path

# ─── Main ────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="GGB Agent Opus — One-command faceless video generator"
    )
    parser.add_argument("topic", help="Video topic or idea")
    parser.add_argument("--duration", type=int, default=60, help="Video duration in seconds (default: 60)")
    parser.add_argument("--output", "-o", help="Output filename (default: auto-generated)")
    parser.add_argument("--no-tts", action="store_true", help="Skip voiceover generation")
    parser.add_argument("--no-images", action="store_true", help="Skip image generation (use placeholders)")
    parser.add_argument("--ai-scenes", action="store_true", help="Use Ollama to generate scenes (default: use curated fallback scenes)")
    parser.add_argument("--publish", "-p", nargs="*", choices=["tiktok", "youtube", "rumble", "x", "pinterest", "all"],
                        help="Platforms to publish to after building (default: none)")
    args = parser.parse_args()

    print(f"\n{'='*50}")
    print(f"  GGB Agent Opus")
    print(f"  Topic: {args.topic}")
    print(f"  Duration: {args.duration}s")
    print(f"{'='*50}\n")

    # Step 1: Write scenes
    log("Writing scenes...")
    if args.ai_scenes:
        scenes = write_scenes(args.topic, args.duration)
    else:
        scenes = fallback_scenes(args.topic, args.duration // SCENE_COUNT)
    log(f"Generated {len(scenes)} scenes")

    # Save scene plan
    scenes_json = OUTPUT_DIR / "scenes.json"
    with open(scenes_json, "w") as f:
        json.dump(scenes, f, indent=2)
    log(f"Scene plan saved to {scenes_json}")
    
    # Spellcheck scene text before proceeding
    log("Spellchecking scene text...")
    all_text = " ".join(s["narration"] + " " + s["text_overlay"] for s in scenes)
    spellcheck_path = OUTPUT_DIR / "_spellcheck.txt"
    with open(spellcheck_path, "w") as f:
        f.write(all_text)
    
    spell_result = subprocess.run([
        sys.executable, "-m", "codespell",
        "--ignore-words", str(ROOT / ".." / "gullahgeecheebiz-site" / ".codespell-ignore"),
        str(spellcheck_path)
    ], capture_output=True, text=True, timeout=30)
    
    if spell_result.returncode != 0:
        log(f"⚠️  Spelling issues found in scene text:")
        for line in spell_result.stdout.strip().split("\n"):
            if line.strip():
                print(f"       {line.strip()}")
        log("Continuing anyway — fix and re-run with --no-scenes to reuse existing plan")
    else:
        log("Spelling check passed ✅")

    # Step 2: Generate voiceover
    voiceover_path = OUTPUT_DIR / "voiceover.mp3"
    if not args.no_tts:
        if not generate_voiceover(scenes, voiceover_path):
            log("Voiceover failed, continuing without audio")
            voiceover_path = None
    else:
        voiceover_path = None

    # Step 3: Generate images
    if not args.no_images:
        log("Generating scene images...")
        for i, scene in enumerate(scenes):
            num = i + 1
            img_path = SCENES_DIR / f"scene{num}.png"
            if not img_path.exists():
                log(f"Image {num}/{len(scenes)}: {scene['text_overlay']}")
                generate_image(scene["image_prompt"], img_path)
            else:
                log(f"Image {num} already exists, skipping")
    else:
        log("Skipping image generation")

    # Step 4: Build video
    output_name = args.output or f"ggb-{args.topic.lower().replace(' ', '-')[:30]}.mp4"
    output_path = OUTPUT_DIR / output_name
    
    if build_video(scenes, voiceover_path, output_path):
        print(f"\n{'='*50}")
        print(f"  ✅ Video ready: {output_path}")
        print(f"  📁 {output_path}")
        
        # Step 5: Publish to platforms
        if args.publish:
            platforms = ["tiktok", "youtube", "rumble", "x", "pinterest"] if "all" in args.publish else args.publish
            log(f"Publishing to: {', '.join(platforms)}")
            
            for platform in platforms:
                log(f"Publishing to {platform}...")
                if platform == "tiktok":
                    # Copy to TikTok upload directory
                    tiktok_dir = Path(os.path.expanduser("~/videos/tiktok"))
                    tiktok_dir.mkdir(parents=True, exist_ok=True)
                    import shutil
                    shutil.copy2(output_path, tiktok_dir / output_path.name)
                    log(f"Video staged for TikTok: {tiktok_dir / output_path.name}")
                elif platform == "youtube":
                    youtube_dir = Path(os.path.expanduser("~/videos/youtube"))
                    youtube_dir.mkdir(parents=True, exist_ok=True)
                    import shutil
                    shutil.copy2(output_path, youtube_dir / output_path.name)
                    log(f"Video staged for YouTube: {youtube_dir / output_path.name}")
                elif platform == "rumble":
                    rumble_dir = Path(os.path.expanduser("~/videos/rumble"))
                    rumble_dir.mkdir(parents=True, exist_ok=True)
                    import shutil
                    shutil.copy2(output_path, rumble_dir / output_path.name)
                    log(f"Video staged for Rumble: {rumble_dir / output_path.name}")
                elif platform == "x":
                    x_dir = Path(os.path.expanduser("~/videos/x"))
                    x_dir.mkdir(parents=True, exist_ok=True)
                    import shutil
                    shutil.copy2(output_path, x_dir / output_path.name)
                    log(f"Video staged for X: {x_dir / output_path.name}")
                elif platform == "pinterest":
                    pins_dir = Path(os.path.expanduser("~/pins-video"))
                    pins_dir.mkdir(parents=True, exist_ok=True)
                    import shutil
                    shutil.copy2(output_path, pins_dir / output_path.name)
                    log(f"Video staged for Pinterest: {pins_dir / output_path.name}")
            
            log("Publishing staging complete. Videos ready for upload bots.")
        
        print(f"{'='*50}\n")
    else:
        print(f"\n  ❌ Video build failed\n")
        sys.exit(1)

if __name__ == "__main__":
    main()
