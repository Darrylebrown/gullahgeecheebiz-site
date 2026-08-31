#!/usr/bin/env python3
"""Wait for rate limit to reset, then upload Encyclopedia Volumes 01-16 to Gumroad."""
import json
import os
import sys
import time
import urllib.request
import urllib.parse
from pathlib import Path

BASE = Path("/Users/darrylsmac/gullahgeecheebiz-site")
TOKEN = None
for line in open(BASE / ".env").read().splitlines():
    if line.startswith("GUMROAD_ACCESS_TOKEN="):
        TOKEN = line.split("=", 1)[1].strip().strip('"')
        break

API = "https://api.gumroad.com/v2"
DB_PATH = BASE / "publish" / "publisher.db"
EVENT_STREAM = BASE / "publish" / "event_stream.jsonl"
VOLUMES_TO_UPLOAD = list(range(1, 17))  # 01-16

def log_event(action, detail):
    event = {"ts": time.strftime("%Y-%m-%dT%H:%M:%S"), "source_bot": "PUBLISHING_TANK_OWNER", "action": action, "detail": detail}
    with open(EVENT_STREAM, "a") as f:
        f.write(json.dumps(event) + "\n")

def api(method, endpoint, data=None, body=None, headers=None):
    url = API + endpoint
    req = urllib.request.Request(url, method=method)
    req.add_header("Authorization", f"Bearer {TOKEN}")
    if headers:
        for k, v in headers.items():
            req.add_header(k, v)
    if body:
        req.data = body if isinstance(body, bytes) else body.encode()
    elif data:
        req.data = urllib.parse.urlencode(data).encode()
        req.add_header("Content-Type", "application/x-www-form-urlencoded")
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        return {"error": f"HTTP {e.code}: {e.read().decode()[:300]}", "status": e.code}

def get_existing_volumes():
    data = api("GET", "/products")
    vols = {}
    for p in data.get("products", []):
        name = p.get("name", "")
        if "Encyclopedia Volume" in name:
            try:
                vol = int(name.split()[-1])
                vols[vol] = {"id": p["id"], "url": p.get("short_url", "")}
            except:
                pass
    return vols, data

def upload_one(vol_num, verbose=True):
    epub = BASE / "publish" / "for-distribution" / "google-play" / f"pedia-vol-{vol_num:02d}.epub"
    cover = BASE / "publish" / "landing-pad" / f"encyclopedia-vol-{vol_num:02d}" / "cover.jpg"
    title = f"Encyclopedia Volume {vol_num:02d}"

    if not epub.exists():
        return {"success": False, "error": f"EPUB missing: {epub}"}
    if not cover.exists():
        return {"success": False, "error": f"Cover missing: {cover}"}

    if verbose:
        print(f"  VOL-{vol_num:02d}: Creating product...")

    # Step 1: Create product via POST /v2/products
    r = api("POST", "/products", data={
        "name": title,
        "description": f"Gullah Geechee Encyclopedia Volume {vol_num:02d} by Darryl Elliott Brown. Publisher: Gullah Geechee Biz.",
        "price": "99",
        "currency": "usd",
        "customizable_price": True,
        "published": False,
    })
    if r.get("error") or not r.get("success"):
        err = r.get("error") or r.get("message", "unknown")
        if verbose:
            print(f"  FAILED: {err[:100]}")
        return {"success": False, "error": str(err), "volume": vol_num}

    pid = r["product"]["id"]
    permalink = r["product"].get("custom_permalink", "")
    if verbose:
        print(f"  Product created: {pid}")
    time.sleep(0.5)

    # Step 2: Upload cover via presign
    if verbose:
        print(f"  Uploading cover...")
    presign = api("POST", "/files/presign", data={"product_id": pid, "filename": "cover.jpg"})
    if presign.get("error"):
        return {"success": False, "error": f"Cover presign: {presign}", "volume": vol_num}
    presign_url = presign["url"]
    file_id_cover = presign["file"]["id"]
    if verbose:
        print(f"  Cover presign: {file_id_cover}")
    with open(cover, "rb") as f:
        cover_data = f.read()
    req = urllib.request.Request(presign_url, data=cover_data, method="PUT")
    req.add_header("Content-Type", "image/jpeg")
    with urllib.request.urlopen(req) as resp:
        if verbose:
            print(f"  Cover PUT: {resp.status}")

    # Step 3: Complete cover
    api("POST", "/files/complete", data={"id": file_id_cover, "product_id": pid})
    if verbose:
        print(f"  Cover complete")
    time.sleep(0.3)

    # Step 4: Upload EPUB via presign
    if verbose:
        print(f"  Uploading EPUB...")
    presign2 = api("POST", "/files/presign", data={"product_id": pid, "filename": "encyclopedia.epub"})
    if presign2.get("error"):
        return {"success": False, "error": f"EPUB presign: {presign2}", "volume": vol_num}
    presign_url2 = presign2["url"]
    file_id_epub = presign2["file"]["id"]
    if verbose:
        print(f"  EPUB presign: {file_id_epub}")
    with open(epub, "rb") as f:
        epub_data = f.read()
    req = urllib.request.Request(presign_url2, data=epub_data, method="PUT")
    req.add_header("Content-Type", "application/epub+zip")
    with urllib.request.urlopen(req) as resp:
        if verbose:
            print(f"  EPUB PUT: {resp.status}")

    # Step 5: Complete EPUB
    api("POST", "/files/complete", data={"id": file_id_epub, "product_id": pid})
    if verbose:
        print(f"  EPUB complete")
    time.sleep(0.3)

    # Step 6: Publish
    if verbose:
        print(f"  Publishing...")
    r = api("POST", "/publish_product", data={"id": pid})
    if r.get("error") or not r.get("success"):
        return {"success": False, "error": f"Publish: {r.get('error', r.get('message', 'unknown'))}", "volume": vol_num}
    if verbose:
        print(f"  Published")
    time.sleep(1)

    # Step 7: Verify on Gumroad
    vols, _ = get_existing_volumes()
    if vol_num in vols:
        url = f"https://debtide0.gumroad.com/l/{vols[vol_num]['url']}"
        if verbose:
            print(f"  VERIFIED: {url}")
        return {
            "success": True,
            "volume": vol_num,
            "id": pid,
            "url": url,
            "gumroad_verified": True,
        }
    if verbose:
        print(f"  WARNING: Product not found on Gumroad after publish")
    return {"success": False, "error": "Not verified on Gumroad", "volume": vol_num}

if __name__ == "__main__":
    print("=" * 60)
    print("GUMROAD PUBLISHING — Encyclopedia Volumes 01-16")
    print("=" * 60)

    # Wait for rate limit to reset
    print("\nChecking rate limit status...")
    for attempt in range(10):
        _, rate_data = get_existing_volumes()
        rl = rate_data.get("rate_limit", {})
        remaining = rl.get("remaining", "?")
        print(f"  Attempt {attempt+1}: rate limit remaining={remaining}")
        if remaining != 0 and remaining != "0":
            break
        wait = 30 * (attempt + 1)
        print(f"  Rate limited, waiting {wait}s...")
        time.sleep(wait)
    else:
        print("WARNING: Still rate limited after 10 attempts, proceeding anyway...")

    existing, all_data = get_existing_volumes()
    print(f"\nAlready on Gumroad: {sorted(existing.keys())}")
    print(f"Uploading: {VOLUMES_TO_UPLOAD}\n")

    results = []
    for vol in VOLUMES_TO_UPLOAD:
        if vol in existing:
            print(f"VOL-{vol:02d}: SKIP (already exists: {existing[vol]['url']})")
            results.append({"volume": vol, "success": True, "skipped": True, "url": existing[vol]["url"]})
            continue

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
            print(f"  SUCCESS: {r['url']} (DB updated: {rows} rows)")
        else:
            log_event("upload_failed", f"Volume {vol:02d}: {r.get('error','unknown')}")
            print(f"  FAILED: {r.get('error','unknown')}")
        time.sleep(2)

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
