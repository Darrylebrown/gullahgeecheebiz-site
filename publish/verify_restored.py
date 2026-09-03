#!/usr/bin/env python3
"""Verify all 22 restored canonicals: published + real file (size>100k) + HTTP 200."""
import json, sqlite3, re, urllib.request, urllib.parse, time

BASE = "/Users/darrylsmac/gullahgeecheebiz-site"
TOKEN = None
for line in open(f"{BASE}/.env").read().splitlines():
    if line.startswith("GUMROAD_ACCESS_TOKEN="):
        TOKEN = line.split("=", 1)[1].strip().strip('"').strip("'")
        break

conn = sqlite3.connect(f"{BASE}/publish/publisher.db")
rows = conn.execute("SELECT data FROM manifests").fetchall()
vol_url = {}
for (data,) in rows:
    try:
        jd = json.loads(data)
    except Exception:
        continue
    m = re.match(r"Encyclopedia Volume (\d{2})", jd.get("title") or "")
    if m and jd.get("gumroad_status") == "unpublished_stub" and jd.get("gumroad_url"):
        vol_url[int(m.group(1))] = jd["gumroad_url"]

# crawl product list -> permalink map
products, url = [], "https://api.gumroad.com/v2/products?limit=100"
while url:
    req = urllib.request.Request(url, headers={"Authorization": "Bearer " + TOKEN})
    d = json.loads(urllib.request.urlopen(req, timeout=60).read().decode())
    products.extend(d.get("products", []))
    url = d.get("next_page_url")
    if url and url.startswith("/"):
        url = "https://api.gumroad.com" + url

def tail(u):
    return (u or "").rstrip("/").split("/")[-1]

ids = {}
for p in products:
    pl = tail(p.get("custom_permalink") or p.get("short_url") or p.get("url"))
    ids.setdefault(pl, p["id"])

out = []
for v in sorted(vol_url):
    pid = ids.get(tail(vol_url[v]))
    if not pid:
        out.append({"vol": v, "ok": False, "why": "no product match"})
        continue
    time.sleep(0.3)
    q = urllib.parse.urlencode({"access_token": TOKEN})
    req = urllib.request.Request(f"https://api.gumroad.com/v2/products/{urllib.parse.quote(pid)}?{q}")
    p = json.loads(urllib.request.urlopen(req, timeout=60).read().decode()).get("product", {})
    files = p.get("files") or []
    big = [f for f in files if (f.get("size") or 0) > 100000]
    url = p.get("short_url") or p.get("url")
    http = "?"
    try:
        http = urllib.request.urlopen(url, timeout=40).status
    except Exception as e:
        http = f"ERR {e}"
    ok = bool(p.get("published")) and len(big) == 1 and http == 200
    out.append({"vol": v, "ok": ok, "published": p.get("published"),
                "n_files": len(files), "real_bytes": big[0]["size"] if big else None,
                "url": url, "http": http})
    print(f"VOL {v:02d}: {'OK ' if ok else 'BAD'} published={p.get('published')} files={len(files)} real={big[0]['size'] if big else None} http={http} {url}")

json.dump(out, open("/tmp/reenable_verify.json", "w"), indent=1)
print(f"\nverified {sum(1 for o in out if o['ok'])}/{len(out)} restored volumes")
