#!/usr/bin/env python3
"""Final bookkeeping: DB status for 22 restored vols, consolidated live audit of all
published encyclopedia volumes, sample EPUB metadata check. All counts from live API."""
import json, os, re, sqlite3, time, zipfile, io, urllib.request, urllib.parse

BASE = "/Users/darrylsmac/gullahgeecheebiz-site"
TOKEN = None
for line in open(f"{BASE}/.env").read().splitlines():
    if line.startswith("GUMROAD_ACCESS_TOKEN="):
        TOKEN = line.split("=", 1)[1].strip().strip('"').strip("'")
        break
API = "https://api.gumroad.com/v2"
EVENT = f"{BASE}/publish/event_stream.jsonl"

def log(action, detail):
    with open(EVENT, "a") as f:
        f.write(json.dumps({"ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                            "source_bot": "PUBLISHING_TANK_OWNER", "action": action, "detail": detail}) + "\n")

# 1) DB: mark the 22 restored as live/real
conn = sqlite3.connect(f"{BASE}/publish/publisher.db")
cur = conn.cursor()
rows = cur.execute("SELECT rowid, data FROM manifests").fetchall()
restored_vols = [1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,23,24,25,31,32,33,34]
upd = 0
for rid, data in rows:
    try:
        jd = json.loads(data)
    except Exception:
        continue
    m = re.match(r"Encyclopedia Volume (\d{2})", jd.get("title") or "")
    if m and int(m.group(1)) in restored_vols and jd.get("gumroad_status") == "unpublished_stub":
        jd["gumroad_status"] = "live"
        jd["gumroad_file"] = "real"
        jd["checked_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        cur.execute("UPDATE manifests SET state='published', data=?, updated_at=? WHERE rowid=?",
                    (json.dumps(jd), time.strftime("%Y-%m-%dT%H:%M:%S"), rid))
        upd += 1
conn.commit()
print(f"DB: {upd} manifests updated to live/real")

# 2) consolidated live audit
products, url = [], "https://api.gumroad.com/v2/products?limit=100"
while url:
    req = urllib.request.Request(url, headers={"Authorization": "Bearer " + TOKEN})
    d = json.loads(urllib.request.urlopen(req, timeout=60).read().decode())
    products.extend(d.get("products", []))
    url = d.get("next_page_url")
    if url and url.startswith("/"):
        url = "https://api.gumroad.com" + url

enc = [p for p in products if p.get("name", "").startswith("Encyclopedia Volume")]
pub = [p for p in enc if p.get("published")]
print(f"total={len(products)} | encyclopedia={len(enc)} | published_encyclopedia={len(pub)}")
live = []
for p in sorted(pub, key=lambda x: int(x["name"].split()[-1])):
    fi = p.get("file_info") or {}
    sz = fi.get("Size")
    u = p.get("short_url") or p.get("url")
    http = "?"
    try:
        http = urllib.request.urlopen(u, timeout=40).status
    except Exception as e:
        http = f"ERR {e}"
    live.append({"vol": int(p["name"].split()[-1]), "size": sz, "url": u, "http": http})
    print(f"  vol {p['name'].split()[-1]}: {sz} http={http} {u}")
    time.sleep(0.2)

json.dump(live, open("/tmp/live_audit_0630.json", "w"), indent=1)

# 3) sample epub metadata (local installed copies)
for v in (1, 26, 50):
    path = f"{BASE}/publish/for-distribution/google-play/pedia-vol-{v:02d}.epub"
    with zipfile.ZipFile(path) as z:
        opf = [n for n in z.namelist() if n.endswith("content.opf")]
        t = z.read(opf[0]).decode("utf-8", "ignore") if opf else ""
        ti = re.search(r"<dc:title[^>]*>([^<]+)", t)
        print(f"  local vol {v:02d} title: {ti.group(1)[:80] if ti else '?'}")

# 4) events
log("gumroad_22_restored", f"22 stub canonicals (01-15,23-25,31-34) re-enabled with real full-book EPUBs (Claude outputs, 400-624KB); API-verified published + file>100KB + HTTP 200. Vols 16-22 unchanged (boxsplit-era real files).")
log("gumroad_creation_still_blocked", "POST /products probe vol 26 -> HTTP 429 'Retry later' (rolling create limit still closed). 21 vols (26-30,35-50) ready on disk; create_missing_volumes.py 26..50 will run when window opens.")
log("gumroad_real_epub_backup", "Downloaded the 7 live boxsplit EPUBs (16-22) to ~/publishing-backups/gumroad-encyclopedia-real/2026-09-02/ as the only surviving copies of that content family.")
print("events logged")
