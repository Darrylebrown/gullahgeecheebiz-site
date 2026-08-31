#!/usr/bin/env python3
"""
GUMROAD PUBLISHING TANK - Final Comprehensive Script
Verifies current state, waits for rate limit reset, uploads with retry.
"""
import json
import sqlite3
import sys
import time
from pathlib import Path
import requests

BASE = Path("/Users/darrylsmac/gullahgeecheebiz-site")
TOKEN = None
for line in open(BASE / ".env").read().splitlines():
    if line.startswith("GUMROAD_ACCESS_TOKEN="):
        TOKEN = line.split("=", 1)[1].strip().strip('"')
        break

API = "https://api.gumroad.com/v2"
DB_PATH = BASE / "publish" / "publisher.db"
EVENT_STREAM = BASE / "publish" / "event_stream.jsonl"
RESULTS_FILE = BASE / "publish" / "gumroad_final_results.json"

def log_event(action, detail):
    event = {"ts": time.strftime("%Y-%m-%dT%H:%M:%S"), "source_bot": "PUBLISHING_TANK_OWNER", "action": action, "detail": detail}
    with open(EVENT_STREAM, "a") as f:
        f.write(json.dumps(event) + "\n")

def api_request(method, endpoint, data=None, file_data=None, headers=None, max_retries=5):
    """API request with exponential backoff on 429."""
    for attempt in range(max_retries):
        try:
            url = f"{API}{endpoint}"
            if method == "GET":
                r = requests.get(url, params={"access_token": TOKEN}, timeout=30)
            elif method == "POST":
                if file_data and headers:
                    # Multipart upload
                    files = {'file': file_data}
                    r = requests.post(url, params={"access_token": TOKEN}, data=data, files=files, headers=headers, timeout=120)
                else:
                    r = requests.post(url, params={"access_token": TOKEN}, data=data or {}, timeout=60)
            elif method == "PUT":
                r = requests.put(url, data=file_data, headers=headers or {}, timeout=120)
            
            if r.status_code == 200:
                return r.json(), None
            elif r.status_code == 429:
                wait = 60 * (2 ** attempt)  # Exponential backoff: 60s, 120s, 240s...
                print(f"    [Rate limited] Waiting {wait}s...")
                time.sleep(wait)
                continue
            else:
                return {"error": f"HTTP {r.status_code}: {r.text[:200]}"}, f"HTTP {r.status_code}"
        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(30)
                continue
            return {"error": str(e)}, str(e)
    return {"error": "Max retries exceeded"}, "rate_limit_exceeded"

def get_live_products():
    """Get all currently live products from Gumroad."""
    data, err = api_request("GET", "/products")
    if err:
        print(f"ERROR: Could not fetch products: {err}")
        return {}
    
    products = {}
    for p in data.get("products", []):
        name = p.get("name", "")
        products[name] = {
            "id": p["id"],
            "url": p.get("short_url", ""),
            "published": p.get("published", False),
            "sales_count": p.get("sales_count", 0)
        }
    
    # Extract volume numbers
    volumes = {}
    for name, info in products.items():
        if "Encyclopedia Volume" in name:
            try:
                vol = int(name.split()[-1])
                volumes[vol] = info
            except:
                pass
    return volumes

def upload_volume(vol_num, verbose=True):
    """Upload a single encyclopedia volume to Gumroad."""
    epub = BASE / "publish" / "for-distribution" / "google-play" / f"pedia-vol-{vol_num:02d}.epub"
    cover = BASE / "publish" / "landing-pad" / f"encyclopedia-vol-{vol_num:02d}" / "cover.jpg"
    title = f"Encyclopedia Volume {vol_num:02d}"
    
    if verbose:
        print(f"  Checking files...")
    
    if not epub.exists():
        return {"success": False, "error": f"EPUB missing: {epub}", "volume": vol_num}
    if not cover.exists():
        return {"success": False, "error": f"Cover missing: {cover}", "volume": vol_num}
    
    if verbose:
        print(f"  Creating product...")
    
    # Step 1: Create product
    r, err = api_request("POST", "/products", {
        "name": title,
        "description": f"Gullah Geechee Encyclopedia Volume {vol_num:02d} by Darryl Elliott Brown. Publisher: Gullah Geechee Biz.",
        "price": "99",
        "currency": "usd",
        "customizable_price": True,
        "published": False,
    })
    if err or not r.get("success"):
        return {"success": False, "error": r.get("error", err or "Unknown"), "volume": vol_num}
    
    pid = r["product"]["id"]
    permalink = r["product"].get("custom_permalink", "")
    if verbose:
        print(f"  Product created: {pid}")
    time.sleep(0.5)
    
    # Step 2: Upload cover
    if verbose:
        print(f"  Uploading cover...")
    presign, err = api_request("POST", "/files/presign", {"product_id": pid, "filename": "cover.jpg"})
    if err or not presign.get("success"):
        return {"success": False, "error": f"Cover presign failed: {presign}", "volume": vol_num}
    
    presign_url = presign["url"]
    file_id_cover = presign["file"]["id"]
    
    with open(cover, "rb") as f:
        cover_data = f.read()
    
    put_r, put_err = api_request("PUT", "", file_data=cover_data, headers={"Content-Type": "image/jpeg"})
    if put_err:
        return {"success": False, "error": f"Cover PUT failed: {put_err}", "volume": vol_num}
    
    api_request("POST", "/files/complete", {"id": file_id_cover, "product_id": pid})
    if verbose:
        print(f"  Cover uploaded")
    time.sleep(0.3)
    
    # Step 3: Upload EPUB
    if verbose:
        print(f"  Uploading EPUB...")
    presign2, err = api_request("POST", "/files/presign", {"product_id": pid, "filename": "encyclopedia.epub"})
    if err or not presign2.get("success"):
        return {"success": False, "error": f"EPUB presign failed: {presign2}", "volume": vol_num}
    
    presign_url2 = presign2["url"]
    file_id_epub = presign2["file"]["id"]
    
    with open(epub, "rb") as f:
        epub_data = f.read()
    
    put_r2, put_err2 = api_request("PUT", "", file_data=epub_data, headers={"Content-Type": "application/epub+zip"})
    if put_err2:
        return {"success": False, "error": f"EPUB PUT failed: {put_err2}", "volume": vol_num}
    
    api_request("POST", "/files/complete", {"id": file_id_epub, "product_id": pid})
    if verbose:
        print(f"  EPUB uploaded")
    time.sleep(0.3)
    
    # Step 4: Publish
    if verbose:
        print(f"  Publishing...")
    pub_r, pub_err = api_request("POST", "/publish_product", {"id": pid})
    if pub_err or not pub_r.get("success"):
        return {"success": False, "error": f"Publish failed: {pub_r.get('error', pub_err)}", "volume": vol_num}
    if verbose:
        print(f"  Published")
    time.sleep(1)
    
    # Step 5: Verify on Gumroad
    live_volumes = get_live_products()
    if vol_num in live_volumes and live_volumes[vol_num]["published"]:
        url = f"https://debtide0.gumroad.com/l/{live_volumes[vol_num]['url']}"
        if verbose:
            print(f"  VERIFIED: {url}")
        return {
            "success": True,
            "volume": vol_num,
            "id": pid,
            "url": url,
            "permalink": permalink,
            "gumroad_verified": True
        }
    
    return {"success": False, "error": "Product not found on Gumroad after publish", "volume": vol_num}

def main():
    print("=" * 70)
    print("GUMROAD PUBLISHING TANK - FINAL VERIFICATION & UPLOAD")
    print("=" * 70)
    print(f"Time: {time.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    
    # Get current state
    print("\n[1] Fetching live products from Gumroad...")
    live_volumes = get_live_products()
    print(f"    Live encyclopedia volumes: {sorted(live_volumes.keys())}")
    
    # Get DB state
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT data, state FROM manifests WHERE data LIKE '%Encyclopedia Volume%'")
    db_volumes = {}
    for row in cur.fetchall():
        try:
            d = json.loads(row[0])
            vol = int(d['title'].split()[-1])
            db_volumes[vol] = row[1]
        except:
            pass
    conn.close()
    
    print(f"    DB marked as 'published': {sorted([v for v,s in db_volumes.items() if s=='published'])}")
    print(f"    DB marked as 'discovered': {sorted([v for v,s in db_volumes.items() if s=='discovered'])}")
    
    # Determine what needs uploading
    all_volumes = set(range(1, 51))
    already_live = set(live_volumes.keys())
    needs_upload = all_volumes - already_live
    
    print(f"\n[2] Status Summary:")
    print(f"    Already live on Gumroad: {sorted(already_live)}")
    print(f"    Need to upload: {sorted(needs_upload)}")
    
    # Check rate limit
    print(f"\n[3] Checking rate limit...")
    _, rl_err = api_request("GET", "/products")
    if rl_err == "429":
        print("    RATE LIMIT ACTIVE - waiting for reset...")
        print("    This may take several minutes to hours depending on quota.")
        log_event("rate_limit_detected", "Gumroad rate limit active, cannot upload")
        return False
    print("    Rate limit OK")
    
    # Upload in batches respecting daily quota
    batch_size = min(10, len(needs_upload))
    volumes_to_upload = sorted(list(needs_upload))[:batch_size]
    
    print(f"\n[4] Uploading batch: {volumes_to_upload}")
    results = []
    
    for vol in volumes_to_upload:
        print(f"\n  --- Vol {vol:02d} ---")
        r = upload_volume(vol, verbose=True)
        results.append(r)
        
        if r["success"]:
            log_event("upload_success", f"Volume {vol:02d}: {r['url']}")
            # Update DB
            conn = sqlite3.connect(DB_PATH)
            cur = conn.cursor()
            cur.execute("UPDATE manifests SET state='published' WHERE data LIKE ?",
                        (f"%Encyclopedia Volume {vol:02d}%",))
            rows = cur.rowcount
            conn.commit()
            conn.close()
            print(f"    DB updated: {rows} rows")
        else:
            log_event("upload_failed", f"Volume {vol:02d}: {r.get('error', 'unknown')}")
        
        time.sleep(5)  # Spacing between uploads
    
    # Save results
    results_data = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "batch": volumes_to_upload,
        "results": results,
        "summary": {
            "total_attempted": len(results),
            "successful": sum(1 for r in results if r["success"]),
            "failed": sum(1 for r in results if not r["success"]),
            "already_live": len(already_live),
            "remaining_to_upload": len(needs_upload) - len([r for r in results if r["success"]])
        }
    }
    
    with open(RESULTS_FILE, "w") as f:
        json.dump(results_data, f, indent=2)
    
    print(f"\n{'='*70}")
    print(f"FINAL RESULTS")
    print(f"{'='*70}")
    print(f"Successfully uploaded this run: {results_data['summary']['successful']}/{len(results)}")
    print(f"Already live before this run: {len(already_live)}")
    print(f"Remaining to upload: {results_data['summary']['remaining_to_upload']}")
    
    # List verified URLs
    print(f"\n[Verified Live Products]")
    final_volumes = get_live_products()
    for vol in sorted(final_volumes.keys()):
        info = final_volumes[vol]
        status = "✓ LIVE" if info["published"] else "✗ DRAFT"
        print(f"  {status} Vol {vol:02d}: {info['url']}")
    
    return len([r for r in results if r["success"]]) > 0

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
