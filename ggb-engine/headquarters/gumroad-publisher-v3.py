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
    # HEALTH_GOAL 2026-09-02: never attach empty-shell EPUBs (<10KB = stub with
    # no real chapters). Real books are 30KB+ (verified: 86KB / 7,282 words).
    if file_type == "epub" and file_path.stat().st_size < 10000:
        log(f"  ⛔ SKIP shell EPUB ({file_path.stat().st_size}B <10KB): {file_path.name} — real content required")
        return False
    if file_type != "epub":
        return False  # covers use the dedicated /covers endpoint, not product files
    # Use the documented 4-step upload flow (presign → S3 PUT → complete → attach
    # via files[][url] on PUT /products/:id). POST /products/{id}/files is retired (404).
    fsize = file_path.stat().st_size
    pr = api_call("POST", "files/presign", data={"filename": file_path.name, "file_size": fsize})
    if not pr or not pr.get("success"):
        log(f"  ⚠️ presign failed: {pr.get('error') if pr else 'no response'}")
        return False
    etags = []
    for part in pr.get("parts", []):
        with open(file_path, "rb") as f:
            r = requests.put(part["presigned_url"], data=f.read(), timeout=120)
        etag = (r.headers.get("ETag") or "").strip('"')
        etags.append(etag)
    if not etags:
        return False
    cr = api_call("POST", "files/complete", data={
        "upload_id": pr.get("upload_id"), "key": pr.get("key"),
        "parts[][part_number]": 1, "parts[][etag]": etags[0]})
    file_url = (cr or {}).get("file_url")
    if not file_url:
        log("  ⚠️ complete returned no file_url")
        return False
    # full replacement of product files with this one (files[][url])
    ar = api_call("PUT", f"products/{product_id}", data={"files[][url]": file_url})
    ok = bool(ar and ar.get("success"))
    if ok:
        log(f"  ✅ Attached {file_path.name} ({fsize}B) via presign flow")
    return ok

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
    """Get ALL existing products on Gumroad (paginated — was page-1-only, which
    caused duplicate re-creation of drafts on later pages)."""
    import urllib.parse as up
    products, page_key = {}, None
    for _ in range(30):  # hard safety cap on pages
        url = f"{API}/products?access_token={TOKEN}"
        if page_key:
            url += f"&page_key={up.quote(page_key)}"
        try:
            r = requests.get(url, timeout=30)
            if r.status_code == 429:
                time.sleep(10)
                continue
            j = r.json()
        except Exception:
            return {}
        if not j.get("success"):
            break
        for p in j.get("products", []):
            products[p.get("name", "").strip().lower()] = p
        page_key = j.get("next_page_key")
        if not page_key:
            break
    return products

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
    consecutive_failures = 0
    
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
            consecutive_failures = 0
        else:
            err = result.get("message") or result.get("error", "")
            if "10 products per day" in str(err):
                log(f"  ⏸️ Daily limit reached ({uploaded_today} created today)")
                break
            log(f"  ❌ {str(err)[:100]}")
            consecutive_failures += 1
            if consecutive_failures >= 5:
                log("  ⛔ 5 consecutive creation failures — API appears down; stopping")
                break
        
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
