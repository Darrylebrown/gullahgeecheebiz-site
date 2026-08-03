#!/usr/bin/env python3
"""
GGB Avatar Promoter — a cute animated character that promotes
books, magazines, and encyclopedia volumes on social media.
Uses Agnes for scripts, images, and video.
"""
import json, os, sys, sqlite3, urllib.request, time, re
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Optional

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
PUB_DB = REPO_ROOT / "publish" / "publisher.db"
AVATAR_DIR = REPO_ROOT / "publish" / "avatar"
LOGS_DIR = Path(__file__).resolve().parent / "logs"
PROMO_DIR = REPO_ROOT / "publish" / "promos"

AVATAR_DIR.mkdir(parents=True, exist_ok=True)
LOGS_DIR.mkdir(parents=True, exist_ok=True)
PROMO_DIR.mkdir(parents=True, exist_ok=True)

AGNES_KEY = os.environ.get("AGNES_API_KEY", "sk-qGBXic9m7VJcJ1vLJ6UPDdJLUbbunIWsNWs4Yl8RqFOfJPCj")
AGNES_CHAT_URL = "https://apihub.agnes-ai.com/v1/chat/completions"
AGNES_VIDEO_URL = "https://apihub.agnes-ai.com/v1/videos"
AGNES_IMAGE_URL = "https://apihub.agnes-ai.com/v1/images/generations"

AVATAR_IMAGE = AVATAR_DIR / "ggb-avatar.png"
AVATAR_URL = "https://gullahgeecheebiz.com/avatar/ggb-avatar.png"

PROMO_DB = LOGS_DIR / "promos.db"

AVATAR_PERSONALITY = """You are Binyah — a cute, warm, funny animated character who is the friendly face of Gullah Geechee Biz. You're the kind of friend who makes everyone feel welcome. You speak with warmth, humor, and genuine excitement about books, culture, and community.

Your style:
- Warm and approachable — like a favorite cousin
- Playful humor — you make people smile
- Genuine enthusiasm — you LOVE books and sharing them
- Gullah Geechee proud — you celebrate the culture
- Never pushy — you invite, you don't sell

You use phrases like:
- "Hey friend!"
- "Come check this out!"
- "Y'all are gonna love this one"
- "Let me tell you about..."
- "This one's special, I'm telling you"

Keep it short (30-60 seconds when spoken), warm, and fun."""

def init_db():
    conn = sqlite3.connect(str(PROMO_DB))
    conn.execute("""CREATE TABLE IF NOT EXISTS promos (
        id TEXT PRIMARY KEY,
        source_type TEXT,
        source_id TEXT,
        title TEXT,
        script TEXT,
        video_url TEXT,
        local_path TEXT,
        platform TEXT,
        posted INTEGER DEFAULT 0,
        created_at TEXT
    )""")
    conn.commit()
    return conn

def call_agnes(prompt: str, max_tokens: int = 2000) -> str:
    data = json.dumps({
        "model": "agnes-2.5-flash",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
    }).encode()
    req = urllib.request.Request(AGNES_CHAT_URL, data=data, headers={
        "Content-Type": "application/json",
        "Authorization": f"Bearer {AGNES_KEY}",
    })
    resp = urllib.request.urlopen(req, timeout=60)
    return json.loads(resp.read())["choices"][0]["message"]["content"]

def upload_avatar_to_agnes() -> Optional[str]:
    """Upload avatar to a publicly accessible URL for Agnes video API."""
    # For now, we use the local path — Agnes needs a public URL
    # In production, upload to the site's CDN
    if AVATAR_IMAGE.exists():
        return str(AVATAR_IMAGE)
    return None

def generate_promo_script(title: str, description: str, source_type: str) -> str:
    """Generate a warm, funny promo script for Binyah the avatar to read."""
    prompt = f"""{AVATAR_PERSONALITY}

Write a short, warm, funny promotional script (30-45 seconds when spoken) for Binyah to present this {source_type}:

Title: {title}
Description: {description}

Write the script as Binyah would say it — warm, playful, inviting. Include stage directions in [brackets] for expressions and gestures. Keep it under 100 words."""

    return call_agnes(prompt, max_tokens=1500)

def generate_promo_image(title: str, source_type: str) -> Optional[str]:
    """Generate a promotional image featuring Binyah with the book/magazine."""
    prompt = f"""A cute animated character named Binyah (warm brown skin, navy blue vest with gold trim, big expressive eyes) holding up a copy of '{title}' with a big smile. Warm, friendly, inviting style. Cartoon/Pixar-inspired. Bright colorful background. Promotional social media post style. 1024x1024 square format."""

    data = json.dumps({
        "model": "agnes-image-2.0-flash",
        "prompt": prompt,
        "n": 1,
        "size": "1024x1024",
    }).encode()
    
    req = urllib.request.Request(AGNES_IMAGE_URL, data=data, headers={
        "Content-Type": "application/json",
        "Authorization": f"Bearer {AGNES_KEY}",
    })
    
    try:
        resp = urllib.request.urlopen(req, timeout=60)
        result = json.loads(resp.read())
        return result["data"][0]["url"]
    except Exception:
        return None

def create_promo_video(script: str, image_url: str) -> Optional[str]:
    """Create a talking video using Agnes Video V2.0 with the avatar image."""
    prompt = f"""Binyah, a cute animated character with warm brown skin and a navy blue vest with gold trim, speaks warmly to the camera with a friendly smile. Gentle head movements, warm expression, natural talking motion. The character says: {script[:200]}"""

    data = json.dumps({
        "model": "agnes-video-v2.0",
        "prompt": prompt,
        "image": image_url,
        "num_frames": 81,
        "frame_rate": 24,
        "width": 576,
        "height": 1024,
    }).encode()
    
    req = urllib.request.Request(AGNES_VIDEO_URL, data=data, headers={
        "Content-Type": "application/json",
        "Authorization": f"Bearer {AGNES_KEY}",
    })
    
    try:
        resp = urllib.request.urlopen(req, timeout=60)
        result = json.loads(resp.read())
        video_id = result.get("video_id")
        if video_id:
            # Poll for completion
            for _ in range(30):
                time.sleep(5)
                poll = urllib.request.Request(
                    f"https://apihub.agnes-ai.com/agnesapi?video_id={video_id}",
                    headers={"Authorization": f"Bearer {AGNES_KEY}"}
                )
                try:
                    poll_resp = urllib.request.urlopen(poll, timeout=30)
                    poll_result = json.loads(poll_resp.read())
                    if poll_result.get("status") == "completed":
                        return poll_result["metadata"]["url"]
                except:
                    pass
        return None
    except Exception as e:
        return None

def promote_book(conn, manifest_id: str, title: str, description: str) -> Dict:
    """Create a full promo package for one book."""
    promo_id = f"promo-{manifest_id[:8]}"
    
    # Check if already done
    existing = conn.execute("SELECT id FROM promos WHERE id = ?", (promo_id,)).fetchone()
    if existing:
        return {"status": "skipped", "id": promo_id}
    
    print(f"  🎬 {title[:50]}...")
    
    # 1. Generate script
    script = generate_promo_script(title, description, "book")
    print(f"     📝 Script: {len(script.split())} words")
    
    # 2. Generate promo image with Binyah
    image_url = generate_promo_image(title, "book")
    if image_url:
        print(f"     🖼️  Promo image generated")
    else:
        print(f"     ⚠️  No promo image")
    
    # 3. Save the promo package
    promo_dir = PROMO_DIR / promo_id
    promo_dir.mkdir(parents=True, exist_ok=True)
    (promo_dir / "script.txt").write_text(script)
    
    conn.execute("INSERT OR REPLACE INTO promos VALUES (?,?,?,?,?,?,?,?,?,?)",
                (promo_id, "book", manifest_id, title, script, image_url or "", str(promo_dir),
                 "tiktok", 0, datetime.now(timezone.utc).isoformat()))
    conn.commit()
    
    return {"status": "created", "id": promo_id, "script_words": len(script.split())}

def promote_magazine(conn, name: str, sport: str) -> Dict:
    """Create a promo package for a magazine issue."""
    promo_id = f"promo-mag-{name}"
    
    existing = conn.execute("SELECT id FROM promos WHERE id = ?", (promo_id,)).fetchone()
    if existing:
        return {"status": "skipped", "id": promo_id}
    
    title = f"{sport} Weekly"
    description = f"Check out the latest issue of {sport} Weekly magazine from Gullah Geechee Biz!"
    
    print(f"  🎬 {title}...")
    
    script = generate_promo_script(title, description, "magazine")
    print(f"     📝 Script: {len(script.split())} words")
    
    promo_dir = PROMO_DIR / promo_id
    promo_dir.mkdir(parents=True, exist_ok=True)
    (promo_dir / "script.txt").write_text(script)
    
    conn.execute("INSERT OR REPLACE INTO promos VALUES (?,?,?,?,?,?,?,?,?,?)",
                (promo_id, "magazine", name, title, script, "", str(promo_dir),
                 "tiktok", 0, datetime.now(timezone.utc).isoformat()))
    conn.commit()
    
    return {"status": "created", "id": promo_id}

def run_batch(limit: int = 5):
    """Process a batch of books and magazines for promotion."""
    print(f"\n{'='*60}")
    print(f"🎬 BINYAH AVATAR PROMOTER")
    print(f"   {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}")
    print(f"{'='*60}")
    
    conn = init_db()
    results = []
    
    # Promote books
    print(f"\n📚 Books")
    pub_conn = sqlite3.connect(str(PUB_DB))
    rows = pub_conn.execute("""
        SELECT manifest_id, json_extract(data, '$.title.canonical'),
               json_extract(data, '$.description.short')
        FROM manifests WHERE state = 'approved'
        LIMIT ?
    """, (limit,)).fetchall()
    pub_conn.close()
    
    for r in rows:
        result = promote_book(conn, r[0], r[1] or "Untitled", r[2] or "A Gullah Geechee Biz publication")
        results.append(result)
        time.sleep(1)
    
    # Promote magazines
    print(f"\n📰 Magazines")
    mag_dir = REPO_ROOT / "publish" / "magazines"
    for f in sorted(mag_dir.glob("*.md"))[:limit]:
        name = f.stem
        parts = name.split("-weekly-")
        if len(parts) >= 2:
            sport = parts[0].replace("-", " ").title()
            result = promote_magazine(conn, name, sport)
            results.append(result)
            time.sleep(1)
    
    conn.close()
    
    print(f"\n{'='*60}")
    print(f"📊 SUMMARY")
    print(f"{'='*60}")
    created = sum(1 for r in results if r.get("status") == "created")
    print(f"Promos created: {created}")
    print(f"Total: {len(results)}")
    
    return results

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch", type=int, default=5)
    args = parser.parse_args()
    run_batch(args.batch)
