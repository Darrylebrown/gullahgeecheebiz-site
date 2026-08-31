#!/usr/bin/env python3
"""
GGB Product Promotion Orchestrator
Automates cross-platform product promotion using existing infrastructure.
"""
import json
import hashlib
import sqlite3
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# Configuration
SITE_DIR = Path("/Users/darrylsmac/gullahgeecheebiz-site")
PROMOTION_DIR = SITE_DIR / "publish" / "promotion" / "googleplay"
EVENT_STREAM = SITE_DIR / "publish" / "event_stream.jsonl"
POSTED_DB = SITE_DIR / "ggb-engine" / "headquarters" / "logs" / "posted.db"
LOG_DIR = SITE_DIR / "ggb-engine" / "headquarters" / "logs"
GUMROAD_RESULTS = SITE_DIR / "publish" / "check_gumroad_products.py"

# Ensure log directory exists
LOG_DIR.mkdir(parents=True, exist_ok=True)

def log_event(action, detail, source_bot="PROMOTION_GOAL"):
    """Log event to event_stream"""
    event = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "source_bot": source_bot,
        "action": action,
        "detail": detail
    }
    with open(EVENT_STREAM, "a", encoding="utf-8") as f:
        f.write(json.dumps(event) + "\n")
    print(f"[EVENT] {action}: {detail}")
    return event

def get_posted_hashes():
    """Get all already-posted file hashes by platform"""
    conn = sqlite3.connect(str(POSTED_DB))
    c = conn.cursor()
    c.execute("SELECT platform, file_hash FROM posted")
    posted = {}
    for platform, file_hash in c.fetchall():
        if platform not in posted:
            posted[platform] = set()
        posted[platform].add(file_hash)
    conn.close()
    return posted

def get_unposted_content(platform, posted_hashes):
    """Get next unposted content for a platform"""
    patterns = {
        "twitter": "*twitter-post-*.md",
        "pinterest": "*pinterest-pin-*.md",
        "instagram": "*instagram-post-*.md",
        "tiktok": "*tiktok-script-*.md"
    }
    pattern = patterns.get(platform)
    if not pattern:
        return None
    
    files = list(PROMOTION_DIR.glob(pattern))
    if not files:
        return None
    
    platform_hash = posted_hashes.get(platform, set())
    
    for f in sorted(files):
        file_hash = hashlib.md5(f.name.encode()).hexdigest()
        if file_hash not in platform_hash:
            return f, file_hash
    
    return None

def read_content(file_path):
    """Read content from markdown file, skip header line"""
    content = file_path.read_text(encoding="utf-8")
    lines = content.split("\n")
    if len(lines) > 1:
        return "\n".join(lines[1:]).strip()
    return content.strip()

def post_to_pinterest(content, cover_image=None):
    """Post to Pinterest via existing browser bot infrastructure"""
    # Use the existing Pinterest browser bot
    pinterest_bot = SITE_DIR / "ggb-engine" / "headquarters" / "pinterest-browser-bot.py"
    
    if not pinterest_bot.exists():
        return {"success": False, "error": "Pinterest bot not found"}
    
    # Create a temporary CSV entry for the bot
    csv_file = LOG_DIR / "universal-submitter" / "csv" / "pinterest-feed.csv"
    csv_file.parent.mkdir(parents=True, exist_ok=True)
    
    # Read existing CSV or create new one
    if csv_file.exists():
        existing = csv_file.read_text()
    else:
        existing = "link,title,description,image\n"
    
    # Generate a simple title from content
    title = content.split("\n")[0][:100] if content else "Gullah Geechee Content"
    
    # Append new entry
    new_entry = f"https://gullahgeecheebiz.com,{title},{content[:500]},\n"
    
    with open(csv_file, "a", encoding="utf-8") as f:
        f.write(new_entry)
    
    log_event("pinterest_content_queued", f"Queued for Pinterest: {title[:50]}...")
    
    return {
        "success": True,
        "message": "Content queued for Pinterest",
        "content_preview": content[:100]
    }

def post_to_twitter_xurl(content):
    """Post to Twitter/X using xurl CLI"""
    xurl_path = Path.home() / ".local" / "bin" / "xurl"
    
    if not xurl_path.exists():
        return {"success": False, "error": "xurl not installed"}
    
    # Check auth status first
    result = subprocess.run(
        [str(xurl_path), "auth", "status"],
        capture_output=True,
        text=True,
        timeout=10
    )
    
    if "No apps registered" in result.stdout:
        return {
            "success": False,
            "error": "xurl not authenticated - need to run: xurl auth apps add",
            "content": content[:280]
        }
    
    # Post to Twitter
    tweet = content[:280]
    result = subprocess.run(
        [str(xurl_path), "post", tweet],
        capture_output=True,
        text=True,
        timeout=30
    )
    
    if result.returncode == 0:
        url = result.stdout.strip()
        return {
            "success": True,
            "url": url,
            "content": tweet
        }
    else:
        return {
            "success": False,
            "error": result.stderr,
            "content": tweet
        }

def mark_as_posted(file_path, platform, file_hash):
    """Mark content as posted in database"""
    posted_at = datetime.now(timezone.utc).isoformat()
    
    conn = sqlite3.connect(str(POSTED_DB))
    c = conn.cursor()
    c.execute(
        "INSERT INTO posted (platform, file_hash, file_path, posted_at) VALUES (?, ?, ?, ?)",
        (platform, file_hash, str(file_path), posted_at)
    )
    conn.commit()
    conn.close()

def get_gumroad_products():
    """Get live Gumroad products"""
    try:
        result = subprocess.run(
            ["python3", str(GUMROAD_RESULTS)],
            capture_output=True,
            text=True,
            timeout=30
        )
        output = result.stdout
        lines = output.strip().split("\n")
        
        products = []
        for line in lines:
            if line.startswith("  Vol"):
                # Parse: "  Vol 06: https://debtide0.gumroad.com/l/ywalzh"
                parts = line.strip().split(": ")
                if len(parts) == 2:
                    vol_num = parts[0].replace("Vol ", "")
                    url = parts[1]
                    products.append({"volume": vol_num, "url": url})
        
        return products
    except Exception as e:
        log_event("gumroad_check_error", str(e))
        return []

def main():
    print(f"\n{'='*70}")
    print(f"🚀 GGB PRODUCT PROMOTION ORCHESTRATOR")
    print(f"   {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print(f"{'='*70}\n")
    
    # Log start
    log_event("promotion_start", "Starting automated promotion cycle")
    
    # Get current state
    gumroad_products = get_gumroad_products()
    log_event("gumroad_status", f"Found {len(gumroad_products)} live Gumroad products")
    
    # Get posted hashes
    posted_hashes = get_posted_hashes()
    log_event("posting_status", f"Already posted: {sum(len(v) for v in posted_hashes.values())} items across {len(posted_hashes)} platforms")
    
    results = {}
    posts_made = []
    
    # Priority 1: Twitter/X (largest content pool, highest impact)
    print("\n📱 Checking Twitter/X...")
    twitter_content = get_unposted_content("twitter", posted_hashes)
    if twitter_content:
        file_path, file_hash = twitter_content
        content = read_content(file_path)
        print(f"   📝 Found unposted tweet: {file_path.name}")
        
        result = post_to_twitter_xurl(content)
        results["twitter"] = result
        
        if result["success"]:
            mark_as_posted(file_path, "twitter", file_hash)
            posts_made.append({"platform": "twitter", "file": file_path.name, "url": result.get("url")})
            print(f"   ✅ Posted to Twitter: {result.get('url', 'URL not returned')}")
        else:
            print(f"   ❌ Failed: {result.get('error', 'Unknown error')}")
    else:
        results["twitter"] = {"success": False, "error": "No unposted content"}
        print("   ⚠️  No unposted Twitter content")
    
    # Priority 2: Pinterest (proven working channel)
    print("\n📌 Checking Pinterest...")
    pinterest_content = get_unposted_content("pinterest", posted_hashes)
    if pinterest_content:
        file_path, file_hash = pinterest_content
        content = read_content(file_path)
        print(f"   📝 Found unposted pin: {file_path.name}")
        
        result = post_to_pinterest(content)
        results["pinterest"] = result
        
        if result["success"]:
            mark_as_posted(file_path, "pinterest", file_hash)
            posts_made.append({"platform": "pinterest", "file": file_path.name})
            print(f"   ✅ Queued for Pinterest")
        else:
            print(f"   ❌ Failed: {result.get('error', 'Unknown error')}")
    else:
        results["pinterest"] = {"success": False, "error": "No unposted content"}
        print("   ⚠️  No unposted Pinterest content")
    
    # Priority 3: Instagram
    print("\n📸 Checking Instagram...")
    instagram_content = get_unposted_content("instagram", posted_hashes)
    if instagram_content:
        file_path, file_hash = instagram_content
        content = read_content(file_path)
        print(f"   📝 Found unposted Instagram post: {file_path.name}")
        
        # Instagram requires browser automation - queue it
        queue_file = LOG_DIR / f"instagram-queue-{datetime.now().strftime('%Y%m%d-%H%M%S')}.txt"
        with open(queue_file, "w", encoding="utf-8") as f:
            f.write(content)
        
        results["instagram"] = {
            "success": True,
            "message": "Content queued for Instagram browser posting",
            "queue_file": str(queue_file)
        }
        mark_as_posted(file_path, "instagram", file_hash)
        posts_made.append({"platform": "instagram", "file": file_path.name})
        print(f"   ✅ Queued for Instagram")
    else:
        results["instagram"] = {"success": False, "error": "No unposted content"}
        print("   ⚠️  No unposted Instagram content")
    
    # Priority 4: TikTok
    print("\n🎵 Checking TikTok...")
    tiktok_content = get_unposted_content("tiktok", posted_hashes)
    if tiktok_content:
        file_path, file_hash = tiktok_content
        content = read_content(file_path)
        print(f"   📝 Found unposted TikTok script: {file_path.name}")
        
        # TikTok requires browser automation - queue it
        queue_file = LOG_DIR / f"tiktok-queue-{datetime.now().strftime('%Y%m%d-%H%M%S')}.txt"
        with open(queue_file, "w", encoding="utf-8") as f:
            f.write(content)
        
        results["tiktok"] = {
            "success": True,
            "message": "Content queued for TikTok browser posting",
            "queue_file": str(queue_file)
        }
        mark_as_posted(file_path, "tiktok", file_hash)
        posts_made.append({"platform": "tiktok", "file": file_path.name})
        print(f"   ✅ Queued for TikTok")
    else:
        results["tiktok"] = {"success": False, "error": "No unposted content"}
        print("   ⚠️  No unposted TikTok content")
    
    # Summary
    print(f"\n{'='*70}")
    print(f"📊 PROMOTION CYCLE COMPLETE")
    print(f"{'='*70}")
    print(f"\nProducts on Gumroad: {len(gumroad_products)}")
    print(f"Posts made this cycle: {len(posts_made)}")
    
    for platform, result in results.items():
        status = "✅" if result.get("success") else "❌"
        msg = result.get("message", result.get("error", "Unknown"))
        print(f"   {status} {platform.capitalize()}: {msg}")
    
    if posts_made:
        print(f"\n📝 Posted content:")
        for post in posts_made:
            print(f"   • {post['platform']}: {post['file']}")
    
    # Final log event
    log_event("promotion_cycle_complete", f"Posted {len(posts_made)} items. Platforms: {list(results.keys())}")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
