#!/usr/bin/env python3
"""Build the first Gullah Geechee Biz faceless commercial.
Uses Pillow for text overlays (no drawtext filter needed)."""

import os
import subprocess
from PIL import Image, ImageDraw, ImageFont

DIR = os.path.expanduser("~/gullahgeecheebiz-site/video-scripts/faceless-commercial-1")
SCENES = os.path.join(DIR, "scenes")
OUT = os.path.join(DIR, "output")
VO = os.path.join(DIR, "voiceover.mp3")
FINAL = os.path.join(OUT, "ggb-faceless-commercial-1.mp4")

os.makedirs(OUT, exist_ok=True)

# Get voiceover duration
result = subprocess.run(
    ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", VO],
    capture_output=True, text=True
)
vo_dur = float(result.stdout.strip())
print(f"Voiceover duration: {vo_dur:.1f}s")

# Scene definitions: (duration_sec, image_file, text_overlay)
scenes = [
    (8,  "scene1.png", "300 years on this land"),
    (8,  "scene2.png", "Every basket carries a story"),
    (8,  "scene3.png", "Roots that run deep"),
    (8,  "scene4.png", "Our stories. Our voice."),
    (8,  "scene5.png", "GULLAH GEECHEE BIZ"),
    (10, "scene6.png", "Shop. Read. Belong."),
    (10, "scene6.png", "gullahgeecheebiz.com"),
]

total_dur = sum(s[0] for s in scenes)
print(f"Total video duration: {total_dur}s")

# Find a good font
font_paths = [
    "/System/Library/Fonts/Helvetica.ttc",
    "/System/Library/Fonts/Helvetica.ttf",
    "/Library/Fonts/Arial.ttf",
]
font_path = None
for fp in font_paths:
    if os.path.exists(fp):
        font_path = fp
        break

if not font_path:
    # Fallback: use any available font
    import glob
    fonts = glob.glob("/System/Library/Fonts/*.ttf") + glob.glob("/System/Library/Fonts/*.ttc")
    font_path = fonts[0] if fonts else None

print(f"Using font: {font_path}")

# Build each scene
clip_files = []
current_time = 0.0

for i, (dur, img, text) in enumerate(scenes):
    num = i + 1
    img_path = os.path.join(SCENES, img)
    clip_path = os.path.join(OUT, f"clip{num}.mp4")
    vo_seg = os.path.join(OUT, f"vo_seg{num}.mp3")
    frame_dir = os.path.join(OUT, f"frames{num}")
    os.makedirs(frame_dir, exist_ok=True)

    # Extract voiceover segment
    subprocess.run([
        "ffmpeg", "-y",
        "-i", VO,
        "-ss", str(current_time), "-t", str(dur),
        "-c:a", "libmp3lame", "-b:a", "48k", "-ar", "24000", "-ac", "1",
        vo_seg
    ], capture_output=True)

    # Open and resize image to 1080x1920
    img = Image.open(img_path).convert("RGB")
    img = img.resize((1080, 1920), Image.LANCZOS)

    # Add text overlay
    draw = ImageDraw.Draw(img)
    
    # Try different font sizes
    font_size = 48
    try:
        if font_path and font_path.endswith('.ttc'):
            font = ImageFont.truetype(font_path, font_size, index=0)
        elif font_path:
            font = ImageFont.truetype(font_path, font_size)
        else:
            font = ImageFont.load_default()
    except:
        font = ImageFont.load_default()

    # Get text size
    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]

    # Draw semi-transparent bar at bottom
    bar_y = 1700
    bar_h = 180
    draw.rectangle([(0, bar_y), (1080, bar_y + bar_h)], fill=(0, 0, 0, 180))

    # Draw text centered in bar
    tx = (1080 - tw) // 2
    ty = bar_y + (bar_h - th) // 2
    draw.text((tx, ty), text, fill=(255, 255, 255), font=font)

    # Save frame
    frame_path = os.path.join(frame_dir, "frame.png")
    img.save(frame_path)

    # Create video from single frame + audio
    subprocess.run([
        "ffmpeg", "-y",
        "-loop", "1", "-i", frame_path,
        "-i", vo_seg,
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-c:a", "aac", "-b:a", "128k",
        "-t", str(dur), "-pix_fmt", "yuv420p",
        "-vf", "scale=1080:1920",
        clip_path
    ], capture_output=True)

    print(f"Scene {num} done ({dur}s): {text}")
    clip_files.append(clip_path)
    current_time += dur

# Concatenate all clips
print("Concatenating...")
concat_file = os.path.join(OUT, "concat.txt")
with open(concat_file, "w") as f:
    for clip in clip_files:
        f.write(f"file '{clip}'\n")

result = subprocess.run([
    "ffmpeg", "-y",
    "-f", "concat", "-safe", "0",
    "-i", concat_file,
    "-c:v", "libx264", "-preset", "fast", "-crf", "23",
    "-c:a", "aac", "-b:a", "128k",
    "-pix_fmt", "yuv420p",
    FINAL
], capture_output=True, text=True)

if os.path.exists(FINAL):
    size = os.path.getsize(FINAL)
    print(f"\nDone! Output: {FINAL}")
    print(f"Size: {size / 1024 / 1024:.1f} MB")
else:
    print("ERROR: Output file not created")
    print(result.stderr[-500:] if result.stderr else "No stderr")
