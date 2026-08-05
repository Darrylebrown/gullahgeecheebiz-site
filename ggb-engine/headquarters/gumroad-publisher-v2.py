#!/usr/bin/env python3
"""
GGB Gumroad Publisher v2 — Uploads all 1,817 books with rate limit handling.
"""
import json, os, sys, time, sqlite3, hashlib, requests
from pathlib import Path
from datetime import datetime

BASE = Path("/Users/darrylsmac/gullahgeecheebiz-site")
DB = BASE / "publish" / "publisher.db"
ENV = BASE / ".env"
LOG_DIR = BASE / "ggb-engine" / "headquarters" / "logs" / "gumroad-publisher"
LOG_DIR.mkdir(parents=True, exist_ok=True)
PROGRESS_FILE = LOG_DIR / "progress.json"

def load_env():
    env = {}
    if ENV.exists():
        for line in ENV.read_text().splitlines():
            if "=" in line and not line.strip().startswith("#"):
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip().strip('"').strip("'")
    return env

env = load_env()
TOKEN = env.get("GUMROAD_ACCESS_TOKEN", "")

if not TOKEN:
    print("❌ GUMROAD_ACCESS_TOKEN not found in .env")
    sys.exit(1)

def log(msg):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"  [{ts}] {msg}")
    with open(LOG_DIR / "publisher.log", "a") as f:
        f.write(f"[{ts}] {msg}\n")

def get_books():
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
            "price": data.get("publishing", {}).get("price", 3.99),
        })
    return books

def load_progress():
    if PROGRESS_FILE.exists():
        try:
            return json.loads(PROGRESS_FILE.read_text())
        except:
            pass
    return {"submitted": [], "failed": [], "last_index": 0}

def save_progress(p):
    PROGRESS_FILE.write_text(json.dumps(p, indent=2))

def upload_book(book):
    """Upload a single book to Gumroad with retry logic."""
    price_cents = int(float(book.get("price", 3.99)) * 100)
    
    data = {
        "name": book["title"][:100],
        "description": book.get("description", "")[:500],
        "price": price_cents,
        "customizable_price": True,
        "max_purchase_count": None,
        "require_shipping": False,
    }
    
    for attempt in range(3):
        try:
            r = requests.post(
                "https://api.gumroad.com/v2/products",
                params={"access_token": TOKEN},
                data=data,
                timeout=30
            )
            
            if r.status_code == 200:
                result = r.json()
                if result.get("success"):
                    return True, result.get("product", {}).get("id", "?")
            
            if r.status_code == 429:
                wait = (attempt + 1) * 5
                log(f"Rate limited, waiting {wait}s...")
                time.sleep(wait)
                continue
            
            if r.status_code >= 500:
                time.sleep(3)
                continue
            
            return False, r.text[:100]
            
        except Exception as e:
            if attempt < 2:
                time.sleep(3)
                continue
            return False, str(e)
    
    return False, "Max retries"

def main():
    print(f"\n{'='*55}")
    print(f"  📦 GGB GUMROAD PUBLISHER v2")
    print(f"  Target: 1,817 books")
    print(f"{'='*55}\n")
    
    books = get_books()
    progress = load_progress()
    submitted_ids = set(progress.get("submitted", []))
    failed_ids = set(progress.get("failed", []))
    
    log(f"Loaded {len(books)} books")
    log(f"Already submitted: {len(submitted_ids)}")
    log(f"Previously failed: {len(failed_ids)}")
    
    # Get existing products to avoid duplicates
    existing = set()
    try:
        r = requests.get("https://api.gumroad.com/v2/products", params={"access_token": TOKEN}, timeout=30)
        if r.status_code == 200:
            for p in r.json().get("products", []):
                existing.add(p.get("name", "").strip().lower())
        log(f"Existing products on Gumroad: {len(existing)}")
    except:
        log("Could not fetch existing products")
    
    submitted = 0
    failed = 0
    skipped = 0
    
    for i, book in enumerate(books):
        title_lower = book["title"].strip().lower()
        
        if book["id"] in submitted_ids:
            skipped += 1
            continue
        
        if title_lower in existing:
            log(f"⏭️  [{i+1}/{len(books)}] {book['title'][:50]}... already exists")
            submitted_ids.add(book["id"])
            submitted += 1
            continue
        
        log(f"📤 [{i+1}/{len(books)}] {book['title'][:50]}...")
        
        success, result = upload_book(book)
        
        if success:
            submitted_ids.add(book["id"])
            submitted += 1
            log(f"  ✅ ID: {result}")
        else:
            failed_ids.add(book["id"])
            failed += 1
            log(f"  ❌ {result}")
        
        # Save progress every 5 books
        if (i + 1) % 5 == 0:
            progress = {
                "submitted": list(submitted_ids),
                "failed": list(failed_ids),
                "last_index": i,
                "total": len(books),
            }
            save_progress(progress)
            log(f"📊 Progress: {submitted} submitted, {failed} failed, {skipped} skipped")
        
        # Rate limit: wait 2 seconds between uploads
        time.sleep(2)
    
    # Final report
    print(f"\n{'='*55}")
    print(f"  📊 PUBLISHING COMPLETE")
    print(f"  Submitted: {submitted}")
    print(f"  Failed: {failed}")
    print(f"  Skipped (already existed): {skipped}")
    print(f"  Total on Gumroad: {len(submitted_ids)}")
    print(f"{'='*55}")
    
    progress = {
        "submitted": list(submitted_ids),
        "failed": list(failed_ids),
        "last_index": len(books),
        "total": len(books),
    }
    save_progress(progress)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log("\n⚠️ Interrupted by user")
        sys.exit(1)
