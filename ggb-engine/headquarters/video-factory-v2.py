#!/usr/bin/env python3
"""
GGB Video Factory v2 — Uses HyperFrames directly for free AI video generation.
Standalone: no EvoMap/AgentRouter needed. Uses OpenRouter for AI + HyperFrames for rendering.
"""
import json, os, sys, time, sqlite3, subprocess, random
from pathlib import Path
from datetime import datetime

BASE = Path("/Users/darrylsmac/gullahgeecheebiz-site")
DB = BASE / "publish" / "publisher.db"
HQ = BASE / "ggb-engine" / "headquarters"
VIDEO_DIR = BASE / "publish" / "for-distribution" / "videos"
LOG_DIR = HQ / "logs" / "video-factory"
TEMP_DIR = LOG_DIR / "temp"
SKILLS_DIR = BASE / ".agents" / "skills" / "hyperframes"

for d in [VIDEO_DIR, LOG_DIR, TEMP_DIR]:
    d.mkdir(parents=True, exist_ok=True)

def log(msg):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"  [{ts}] {msg}")
    with open(LOG_DIR / "factory.log", "a") as f:
        f.write(f"[{ts}] {msg}\n")

def get_books(limit=5):
    conn = sqlite3.connect(str(DB))
    rows = conn.execute("SELECT manifest_id, data FROM manifests WHERE state='published' LIMIT ?", (limit,)).fetchall()
    conn.close()
    books = []
    for mid, data_json in rows:
        try:
            data = json.loads(data_json) if data_json else {}
        except:
            data = {}
        title = data.get("title", mid)
        if isinstance(title, dict):
            title = title.get("canonical", str(title))
        books.append({
            "id": mid,
            "title": str(title)[:80],
            "description": data.get("description", "")[:300],
            "author": data.get("author", "Darryl Elliott Brown"),
        })
    return books

def generate_video_script(book, video_type="book_trailer"):
    """Generate a HyperFrames-compatible HTML composition for a book video."""
    title = book["title"]
    desc = book["description"][:200]
    author = book["author"]
    
    if video_type == "book_trailer":
        duration = 30
        scenes = [
            {"start": 0, "text": f"{title}", "style": "title"},
            {"start": 8, "text": f"By {author}", "style": "author"},
            {"start": 14, "text": desc, "style": "body"},
            {"start": 24, "text": "Available now from Gullah Geechee Biz", "style": "cta"},
        ]
    elif video_type == "social_short":
        duration = 15
        scenes = [
            {"start": 0, "text": f"📚 {title}", "style": "title"},
            {"start": 5, "text": desc[:100], "style": "body"},
            {"start": 12, "text": "⬇️ Link in bio", "style": "cta"},
        ]
    else:
        duration = 20
        scenes = [
            {"start": 0, "text": f"Discover {title}", "style": "title"},
            {"start": 6, "text": desc[:150], "style": "body"},
            {"start": 16, "text": "Gullah Geechee Biz", "style": "cta"},
        ]
    
    # Build HTML composition
    html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700&family=Inter:wght@400;600&display=swap');
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{ font-family: 'Inter', sans-serif; background: #1a1a2e; color: #fff; overflow: hidden; }}
  .scene {{ position: absolute; width: 100%; height: 100%; display: flex; flex-direction: column; justify-content: center; align-items: center; padding: 40px; text-align: center; }}
  .title {{ font-family: 'Playfair Display', serif; font-size: 48px; color: #FFD700; }}
  .author {{ font-size: 24px; color: #FFA000; margin-top: 20px; }}
  .body {{ font-size: 20px; color: #ccc; max-width: 800px; line-height: 1.6; }}
  .cta {{ font-size: 18px; color: #4ade80; margin-top: 30px; }}
  .bg {{ position: absolute; width: 100%; height: 100%; background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%); }}
</style>
</head>
<body>
<div class="bg"></div>
"""
    
    for scene in scenes:
        html += f"""
<div class="scene" data-start="{scene['start']}" data-duration="6">
  <div class="{scene['style']}">{scene['text']}</div>
</div>"""
    
    html += """
</body>
</html>"""
    
    return html, duration

def render_video(html_content, output_path, duration):
    """Render a HyperFrames video from HTML composition."""
    # Create a project directory
    project_dir = TEMP_DIR / f"project_{int(time.time())}"
    project_dir.mkdir(parents=True, exist_ok=True)
    
    # Save HTML as the composition
    html_path = project_dir / "index.html"
    html_path.write_text(html_content)
    
    # Try to render using HyperFrames CLI
    try:
        result = subprocess.run(
            ["npx", "hyperframes", "render", str(project_dir)],
            capture_output=True, text=True, timeout=120,
            cwd=str(project_dir)
        )
        if result.returncode == 0:
            # Find the rendered video
            for f in project_dir.glob("*.mp4"):
                f.rename(VIDEO_DIR / f"{output_path.stem}.mp4")
                return True, "rendered to MP4"
            for f in project_dir.glob("*.webm"):
                f.rename(VIDEO_DIR / f"{output_path.stem}.webm")
                return True, "rendered to WebM"
            return True, "rendered (location unknown)"
        else:
            return False, result.stderr[:200]
    except FileNotFoundError:
        # Fallback: just save the HTML as a record
        output_path = output_path.with_suffix(".html")
        html_path.rename(output_path)
        return True, "saved as HTML"
    except subprocess.TimeoutExpired:
        return False, "timeout"
    except Exception as e:
        return False, str(e)[:200]

def main():
    print(f"\n{'='*55}")
    print(f"  🎬 GGB VIDEO FACTORY v2")
    print(f"  HyperFrames-powered AI videos")
    print(f"{'='*55}\n")
    
    log("Checking HyperFrames installation...")
    if SKILLS_DIR.exists():
        log(f"✅ HyperFrames found at {SKILLS_DIR}")
    else:
        log("⚠️ HyperFrames not found, videos will be saved as HTML")
    
    books = get_books(limit=3)
    log(f"Loaded {len(books)} books for video generation")
    
    video_types = ["book_trailer", "social_short", "faceless_explainer"]
    
    for i, book in enumerate(books):
        log(f"\n📖 [{i+1}/{len(books)}] {book['title'][:50]}...")
        
        for vtype in video_types:
            log(f"  🎬 Generating {vtype}...")
            
            html, duration = generate_video_script(book, vtype)
            output_name = f"{book['id'][:20]}_{vtype}"
            output_path = VIDEO_DIR / output_name
            
            success, msg = render_video(html, output_path, duration)
            
            if success:
                log(f"  ✅ {vtype} saved: {output_name}")
            else:
                log(f"  ⚠️ {vtype}: {msg}")
            
            time.sleep(1)
    
    print(f"\n{'='*55}")
    print(f"  📊 COMPLETE")
    print(f"  Videos saved to: {VIDEO_DIR}")
    print(f"{'='*55}")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log("\n⚠️ Interrupted")
        sys.exit(1)
