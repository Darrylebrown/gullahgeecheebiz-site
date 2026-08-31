#!/usr/bin/env python3
"""Wait for rate limit and upload Volumes 01-10 to Gumroad."""
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

def log_event(action, detail):
    event = {"ts": time.strftime("%Y-%m-%dT%H:%M:%S"), "source_bot": "PUBLISHING_TANK_OWNER", "action": action, "detail": detail}
    with open(EVENT_STREAM, "a") as f:
        f.write(json.dumps(event) + "\n")

def wait_for_rate_limit():
    """Wait until POST is no longer rate limited."""
    print("Waiting for rate limit to reset...")
    for attempt in range(20):
        r = requests.post(f"{API}/products", params={"access_token": TOKEN}, data={"name": f"Test {attempt}", "price": "99", "currency": "usd"}, timeout=30)
        if r.status_code == 200:
            # Clean up test product
            pid = r.json().get("product", {}).get("id")
            if pid:
                requests.delete(f"{API}/products/{pid}", params={"access_token": TOKEN}, timeout=30)
            print(f"  Rate limit reset after {attempt} checks!")
            return True
        wait_time = 60 * (attempt + 1)
        if attempt < 19:
            print(f"  Still rate limited (attempt {attempt+1}), waiting {wait_time}s...")
            time.sleep(wait_time)
    print("  Still rate limited after 20 attempts - giving up")
    return False

def api_post(endpoint, data):
    r = requests.post(f"{API}{endpoint}", params={"access_token": TOKEN}, data=data, timeout=60)
    if r.status_code == 200:
        return r.json(), None
    return {"error": f"HTTP {r.status_code}: {r.text[:200]}", "status": r.status_code}, f"HTTP {r.status_code}"

def api_put(endpoint, data):
    r = requests.put(f"{API}{endpoint}", params={"access_token": TOKEN}, data=data, timeout=60)
    if r.status_code == 200:
        return r.json(), None
    return {"error": f"HTTP {r.status_code}: {r.text[:200]}", "status": r.status_code}, f"HTTP {r.status_code}"

def api_get(endpoint):
    r = requests.get(f"{API}{endpoint}", params={"access_token": TOKEN}, timeout=30)
    if r.status_code == 200:
        return r.json(), None
    return None, f"HTTP {r.status_code}"

def get_existing_volumes():
    data, err = api_get("/products")
    if err:
        return {}
    vols = {}
    for p in data.get("products", []):
        name = p.get("name", "")
        if "Encyclopedia Volume" in name:
            try:
                vol = int(name.split()[-1])
                vols[vol] = {"id": p["id"], "url": p.get("short_url", "")}
            except:
                pass
    return vols

def upload_volume(vol_num):
    epub = BASE / "publish" / "for-distribution" / "google-play" / f"pedia-vol-{vol_num:02d}.epub"
    cover = BASE / "publish" / "landing-pad" / f"encyclopedia-vol-{vol_num:02d}" / "cover.jpg"
    title = f"Encyclopedia Volume {vol_num:02d}"

    if not epub.exists():
        return {"success": False, "error": f"EPUB missing", "volume": vol_num}
    if not cover.exists():
        return {"success": False, "error": f"Cover missing", "volume": vol_num}

    print(f"  Creating product...")
    r, err = api_post("/products", {
        "name": title,
        "description": f"Gullah Geechee Encyclopedia Volume {vol_num:02d} by Darryl Elliott Brown.",
        "price": "99",
        "currency": "usd",
        "customizable_price": True,
        "published": False,
    })
    if err or not r.get("success"):
        return {"success": False, "error": str(r.get("error", err or "unknown")), "volume": vol_num}

    pid = r["product"]["id"]
    print(f"  Product created: {pid}")
    time.sleep(0.5)

    # Upload cover via presign
    print(f"  Uploading cover...")
    presign, err = api_post("/files/presign", {"product_id": pid, "filename": "cover.jpg"})
    if err or not presign.get("success"):
        return {"success": False, "error": f"Cover presign: {presign}", "volume": vol_num}
    
    presign_url = presign["url"]
    file_id_cover = presign["file"]["id"]
    
    with open(cover, "rb") as f:
        cover_data = f.read()
    req = requests.put(presign_url, data=cover_data, headers={"Content-Type": "image/jpeg"}, timeout=120)
    if req.status_code not in (200, 204):
        return {"success": False, "error": f"Cover PUT: {req.status_code}", "volume": vol_num}
    
    api_post("/files/complete", {"id": file_id_cover, "product_id": pid})
    print(f"  Cover uploaded")
    time.sleep(0.3)

    # Upload EPUB via presign
    print(f"  Uploading EPUB...")
    presign2, err = api_post("/files/presign", {"product_id": pid, "filename": "encyclopedia.epub"})
    if err or not presign2.get("success"):
        return {"success": False, "error": f"EPUB presign: {presign2}", "volume": vol_num}
    
    presign_url2 = presign2["url"]
    file_id_epub = presign2["file"]["id"]
    
    with open(epub, "rb") as f:
        epub_data = f.read()
    req = requests.put(presign_url2, data=epub_data, headers={"Content-Type": "application/epub+zip"}, timeout=120)
    if req.status_code not in (200, 204):
        return {"success": False, "error": f"EPUB PUT: {req.status_code}", "volume": vol_num}
    
    api_post("/files/complete", {"id": file_id_epub, "product_id": pid})
    print(f"  EPUB uploaded")
    time.sleep(0.3)

    # Publish
    print(f"  Publishing...")
    r, err = api_post("/publish_product", {"id": pid})
    if err or not r.get("success"):
        return {"success": False, "error": f"Publish failed: {r.get('error', err)}", "volume": vol_num}
    print(f"  Published")
    time.sleep(1)

    # Verify
    vols = get_existing_volumes()
    if vol_num in vols:
        url = f"https://debtide0.gumroad.com/l/{vols[vol_num]['url']}"
        return {"success": True, "volume": vol_num, "id": pid, "url": url, "gumroad_verified": True}
    
    return {"success": False, "error": "Not verified on Gumroad", "volume": vol_num}

if __name__ == "__main__":
    print("=" * 60)
    print("GUMROAD PUBLISHING - Volumes 01-10")
    print("=" * 60)
    
    if not wait_for_rate_limit():
        sys.exit(1)
    
    existing = get_existing_volumes()
    print(f"Already live: {sorted(existing.keys())}")
    
    volumes_to_upload = [v for v in range(1, 11) if v not in existing]
    print(f"To upload: {volumes_to_upload}")
    
    results = []
    for vol in volumes_to_upload:
        print(f"\nVOL-{vol:02d}:")
        r = upload_volume(vol)
        results.append(r)
        
        if r["success"]:
            log_event("upload_success", f"Volume {vol:02d}: {r['url']}")
            conn = sqlite3.connect(DB_PATH)
            cur = conn.cursor()
            cur.execute("UPDATE manifests SET state='published' WHERE data LIKE ?",
                        (f"%Encyclopedia Volume {vol:02d}%",))
            conn.commit()
            conn.close()
            print(f"  ✓ SUCCESS: {r['url']}")
        else:
            log_event("upload_failed", f"Volume {vol:02d}: {r.get('error', 'unknown')}")
            print(f"  ✗ FAILED: {r.get('error', 'unknown')}")
        time.sleep(10)  # Extra spacing
    
    ok = sum(1 for r in results if r["success"])
    print(f"\n{'='*60}")
    print(f"RESULTS: {ok}/{len(results)} succeeded")
    print(f"{'='*60}")
    for r in results:
        status = "✓" if r["success"] else "✗"
        print(f"  {status} Vol {r['volume']:02d}: {r.get('url', r.get('error', ''))}")
    
    sys.exit(0 if ok == len(results) else 1)
