#!/usr/bin/env python3
"""
Upload EPUB files to published Gumroad products.
V3: Fixed matching for Encyclopedia volumes.
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

def extract_volume_number(product_name):
    """Extract volume number from product name."""
    # Match patterns like "Encyclopedia Volume 06", "Volume 06", etc.
    match = re.search(r'volume\s+(\d+)', product_name, re.IGNORECASE)
    if match:
        return int(match.group(1))
    return None

def find_epub_by_volume(volume_num, epub_files):
    """Find EPUB for a specific volume number."""
    # Try pedia-vol-XX format
    for epub_path in epub_files:
        name = epub_path.name.replace('.epub', '')
        # Match pedia-vol-06, pedia-vol-6, etc.
        match = re.search(r'vol[-_]?(\d+)', name, re.IGNORECASE)
        if match and int(match.group(1)) == volume_num:
            return epub_path
    return None

def main():
    global TOKEN
    TOKEN = load_token()
    if not TOKEN:
        log("ERROR: GUMROAD_ACCESS_TOKEN not found")
        return
    
    log("=" * 60)
    log("Gumroad EPUB Upload V3")
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
    
    # Match and upload
    uploaded = 0
    skipped = 0
    failed = 0
    matches = []
    
    for pid, product in products.items():
        name = product.get("name", "").strip()
        
        # Skip products that already have files
        if len(product.get("files", [])) > 0:
            log(f"SKIP {name}: Already has {len(product['files'])} file(s)")
            skipped += 1
            continue
        
        # Extract volume number
        vol_num = extract_volume_number(name)
        if vol_num is None:
            log(f"SKIP {name}: No volume number found")
            skipped += 1
            continue
        
        # Find matching EPUB
        epub_path = find_epub_by_volume(vol_num, epub_files)
        if not epub_path:
            log(f"SKIP {name}: No EPUB found for Volume {vol_num}")
            skipped += 1
            continue
        
        log(f"UPLOAD {name} (Vol {vol_num})")
        log(f"  -> {epub_path.name}")
        matches.append((name, epub_path.name))
        
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
    
    # Save matches for reference
    with open(LOG_DIR / "matches.json", "w") as f:
        json.dump(matches, f, indent=2)
    log(f"Saved {len(matches)} matches to matches.json")
    
    # Verify
    log("\nVerifying products...")
    products = get_products()
    for pid, product in products.items():
        name = product.get("name", "").strip()
        file_count = len(product.get("files", []))
        sales_count = product.get("sales_count", 0)
        status = "READY" if file_count > 0 else "NO FILE"
        log(f"  [{status}] {name} ({file_count} files, {sales_count} sales)")

if __name__ == "__main__":
    main()
