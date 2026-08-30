#!/usr/bin/env python3
"""
GGB Promotion Orchestrator — August 30, 2026 Run (Final)
Publishes all 10 Encyclopedia volumes on Gumroad using PUT method.
"""
import json, os, sys, time, sqlite3
from datetime import datetime
from pathlib import Path

import requests

BASE = Path("/Users/darrylsmac/gullahgeecheebiz-site")
ENV_FILE = BASE / ".env"
DB_FILE = BASE / "publish" / "publisher.db"

# Load token
token = None
for line in ENV_FILE.read_text().splitlines():
    if line.startswith("GUMROAD_ACCESS_TOKEN="):
        token = line.split("=", 1)[1].strip().strip('"').strip("'")
        break
if not token:
    print("ERROR: No GUMROAD_ACCESS_TOKEN"); sys.exit(1)

API = "https://api.gumroad.com/v2"

def log(msg):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"  [{ts}] {msg}")

def get_products():
    r = requests.get(f"{API}/products", params={"access_token": token}, timeout=30)
    if r.status_code != 200:
        print(f"ERROR fetching products: {r.status_code} {r.text[:200]}"); return []
    return r.json().get("products", [])

def publish_product(pid, vol_num):
    """Publish a product using PUT method."""
    r = requests.put(
        f"{API}/products/{pid}",
        params={"access_token": token},
        data={
            "published": "true",
            "description": f"Encyclopedia Volume {vol_num:02d} of the Gullah Geechee Encyclopedia — the definitive cultural reference on the Gullah Geechee people of the Lowcountry Sea Islands. Author: Darryl Elliott Brown. Publisher: Gullah Geechee Biz.",
            "price": "399",
            "customizable_price": "true",
        },
        timeout=60
    )
    if r.status_code != 200:
        return {"success": False, "error": f"PUT HTTP {r.status_code}: {r.text[:300]}", "pid": pid, "volume": vol_num}
    
    result = r.json()
    if not result.get("success"):
        return {"success": False, "error": result.get("message", "unknown"), "pid": pid, "volume": vol_num}
    
    # Verify
    time.sleep(1)
    r2 = requests.get(f"{API}/products/{pid}", params={"access_token": token}, timeout=30)
    product = r2.json().get("product", {})
    is_published = product.get("published", False)
    url = product.get("short_url") or product.get("url")
    
    return {
        "success": True,
        "pid": pid,
        "volume": vol_num,
        "published": is_published,
        "url": url,
    }

# Main
products = get_products()
log(f"Found {len(products)} products on Gumroad")

results = []
for p in products:
    name = p["name"]
    pid = p["id"]
    
    # Extract volume number
    try:
        vol_num = int(name.split()[-1])
    except:
        vol_num = 0
    
    log(f"Processing {name} (Vol {vol_num:02d})...")
    r = publish_product(pid, vol_num)
    results.append(r)
    
    if r["success"]:
        log(f"  ✓ {name}: published={r.get('published', False)} url={r.get('url', 'N/A')}")
    else:
        log(f"  ✗ {name}: {r.get('error','?')}")
    
    time.sleep(1)

# Save results
out = BASE / "publish" / "gumroad_publish_results.json"
out.write_text(json.dumps(results, indent=2))
log(f"\nSaved results to {out}")

# Update DB
conn = sqlite3.connect(str(DB_FILE))
for r in results:
    if r.get("success") and r.get("published"):
        v = r.get("volume", 0)
        data = json.dumps({
            "id": r["pid"],
            "title": f"Encyclopedia Volume {v:02d}",
            "author": "Darryl Elliott Brown",
            "url": r.get("url", ""),
            "status": "published"
        })
        conn.execute("INSERT OR REPLACE INTO manifests (manifest_id, data, state) VALUES (?,?,?)",
                    (r["pid"], data, "published"))
conn.commit()
conn.close()
log("DB updated")

# Summary
ok = [r for r in results if r.get("success") and r.get("published")]
fail = [r for r in results if not r.get("success")]
published_already = [r for r in results if r.get("success") and not r.get("published")]

log(f"\n=== RESULTS ===")
log(f"Successfully published: {len(ok)}")
log(f"Published but not confirmed: {len(published_already)}")
log(f"Failed: {len(fail)}")
for r in ok:
    log(f"  ✓ Vol {r['volume']:02d}: {r.get('url')}")
for r in published_already:
    log(f"  ~ Vol {r['volume']:02d}: uploaded but not yet published")
for r in fail:
    vol = r.get("volume", "?")
    log(f"  ✗ Vol {str(vol):>2}: {r.get('error', '?')}")

# Log to event_stream
import sqlite3 as sqlite3_mod
conn2 = sqlite3_mod.connect(str(DB_FILE))
c = conn2.cursor()
c.execute("""
INSERT INTO event_stream (source_bot, event_type, payload, created_at)
VALUES (?, ?, ?, ?)
""", (
    'promotion_orchestrator',
    'gumroad_publish_run',
    json.dumps({
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "total_products": len(products),
        "successfully_published": len(ok),
        "failed": len(fail),
        "results": results
    }),
    datetime.utcnow().isoformat()
))
conn2.commit()
conn2.close()
log("Event logged to brain-state.db")

sys.exit(0 if not fail else 1)
