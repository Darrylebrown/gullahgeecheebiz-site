#!/usr/bin/env python3
"""Upload Encyclopedia Volume to Gumroad using proven v2 API flow."""
import json
import os
import sys
import time
import requests
from pathlib import Path

BASE = Path("/Users/darrylsmac/gullahgeecheebiz-site")
TOKEN = os.getenv("GUMROAD_ACCESS_TOKEN") or [l.split('=', 1)[1] for l in open(BASE / ".env").read().splitlines() if l.startswith("GUMROAD_ACCESS_TOKEN=")][0]
API = "https://api.gumroad.com/v2"
EVENT_STREAM = BASE / "publish" / "event_stream.jsonl"

def log_event(action, detail):
    event = {"ts": time.strftime("%Y-%m-%dT%H:%M:%S"), "source_bot": "PUBLISHING_TANK_OWNER", "action": action, "detail": detail}
    with open(EVENT_STREAM, "a") as f:
        f.write(json.dumps(event) + "\n")

def get_existing_volumes():
    r = requests.get(f"{API}/products", params={"access_token": TOKEN}, timeout=30)
    if r.status_code == 200:
        vols = {}
        for p in r.json().get("products", []):
            name = p.get("name", "")
            if "Encyclopedia Volume" in name:
                try:
                    vol = int(name.split()[-1])
                    vols[vol] = {"id": p["id"], "url": p.get("short_url", "")}
                except:
                    pass
        return vols
    return {}

def upload_volume(vol_num):
    """Upload a single volume to Gumroad."""
    epub = BASE / "publish" / "for-distribution" / "google-play" / f"pedia-vol-{vol_num:02d}.epub"
    cover = BASE / "ggb-engine" / "headquarters" / "covers" / f"encyclopedia-vol-{vol_num:02d}-1_1.jpg"
    title = f"Encyclopedia Volume {vol_num:02d}"
    
    if not epub.exists():
        return {"success": False, "error": f"EPUB missing: {epub}"}
    if not cover.exists():
        return {"success": False, "error": f"Cover missing: {cover}"}
    
    desc = (f"Encyclopedia Volume {vol_num:02d} of the Gullah Geechee Encyclopedia — "
            f"the definitive cultural reference on the Gullah Geechee people of the "
            f"Lowcountry Sea Islands. Author: Darryl Elliott Brown. Publisher: Gullah Geechee Biz.")
    
    # Create product
    r = requests.post(f"{API}/products", params={"access_token": TOKEN}, 
                      data={"name": title, "description": desc, "price": "499", "customizable_price": True},
                      timeout=60)
    if r.status_code != 200:
        return {"success": False, "error": f"Create failed: {r.text[:200]}"}
    resp = r.json()
    if not resp.get("success"):
        return {"success": False, "error": resp.get("message", "Unknown error")}
    
    pid = resp["product"]["id"]
    print(f"  Created product ID: {pid}")
    
    # Upload EPUB
    with open(epub, "rb") as f:
        files = {"file": (epub.name, f, "application/epub+zip")}
        r = requests.post(f"{API}/products/{pid}/files", params={"access_token": TOKEN}, files=files, timeout=90)
    if r.status_code != 200:
        return {"success": False, "error": f"EPUB upload failed: {r.text[:200]}"}
    epub_ok = r.json().get("success", False)
    
    # Upload cover
    with open(cover, "rb") as f:
        files = {"cover": (cover.name, f, "image/jpeg")}
        r = requests.post(f"{API}/products/{pid}/asset", params={"access_token": TOKEN, "type": "cover"}, files=files, timeout=90)
    if r.status_code != 200:
        cover_ok = False
    else:
        cover_ok = r.json().get("success", False)
    
    # Verify product exists
    time.sleep(1)
    r = requests.get(f"{API}/products/{pid}", params={"access_token": TOKEN}, timeout=30)
    if r.status_code == 200:
        prod = r.json().get("product", {})
        url = prod.get("short_url", "") or prod.get("url", "")
        print(f"  Verified: {url}")
        return {"success": True, "volume": vol_num, "id": pid, "url": url, "epub_ok": epub_ok, "cover_ok": cover_ok}
    
    return {"success": False, "error": "Product verification failed"}

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: upload_volume_single.py <volume_number>")
        sys.exit(1)
    
    vol = int(sys.argv[1])
    print(f"Uploading Encyclopedia Volume {vol:02d}...")
    
    # Check if already uploaded
    existing = get_existing_volumes()
    if vol in existing:
        print(f"SKIP: Volume {vol:02d} already exists on Gumroad")
        log_event("skip_already_exists", f"Volume {vol:02d} already on Gumroad: {existing[vol]['url']}")
        sys.exit(0)
    
    result = upload_volume(vol)
    print(f"Result: {result}")
    
    if result["success"]:
        log_event("upload_success", f"Volume {vol:02d}: {result['url']}")
    else:
        log_event("upload_failed", f"Volume {vol:02d}: {result.get('error', 'unknown')}")
    
    sys.exit(0 if result["success"] else 1)
