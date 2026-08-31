#!/usr/bin/env python3
"""
Upload EPUB files to published Gumroad products using presign flow.
Debug version to understand why attachments aren't persisting.
"""
import json, os, requests, time, sqlite3, re, hashlib
from pathlib import Path

BASE = Path("/Users/darrylsmac/gullahgeecheebiz-site")
ENV = BASE / ".env"
EPUB_DIR = BASE / "publish" / "for-distribution" / "google-play"
LOG_DIR = BASE / "ggb-engine" / "headquarters" / "logs" / "gumroad-publisher"
LOG_FILE = LOG_DIR / "upload_debug.log"

API = "https://api.gumroad.com/v2"

def log(msg):
    ts = time.strftime("%H:%M:%S")
    print(f"[{ts}] {msg}")
    with open(LOG_FILE, "a") as f:
        f.write(f"[{ts}] {msg}\n")

def load_token():
    for line in ENV.read_text().splitlines():
        if "GUMROAD_ACCESS_TOKEN" in line:
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    return None

TOKEN = load_token()
params = {"access_token": TOKEN}

def upload_file_presign(epub_path):
    """Upload file using presign flow."""
    filename = epub_path.name
    filesize = epub_path.stat().st_size
    
    log(f"Uploading {filename} ({filesize} bytes)")
    
    # Step 1: Get presign URL
    r = requests.post(f"{API}/files/presign", params=params, data={
        "filename": filename,
        "file_size": filesize
    }, timeout=30)
    result = r.json()
    
    if not result.get("success"):
        return None, f"Presign failed: {result.get('error')}"
    
    upload_id = result.get("upload_id")
    key = result.get("key")
    parts = result.get("parts", [])
    
    # Step 2: Upload to S3
    with open(epub_path, 'rb') as f:
        file_data = f.read()
    
    part_etags = []
    for i, part in enumerate(parts):
        s3_url = part.get("presigned_url")
        part_number = part.get("part_number", i + 1)
        
        r = requests.put(s3_url, data=file_data, timeout=120)
        if r.status_code not in [200, 204]:
            return None, f"S3 upload failed for part {part_number}"
        
        etag = r.headers.get('ETag', '').strip('"')
        part_etags.append({"part_number": part_number, "etag": etag})
    
    # Step 3: Complete
    r = requests.post(f"{API}/files/complete", params=params,
        json={"upload_id": upload_id, "key": key, "parts": part_etags},
        headers={"Content-Type": "application/json"}, timeout=30)
    result = r.json()
    
    if not result.get("success"):
        return None, f"Complete failed: {result.get('error')}"
    
    return result.get("file_url"), None

def main():
    log("=" * 60)
    log("DEBUG: Gumroad EPUB Upload")
    log("=" * 60)
    
    # Get products
    r = requests.get(f"{API}/products", params=params, timeout=30)
    data = r.json()
    products = {p["id"]: p for p in data.get("products", [])}
    log(f"Found {len(products)} products")
    
    # Get EPUBs
    epub_files = list(EPUB_DIR.glob("*.epub"))
    log(f"Found {len(epub_files)} EPUB files")
    
    # Test with first product
    for pid, product in list(products.items())[:3]:
        name = product.get("name", "").strip()
        log(f"\n--- Testing: {name} ---")
        
        # Check current files
        r = requests.get(f"{API}/products/{pid}", params=params, timeout=30)
        full_product = r.json().get("product", {})
        current_files = full_product.get("files", [])
        log(f"Current files: {len(current_files)}")
        
        # Extract volume number
        vol_match = re.search(r'Volume\s+(\d+)', name)
        if not vol_match:
            log(f"  No volume number, skipping")
            continue
        
        vol_num = int(vol_match.group(1))
        
        # Find EPUB
        epub_path = None
        for epub in epub_files:
            if f'vol-{vol_num:02d}' in epub.name.lower() or f'vol-{vol_num}' in epub.name.lower():
                epub_path = epub
                break
        
        if not epub_path:
            log(f"  No EPUB found for Volume {vol_num}")
            continue
        
        log(f"  Found EPUB: {epub_path.name}")
        
        # Upload file
        file_url, error = upload_file_presign(epub_path)
        if error:
            log(f"  Upload failed: {error}")
            continue
        
        log(f"  Uploaded to: {file_url}")
        
        # Try attaching using PUT with file_url
        log(f"  Attaching to product...")
        r = requests.put(f"{API}/products/{pid}", params=params, data={
            "name": name,
            "file_url": file_url
        }, timeout=30)
        
        log(f"  PUT response: {r.status_code}")
        if r.status_code == 200:
            result = r.json()
            if result.get("success"):
                log(f"  PUT succeeded")
            else:
                log(f"  PUT failed: {result}")
        else:
            log(f"  PUT failed: {r.text[:200]}")
        
        # Verify by getting product again
        time.sleep(1)
        r = requests.get(f"{API}/products/{pid}", params=params, timeout=30)
        updated_product = r.json().get("product", {})
        new_files = updated_product.get("files", [])
        log(f"  Files after attach: {len(new_files)}")
        for f in new_files:
            log(f"    - {f.get('name')} | url={'YES' if f.get('url') else 'NO'}")
    
    log("\n" + "=" * 60)
    log("DEBUG COMPLETE")
    log("=" * 60)

if __name__ == "__main__":
    main()
