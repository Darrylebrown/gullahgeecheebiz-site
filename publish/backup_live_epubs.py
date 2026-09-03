#!/usr/bin/env python3
"""Backup the 7 live real-content encyclopedia EPUBs from Gumroad to HOME disk.
Only touches published encyclopedia products; every step verified."""
import json, os, re, sys, time, urllib.request, urllib.parse, hashlib, zipfile, io

BASE = "/Users/darrylsmac/gullahgeecheebiz-site"
TOKEN = None
for line in open(f"{BASE}/.env").read().splitlines():
    if line.startswith("GUMROAD_ACCESS_TOKEN="):
        TOKEN = line.split("=", 1)[1].strip().strip('"').strip("'")
        break
assert TOKEN, "no token"

API = "https://api.gumroad.com/v2"
OUT = os.path.expanduser("~/publishing-backups/gumroad-encyclopedia-real/2026-09-02")
os.makedirs(OUT, exist_ok=True)

def fetch(url):
    req = urllib.request.Request(url, headers={"Authorization": "Bearer " + TOKEN})
    for a in range(5):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            if e.code == 429:
                time.sleep(8 * (a + 1)); continue
            raise
    raise RuntimeError("max retries")

def api_get(endpoint):
    d = fetch(API + endpoint)
    if not d.get("success"):
        raise RuntimeError(f"{endpoint}: {d}")
    return d

# 1) paginated list -> published encyclopedia products
products, url = [], "https://api.gumroad.com/v2/products?limit=100"
while url:
    d = fetch(url)
    products.extend(d.get("products", []))
    url = d.get("next_page_url")
    if url and url.startswith("/"):
        url = "https://api.gumroad.com" + url

enc_pub = [p for p in products if p.get("name", "").startswith("Encyclopedia Volume") and p.get("published")]
print(f"TOTAL products: {len(products)} | published encyclopedia: {len(enc_pub)}")
for p in sorted(enc_pub, key=lambda x: x["name"]):
    fi = p.get("file_info") or {}
    print(f"  {p['name']}: {fi.get('Size')} | {p.get('short_url')}")

# 2) detail per product -> file download urls
manifest = []
for p in sorted(enc_pub, key=lambda x: int(x["name"].split()[-1])):
    vol = int(p["name"].split()[-1])
    det = api_get(f"/products/{urllib.parse.quote(p['id'])}").get("product", {})
    files = det.get("files") or []
    big = [f for f in files if (f.get("size") or 0) > 100000]
    if not big:
        print(f"VOL {vol:02d}: NO big file found on product detail! files={[(f.get('name'), f.get('size')) for f in files]}")
        manifest.append({"volume": vol, "ok": False, "reason": "no big file"})
        continue
    f = big[0]
    fname = f.get("name") or f.get("original_name") or "encyclopedia.epub"
    furl = f.get("url")
    if not furl:
        manifest.append({"volume": vol, "ok": False, "reason": "no url"})
        continue
    # download
    try:
        req = urllib.request.Request(furl, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=120) as r:
            data = r.read()
    except Exception as e:
        print(f"VOL {vol:02d}: download FAILED: {e}")
        manifest.append({"volume": vol, "ok": False, "reason": str(e)})
        continue
    dest = os.path.join(OUT, f"pedia-vol-{vol:02d}.epub")
    with open(dest, "wb") as fh:
        fh.write(data)
    # verify: epub zip + chapter count
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            names = z.namelist()
            chapters = [n for n in names if re.search(r"ch(apter)?\d|OEBPS/.*\.(xhtml|html)", n, re.I)]
            ok_zip = True
    except Exception as e:
        ok_zip, chapters = False, [str(e)]
    sha = hashlib.sha256(data).hexdigest()[:16]
    print(f"VOL {vol:02d}: saved {dest} | {len(data)} bytes | sha256 {sha} | zip_ok={ok_zip} | entries={len(chapters) if chapters else '?'}")
    manifest.append({"volume": vol, "ok": True, "bytes": len(data), "sha256": sha,
                     "dest": dest, "source_url": furl, "zip_ok": ok_zip,
                     "n_zip_entries": len(chapters) if ok_zip else None})

json.dump(manifest, open(os.path.join(OUT, "manifest.json"), "w"), indent=1)
ok = sum(1 for m in manifest if m.get("ok"))
print(f"\nBacked up {ok}/{len(manifest)} published encyclopedia volumes to {OUT}")
sys.exit(0 if ok == len(manifest) and ok > 0 else 2)
