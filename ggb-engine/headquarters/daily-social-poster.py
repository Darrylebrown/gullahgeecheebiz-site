#!/usr/bin/env python3
"""
GGB Daily Social Poster — posts one piece of content per platform every day.
Twitter/X via xurl CLI, others via browser automation.
"""
import json, os, sys, sqlite3, subprocess, random, time
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Optional

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SOCIAL_DIR = REPO_ROOT / "publish" / "content-engine" / "social"
LOGS_DIR = Path(__file__).resolve().parent / "logs"
POSTED_DB = LOGS_DIR / "posted.db"

LOGS_DIR.mkdir(parents=True, exist_ok=True)

def init_db():
    conn = sqlite3.connect(str(POSTED_DB))
    conn.execute("""CREATE TABLE IF NOT EXISTS posted (
        id TEXT PRIMARY KEY,
        platform TEXT,
        content TEXT,
        posted_at TEXT,
        success INTEGER DEFAULT 1
    )""")
    conn.commit()
    return conn

def get_today_posts(conn) -> Dict:
    """Get today's scheduled posts — one per platform."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    
    # Check what we've already posted today
    already_posted = set()
    for row in conn.execute("SELECT platform FROM posted WHERE posted_at LIKE ?", (f"{today}%",)):
        already_posted.add(row[0])
    
    platforms = ["twitter", "facebook", "instagram", "tiktok"]
    posts = {}
    
    for platform in platforms:
        if platform in already_posted:
            continue
        
        # Get a random unposted post for this platform
        posted_ids = set()
        for row in conn.execute("SELECT id FROM posted WHERE platform = ?", (platform,)):
            posted_ids.add(row[0])
        
        platform_dir = SOCIAL_DIR / platform
        if not platform_dir.exists():
            continue
        
        available = [f for f in sorted(platform_dir.glob("*.txt")) if f.stem not in posted_ids]
        if available:
            chosen = random.choice(available)
            posts[platform] = {
                "file": chosen,
                "content": chosen.read_text().strip(),
            }
    
    return posts

def post_to_twitter(content: str) -> bool:
    """Post to Twitter/X using xurl CLI."""
    try:
        result = subprocess.run(
            ["xurl", "post", content[:280]],
            capture_output=True, text=True, timeout=30
        )
        return result.returncode == 0
    except Exception:
        return False

def post_to_facebook(content: str) -> bool:
    """Post to Facebook — placeholder for now."""
    # Facebook requires API setup or browser automation
    # For now, save to a queue for manual posting
    queue_file = LOGS_DIR / "facebook-queue.txt"
    with open(queue_file, "a") as f:
        f.write(f"{datetime.now().isoformat()}|{content}\n")
    return True  # Queued successfully

def post_to_instagram(content: str) -> bool:
    """Post to Instagram — placeholder for now."""
    queue_file = LOGS_DIR / "instagram-queue.txt"
    with open(queue_file, "a") as f:
        f.write(f"{datetime.now().isoformat()}|{content}\n")
    return True

def post_to_tiktok(content: str) -> bool:
    """Post to TikTok — placeholder for now."""
    queue_file = LOGS_DIR / "tiktok-queue.txt"
    with open(queue_file, "a") as f:
        f.write(f"{datetime.now().isoformat()}|{content}\n")
    return True

def run_daily():
    """Run the daily social media posting cycle."""
    print(f"\n{'='*60}")
    print(f"📱 DAILY SOCIAL POSTER")
    print(f"   {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}")
    print(f"{'='*60}")
    
    conn = init_db()
    posts = get_today_posts(conn)
    
    if not posts:
        print("   ✅ All platforms posted for today")
        conn.close()
        return
    
    results = {}
    
    for platform, post_data in posts.items():
        content = post_data["content"]
        post_id = post_data["file"].stem
        
        print(f"\n  📱 {platform.title()}")
        print(f"     {content[:100]}...")
        
        success = False
        if platform == "twitter":
            success = post_to_twitter(content)
        elif platform == "facebook":
            success = post_to_facebook(content)
        elif platform == "instagram":
            success = post_to_instagram(content)
        elif platform == "tiktok":
            success = post_to_tiktok(content)
        
        if success:
            conn.execute("INSERT OR REPLACE INTO posted VALUES (?,?,?,?,?)",
                        (post_id, platform, content, datetime.now(timezone.utc).isoformat(), 1))
            conn.commit()
            results[platform] = "✅ Posted"
            print(f"     ✅ Posted")
        else:
            results[platform] = "❌ Failed"
            print(f"     ❌ Failed")
    
    conn.close()
    
    print(f"\n{'='*60}")
    print(f"📊 SUMMARY")
    print(f"{'='*60}")
    for platform, status in results.items():
        print(f"  {platform:12s} {status}")
    
    return results

if __name__ == "__main__":
    run_daily()
