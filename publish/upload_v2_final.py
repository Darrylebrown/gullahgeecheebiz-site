#!/usr/bin/env python3
"""Upload Encyclopedia Volumes to Gumroad using proven v2 presign flow."""
import json
import sys
import time
from pathlib import Path
import requests

BASE = Path("/Users/darrylsmac/gullahgeecheebiz-site")
ENV_FILE = BASE / ".env"
DB_FILE = BASE / "publish" / "publisher.db"
EVENT_STREAM = BASE / "publish" / "event_stream.jsonl"
EPUB_DIR = BASE / "publish" / "for-distribution" / "google-play"
COVER_DIR = BASE / "publish" / "landing-pad"
API = "https://api.gumroad.com/v2"

# Load token
token = None
for line in ENV_FILE.read_text().splitlines():
    if line.startswith("GUMROAD_ACCESS_TOKEN="):
        token = line.split("=", 1)[1].strip().strip('"')
        break
if not token:
    print("ERROR: No GUMROAD_ACCESS_TOKEN"); sys.exit(1)

def log_event(action, detail):
    event = {"ts": time.strftime("%Y-%m-%dT%H:%M:%S"), "source_bot": "PUBLISHING_TANK_OWNER", "action": action, "detail": detail}
    with open(EVENT_STREAM, "a") as f:
        f.write(json.dumps(event) + "\n")

def get_existing_volumes():
    r = requests.get(f"{API}/products", params={"access_token": token}, timeout=30)
    if r.status_code != 200:
        print(f"ERROR fetching products: {r.status_code} {r.text[:200]}")
        return {}
    vols = {}
    for p in r.json().get("products", []):
        name = p.get("name", "")
        if "Encyclopedia Volume" in name:
            try:
                vol = int(name.split()[-1])
                vols[vol] = {"id": p["id"], "url": p.get("short_url", ""), "name": name}
            except:
                pass
    return vols

def create_product(vol_num):
    """Create a new Gumroad product for the volume."""
    title = f"Encyclopedia Volume {vol_num:02d}"
    desc = f"Gullah Geechee Encyclopedia Volume {vol_num:02d} by Darryl Elliott Brown. Publisher: Gullah Geechee Biz."
    
    r = requests.post(
        f"{API}/products",
        params={"access_token": token},
        data={
            "name": title,
            "description": desc,
            "price": "99",
            "currency": "usd",
            "customizable_price": True,
            "published": False,
        },
        timeout=30
    )
    if r.status_code != 200:
        return None, f"HTTP {r.status_code}: {r.text[:200]}"
    resp = r.json()
    if not resp.get("success"):
        return None, resp.get("message", "Unknown error")
    return resp["product"]["id"], None

def upload_file(pid, file_path, file_type, filename):
    """Upload a file using the v2 presign flow."""
    file_size = file_path.stat().st_size
    
    # Presign
    r = requests.post(
        f"{API}/files/presign",
        params={"access_token": token},
        data={
            "product_id": pid,
            "filename": filename,
            "file_size": file_size,
            "file_type": file_type,
        },
        timeout=60
    )
    if r.status_code != 200:
        return None, f"Presign HTTP {r.status_code}: {r.text[:200]}"
    presign = r.json()
    if not presign.get("success"):
        return None, presign.get("message", "Presign failed")
    
    part = presign["parts"][0]
    presigned_url = part["presigned_url"]
    upload_id = presign["upload_id"]
    key = presign["key"]
    
    # PUT to presigned URL
    with open(file_path, "rb") as f:
        r = requests.put(presigned_url, data=f, timeout=120)
    if r.status_code not in (200, 204):
        return None, f"PUT HTTP {r.status_code}: {r.text[:200]}"
    
    # Complete
    etag = r.headers.get("ETag", "").strip('"')
    r = requests.post(
        f"{API}/files/complete",
        params={"access_token": token},
        data=json.dumps({
            "upload_id": upload_id,
            "key": key,
            "parts": [{"part_number": 1, "etag": etag}]
        }),
        headers={"Content-Type": "application/json"},
        timeout=60
    )
    if r.status_code != 200:
        return None, f"Complete HTTP {r.status_code}: {r.text[:200]}"
    
    return upload_id, None

def upload_cover(pid, cover_path):
    """Upload cover image."""
    if not cover_path.exists():
        return False
    with open(cover_path, "rb") as f:
        r = requests.post(
            f"{API}/products/{pid}/asset",
            params={"access_token": token, "type": "cover"},
            files={"cover": (cover_path.name, f, "image/jpeg")},
            timeout=60
        )
    return r.status_code == 200 and r.json().get("success", False)

def publish_product(pid):
    """Publish a product."""
    r = requests.post(
        f"{API}/products/{pid}/update",
        params={"access_token": token},
        data={"published": "true"},
        timeout=30
    )
    return r.status_code == 200 and r.json().get("success", False)

def verify_volume(vol_num):
    """Verify volume exists on Gumroad."""
    vols = get_existing_volumes()
    return vol_num in vols, vols.get(vol_num, {}).get("url", "")

def update_db(manifest_id, gumroad_id, volume, url=""):
    """Update the publisher database."""
    import sqlite3
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute(
        "UPDATE manifests SET state='published' WHERE manifest_id=? AND data LIKE ?",
        (manifest_id, f"%Encyclopedia Volume {volume:02d}%")
    )
    rows = cur.rowcount
    conn.commit()
    conn.close()
    return rows

def upload_volume(vol_num):
    """Upload a single volume to Gumroad."""
    epub_path = EPUB_DIR / f"pedia-vol-{vol_num:02d}.epub"
    cover_path = COVER_DIR / f"encyclopedia-vol-{vol_num:02d}" / "cover.jpg"
    title = f"Encyclopedia Volume {vol_num:02d}"
    
    if not epub_path.exists():
        return {"success": False, "error": f"EPUB missing: {epub_path}"}
    if not cover_path.exists():
        return {"success": False, "error": f"Cover missing: {cover_path}"}
    
    # Check if already exists
    existing = get_existing_volumes()
    if vol_num in existing:
        print(f"  SKIP: Already exists at {existing[vol_num]['url']}")
        return {
            "success": True,
            "volume": vol_num,
            "id": existing[vol_num]["id"],
            "url": existing[vol_num]["url"],
            "skipped": True
        }
    
    # Create product
    print(f"  Creating product...")
    pid, err = create_product(vol_num)
    if err:
        return {"success": False, "error": err}
    print(f"  Product created: {pid}")
    time.sleep(0.5)
    
    # Upload EPUB
    print(f"  Uploading EPUB...")
    upload_id, err = upload_file(pid, epub_path, "application/epub+zip", "encyclopedia.epub")
    if err:
        return {"success": False, "error": f"EPUB: {err}"}
    print(f"  EPUB uploaded")
    time.sleep(0.3)
    
    # Upload cover
    print(f"  Uploading cover...")
    cover_ok = upload_cover(pid, cover_path)
    print(f"  Cover {'uploaded' if cover_ok else 'failed'}")
    time.sleep(0.3)
    
    # Publish
    print(f"  Publishing...")
    pub_ok = publish_product(pid)
    print(f"  Published: {pub_ok}")
    time.sleep(1)
    
    # Verify
    found, url = verify_volume(vol_num)
    if found:
        print(f"  VERIFIED: {url}")
        return {"success": True, "volume": vol_num, "id": pid, "url": url, "gumroad_verified": True}
    
    return {"success": False, "error": "Verification failed - product not found after publish"}

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: upload_v2_final.py <volume_number> [volume_number ...]")
        sys.exit(1)
    
    volumes = [int(x) for x in sys.argv[1:]]
    existing = get_existing_volumes()
    print(f"Already on Gumroad: {sorted(existing.keys())}")
    print(f"Uploading: {volumes}\n")
    
    results = []
    for vol in volumes:
        print(f"VOL-{vol:02d}: uploading...")
        r = upload_volume(vol)
        results.append(r)
        
        if r["success"]:
            log_event("upload_success", f"Volume {vol:02d}: {r['url']}")
            # Update DB - find the manifest for this volume
            import sqlite3
            conn = sqlite3.connect(DB_FILE)
            cur = conn.cursor()
            cur.execute(
                "UPDATE manifests SET state='published' WHERE data LIKE ?",
                (f"%Encyclopedia Volume {vol:02d}%",)
            )
            rows = cur.rowcount
            conn.commit()
            conn.close()
            print(f"  SUCCESS: {r['url']} (DB: {rows} rows updated)")
        else:
            log_event("upload_failed", f"Volume {vol:02d}: {r.get('error','unknown')}")
            print(f"  FAILED: {r.get('error','unknown')}")
        time.sleep(2)
    
    ok = [r for r in results if r["success"]]
    fail = [r for r in results if not r["success"]]
    print(f"\n=== RESULTS ===")
    print(f"Succeeded: {len(ok)}/{len(results)}")
    print(f"Failed: {len(fail)}/{len(results)}")
    for r in ok:
        print(f"  ✓ Vol {r['volume']:02d}: {r.get('url','N/A')}")
    for r in fail:
        vol = r.get('volume')
        if isinstance(vol, int):
            print(f"  ✗ Vol {vol:02d}: {r.get('error','?')}")
        else:
            print(f"  ✗ Vol {vol}: {r.get('error','?')}")
    
    sys.exit(0 if not fail else 1)
