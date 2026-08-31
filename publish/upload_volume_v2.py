#!/usr/bin/env python3
"""Upload Encyclopedia Volumes to Gumroad using proven v2 presign flow."""
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
        return {"error": f"HTTP {e.code}: {e.read().decode()[:200]}"}

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

def upload_one(vol_num):
    epub = BASE / "publish" / "for-distribution" / "google-play" / f"pedia-vol-{vol_num:02d}.epub"
    cover = BASE / "publish" / "landing-pad" / f"encyclopedia-vol-{vol_num:02d}" / "cover.jpg"
    title = f"Encyclopedia Volume {vol_num:02d}"

    if not epub.exists():
        return {"success": False, "error": f"EPUB missing: {epub}"}
    if not cover.exists():
        return {"success": False, "error": f"Cover missing: {cover}"}

    # Step 1: Create product (draft)
    r = api("POST", "/create_product", data={
        "name": title,
        "description": f"Gullah Geechee Encyclopedia Volume {vol_num:02d} by Darryl Elliott Brown. Publisher: Gullah Geechee Biz.",
        "price": "99",
        "currency": "usd",
        "customizable_price": True,
        "published": False,
        "preorder": False,
    })
    if r.get("error") or not r.get("success"):
        return {"success": False, "error": str(r.get("error") or r.get("message", "unknown"))}
    pid = r["product"]["id"]
    permalink = r["product"].get("custom_permalink", "")
    print(f"  Product created: {pid} permalink={permalink}")
    time.sleep(0.5)

    # Step 2: Presign + upload cover
    presign = api("POST", "/files/presign", data={"product_id": pid, "filename": "cover.jpg"})
    if presign.get("error"):
        return {"success": False, "error": f"Cover presign failed: {presign}"}
    presign_url = presign["url"]
    file_id_cover = presign["file"]["id"]
    print(f"  Cover presign: {file_id_cover}")
    with open(cover, "rb") as f:
        cover_data = f.read()
    req = urllib.request.Request(presign_url, data=cover_data, method="PUT")
    req.add_header("Content-Type", "image/jpeg")
    with urllib.request.urlopen(req) as resp:
        print(f"  Cover PUT: {resp.status}")

    # Step 3: Complete cover
    api("POST", "/files/complete", data={"id": file_id_cover, "product_id": pid})
    print("  Cover complete")
    time.sleep(0.3)

    # Step 4: Presign + upload EPUB
    presign2 = api("POST", "/files/presign", data={"product_id": pid, "filename": "encyclopedia.epub"})
    if presign2.get("error"):
        return {"success": False, "error": f"EPUB presign failed: {presign2}"}
    presign_url2 = presign2["url"]
    file_id_epub = presign2["file"]["id"]
    print(f"  EPUB presign: {file_id_epub}")
    with open(epub, "rb") as f:
        epub_data = f.read()
    req = urllib.request.Request(presign_url2, data=epub_data, method="PUT")
    req.add_header("Content-Type", "application/epub+zip")
    with urllib.request.urlopen(req) as resp:
        print(f"  EPUB PUT: {resp.status}")

    # Step 5: Complete EPUB
    api("POST", "/files/complete", data={"id": file_id_epub, "product_id": pid})
    print("  EPUB complete")
    time.sleep(0.3)

    # Step 6: Publish
    r = api("POST", "/publish_product", data={"id": pid})
    if r.get("error") or not r.get("success"):
        return {"success": False, "error": str(r.get("error") or r.get("message", "publish failed"))}
    print("  Product published")
    time.sleep(1)

    # Step 7: Verify on Gumroad
    vols, _ = get_existing_volumes()
    if vol_num in vols:
        return {
            "success": True,
            "volume": vol_num,
            "id": pid,
            "permalink": permalink,
            "url": f"https://debtide0.gumroad.com/l/{permalink}",
            "gumroad_verified": True,
        }
    return {"success": False, "error": "Product not found on Gumroad after publish"}

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: upload_volume_v2.py <volume_number> [volume_number ...]")
        sys.exit(1)

    volumes = [int(x) for x in sys.argv[1:]]
    existing, _ = get_existing_volumes()
    print(f"Already on Gumroad: {sorted(existing.keys())}")
    print(f"Uploading: {volumes}\n")

    results = []
    for vol in volumes:
        if vol in existing:
            print(f"VOL-{vol:02d}: SKIP (already exists: {existing[vol]['url']})")
            results.append({"volume": vol, "success": True, "skipped": True, "url": existing[vol]["url"]})
            continue
        print(f"VOL-{vol:02d}: uploading...")
        r = upload_one(vol)
        results.append(r)
        if r["success"]:
            log_event("upload_success", f"Volume {vol:02d}: {r['url']}")
            # Update DB
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
        time.sleep(1)

    print(f"\nResults: {sum(1 for r in results if r['success'])}/{len(results)} succeeded")
    sys.exit(0 if all(r["success"] for r in results) else 1)
