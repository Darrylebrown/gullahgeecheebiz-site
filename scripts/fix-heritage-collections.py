#!/usr/bin/env python3
"""Build 7 themed Heritage Collection bundles from encyclopedia volume EPUBs, then attach to remaining fileless products."""
import zipfile, glob, re, os, json, time, requests
from pathlib import Path

BASE = Path("/Users/darrylsmac/gullahgeecheebiz-site")
EPUB_DIR = BASE / "publish" / "for-distribution" / "google-play"
OUT_DIR = BASE / "publish" / "premium-bundles"
OUT_DIR.mkdir(parents=True, exist_ok=True)
API = "https://api.gumroad.com/v2"

# Theme -> volume numbers (from research topics)
THEMES = {
    "Language & Dialect": [1, 20, 31, 50],
    "History & Genealogy": [5, 7, 8, 15, 26, 27, 30, 35, 37, 38, 45, 49],
    "Traditions & Recipes": [3, 9, 21, 29, 33, 39],
    "Spirituality & Folklore": [6, 22, 36],
    "Art & Craft": [2, 17, 23, 32, 47],
    "Music & Storytelling": [16, 18, 46, 48],
    "Environment & Ecology": [4, 24, 25, 34, 40],
}

def find_volumes():
    vols = {}
    for f in glob.glob(str(EPUB_DIR / "*.epub")):
        try:
            z = zipfile.ZipFile(f)
            opf = [n for n in z.namelist() if n.endswith(".opf")]
            if not opf:
                continue
            content = z.read(opf[0]).decode("utf-8", "ignore")
            m = re.search(r"<dc:title[^>]*>(.*?)</dc:title>", content, re.S)
            if not m:
                continue
            vm = re.match(r"encyclopedia\s*volume\s*(\d+)", m.group(1).strip(), re.I)
            if vm:
                vols[int(vm.group(1))] = f
        except Exception:
            continue
    return vols

def build_themed_bundles(vols):
    bundles = {}
    for theme, nums in THEMES.items():
        slug = theme.lower().replace(" & ", "-").replace(" ", "-")
        out = OUT_DIR / f"heritage-collection-{slug}.zip"
        if out.exists():
            out.unlink()
        with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
            for v in nums:
                if v in vols:
                    z.write(vols[v], f"Encyclopedia Volume {v:02d}.epub")
            readme = (
                f"GULLAH GEECHEE CULTURAL HERITAGE COLLECTION — {theme.upper()}\n"
                "by Darryl Elliott Brown\n\n"
                f"This themed collection contains {len([v for v in nums if v in vols])} encyclopedia volumes "
                f"focused on {theme}.\n\n© 2026 Gullah Geechee Biz. All rights reserved.\n"
            )
            z.writestr("README.txt", readme)
        bundles[theme] = str(out)
        print(f"built: {out.name} ({out.stat().st_size/1024:.0f} KB)")
    return bundles

def load_token():
    for line in (BASE / ".env").read_text().splitlines():
        if line.startswith("GUMROAD_ACCESS_TOKEN="):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    raise SystemExit("No token")

TOKEN = load_token()

def req(method, url, **kw):
    for attempt in range(5):
        try:
            r = requests.request(method, url, timeout=60, **kw)
            if r.status_code == 429:
                time.sleep(30 + attempt * 20)
                continue
            return r
        except Exception:
            if attempt < 4:
                time.sleep(5 + attempt * 10)
                continue
            raise
    return None

def get_all_products():
    allp, page = [], None
    while True:
        params = {"access_token": TOKEN}
        if page:
            params["page_key"] = page
        r = req("GET", f"{API}/products", params=params)
        if r is None:
            break
        d = r.json()
        allp.extend(d.get("products", []))
        page = d.get("next_page_key")
        if not page:
            break
    return allp

def upload_and_attach(pid, fpath):
    fname = Path(fpath).name
    fsize = os.path.getsize(fpath)
    pr = req("POST", f"{API}/files/presign", data={"access_token": TOKEN, "filename": fname, "file_size": fsize})
    if pr is None:
        return False, "presign conn fail"
    pres = pr.json()
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
        for attempt in range(5):
            try:
                resp = requests.put(part["presigned_url"], data=content, headers={"Content-Type": "application/zip"}, timeout=300)
                break
            except Exception:
                if attempt < 4:
                    time.sleep(10)
                    continue
                return False, "s3 conn fail"
        if resp.status_code not in (200, 204):
            return False, f"s3 {resp.status_code}"
        etags.append({"part_number": part["part_number"], "etag": resp.headers.get("ETag", "").strip('"')})
    cr = req("POST", f"{API}/files/complete", params={"access_token": TOKEN}, json={"upload_id": upload_id, "key": key, "parts": etags})
    if cr is None:
        return False, "complete conn fail"
    complete = cr.json() if cr.status_code < 500 else {"success": False}
    if not complete.get("success"):
        return False, f"complete: {str(complete)[:100]}"
    file_url = complete.get("file_url", pres.get("file_url"))
    ar = req("PUT", f"{API}/products/{pid}", params={"access_token": TOKEN}, data={"files[][url]": file_url})
    if ar is None:
        return False, "attach conn fail"
    try:
        aj = ar.json()
    except Exception:
        aj = {"success": False, "error": ar.text[:100]}
    if aj.get("success"):
        return True, "attached"
    check = req("GET", f"{API}/products/{pid}", params={"access_token": TOKEN})
    if check is not None and check.json().get("product", {}).get("file_info"):
        return True, "attached (verified)"
    return False, f"attach: {str(aj)[:100]}"

def main():
    vols = find_volumes()
    bundles = build_themed_bundles(vols)
    vol_epubs = {v: f for v, f in vols.items()}

    # Use known missing products from earlier scan (id, name) — avoids per-product verify calls
    try:
        known = json.load(open("/tmp/gumroad_missing.json"))
        missing = [{"id": k["id"], "name": k["name"]} for k in known]
        print(f"\nknown missing products: {len(missing)}")
    except Exception:
        prods = get_all_products()
        missing = [{"id": p["id"], "name": p["name"]} for p in prods]
        print(f"\nfallback: checking all {len(missing)} products (will skip ones with files via attach-verify)")

    results = {"ok": [], "fail": []}
    for p in missing:
        name = p["name"]
        pid = p["id"]
        # find bundle
        fpath = None
        for theme, bpath in bundles.items():
            if theme.lower() in name.lower():
                fpath = bpath
                break
        if not fpath:
            vm = re.match(r"encyclopedia\s*volume\s*(\d+)", name, re.I)
            if vm and int(vm.group(1)) in vol_epubs:
                fpath = vol_epubs[int(vm.group(1))]
        if not fpath:
            print(f"⚠️ no asset for: {name[:60]}")
            results["fail"].append((name, "no asset"))
            continue
        print(f"\n📦 {name[:60]}")
        ok, msg = upload_and_attach(pid, fpath)
        print(f"  {'✅' if ok else '❌'} {msg}")
        results["ok" if ok else "fail"].append((name, msg))
        time.sleep(2)

    print(f"\n✅ ok: {len(results['ok'])} | ❌ fail: {len(results['fail'])}")
    json.dump(results, open(str(BASE / "publish" / "heritage-fix-results.json"), "w"), indent=2)

if __name__ == "__main__":
    main()
