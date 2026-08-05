#!/usr/bin/env python3
"""
GGB Video Factory v3 — Uses HyperFrames project structure for proper video rendering.
"""
import json, os, sys, time, sqlite3, subprocess, shutil
from pathlib import Path
from datetime import datetime

BASE = Path("/Users/darrylsmac/gullahgeecheebiz-site")
DB = BASE / "publish" / "publisher.db"
VIDEO_DIR = BASE / "publish" / "for-distribution" / "videos"
LOG_DIR = BASE / "ggb-engine" / "headquarters" / "logs" / "video-factory"
PROJECT_DIR = LOG_DIR / "hyperframes-project"
TEMPLATE_DIR = Path("/tmp/hf-project")

for d in [VIDEO_DIR, LOG_DIR]:
    d.mkdir(parents=True, exist_ok=True)

def log(msg):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"  [{ts}] {msg}")
    with open(LOG_DIR / "factory.log", "a") as f:
        f.write(f"[{ts}] {msg}\n")

def get_books(limit=3):
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

def setup_project():
    """Set up the HyperFrames project if not already done."""
    if not PROJECT_DIR.exists():
        log("Setting up HyperFrames project...")
        shutil.copytree(str(TEMPLATE_DIR), str(PROJECT_DIR))
        log("✅ Project created")
    return PROJECT_DIR

def generate_composition(book, video_type):
    """Generate a HyperFrames composition HTML for a book."""
    title = book["title"]
    desc = book["description"][:200]
    author = book["author"]
    
    if video_type == "book_trailer":
        html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700&family=Inter:wght@400;600&display=swap');
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{ font-family: 'Inter', sans-serif; background: #1a1a2e; color: #fff; }}
  .slide {{ width: 1920px; height: 1080px; display: flex; flex-direction: column; justify-content: center; align-items: center; text-align: center; padding: 80px; }}
  h1 {{ font-family: 'Playfair Display', serif; font-size: 72px; color: #FFD700; margin-bottom: 20px; }}
  h2 {{ font-size: 36px; color: #FFA000; margin-bottom: 30px; }}
  p {{ font-size: 28px; color: #ccc; max-width: 1400px; line-height: 1.6; }}
  .cta {{ font-size: 24px; color: #4ade80; margin-top: 40px; }}
</style>
</head>
<body>
<div class="slide">
  <h1>{title}</h1>
  <h2>By {author}</h2>
  <p>{desc}</p>
  <p class="cta">Available now from Gullah Geechee Biz</p>
</div>
</body>
</html>"""
    else:
        html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{ font-family: -apple-system, sans-serif; background: #1a1a2e; color: #fff; }}
  .slide {{ width: 1080px; height: 1920px; display: flex; flex-direction: column; justify-content: center; align-items: center; text-align: center; padding: 60px; }}
  h1 {{ font-size: 48px; color: #FFD700; margin-bottom: 20px; }}
  p {{ font-size: 24px; color: #ccc; max-width: 800px; line-height: 1.6; }}
</style>
</head>
<body>
<div class="slide">
  <h1>📚 {title}</h1>
  <p>{desc[:150]}</p>
  <p style="color:#4ade80;margin-top:40px">⬇️ Link in bio</p>
</div>
</body>
</html>"""
    
    return html

def render_video(html_content, output_name):
    """Render a video using HyperFrames."""
    project = setup_project()
    
    # Write the composition
    comp_path = project / "index.html"
    comp_path.write_text(html_content)
    
    # Render
    log(f"  Rendering {output_name}...")
    result = subprocess.run(
        ["npm", "run", "render"],
        capture_output=True, text=True, timeout=120,
        cwd=str(project)
    )
    
    if result.returncode == 0:
        # Find output
        for ext in [".mp4", ".webm", ".mov"]:
            for f in project.glob(f"*{ext}"):
                dest = VIDEO_DIR / f"{output_name}{ext}"
                shutil.copy2(str(f), str(dest))
                return True, f"rendered to {ext}"
        return True, "rendered (check project dir)"
    else:
        return False, result.stderr[:300]

def main():
    print(f"\n{'='*55}")
    print(f"  🎬 GGB VIDEO FACTORY v3")
    print(f"  HyperFrames project-based rendering")
    print(f"{'='*55}\n")
    
    log("Setting up HyperFrames project...")
    setup_project()
    
    books = get_books(limit=2)
    log(f"Loaded {len(books)} books")
    
    for i, book in enumerate(books):
        log(f"\n📖 [{i+1}/{len(books)}] {book['title'][:50]}...")
        
        for vtype in ["book_trailer", "social_short"]:
            log(f"  🎬 {vtype}...")
            html = generate_composition(book, vtype)
            output_name = f"{book['id'][:20]}_{vtype}"
            
            success, msg = render_video(html, output_name)
            if success:
                log(f"  ✅ {msg}")
            else:
                log(f"  ⚠️ {msg}")
            
            time.sleep(2)
    
    print(f"\n{'='*55}")
    print(f"  📊 COMPLETE")
    print(f"  Videos: {VIDEO_DIR}")
    print(f"{'='*55}")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log("\n⚠️ Interrupted")
        sys.exit(1)
