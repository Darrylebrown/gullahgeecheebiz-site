#!/usr/bin/env python3
"""Step A: preflight-validate + install the 50 real encyclopedia EPUBs (Claude outputs)
into the canonical pipeline dir (replacing 7.4KB stubs). Step B: attach real EPUBs to the
22 disabled stub canonicals and re-enable them. Every claim GET-verified."""
import json, os, re, sys, time, io, zipfile, sqlite3, urllib.request, urllib.parse

BASE = "/Users/darrylsmac/gullahgeecheebiz-site"
SRC = "/Users/darrylsmac/Library/Application Support/Claude/local-agent-mode-sessions/3b6ffb51-0fd1-4b40-9640-47640b67d912/4aee6ea0-1c43-4d11-b075-f28f004539d2/local_29b3d16d-3c28-4619-943e-dde0a92a6fea/outputs"
DST = f"{BASE}/publish/for-distribution/google-play"
DB = f"{BASE}/publish/publisher.db"
EVENT = f"{BASE}/publish/event_stream.jsonl"
TOKEN = None
for line in open(f"{BASE}/.env").read().splitlines():
    if line.startswith("GUMROAD_ACCESS_TOKEN="):
        TOKEN = line.split("=", 1)[1].strip().strip('"').strip("'")
        break
API = "https://api.gumroad.com/v2"

def log(action, detail):
    with open(EVENT, "a") as f:
        f.write(json.dumps({"ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                            "source_bot": "PUBLISHING_TANK_OWNER", "action": action, "detail": detail}) + "\n")

def api(method, path, data=None, json_body=None, raw=False):
    url = API + path if path.startswith("/") else path
    body = None
    if json_body is not None:
        body = json.dumps(json_body).encode()
    elif data is not None:
        body = urllib.parse.urlencode(data).encode()
    r = urllib.request.Request(url, data=body, method=method)
    r.add_header("Authorization", "Bearer " + TOKEN)
    if body:
        r.add_header("Content-Type", "application/json" if json_body is not None else "application/x-www-form-urlencoded")
    try:
        resp = urllib.request.urlopen(r, timeout=240)
        out = resp.read()
        return out if raw else json.loads(out.decode())
    except urllib.error.HTTPError as e:
        return {"error": e.code, "body": e.read().decode()[:400]}
    except Exception as e:
        return {"error": -1, "body": str(e)[:400]}

def s3_put(url, content):
    r = urllib.request.Request(url, data=content, method="PUT", headers={"Content-Type": "application/epub+zip"})
    try:
        resp = urllib.request.urlopen(r, timeout=240)
        return resp.status, dict(resp.headers)
    except urllib.error.HTTPError as e:
        return e.code, {}
    except Exception as e:
        return -1, {}

def validate_epub(path):
    """Return (ok, size, n_chapters, sample_note) — reject placeholders."""
    try:
        with zipfile.ZipFile(path) as z:
            names = z.namelist()
            bad = z.testzip()
            if bad:
                return False, os.path.getsize(path), 0, f"corrupt member {bad}"
            text = b"".join(z.read(n) for n in names if n.endswith((".xhtml", ".html")))[:40000]
        low = text.lower()
        if b"placeholder epub" in low or b"placeholder for distribution" in low:
            return False, os.path.getsize(path), 0, "placeholder text found"
        chs = len([n for n in names if re.search(r"chapters?/ch\d+\.xhtml$", n) or re.search(r"ch\d+\.(xhtml|html)$", n, re.I)])
        return True, os.path.getsize(path), chs, "ok"
    except Exception as e:
        return False, os.path.getsize(path), 0, str(e)[:120]

# ---------- STEP A: install 50 real epubs ----------
src_map = {}
for fn in os.listdir(SRC):
    m = re.match(r"Gullah_Geechee_Encyclopedia_Vol(\d+)_.+\.epub$", fn)
    if m:
        src_map[int(m.group(1))] = os.path.join(SRC, fn)
assert len(src_map) == 50, f"expected 50 src epubs, got {len(src_map)}"
installed, failed = [], []
for v in range(1, 51):
    ok, sz, nch, note = validate_epub(src_map[v])
    if not ok:
        failed.append((v, note))
        continue
    dest = os.path.join(DST, f"pedia-vol-{v:02d}.epub")
    with open(dest, "wb") as fh:
        fh.write(open(src_map[v], "rb").read())
    installed.append((v, sz, nch))
print(f"STEP A: installed {len(installed)}/50 real EPUBs into google-play/ | failed={failed}")

# ---------- STEP B: find the 22 disabled stub canonicals ----------
# canonical permalink per volume from DB manifests (gumroad_url)
conn = sqlite3.connect(DB)
rows = conn.execute("SELECT data FROM manifests").fetchall()
vol_url = {}
for (data,) in rows:
    try:
        jd = json.loads(data)
    except Exception:
        continue
    t = jd.get("title") or ""
    m = re.match(r"Encyclopedia Volume (\d{2})", t)
    if m and jd.get("gumroad_status") == "unpublished_stub" and jd.get("gumroad_url"):
        vol_url[int(m.group(1))] = jd["gumroad_url"]
print(f"STEP B: {len(vol_url)} stub-disabled volumes in DB: {sorted(vol_url)}")

# crawl current product list
products, url = [], "https://api.gumroad.com/v2/products?limit=100"
while url:
    d = api("GET", url)
    products.extend(d.get("products", []))
    url = d.get("next_page_url")
    if url and url.startswith("/"):
        url = "https://api.gumroad.com" + url
print(f"STEP B: crawled {len(products)} products")

def perm_of(p):
    return (p.get("custom_permalink") or "").strip() or (p.get("url") or "").rstrip("/").split("/")[-1] or (p.get("short_url") or "").rstrip("/").split("/")[-1]

by_perm = {perm_of(p): p for p in products}
# also index short_url tail
for p in products:
    su = (p.get("short_url") or "").rstrip("/").split("/")[-1]
    by_perm.setdefault(su, p)

target_ids = {}
for v, u in vol_url.items():
    pl = u.rstrip("/").split("/")[-1]
    p = by_perm.get(pl)
    if p:
        target_ids[v] = p["id"]
    else:
        print(f"  vol {v:02d}: NO product matched permalink {pl} !!")
print(f"STEP B: matched {len(target_ids)}/{len(vol_url)} canonical ids")

# ---------- attach real epub + enable, verify each ----------
def attach_file(pid, path):
    fname = os.path.basename(path)
    fsize = os.path.getsize(path)
    pr = api("POST", f"/files/presign?access_token={urllib.parse.quote(TOKEN)}",
             data={"filename": fname, "file_size": str(fsize)})
    if not (isinstance(pr, dict) and pr.get("success")):
        return None, f"presign {str(pr)[:200]}"
    parts = pr.get("parts") or []
    upid, key = pr.get("upload_id"), pr.get("key")
    content = open(path, "rb").read()
    etags = []
    for part in parts:
        p_url = part.get("presigned_url") or part.get("url")
        st, h2 = s3_put(p_url, content)
        if st not in (200, 204):
            return None, f"S3 PUT {st}"
        etags.append({"part_number": part.get("part_number", 1), "etag": (h2.get("ETag") or "").strip('"')})
    comp = api("POST", f"/files/complete?access_token={urllib.parse.quote(TOKEN)}",
               json_body={"upload_id": upid, "key": key, "parts": etags})
    if not (isinstance(comp, dict) and comp.get("success")):
        return None, f"complete {str(comp)[:200]}"
    final_url = comp.get("file_url") or pr.get("file_url")
    att = api("PUT", f"/products/{urllib.parse.quote(pid)}?{urllib.parse.urlencode({'access_token': TOKEN, 'files[][url]': final_url})}")
    if not (isinstance(att, dict) and att.get("success")):
        return None, f"attach {str(att)[:200]}"
    return final_url, None

results = []
for v in sorted(target_ids):
    pid = target_ids[v]
    path = os.path.join(DST, f"pedia-vol-{v:02d}.epub")
    final_url, err = attach_file(pid, path)
    if err:
        results.append({"vol": v, "ok": False, "step": err})
        print(f"VOL {v:02d}: ATTACH FAIL: {err}")
        continue
    time.sleep(0.5)
    en = api("PUT", f"/products/{urllib.parse.quote(pid)}/enable?access_token={urllib.parse.quote(TOKEN)}")
    if not (isinstance(en, dict) and en.get("success")):
        results.append({"vol": v, "ok": False, "step": f"enable {str(en)[:200]}"})
        print(f"VOL {v:02d}: ENABLE FAIL: {str(en)[:200]}")
        continue
    time.sleep(0.8)
    g = api("GET", f"/products/{urllib.parse.quote(pid)}?access_token={urllib.parse.quote(TOKEN)}")
    p = g.get("product", {})
    files = [(f.get("file_name"), f.get("size")) for f in (p.get("files") or [])]
    url = p.get("short_url") or p.get("url")
    pub = bool(p.get("published"))
    real = any((s or 0) > 100000 for _, s in files)
    http = "?"
    if url:
        try:
            http = urllib.request.urlopen(url, timeout=40).status
        except Exception as e:
            http = f"ERR {e}"
    ok = pub and real and http == 200
    results.append({"vol": v, "ok": ok, "published": pub, "real_file": real, "files": files,
                    "url": url, "http": http})
    print(f"VOL {v:02d}: {'OK' if ok else 'CHECK'} published={pub} real={real} files={files} http={http} {url}")
    time.sleep(0.5)

json.dump(results, open("/tmp/reenable_results.json", "w"), indent=1)
okn = sum(1 for r in results if r.get("ok"))
print(f"\nSTEP B: {okn}/{len(results)} volumes attached+enabled+verified")
