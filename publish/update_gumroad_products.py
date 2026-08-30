#!/usr/bin/env python3
"""Update Gumroad products with prices, publish, and permalinks."""
import json, os, urllib.request, urllib.parse

BASE = "/Users/darrylsmac/gullahgeecheebiz-site"
TOKEN = None
for line in open(f"{BASE}/.env").read().splitlines():
    if line.startswith("GUMROAD_ACCESS_TOKEN="):
        TOKEN = line.split("=", 1)[1].strip().strip('"').strip("'")
        break

if not TOKEN:
    print("ERROR: No token"); exit(1)

req = urllib.request.Request(
    "https://api.gumroad.com/v2/products",
    headers={"Authorization": f"Bearer {TOKEN}"}
)
with urllib.request.urlopen(req) as resp:
    data = json.loads(resp.read().decode())

for p in data.get("products", []):
    pid = p["id"]
    name = p["name"]
    permalink = name.lower().replace(" ", "-").replace("&", "and").replace(",", "").replace("'", "").replace("(", "").replace(")", "")
    
    params = urllib.parse.urlencode({
        "access_token": TOKEN,
        "product_id": pid,
        "price": "99",
        "currency": "usd",
        "published": "true",
        "description": f"{name} — Gullah Geechee cultural heritage collection. Preserve the past. Inspire the future.",
        "custom_permalink": permalink,
        "preview_url": "https://gullahgeecheebiz.com/",
    })
    
    req2 = urllib.request.Request(
        "https://api.gumroad.com/v2/update_product",
        data=params.encode(),
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    try:
        with urllib.request.urlopen(req2, timeout=30) as resp2:
            result = json.loads(resp2.read().decode())
            if result.get("success"):
                prod = result.get("product", {})
                print(f"  ✅ {name} -> {prod.get('product_url', '?')}")
            else:
                print(f"  ⚠️  {name}: {result.get('error', 'unknown')}")
    except Exception as e:
        print(f"  ❌ {name}: {e}")
