#!/usr/bin/env python3
"""
GGB Promotion Orchestrator — August 30, 2026 Run
Uploads EPUB files to existing Gumroad products (Vol 06-15) so they can be published.
Uses JSON content type for /files/complete endpoint.
"""
import json, os, sys, time, sqlite3
from datetime import datetime
from pathlib import Path

import requests

BASE = Path("/Users/darrylsmac/gullahgeecheebiz-site")
ENV_FILE = BASE / ".env"
DB_FILE = BASE / "publish" / "publisher.db"
EPUB_DIR = BASE / "publish" / "for-distribution" / "google-play"
COVERS_DIR = BASE / "ggb-engine" / "headquarters" / "covers"

# Load token
token = None
for line in ENV_FILE.read_text().splitlines():
    if line.startswith("GUMROAD_ACCESS_TOKEN="):
        token = line.split("=", 1)[1].strip().strip('"').strip("'")
        break
if not token:
    print("ERROR: No GUMROAD_ACCESS_TOKEN"); sys.exit(1)

API = "https://api.gumroad.com/v2"

def log(msg):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"  [{ts}] {msg}")

def get_existing():
    r = requests.get(f"{API}/products", params={"access_token": token}, timeout=30)
    if r.status_code != 200:
        print(f"ERROR fetching products: {r.status_code} {r.text[:200]}"); return {}
    return {p["name"].strip().lower(): p for p in r.json().get("products", [])}

def gumroad_upload_file(pid, epub_path, cover_path=None):
    """Upload EPUB file to existing product via presign flow."""
    file_name = os.path.basename(epub_path)
    file_size = os.path.getsize(epub_path)
    
    # 1. Presign
    r2 = requests.post(
        f"{API}/files/presign",
        data={
            "access_token": token,
            "product_id": pid,
            "filename": file_name,
            "file_size": file_size,
            "file_type": "application/epub+zip",
        },
        timeout=60
    )
    log(f"    Presign response: {r2.status_code}")
    if r2.status_code != 200:
        return {"success": False, "error": f"Presign HTTP {r2.status_code}: {r2.text[:300]}", "pid": pid}
    presign = r2.json()
    if not presign.get("success"):
        return {"success": False, "error": presign.get("message", "presign failed"), "pid": pid}
    
    part = presign["parts"][0]
    presigned_url = part["presigned_url"]
    file_id = presign.get("file_id", "")
    log(f"    Presign OK: upload_id={presign['upload_id'][:20]}...")
    
    # 2. PUT to presigned URL
    with open(epub_path, "rb") as f:
        r3 = requests.put(presigned_url, data=f, timeout=120)
    log(f"    PUT status: {r3.status_code}")
    if r3.status_code not in (200, 204):
        return {"success": False, "error": f"PUT HTTP {r3.status_code}: {r3.text[:300]}", "pid": pid, "file_id": file_id}
    
    # 3. Complete file - MUST use JSON content type
    etag = r3.headers.get("ETag", "").strip('"')
    r4 = requests.post(
        f"{API}/files/complete",
        params={"access_token": token},
        data=json.dumps({
            "upload_id": presign["upload_id"],
            "key": presign["key"],
            "parts": [{"part_number": 1, "etag": etag}]
        }),
        headers={"Content-Type": "application/json"},
        timeout=60
    )
    if r4.status_code != 200:
        return {"success": False, "error": f"Complete HTTP {r4.status_code}: {r4.text[:300]}", "pid": pid}
    log(f"    File complete OK")
    
    # 4. Attach cover if available
    cover_ok = False
    if cover_path and os.path.exists(cover_path):
        try:
            with open(cover_path, "rb") as cf:
                r5 = requests.post(
                    f"{API}/products/{pid}/asset",
                    params={"access_token": token, "type": "cover"},
                    files={"cover": (os.path.basename(cover_path), cf, "image/jpeg")},
                    timeout=60
                )
            cover_ok = r5.status_code == 200 and r5.json().get("success", False)
        except Exception as e:
            log(f"    Cover upload error: {e}")
    
    # 5. Publish the product
    time.sleep(1)
    vol_num = int(file_name.replace("pedia-vol-", "").replace(".epub", ""))
    r6 = requests.post(
        f"{API}/products/{pid}/update",
        params={"access_token": token},
        data={
            "published": "true",
            "description": f"Encyclopedia Volume {vol_num:02d} of the Gullah Geechee Encyclopedia — the definitive cultural reference on the Gullah Geechee people of the Lowcountry Sea Islands. Author: Darryl Elliott Brown. Publisher: Gullah Geechee Biz.",
        },
        timeout=60
    )
    pub_ok = r6.status_code == 200 and r6.json().get("success", False)
    log(f"    Publish status: {r6.status_code}, success={pub_ok}")
    
    # 6. Verify
    time.sleep(1)
    r7 = requests.get(f"{API}/products/{pid}", params={"access_token": token}, timeout=30)
    live = r7.json().get("product", {})
    live_url = live.get("short_url") or live.get("url")
    is_published = live.get("published", False)
    
    return {
        "success": True,
        "pid": pid,
        "url": live_url,
        "published": is_published,
        "cover_ok": cover_ok,
        "pub_ok": pub_ok,
    }

# Main
volumes_to_process = list(range(6, 16))  # Vol 06-15
results = []

existing = get_existing()
log(f"Live Gumroad products: {len(existing)}")

for v in volumes_to_process:
    name = f"Encyclopedia Volume {v:02d}"
    key = name.strip().lower()
    
    if key not in existing:
        log(f"SKIP {name}: not found on Gumroad")
        results.append({"volume": v, "status": "not_found"})
        continue
    
    pid = existing[key]["id"]
    epub = EPUB_DIR / f"pedia-vol-{v:02d}.epub"
    
    if not epub.exists():
        log(f"FAIL {name}: EPUB missing at {epub}")
        results.append({"volume": v, "status": "no_epub"})
        continue
    
    # Find cover
    cover = None
    for pattern in [f"encyclopedia-vol-{v:02d}-1_1.jpg", f"encyclopedia-volume-{v:02d}-1_1.jpg"]:
        candidates = list(COVERS_DIR.glob(pattern))
        if candidates:
            cover = str(candidates[0])
            break
    if cover:
        log(f"  Found cover: {cover}")
    
    log(f"Processing {name}...")
    r = gumroad_upload_file(pid, str(epub), cover)
    results.append(r)
    
    if r["success"]:
        log(f"  ✓ {name}: published={r.get('published', False)} url={r.get('url', 'N/A')}")
    else:
        log(f"  ✗ {name}: {r.get('error','?')}")
    
    time.sleep(2)

# Save results
out = BASE / "publish" / "gumroad_vol06-15_results.json"
out.write_text(json.dumps(results, indent=2))
log(f"\nSaved results to {out}")

# Update DB
conn = sqlite3.connect(str(DB_FILE))
for r in results:
    if r.get("success") and r.get("published"):
        v = r.get("volume", 0)
        data = json.dumps({
            "id": r["pid"],
            "title": f"Encyclopedia Volume {v:02d}",
            "author": "Darryl Elliott Brown",
            "url": r.get("url", ""),
            "status": "published"
        })
        conn.execute("INSERT OR REPLACE INTO manifests (manifest_id, data, state) VALUES (?,?,?)",
                    (r["pid"], data, "published"))
conn.commit()
conn.close()
log("DB updated")

# Summary
ok = [r for r in results if r.get("success") and r.get("published")]
fail = [r for r in results if not r.get("success")]
log(f"\n=== RESULTS ===")
log(f"Successfully published: {len(ok)}")
log(f"Failed: {len(fail)}")
for r in ok:
    log(f"  ✓ Vol {r['volume']:02d}: {r.get('url')}")
for r in fail:
    vol = r.get("volume", "?")
    log(f"  ✗ Vol {str(vol):>2}: {r.get('error', '?')}")

sys.exit(0 if not fail else 1)
