#!/usr/bin/env python3
"""Upload Encyclopedia Volumes with retry and rate limit handling."""
import json
import os
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

def api_post(endpoint, data, max_retries=5):
    """POST with exponential backoff on 429."""
    for attempt in range(max_retries):
        r = requests.post(f"{API}{endpoint}", params={"access_token": TOKEN}, data=data, timeout=60)
        if r.status_code == 200:
            return r.json(), None
        if r.status_code == 429:
            wait = 30 * (2 ** attempt)
            print(f"    Rate limited (429), waiting {wait}s (attempt {attempt+1}/{max_retries})...")
            time.sleep(wait)
            continue
        return {"error": f"HTTP {r.status_code}: {r.text[:200]}", "status": r.status_code}, f"HTTP {r.status_code}"
    return {"error": "Rate limit exceeded after retries"}, "429"

def api_get(endpoint):
    r = requests.get(f"{API}{endpoint}", params={"access_token": TOKEN}, timeout=30)
    if r.status_code != 200:
        return None, f"HTTP {r.status_code}"
    return r.json(), None

def get_existing_volumes():
    data, err = api_get("/products")
    if err:
        print(f"  Error fetching products: {err}")
        return {}
    vols = {}
    for p in data.get("products", []):
        name = p.get("name", "")
        if "Encyclopedia Volume" in name:
            try:
                vol = int(name.split()[-1])
                vols[vol] = {"id": p["id"], "url": p.get("short_url", ""), "published": p.get("published", False)}
            except:
                pass
    return vols

def upload_one(vol_num, verbose=True):
    epub = BASE / "publish" / "for-distribution" / "google-play" / f"pedia-vol-{vol_num:02d}.epub"
    cover = BASE / "publish" / "landing-pad" / f"encyclopedia-vol-{vol_num:02d}" / "cover.jpg"
    title = f"Encyclopedia Volume {vol_num:02d}"

    if not epub.exists():
        return {"success": False, "error": f"EPUB missing: {epub}", "volume": vol_num}
    if not cover.exists():
        return {"success": False, "error": f"Cover missing: {cover}", "volume": vol_num}

    if verbose:
        print(f"  Creating product...")

    # Step 1: Create product
    r, err = api_post("/products", {
        "name": title,
        "description": f"Gullah Geechee Encyclopedia Volume {vol_num:02d} by Darryl Elliott Brown.",
        "price": "99",
        "currency": "usd",
        "customizable_price": True,
        "published": False,
    })
    if err:
        return {"success": False, "error": err, "volume": vol_num}
    if not r.get("success"):
        return {"success": False, "error": r.get("message", "Unknown"), "volume": vol_num}

    pid = r["product"]["id"]
    permalink = r["product"].get("custom_permalink", "")
    if verbose:
        print(f"  Product created: {pid}")
    time.sleep(0.5)

    # Step 2: Upload cover via presign
    if verbose:
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
        return {"success": False, "error": f"Cover PUT failed: {req.status_code}", "volume": vol_num}
    if verbose:
        print(f"  Cover uploaded")
    time.sleep(0.3)

    # Step 3: Complete cover
    api_post("/files/complete", {"id": file_id_cover, "product_id": pid})

    # Step 4: Upload EPUB via presign
    if verbose:
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
        return {"success": False, "error": f"EPUB PUT failed: {req.status_code}", "volume": vol_num}
    if verbose:
        print(f"  EPUB uploaded")
    time.sleep(0.3)

    # Step 5: Complete EPUB
    api_post("/files/complete", {"id": file_id_epub, "product_id": pid})

    # Step 6: Publish
    if verbose:
        print(f"  Publishing...")
    r, err = api_post("/publish_product", {"id": pid})
    if err or not r.get("success"):
        return {"success": False, "error": f"Publish failed: {err or r}", "volume": vol_num}
    if verbose:
        print(f"  Published")
    time.sleep(1)

    # Step 7: Verify
    vols = get_existing_volumes()
    if vol_num in vols and vols[vol_num]["published"]:
        url = f"https://debtide0.gumroad.com/l/{vols[vol_num]['url']}"
        if verbose:
            print(f"  VERIFIED: {url}")
        return {"success": True, "volume": vol_num, "id": pid, "url": url, "gumroad_verified": True}
    return {"success": False, "error": "Not verified on Gumroad", "volume": vol_num}

if __name__ == "__main__":
    volumes = list(range(1, 17))  # 01-16
    
    print("=" * 60)
    print("GUMROAD PUBLISHING — Encyclopedia Volumes 01-16")
    print("=" * 60)

    existing = get_existing_volumes()
    print(f"\nAlready on Gumroad: {sorted(existing.keys())}")
    to_upload = [v for v in volumes if v not in existing]
    print(f"To upload: {to_upload}\n")

    results = []
    for vol in to_upload:
        print(f"VOL-{vol:02d}: uploading...")
        r = upload_one(vol, verbose=True)
        results.append(r)

        if r["success"]:
            log_event("upload_success", f"Volume {vol:02d}: {r['url']}")
            import sqlite3
            conn = sqlite3.connect(DB_PATH)
            cur = conn.cursor()
            cur.execute("UPDATE manifests SET state='published' WHERE data LIKE ?",
                        (f"%Encyclopedia Volume {vol:02d}%",))
            rows = cur.rowcount
            conn.commit()
            conn.close()
            print(f"  SUCCESS: {r['url']} (DB: {rows} rows)")
        else:
            log_event("upload_failed", f"Volume {vol:02d}: {r.get('error','unknown')}")
            print(f"  FAILED: {r.get('error','unknown')}")
        time.sleep(3)  # Extra spacing between uploads

    ok = [r for r in results if r["success"]]
    fail = [r for r in results if not r["success"]]
    print(f"\n{'='*60}")
    print(f"RESULTS: {len(ok)} succeeded, {len(fail)} failed out of {len(results)}")
    print(f"{'='*60}")
    for r in ok:
        vol = r.get('volume', '?')
        if isinstance(vol, int):
            print(f"  ✓ Vol {vol:02d}: {r.get('url','N/A')}")
        else:
            print(f"  ✓ Vol {vol}: {r.get('url','N/A')}")
    for r in fail:
        vol = r.get('volume')
        if isinstance(vol, int):
            print(f"  ✗ Vol {vol:02d}: {r.get('error','?')}")
        else:
            print(f"  ✗ Vol {vol}: {r.get('error','?')}")

    sys.exit(0 if not fail else 1)
