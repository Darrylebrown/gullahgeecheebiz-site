#!/usr/bin/env python3
"""
GGB Gumroad Publisher v3 — Full customization: profile, covers, EPUBs, descriptions.
"""
import json, os, sys, time, sqlite3, hashlib, requests, mimetypes
from pathlib import Path
from datetime import datetime

BASE = Path("/Users/darrylsmac/gullahgeecheebiz-site")
DB = BASE / "publish" / "publisher.db"
ENV = BASE / ".env"
EPUB_DIR = BASE / "publish" / "for-distribution" / "google-play"
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

API = "https://api.gumroad.com/v2"

def log(msg):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"  [{ts}] {msg}")
    with open(LOG_DIR / "publisher.log", "a") as f:
        f.write(f"[{ts}] {msg}\n")

def api_call(method, endpoint, data=None, files=None):
    """Make an API call with retry logic."""
    url = f"{API}/{endpoint}"
    params = {"access_token": TOKEN}
    
    for attempt in range(3):
        try:
            if method == "GET":
                r = requests.get(url, params=params, timeout=30)
            elif method == "PUT":
                r = requests.put(url, params=params, data=data, timeout=30)
            elif method == "POST":
                r = requests.post(url, params=params, data=data, files=files, timeout=60)
            
            if r.status_code == 200:
                return r.json()
            if r.status_code == 429:
                wait = (attempt + 1) * 5
                time.sleep(wait)
                continue
            return {"success": False, "error": r.text[:200]}
        except Exception as e:
            if attempt < 2:
                time.sleep(3)
                continue
            return {"success": False, "error": str(e)}
    return {"success": False, "error": "Max retries"}

def customize_profile():
    """Set up the Gumroad profile."""
    log("Customizing profile...")
    
    profile_data = {
        "name": "Gullah Geechee Biz",
        "bio": "Preserving and sharing Gullah Geechee heritage through books, culture, and community. 1,800+ volumes exploring history, language, food, music, art, and spirituality.",
        "url": "https://gullahgeecheebiz.com",
        "twitter_handle": "@GullahBiz",
    }
    
    result = api_call("PUT", "user", profile_data)
    if result.get("success"):
        log("✅ Profile customized!")
    else:
        log(f"⚠️ Profile update: {result.get('error', 'unknown')}")

def get_epub_path(book_id):
    """Find the EPUB file for a book."""
    for f in EPUB_DIR.glob("*.epub"):
        if book_id in f.name or book_id.replace("ggb-manifest-", "") in f.name:
            return f
    return None

def get_cover_path(book_id):
    """Find the cover image for a book."""
    landing_pad = BASE / "publish" / "landing-pad"
    for d in landing_pad.iterdir():
        if d.is_dir():
            cover = d / "cover.jpg"
            if cover.exists():
                return cover
    return None

def upload_file(product_id, file_path, file_type="epub"):
    """Upload a file to an existing product."""
    if not file_path or not file_path.exists():
        return False
    
    with open(file_path, "rb") as f:
        files = {"file": (file_path.name, f, "application/epub+zip" if file_type == "epub" else "image/jpeg")}
        result = api_call("POST", f"products/{product_id}/files", files=files)
    
    return result.get("success", False)

def update_product(product_id, data):
    """Update an existing product."""
    result = api_call("PUT", f"products/{product_id}", data)
    return result.get("success", False)

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
            "author": data.get("author", "Darryl Elliott Brown"),
            "tags": data.get("metadata", {}).get("keywords", []),
        })
    return books

def get_existing_products():
    """Get all existing products on Gumroad."""
    result = api_call("GET", "products")
    if result.get("success"):
        return {p.get("name", "").strip().lower(): p for p in result.get("products", [])}
    return {}

def main():
    print(f"\n{'='*55}")
    print(f"  📦 GGB GUMROAD PUBLISHER v3")
    print(f"  Full customization + file uploads")
    print(f"{'='*55}\n")
    
    # Step 1: Customize profile
    customize_profile()
    
    # Step 2: Get books and existing products
    books = get_books()
    existing = get_existing_products()
    
    log(f"Loaded {len(books)} books")
    log(f"Existing products on Gumroad: {len(existing)}")
    
    # Step 3: Update existing products with files and better descriptions
    updated = 0
    for name, product in existing.items():
        pid = product.get("id")
        if not pid:
            continue
        
        # Find matching book
        book = None
        for b in books:
            if b["title"].strip().lower() == name:
                book = b
                break
        
        if not book:
            continue
        
        log(f"📝 Updating: {book['title'][:50]}...")
        
        # Update description
        desc = book.get("description", "")
        if desc:
            update_product(pid, {"description": desc})
        
        # Upload EPUB
        epub = get_epub_path(book["id"])
        if epub:
            if upload_file(pid, epub, "epub"):
                log(f"  ✅ EPUB attached")
            else:
                log(f"  ⚠️ Could not attach EPUB")
        
        # Upload cover
        cover = get_cover_path(book["id"])
        if cover:
            if upload_file(pid, cover, "image"):
                log(f"  ✅ Cover attached")
        
        updated += 1
        time.sleep(1)
    
    log(f"\n📊 Updated {updated} products with files and descriptions")
    
    # Step 4: Upload new books (up to 10 per day)
    daily_limit = 10
    uploaded_today = 0
    
    for book in books:
        if uploaded_today >= daily_limit:
            break
        
        name_lower = book["title"].strip().lower()
        if name_lower in existing:
            continue
        
        log(f"📤 Creating: {book['title'][:50]}...")
        
        price_cents = int(float(book.get("price", 3.99)) * 100)
        data = {
            "name": book["title"][:100],
            "description": book.get("description", "")[:500],
            "price": price_cents,
            "customizable_price": True,
        }
        
        result = api_call("POST", "products", data)
        
        if result.get("success"):
            pid = result.get("product", {}).get("id")
            log(f"  ✅ Created (ID: {pid})")
            
            # Attach EPUB
            epub = get_epub_path(book["id"])
            if epub:
                if upload_file(pid, epub, "epub"):
                    log(f"  ✅ EPUB attached")
            
            # Attach cover
            cover = get_cover_path(book["id"])
            if cover:
                if upload_file(pid, cover, "image"):
                    log(f"  ✅ Cover attached")
            
            uploaded_today += 1
        else:
            err = result.get("error", "")
            if "10 products per day" in err:
                log(f"  ⏸️ Daily limit reached")
                break
            log(f"  ❌ {err[:100]}")
        
        time.sleep(2)
    
    print(f"\n{'='*55}")
    print(f"  📊 COMPLETE")
    print(f"  Updated: {updated}")
    print(f"  New today: {uploaded_today}")
    print(f"  Total on Gumroad: {len(existing) + uploaded_today}")
    print(f"  Remaining: {len(books) - len(existing) - uploaded_today}")
    print(f"{'='*55}")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log("\n⚠️ Interrupted")
        sys.exit(1)
