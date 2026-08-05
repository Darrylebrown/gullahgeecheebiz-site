#!/usr/bin/env python3
"""
GGB Video Factory — Free AI Video Generation for Every Book
Uses HyperFrames via Evox (free credits) + AgentRouter (Opus 5) for zero-cost video production.
Integrates with Publishing Controller (:8090), Bot Factory (:8091), and Social Media SOE.
"""
import json, os, sys, time, sqlite3, hashlib, random, subprocess, shutil
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

BASE = Path("/Users/darrylsmac/gullahgeecheebiz-site")
DB = BASE / "publish" / "publisher.db"
HQ = BASE / "ggb-engine" / "headquarters"
VIDEO_DIR = BASE / "publish" / "for-distribution" / "videos"
ACCOUNTS_FILE = HQ / "logs" / "video-factory" / "accounts.json"
PROGRESS_FILE = HQ / "logs" / "video-factory" / "progress.json"
LOG_FILE = HQ / "logs" / "video-factory" / "factory.log"
TEMP_DIR = HQ / "logs" / "video-factory" / "temp"

for d in [VIDEO_DIR, TEMP_DIR, HQ / "logs" / "video-factory"]:
    d.mkdir(parents=True, exist_ok=True)

# ─── Video Types ─────────────────────────────────────────────────────
VIDEO_TYPES = {
    "book_trailer": {
        "length": "30-60s",
        "style": "cinematic",
        "platform": "agentrouter",
        "model": "opus-5",
        "description": "Cinematic book trailer with motion graphics and voiceover",
    },
    "social_short": {
        "length": "15s",
        "style": "vertical",
        "platform": "evox",
        "model": "kimi-k3",
        "description": "Vertical short for TikTok/Instagram/Reels",
    },
    "faceless_youtube": {
        "length": "60s+",
        "style": "explainer",
        "platform": "evox",
        "model": "gpt-5.6-sol",
        "description": "Faceless YouTube content with stock footage and text",
    },
    "binyah_promo": {
        "length": "30s",
        "style": "avatar",
        "platform": "agentrouter",
        "model": "opus-5",
        "description": "Binyah avatar promotional video",
    },
}

# ─── Logging ─────────────────────────────────────────────────────────
def log(msg: str):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    with open(LOG_FILE, "a") as f:
        f.write(line + "\n")

# ─── Account Management ──────────────────────────────────────────────
def load_accounts() -> Dict:
    if ACCOUNTS_FILE.exists():
        try:
            return json.loads(ACCOUNTS_FILE.read_text())
        except:
            pass
    return {"evox": [], "agentrouter": []}

def save_accounts(accounts: Dict):
    ACCOUNTS_FILE.write_text(json.dumps(accounts, indent=2))

def add_evox_account(email: str, password: str, credits: int = 1500):
    accounts = load_accounts()
    accounts["evox"].append({
        "email": email,
        "password": password,
        "credits": credits,
        "videos_generated": 0,
        "active": True,
    })
    save_accounts(accounts)
    log(f"✅ Added Evox account: {email} ({credits} credits)")

def add_agentrouter_account(api_key: str, credits: float = 175.0):
    accounts = load_accounts()
    accounts["agentrouter"].append({
        "api_key": api_key,
        "credits": credits,
        "videos_generated": 0,
        "active": True,
    })
    save_accounts(accounts)
    log(f"✅ Added AgentRouter account (${credits} credit)")

def get_available_account(platform: str) -> Optional[Dict]:
    accounts = load_accounts()
    for acc in accounts.get(platform, []):
        if acc.get("active", False):
            if platform == "evox" and acc.get("credits", 0) >= 19:
                return acc
            if platform == "agentrouter" and acc.get("credits", 0) >= 1:
                return acc
    return None

# ─── Book Data ───────────────────────────────────────────────────────
def get_books(limit: int = None) -> List[Dict]:
    conn = sqlite3.connect(str(DB))
    rows = conn.execute("SELECT manifest_id, data FROM manifests WHERE state='published'").fetchall()
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
            "title": str(title)[:100],
            "description": data.get("description", "")[:500],
            "author": "Darryl Elliott Brown",
            "tags": data.get("tags", []),
            "genre": data.get("genre", "Gullah Geechee Heritage"),
        })
    if limit:
        books = books[:limit]
    return books

# ─── Prompt Generation ───────────────────────────────────────────────
def generate_prompt(book: Dict, video_type: str) -> str:
    vt = VIDEO_TYPES.get(video_type, VIDEO_TYPES["social_short"])
    
    prompts = {
        "book_trailer": (
            f"Create a {vt['length']} cinematic book trailer for '{book['title']}' "
            f"by {book['author']}. Genre: {book['genre']}. "
            f"Description: {book['description'][:200]}. "
            f"Style: dramatic, atmospheric, with slow motion and text overlays. "
            f"End with the book title and 'Available now from Gullah Geechee Biz.'"
        ),
        "social_short": (
            f"Create a {vt['length']} vertical short promoting '{book['title']}' "
            f"by {book['author']}. "
            f"Description: {book['description'][:150]}. "
            f"Style: fast-paced, engaging, with captions. "
            f"Optimized for TikTok and Instagram Reels."
        ),
        "faceless_youtube": (
            f"Create a {vt['length']} faceless explainer video about '{book['title']}' "
            f"by {book['author']}. "
            f"Description: {book['description'][:300]}. "
            f"Style: educational, with stock footage, text overlays, and AI voiceover. "
            f"Suitable for YouTube."
        ),
        "binyah_promo": (
            f"Create a {vt['length']} promotional video featuring Binyah the Gullah Geechee "
            f"water spirit avatar promoting '{book['title']}' by {book['author']}. "
            f"Description: {book['description'][:200]}. "
            f"Style: warm, inviting, culturally authentic Gullah Geechee voice."
        ),
    }
    return prompts.get(video_type, prompts["social_short"])

# ─── Video Generation (Simulated) ───────────────────────────────────
def generate_video_evox(book: Dict, video_type: str, account: Dict) -> bool:
    """Submit video generation to Evox (simulated until real API access)."""
    prompt = generate_prompt(book, video_type)
    credit_cost = 19 if video_type == "social_short" else 64
    
    log(f"  🎬 Evox: Generating {video_type} for '{book['title'][:40]}...' ({credit_cost} credits)")
    
    # Simulate generation time
    time.sleep(2)
    
    # Deduct credits
    account["credits"] -= credit_cost
    account["videos_generated"] += 1
    save_accounts(load_accounts())
    
    # Save placeholder video info
    video_info = {
        "book_id": book["id"],
        "title": book["title"],
        "video_type": video_type,
        "platform": "evox",
        "model": VIDEO_TYPES[video_type]["model"],
        "prompt": prompt,
        "generated_at": datetime.now().isoformat(),
        "status": "generated",
        "credit_cost": credit_cost,
    }
    video_file = VIDEO_DIR / f"{book['id']}_{video_type}.json"
    video_file.write_text(json.dumps(video_info, indent=2))
    
    log(f"  ✅ {video_type} for '{book['title'][:40]}...' complete")
    return True

def generate_video_agentrouter(book: Dict, video_type: str, account: Dict) -> bool:
    """Submit video generation to AgentRouter (simulated until real API access)."""
    prompt = generate_prompt(book, video_type)
    credit_cost = 2.0  # $2 per cinematic video
    
    log(f"  🎬 AgentRouter: Generating {video_type} for '{book['title'][:40]}...' (${credit_cost})")
    
    time.sleep(3)
    
    account["credits"] -= credit_cost
    account["videos_generated"] += 1
    save_accounts(load_accounts())
    
    video_info = {
        "book_id": book["id"],
        "title": book["title"],
        "video_type": video_type,
        "platform": "agentrouter",
        "model": VIDEO_TYPES[video_type]["model"],
        "prompt": prompt,
        "generated_at": datetime.now().isoformat(),
        "status": "generated",
        "credit_cost": credit_cost,
    }
    video_file = VIDEO_DIR / f"{book['id']}_{video_type}.json"
    video_file.write_text(json.dumps(video_info, indent=2))
    
    log(f"  ✅ {video_type} for '{book['title'][:40]}...' complete")
    return True

# ─── Progress Tracking ───────────────────────────────────────────────
def load_progress() -> Dict:
    if PROGRESS_FILE.exists():
        try:
            return json.loads(PROGRESS_FILE.read_text())
        except:
            pass
    return {"total_books": 0, "videos_generated": 0, "videos_by_type": {}, "last_book_id": None}

def save_progress(p: Dict):
    PROGRESS_FILE.write_text(json.dumps(p, indent=2))

# ─── Main Factory ────────────────────────────────────────────────────
def main():
    print(f"\n{'='*55}")
    print(f"  🎬 GGB VIDEO FACTORY")
    print(f"  Free AI Video Generation for Every Book")
    print(f"{'='*55}\n")
    
    progress = load_progress()
    books = get_books()
    progress["total_books"] = len(books)
    
    log(f"Loaded {len(books)} books")
    log(f"Video types: {', '.join(VIDEO_TYPES.keys())}")
    
    # Check accounts
    accounts = load_accounts()
    evox_count = len(accounts.get("evox", []))
    ar_count = len(accounts.get("agentrouter", []))
    log(f"Evox accounts: {evox_count}")
    log(f"AgentRouter accounts: {ar_count}")
    
    if evox_count == 0 and ar_count == 0:
        log("\n⚠️  No accounts configured. Add accounts with:")
        log("  add_evox_account('email', 'password', 1500)")
        log("  add_agentrouter_account('api_key', 175.0)")
        print()
        return
    
    # Resume from last book
    start_idx = 0
    if progress.get("last_book_id"):
        for i, b in enumerate(books):
            if b["id"] == progress["last_book_id"]:
                start_idx = i + 1
                break
    
    log(f"Resuming from book index {start_idx}/{len(books)}")
    
    # Generate videos for each book
    for i, book in enumerate(books[start_idx:], start=start_idx):
        log(f"\n📖 [{i+1}/{len(books)}] {book['title'][:60]}")
        
        for vtype in ["social_short", "book_trailer", "faceless_youtube", "binyah_promo"]:
            vt = VIDEO_TYPES[vtype]
            platform = vt["platform"]
            
            account = get_available_account(platform)
            if not account:
                log(f"  ⏭️  No {platform} account available for {vtype}")
                continue
            
            if platform == "evox":
                success = generate_video_evox(book, vtype, account)
            else:
                success = generate_video_agentrouter(book, vtype, account)
            
            if success:
                progress["videos_generated"] += 1
                progress["videos_by_type"][vtype] = progress["videos_by_type"].get(vtype, 0) + 1
            
            time.sleep(1)
        
        progress["last_book_id"] = book["id"]
        save_progress(progress)
        
        # Report every 10 books
        if (i + 1) % 10 == 0:
            log(f"\n📊 Progress: {progress['videos_generated']} videos for {i+1} books")
            log(f"  By type: {json.dumps(progress['videos_by_type'])}")
    
    # Final report
    print(f"\n{'='*55}")
    print(f"  📊 VIDEO FACTORY COMPLETE")
    print(f"  Books processed: {len(books)}")
    print(f"  Videos generated: {progress['videos_generated']}")
    print(f"  By type: {json.dumps(progress['videos_by_type'])}")
    print(f"  Videos saved to: {VIDEO_DIR}")
    print(f"{'='*55}")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log("\n⚠️ Interrupted by user")
        sys.exit(1)
    except Exception as e:
        log(f"💥 Fatal: {e}")
        sys.exit(1)
