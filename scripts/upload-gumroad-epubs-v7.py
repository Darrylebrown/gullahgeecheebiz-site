#!/usr/bin/env python3
"""
Upload EPUB files to published Gumroad products using presign flow.
Fixed: proper multipart upload handling.
"""
import json, os, requests, time, sqlite3, re, hashlib
from pathlib import Path

BASE = Path("/Users/darrylsmac/gullahgeecheebiz-site")
ENV = BASE / ".env"
EPUB_DIR = BASE / "publish" / "for-distribution" / "google-play"
DB = BASE / "publish" / "publisher.db"
LOG_DIR = BASE / "ggb-engine" / "headquarters" / "logs" / "gumroad-publisher"
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / "upload_epub_presign.log"

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
            return {"success": False, "error": r.text[:500]}
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

def find_epub_by_volume(volume_num, epub_files):
    """Find EPUB for a specific volume number."""
    for epub_path in epub_files:
        name = epub_path.name.replace('.epub', '')
        match = re.search(r'vol[-_]?(\d+)', name, re.IGNORECASE)
        if match and int(match.group(1)) == volume_num:
            return epub_path
    return None

def upload_file_presign(epub_path):
    """Upload file using presign flow with proper multipart handling."""
    filename = epub_path.name
    filesize = epub_path.stat().st_size
    
    log(f"  Requesting presign URL for {filename} ({filesize} bytes)")
    
    # Step 1: Get presign URL
    result = api_call("POST", "files/presign", data={
        "filename": filename,
        "file_size": filesize
    })
    
    if not result.get("success"):
        return None, f"Presign failed: {result.get('error')}"
    
    upload_id = result.get("upload_id")
    key = result.get("key")
    parts = result.get("parts", [])
    
    if not upload_id or not key:
        return None, f"No upload_id or key in response"
    
    log(f"  Got presign URL, {len(parts)} part(s)")
    
    # Step 2: Upload to S3 using presigned URLs
    with open(epub_path, 'rb') as f:
        file_data = f.read()
    
    part_etags = []
    for i, part in enumerate(parts):
        s3_url = part.get("presigned_url")
        part_number = part.get("part_number", i + 1)
        
        if not s3_url:
            return None, f"No presigned URL for part {part_number}"
        
        log(f"  Uploading part {part_number} to S3...")
        
        # Upload this part
        r = requests.put(s3_url, data=file_data, timeout=120)
        if r.status_code not in [200, 204]:
            return None, f"S3 part {part_number} upload failed: {r.status_code} - {r.text[:200]}"
        
        etag = r.headers.get('ETag', '').strip('"')
        part_etags.append({"part_number": part_number, "etag": etag})
        log(f"  Part {part_number} uploaded, ETag: {etag}")
    
    # Step 3: Complete multipart upload
    complete_data = {
        "upload_id": upload_id,
        "key": key,
        "parts": json.dumps(part_etags)
    }
    
    log(f"  Completing upload...")
    complete_result = api_call("POST", "files/complete", data=complete_data)
    
    if not complete_result.get("success"):
        return None, f"Complete failed: {complete_result.get('error')}"
    
    final_url = complete_result.get("file_url")
    log(f"  File uploaded successfully: {final_url}")
    return final_url, None

def main():
    global TOKEN
    TOKEN = load_token()
    if not TOKEN:
        log("ERROR: GUMROAD_ACCESS_TOKEN not found")
        return
    
    log("=" * 60)
    log("Gumroad EPUB Upload V7 (Multipart Fixed)")
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
        vol_match = re.search(r'Volume\s+(\d+)', name)
        if not vol_match:
            log(f"SKIP {name}: No volume number found")
            skipped += 1
            continue
        
        vol_num = int(vol_match.group(1))
        log(f"Processing: {name} (Volume {vol_num})")
        
        # Find matching EPUB
        epub_path = find_epub_by_volume(vol_num, epub_files)
        if not epub_path:
            log(f"  SKIP: No EPUB found for Volume {vol_num}")
            skipped += 1
            continue
        
        log(f"  Found EPUB: {epub_path.name}")
        
        # Upload using presign flow
        file_url, error = upload_file_presign(epub_path)
        
        if error:
            log(f"  FAILED: {error}")
            failed += 1
            continue
        
        # Attach file to product using PUT /products/{id}
        log(f"  Attaching file to product...")
        attach_result = api_call("PUT", f"products/{pid}", data={
            "name": name,
            "file_url": file_url
        })
        
        if attach_result.get("success"):
            log(f"  SUCCESS")
            uploaded += 1
            matches.append((name, epub_path.name, file_url))
        else:
            log(f"  ATTACH FAILED: {attach_result.get('error')}")
            failed += 1
        
        time.sleep(1)  # Rate limit respect
    
    log(f"\n{'=' * 60}")
    log(f"UPLOAD COMPLETE")
    log(f"  Uploaded: {uploaded}")
    log(f"  Skipped: {skipped}")
    log(f"  Failed: {failed}")
    log(f"{'=' * 60}")
    
    # Save matches
    with open(LOG_DIR / "matches_presign.json", "w") as f:
        json.dump(matches, f, indent=2)
    log(f"Saved {len(matches)} matches to matches_presign.json")
    
    # Verify
    log("\nVerifying products...")
    products = get_products()
    ready_count = 0
    for pid, product in products.items():
        name = product.get("name", "").strip()
        file_count = len(product.get("files", []))
        sales_count = product.get("sales_count", 0)
        status = "READY" if file_count > 0 else "NO FILE"
        if file_count > 0:
            ready_count += 1
        log(f"  [{status}] {name} ({file_count} files, {sales_count} sales)")
    
    log(f"\nProducts ready for sale: {ready_count}/{len(products)}")
    
    # Return summary
    print(f"\n{'=' * 60}")
    print(f"SUMMARY: {uploaded} uploaded, {skipped} skipped, {failed} failed")
    print(f"Products ready for sale: {ready_count}/{len(products)}")
    print(f"{'=' * 60}")

if __name__ == "__main__":
    main()
