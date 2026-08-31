#!/usr/bin/env python3
"""
Upload EPUB files to published Gumroad products.
V2: Better matching logic, handles all product types.
"""
import json, os, requests, time, sqlite3, re
from pathlib import Path

BASE = Path("/Users/darrylsmac/gullahgeecheebiz-site")
ENV = BASE / ".env"
EPUB_DIR = BASE / "publish" / "for-distribution" / "google-play"
DB = BASE / "publish" / "publisher.db"
LOG_DIR = BASE / "ggb-engine" / "headquarters" / "logs" / "gumroad-publisher"
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / "upload_epub.log"

API = "https://api.gumroad.com/v2"

def log(msg):
    ts = time.strftime("%H:%M:%S")
    print(f"[{ts}] {msg}")
    with open(LOG_FILE, "a") as f:
        f.write(f"[{ts}] {msg}\n")

def load_token():
    if ENV.exists():
        for line in ENV.read_text().splitlines():
            if "GUMROAD_ACCESS_TOKEN" in line:
                token = line.split("=", 1)[1].strip().strip('"').strip("'")
                return token
    return None

def api_call(method, endpoint, data=None, files=None):
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
                log(f"  Rate limited, waiting {wait}s...")
                time.sleep(wait)
                continue
            return {"success": False, "error": r.text[:200]}
        except Exception as e:
            if attempt < 2:
                time.sleep(3)
                continue
            return {"success": False, "error": str(e)}
    return {"success": False, "error": "Max retries"}

def get_products():
    result = api_call("GET", "products")
    if result.get("success"):
        return {p["id"]: p for p in result.get("products", [])}
    return {}

def get_manifest_map():
    """Get manifest_id -> title mapping."""
    conn = sqlite3.connect(str(DB))
    rows = conn.execute("SELECT manifest_id, data FROM manifests WHERE state='published'").fetchall()
    conn.close()
    mapping = {}
    for mid, data_json in rows:
        try:
            data = json.loads(data_json) if data_json else {}
            title = data.get("title", mid)
            if isinstance(title, dict):
                title = title.get("canonical", str(title))
            mapping[mid] = str(title).strip()
        except:
            pass
    return mapping

def normalize_title(title):
    """Normalize title for matching: lowercase, remove special chars, expand abbreviations."""
    t = title.lower()
    t = re.sub(r'[^\w\s-]', '', t)
    t = re.sub(r'\s+', ' ', t).strip()
    # Expand common abbreviations
    t = t.replace('vol', 'volume')
    t = t.replace('encyc', 'encyclopedia')
    return t

def find_epub_for_product(product_name, manifest_map, epub_files):
    """Find the best matching EPUB for a product."""
    norm_name = normalize_title(product_name)
    
    # Try exact match first
    for epub_path in epub_files:
        epub_name = epub_path.name.replace('.epub', '')
        norm_epub = normalize_title(epub_name)
        if norm_name == norm_epub:
            return epub_path
    
    # Try contains match
    for epub_path in epub_files:
        epub_name = epub_path.name.replace('.epub', '')
        norm_epub = normalize_title(epub_name)
        if norm_name in norm_epub or norm_epub in norm_name:
            return epub_path
    
    # Try keyword matching
    keywords = [w for w in norm_name.split() if len(w) > 3]
    for epub_path in epub_files:
        epub_name = epub_path.name.replace('.epub', '')
        for kw in keywords:
            if kw in epub_name.lower():
                return epub_path
    
    # Try manifest matching
    for mid, title in manifest_map.items():
        norm_title = normalize_title(title)
        if norm_name == norm_title or norm_name in norm_title or norm_title in norm_name:
            # Try to find EPUB by manifest ID
            for epub_path in epub_files:
                if mid in epub_path.name:
                    return epub_path
            # Try by normalized title
            for epub_path in epub_files:
                norm_epub = normalize_title(epub_path.name.replace('.epub', ''))
                if norm_epub == norm_title:
                    return epub_path
    
    return None

def main():
    global TOKEN
    TOKEN = load_token()
    if not TOKEN:
        log("ERROR: GUMROAD_ACCESS_TOKEN not found")
        return
    
    log("=" * 60)
    log("Gumroad EPUB Upload V2")
    log("=" * 60)
    
    # Get EPUB files
    if not EPUB_DIR.exists():
        log(f"ERROR: EPUB directory not found: {EPUB_DIR}")
        return
    
    epub_files = list(EPUB_DIR.glob("*.epub"))
    log(f"Found {len(epub_files)} EPUB files in {EPUB_DIR}")
    
    # Get products
    products = get_products()
    log(f"Found {len(products)} products on Gumroad")
    
    # Get manifest map
    manifest_map = get_manifest_map()
    log(f"Found {len(manifest_map)} published manifests")
    
    # Match and upload
    uploaded = 0
    skipped = 0
    failed = 0
    
    for pid, product in products.items():
        name = product.get("name", "").strip()
        
        # Skip products that already have files
        if len(product.get("files", [])) > 0:
            log(f"SKIP {name}: Already has {len(product['files'])} file(s)")
            skipped += 1
            continue
        
        # Find matching EPUB
        epub_path = find_epub_for_product(name, manifest_map, epub_files)
        if not epub_path:
            log(f"SKIP {name}: No matching EPUB found")
            skipped += 1
            continue
        
        log(f"Uploading: {name}")
        log(f"  -> {epub_path.name}")
        
        # Upload file
        with open(epub_path, "rb") as f:
            files = {"file": (epub_path.name, f, "application/epub+zip")}
            result = api_call("POST", f"products/{pid}/files", files=files)
        
        if result.get("success"):
            log(f"  SUCCESS")
            uploaded += 1
        else:
            log(f"  FAILED: {result.get('error', 'unknown')}")
            failed += 1
        
        time.sleep(1)  # Rate limit respect
    
    log(f"\n{'=' * 60}")
    log(f"UPLOAD COMPLETE")
    log(f"  Uploaded: {uploaded}")
    log(f"  Skipped: {skipped}")
    log(f"  Failed: {failed}")
    log(f"{'=' * 60}")
    
    # Verify
    log("\nVerifying products...")
    products = get_products()
    for pid, product in products.items():
        name = product.get("name", "").strip()
        file_count = len(product.get("files", []))
        sales_count = product.get("sales_count", 0)
        status = "READY" if file_count > 0 else "NO FILE"
        log(f"  [{status}] {name} ({file_count} files, {sales_count} sales)")
    
    # List remaining EPUBs without matches
    used_epubs = set()
    for pid, product in products.items():
        if len(product.get("files", [])) > 0:
            # Find which EPUB was used
            name = product.get("name", "").strip()
            for epub_path in epub_files:
                if normalize_title(name) in normalize_title(epub_path.name.replace('.epub', '')):
                    used_epubs.add(epub_path.name)
                    break
    
    unused = [f for f in epub_files if f.name not in used_epubs]
    log(f"\nUnused EPUBs: {len(unused)}")
    if unused:
        log("  First 20:")
        for f in unused[:20]:
            log(f"    {f.name}")

if __name__ == "__main__":
    main()
