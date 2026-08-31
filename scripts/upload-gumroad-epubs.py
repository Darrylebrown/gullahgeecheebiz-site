#!/usr/bin/env python3
"""
Upload EPUB files to published Gumroad products.
"""
import json, os, requests, time, sqlite3
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

def find_epub(manifest_id, manifest_map):
    """Find EPUB file matching a manifest ID."""
    title = manifest_map.get(manifest_id, "")
    # Look for EPUB by manifest ID
    for epub_path in EPUB_DIR.glob("*.epub"):
        if manifest_id in epub_path.name:
            return epub_path
    # Fallback: look for EPUB matching title keywords
    keywords = [w for w in title.split() if len(w) > 3]
    for epub_path in EPUB_DIR.glob("*.epub"):
        for kw in keywords:
            if kw.lower() in epub_path.name.lower():
                return epub_path
    return None

def main():
    global TOKEN
    TOKEN = load_token()
    if not TOKEN:
        log("ERROR: GUMROAD_ACCESS_TOKEN not found")
        return
    
    log("=" * 50)
    log("Gumroad EPUB Upload")
    log("=" * 50)
    
    # Get products
    products = get_products()
    log(f"Found {len(products)} products on Gumroad")
    
    # Get manifest map
    manifest_map = get_manifest_map()
    log(f"Found {len(manifest_map)} published manifests")
    
    # Match products to manifests and upload EPUBs
    uploaded = 0
    skipped = 0
    
    for pid, product in products.items():
        name = product.get("name", "").strip()
        
        # Find matching manifest
        manifest_id = None
        for mid, title in manifest_map.items():
            if name in title or title in name:
                manifest_id = mid
                break
        
        if not manifest_id:
            log(f"SKIP {name}: No matching manifest")
            skipped += 1
            continue
        
        # Find EPUB
        epub_path = find_epub(manifest_id, manifest_map)
        if not epub_path:
            log(f"SKIP {name}: No EPUB file found (manifest={manifest_id})")
            skipped += 1
            continue
        
        log(f"Uploading {name}: {epub_path.name}")
        
        # Upload file
        with open(epub_path, "rb") as f:
            files = {"file": (epub_path.name, f, "application/epub+zip")}
            result = api_call("POST", f"products/{pid}/files", files=files)
        
        if result.get("success"):
            log(f"  SUCCESS: {name}")
            uploaded += 1
        else:
            log(f"  FAILED: {name} - {result.get('error', 'unknown')}")
        
        time.sleep(1)  # Rate limit respect
    
    log(f"\nDone! Uploaded: {uploaded}, Skipped: {skipped}")
    
    # Verify
    log("\nVerifying...")
    products = get_products()
    for pid, product in products.items():
        name = product.get("name", "").strip()
        file_count = len(product.get("files", []))
        sales_count = product.get("sales_count", 0)
        status = "READY" if file_count > 0 else "NO FILE"
        log(f"  {status}: {name} ({file_count} files, {sales_count} sales)")

if __name__ == "__main__":
    main()
