#!/usr/bin/env python3
"""GGB Marketing Orchestrator — publish unpublished Gumroad products with EPUBs via presign flow."""
import json, os, re, sys, time, zipfile, glob
from pathlib import Path
import requests

BASE = Path("/Users/darrylsmac/gullahgeecheebiz-site")
EPUB_DIR = BASE / "publish" / "for-distribution" / "google-play"
API = "https://api.gumroad.com/v2"

def load_token():
    for line in (BASE / ".env").read_text().splitlines():
        if line.startswith("GUMROAD_ACCESS_TOKEN="):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    raise SystemExit("No token")

TOKEN = load_token()

def api(method, path, data=None, files=None, timeout=60):
    url = f"{API}/{path}"
    payload = dict(data) if data else {}
    for attempt in range(4):
        try:
            if method == "GET":
                r = requests.get(url, params={**payload, "access_token": TOKEN}, timeout=timeout)
            elif method == "POST":
                r = requests.post(url, data={**payload, "access_token": TOKEN}, files=files, timeout=timeout)
            else:  # PUT
                r = requests.put(url, data={**payload, "access_token": TOKEN}, timeout=timeout)
            if r.status_code == 429:
                wait = 30 + attempt * 20
                print(f"  rate-limited, sleeping {wait}s")
                time.sleep(wait)
                continue
            return r.json()
        except Exception as e:
            if attempt < 3:
                time.sleep(3)
                continue
            return {"success": False, "error": str(e)}
    return {"success": False, "error": "max retries"}

def build_epub_map():
    """normalized title -> list of epub paths"""
    m = {}
    for f in glob.glob(str(EPUB_DIR / "*.epub")):
        try:
            z = zipfile.ZipFile(f)
            opf = [n for n in z.namelist() if n.endswith(".opf")]
            if not opf:
                continue
            content = z.read(opf[0]).decode("utf-8", "ignore")
            mt = re.search(r"<dc:title[^>]*>(.*?)</dc:title>", content, re.S)
            if not mt:
                continue
            title = mt.group(1).strip()
            norm = re.sub(r"^(batch\s*\d+\s+|kdp\s*draft\s*[-—]?\s*|es\s*prep\s*)", "", title, flags=re.I)
            norm = re.sub(r"\s+", " ", norm).strip().lower()
            m.setdefault(norm, []).append(f)
        except Exception:
            continue
    return m

def norm_name(name):
    return re.sub(r"\s+", " ", name).strip().lower()

def upload_and_attach(pid, fpath):
    """presign -> upload -> complete -> attach. Returns True on success."""
    fname = Path(fpath).name
    fsize = os.path.getsize(fpath)
    presign = api("POST", "files/presign", data={"filename": fname, "file_size": fsize})
    if not presign.get("success"):
        print(f"  presign failed: {presign.get('error', '')[:100]}")
        return False
    upload_id = presign["upload_id"]
    key = presign["key"]
    parts = presign.get("parts", [])
    if not parts:
        print("  no parts in presign response")
        return False
    with open(fpath, "rb") as f:
        content = f.read()
    etags = []
    for part in parts:
        pn = part["part_number"]
        url = part["presigned_url"]
        resp = requests.put(url, data=content, headers={"Content-Type": "application/epub+zip"}, timeout=180)
        if resp.status_code not in (200, 204):
            print(f"  s3 upload part {pn} failed: {resp.status_code}")
            return False
        etag = resp.headers.get("ETag", "").strip('"')
        etags.append({"part_number": pn, "etag": etag})
    # parts must be a real JSON array; send as json body with token in query
    cr = requests.post(
        f"{API}/files/complete",
        params={"access_token": TOKEN},
        json={"upload_id": upload_id, "key": key, "parts": etags},
        timeout=60,
    )
    complete = cr.json() if cr.status_code < 500 else {"success": False, "error": f"HTTP {cr.status_code}"}
    if not complete.get("success"):
        print(f"  complete failed: {complete.get('error', '')[:120]} | {str(complete)[:150]}")
        return False
    file_url = complete.get("file_url", presign.get("file_url"))
    # Attach via PUT /products/:id with files[][url] (files is a full replacement — product has none yet)
    attach = requests.put(
        f"{API}/products/{pid}",
        params={"access_token": TOKEN},
        data={"files[][url]": file_url},
        timeout=60,
    )
    try:
        attach_json = attach.json()
    except Exception:
        attach_json = {"success": False, "error": attach.text[:150]}
    if attach_json.get("success"):
        return True
    # fallback check
    check = api("GET", f"products/{pid}")
    if check.get("success") and check.get("product", {}).get("file_info"):
        return True
    print(f"  attach failed: {str(attach)[:150]}")
    return False

def publish_product(pid):
    res = api("PUT", f"products/{pid}/enable")
    return res.get("success", False)

def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "single"
    report = json.loads((BASE / "gumroad_products_report.json").read_text())
    epub_map = build_epub_map()
    print(f"epub map size: {len(epub_map)}")

    # Fetch fresh product list to skip anything already handled
    fresh = api("GET", "products")
    all_products = list(fresh.get("products", []))
    while fresh.get("next_page_key"):
        fresh = api("GET", "products", data={"page_key": fresh["next_page_key"]})
        all_products.extend(fresh.get("products", []))
    print(f"fresh product count: {len(all_products)}")

    unpublished = [p for p in all_products if not p.get("published")]
    no_files = [p for p in unpublished if not p.get("file_info")]
    with_files = [p for p in unpublished if p.get("file_info")]
    print(f"unpublished: {len(unpublished)} | without files: {len(no_files)} | with files (just enable): {len(with_files)}")

    # Publish products that already have files but are unpublished
    for p in with_files:
        if publish_product(p["id"]):
            print(f"✅ enabled existing product: {p['name'][:50]}")
        else:
            print(f"⚠️ enable failed: {p['name'][:50]}")
        time.sleep(1)

    results = {"attached_and_published": [], "attached_no_publish": [], "failed": [], "no_match": []}

    if mode == "single":
        # test: How to Develop Emotional Intelligence
        targets = [p for p in no_files if p["name"] == "How to Develop Emotional Intelligence"]
    else:
        targets = no_files

    for p in targets:
        name = p["name"]
        pid = p["id"]
        n = norm_name(name)
        matches = epub_map.get(n, [])
        print(f"\n📦 {name} ({pid[:20]}...)")
        if not matches:
            print(f"  ⚠️ no epub match")
            results["no_match"].append(name)
            continue
        fpath = matches[0]
        print(f"  epub: {Path(fpath).name}")
        ok = upload_and_attach(pid, fpath)
        if not ok:
            results["failed"].append(name)
            continue
        pub = publish_product(pid)
        if pub:
            results["attached_and_published"].append(name)
            print(f"  ✅ attached + published")
        else:
            results["attached_no_publish"].append(name)
            print(f"  ⚠️ attached but publish failed")
        time.sleep(2)

    print("\n=== RESULTS ===")
    for k, v in results.items():
        print(f"{k}: {len(v)}")
        if v and k in ("failed", "attached_no_publish"):
            print("   ", v[:10])
    (BASE / "publish" / "marketing-publish-results.json").write_text(json.dumps(results, indent=2))
    print("saved to publish/marketing-publish-results.json")

if __name__ == "__main__":
    main()
