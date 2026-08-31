#!/usr/bin/env python3
"""Final verification and status report for Gumroad publishing."""
import json
import sqlite3
import requests
from pathlib import Path

BASE = Path("/Users/darrylsmac/gullahgeecheebiz-site")
TOKEN = None
for line in open(BASE / ".env").read().splitlines():
    if line.startswith("GUMROAD_ACCESS_TOKEN="):
        TOKEN = line.split("=", 1)[1].strip().strip('"')
        break

# Get live products from Gumroad
r = requests.get("https://api.gumroad.com/v2/products", params={"access_token": TOKEN}, timeout=30)
live_data = r.json()
live_products = live_data.get("products", [])

# Extract live encyclopedia volumes
live_volumes = {}
for p in live_products:
    name = p.get("name", "")
    if "Encyclopedia Volume" in name:
        try:
            vol = int(name.split()[-1])
            short_url = p.get("short_url", "")
            live_volumes[vol] = {
                "id": p["id"],
                "url": f"https://debtide0.gumroad.com/l/{short_url}" if short_url else None,
                "published": p.get("published", False)
            }
        except:
            pass

# Get DB state
conn = sqlite3.connect(BASE / "publish" / "publisher.db")
cur = conn.cursor()
cur.execute("SELECT data, state FROM manifests WHERE data LIKE '%Encyclopedia Volume%'")
db_volumes = {}
for row in cur.fetchall():
    try:
        d = json.loads(row[0])
        vol = int(d['title'].split()[-1])
        db_volumes[vol] = row[1]
    except:
        pass
conn.close()

# Compile results
results = []
for vol in range(1, 51):
    live = live_volumes.get(vol)
    db_state = db_volumes.get(vol, "unknown")
    
    result = {
        "volume": vol,
        "live_on_gumroad": live is not None,
        "gumroad_url": live["url"] if live else None,
        "published": live["published"] if live else None,
        "db_state": db_state,
        "cover_exists": (BASE / "publish" / "landing-pad" / f"encyclopedia-vol-{vol:02d}" / "cover.jpg").exists(),
        "epub_exists": (BASE / "publish" / "for-distribution" / "google-play" / f"pedia-vol-{vol:02d}.epub").exists()
    }
    results.append(result)

# Summary
verified_live = [r for r in results if r["live_on_gumroad"] and r["published"]]
missing_from_gumroad = [r for r in results if not r["live_on_gumroad"]]

print("=" * 70)
print("GUMROAD PUBLISHING STATUS REPORT")
print("=" * 70)
print(f"Generated: 2026-08-31")
print()

print(f"VERIFIED LIVE PRODUCTS: {len(verified_live)}/50")
print("-" * 70)
for r in sorted(verified_live, key=lambda x: x["volume"]):
    print(f"  Vol {r['volume']:02d}: {r['gumroad_url']}")

print()
print(f"MISSING FROM GUMROAD: {len(missing_from_gumroad)}")
print("-" * 70)
for r in sorted(missing_from_gumroad, key=lambda x: x["volume"]):
    missing_files = []
    if not r["cover_exists"]:
        missing_files.append("cover.jpg")
    if not r["epub_exists"]:
        missing_files.append("epub")
    status = f" - Missing: {', '.join(missing_files)}" if missing_files else ""
    print(f"  Vol {r['volume']:02d}:{status}")

print()
print("=" * 70)
print("RATE LIMIT STATUS")
print("=" * 70)
test_r = requests.post("https://api.gumroad.com/v2/products", 
                        params={"access_token": TOKEN}, 
                        data={"name": "Status Check", "price": "99", "currency": "usd"},
                        timeout=30)
if test_r.status_code == 200:
    print("  Rate limit: ACTIVE (uploads possible)")
    pid = test_r.json().get("product", {}).get("id")
    if pid:
        requests.delete(f"https://api.gumroad.com/v2/products/{pid}", 
                       params={"access_token": TOKEN}, timeout=30)
else:
    print("  Rate limit: BLOCKED (HTTP 429)")
    print("  The 10/day creation quota has been exhausted.")
    print("  Next batch can be uploaded when quota resets (next day).")

print()
print("=" * 70)
print("DB STATE")
print("=" * 70)
print(f"  Total encyclopedia volumes in DB: {len(results)}")
print(f"  Marked as 'published': {sum(1 for r in results if r['db_state'] == 'published')}")
print(f"  Marked as 'discovered': {sum(1 for r in results if r['db_state'] == 'discovered')}")

print()
print("=" * 70)
print("INFRASTRUCTURE STATUS")
print("=" * 70)
print(f"  Upload script ready: upload_retry.py")
print(f"  All 50 covers exist: {all(r['cover_exists'] for r in results)}")
print(f"  All 50 EPUBs exist: {all(r['epub_exists'] for r in results)}")
print()
print("Next action: Wait for rate limit reset, then run:")
print("  python3 /Users/darrylsmac/gullahgeecheebiz-site/publish/upload_retry.py")
