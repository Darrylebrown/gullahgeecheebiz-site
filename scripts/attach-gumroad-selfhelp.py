#!/usr/bin/env python3
"""Attach EPUBs to the 6 self-help Gumroad products (presign + files[][url] flow, proven on encyclopedia batch)."""
import json, os, requests, time
from pathlib import Path

BASE = Path("/Users/darrylsmac/gullahgeecheebiz-site")
ENV = BASE / ".env"
EPUB_DIR = BASE / "publish" / "for-distribution" / "google-play"
API = "https://api.gumroad.com/v2"

def load_token():
    for line in ENV.read_text().splitlines():
        if "GUMROAD_ACCESS_TOKEN" in line:
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    return None

TOKEN = load_token()

def api_call(method, endpoint, data=None, json_data=None, headers=None):
    url = f"{API}/{endpoint}"
    params = {"access_token": TOKEN}
    for attempt in range(3):
        try:
            if method == "GET":
                r = requests.get(url, params=params, timeout=30)
            elif method == "PUT":
                r = requests.put(url, params=params, data=data, timeout=30)
            elif method == "POST":
                r = requests.post(url, params=params, data=data, json=json_data, headers=headers, timeout=60)
            if r.status_code == 200:
                return r.json()
            if r.status_code == 429:
                time.sleep((attempt + 1) * 5)
                continue
            return {"success": False, "error": r.text[:300]}
        except Exception as e:
            if attempt < 2:
                time.sleep(3)
                continue
            return {"success": False, "error": str(e)}
    return {"success": False, "error": "Max retries"}

def get_product(pid):
    result = api_call("GET", f"products/{pid}")
    return result.get("product", {}) if result.get("success") else {}

def upload_file_presign(epub_path):
    filename = epub_path.name
    filesize = epub_path.stat().st_size
    result = api_call("POST", "files/presign", data={"filename": filename, "file_size": filesize})
    if not result.get("success"):
        return None, f"Presign failed: {result.get('error')}"
    upload_id = result.get("upload_id")
    key = result.get("key")
    parts = result.get("parts", [])
    if not upload_id or not key:
        return None, "No upload_id or key"
    with open(epub_path, "rb") as f:
        file_data = f.read()
    part_etags = []
    for i, part in enumerate(parts):
        s3_url = part.get("presigned_url")
        part_number = part.get("part_number", i + 1)
        if not s3_url:
            return None, f"No presigned URL for part {part_number}"
        r = requests.put(s3_url, data=file_data, timeout=120)
        if r.status_code not in (200, 204):
            return None, f"S3 part {part_number} failed: {r.status_code}"
        etag = r.headers.get("ETag", "").strip('"')
        part_etags.append({"part_number": part_number, "etag": etag})
    complete = api_call("POST", "files/complete", json_data={"upload_id": upload_id, "key": key, "parts": part_etags},
                        headers={"Content-Type": "application/json"})
    if not complete.get("success"):
        return None, f"Complete failed: {complete.get('error')}"
    return complete.get("file_url"), None

TARGETS = {
    "How to Practice Radical Self-Care": "al-self-care.epub",
    "How to Set Boundaries That Stick": "s-that-stick.epub",
    "How to Break Bad Habits Forever": "bits-forever.epub",
    "How to Cultivate Daily Gratitude": "ly-gratitude.epub",
    "How to Manage Anxiety Naturally": "ty-naturally.epub",
    "How to Develop Emotional Intelligence": "intelligence.epub",
}

def main():
    # Get products
    result = api_call("GET", "products")
    products = result.get("products", [])
    print(f"Fetched {len(products)} products")
    done = 0
    for pid, product in [(p["id"], p) for p in products]:
        name = product.get("name", "").strip()
        if name not in TARGETS:
            continue
        full = get_product(pid)
        if [f for f in full.get("files", []) if f.get("url")]:
            print(f"SKIP {name}: already has file")
            continue
        epub = EPUB_DIR / TARGETS[name]
        if not epub.exists():
            print(f"FAIL {name}: EPUB missing {epub}")
            continue
        file_url, err = upload_file_presign(epub)
        if err:
            print(f"FAIL {name}: {err}")
            continue
        attach = api_call("PUT", f"products/{pid}", data={"name": name, "files[][url]": file_url})
        if attach.get("success"):
            print(f"OK {name}: attached")
            done += 1
        else:
            print(f"ATTACH FAIL {name}: {attach.get('error')}")
        time.sleep(1)

    # Verify via detail endpoint
    print("\n=== VERIFY ===")
    result = api_call("GET", "products")
    for p in result.get("products", []):
        name = p.get("name", "").strip()
        if name in TARGETS:
            full = get_product(p["id"])
            files = [f for f in full.get("files", []) if f.get("url")]
            print(f"[{'READY' if files else 'NO FILE'}] {name} ({len(files)} files)")
    print(f"\nAttached: {done}")

if __name__ == "__main__":
    main()
