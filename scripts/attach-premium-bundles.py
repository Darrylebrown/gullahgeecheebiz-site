#!/usr/bin/env python3
"""Attach premium bundle Zips to box set / vault / license products, then publish any unpublished ones."""
import json, os, sys, time, requests
from pathlib import Path

BASE = Path("/Users/darrylsmac/gullahgeecheebiz-site")
API = "https://api.gumroad.com/v2"

def load_token():
    for line in (BASE / ".env").read_text().splitlines():
        if line.startswith("GUMROAD_ACCESS_TOKEN="):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    raise SystemExit("No token")

TOKEN = load_token()

def get_all_products():
    allp, page = [], None
    while True:
        params = {"access_token": TOKEN}
        if page:
            params["page_key"] = page
        r = requests.get(f"{API}/products", params=params, timeout=30)
        d = r.json()
        allp.extend(d.get("products", []))
        page = d.get("next_page_key")
        if not page:
            break
    return allp

def presign(fpath):
    fname = Path(fpath).name
    fsize = os.path.getsize(fpath)
    r = requests.post(f"{API}/files/presign", data={"access_token": TOKEN, "filename": fname, "file_size": fsize}, timeout=30)
    return r.json()

def upload_and_attach(pid, fpath):
    """Full presign flow + attach via PUT files[][url]. Returns (ok, msg)."""
    pres = presign(fpath)
    if not pres.get("success"):
        return False, f"presign: {pres.get('error','')[:80]}"
    upload_id, key = pres["upload_id"], pres["key"]
    parts = pres.get("parts", [])
    if not parts:
        return False, "no parts"
    with open(fpath, "rb") as f:
        content = f.read()
    etags = []
    for part in parts:
        resp = requests.put(part["presigned_url"], data=content, headers={"Content-Type": "application/zip"}, timeout=300)
        if resp.status_code not in (200, 204):
            return False, f"s3 upload {resp.status_code}"
        etags.append({"part_number": part["part_number"], "etag": resp.headers.get("ETag", "").strip('"')})
    cr = requests.post(f"{API}/files/complete", params={"access_token": TOKEN}, json={"upload_id": upload_id, "key": key, "parts": etags}, timeout=60)
    complete = cr.json() if cr.status_code < 500 else {"success": False}
    if not complete.get("success"):
        return False, f"complete: {str(complete)[:100]}"
    file_url = complete.get("file_url", pres.get("file_url"))
    ar = requests.put(f"{API}/products/{pid}", params={"access_token": TOKEN}, data={"files[][url]": file_url}, timeout=60)
    try:
        aj = ar.json()
    except Exception:
        aj = {"success": False, "error": ar.text[:100]}
    if aj.get("success"):
        return True, "attached"
    check = requests.get(f"{API}/products/{pid}", params={"access_token": TOKEN}, timeout=30)
    if check.json().get("product", {}).get("file_info"):
        return True, "attached (verified)"
    return False, f"attach: {str(aj)[:100]}"

def classify(name):
    n = name.lower()
    if "institutional" in n or "site license" in n:
        return "license"
    if "vault" in n:
        return "vault"
    if "box set" in n:
        return "box"
    return None

def main():
    bundles = {
        "box": str(BASE / "publish" / "premium-bundles" / "ggb-encyclopedia-box-set-vol-1-25.zip"),
        "vault": str(BASE / "publish" / "premium-bundles" / "ggb-heritage-vault.zip"),
        "license": str(BASE / "publish" / "premium-bundles" / "ggb-institutional-site-license.zip"),
    }
    prods = get_all_products()
    targets = [p for p in prods if classify(p["name"]) and not p.get("file_info")]
    print(f"premium products needing files: {len(targets)}")
    for p in targets:
        kind = classify(p["name"])
        name = p["name"][:60]
        print(f"\n📦 [{kind.upper()}] {name}")
        ok, msg = upload_and_attach(p["id"], bundles[kind])
        print(f"  {'✅' if ok else '❌'} {msg}")
        if ok and not p.get("published"):
            pr = requests.put(f"{API}/products/{p['id']}/enable", params={"access_token": TOKEN}, timeout=30)
            en = pr.json().get("success") if pr.status_code < 500 else False
            print(f"  {'✅ published' if en else '⚠️ enable failed'}")
        time.sleep(2)

if __name__ == "__main__":
    main()
