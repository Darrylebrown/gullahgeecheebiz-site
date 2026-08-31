#!/usr/bin/env python3
"""Fix Gumroad product prices and publish them."""
import json, os, urllib.request, urllib.error, time, sys

BASE = "/Users/darrylsmac/gullahgeecheebiz-site"
TOKEN = None
for line in open(f"{BASE}/.env").read().splitlines():
    if line.startswith("GUMROAD_ACCESS_TOKEN="):
        TOKEN = line.split("=", 1)[1].strip().strip('"').strip("'")
        break

if not TOKEN:
    print("ERROR: No token"); sys.exit(1)

req = urllib.request.Request(
    "https://api.gumroad.com/v2/products",
    headers={"Authorization": f"Bearer {TOKEN}"}
)
with urllib.request.urlopen(req) as resp:
    data = json.loads(resp.read().decode())

print(f"Found {len(data.get('products', []))} products")

success_count = 0
fail_count = 0

for p in data.get("products", []):
    pid = p["id"]
    name = p["name"]
    
    # Set appropriate prices based on product type
    if "Volume" in name and "Box" not in name and "Vault" not in name and "License" not in name:
        price = "999"  # $9.99 for encyclopedia volumes
    elif "Imposter" in name or "Morning" in name or "Confidence" in name or "Purpose" in name:
        price = "399"  # $3.99 for how-to guides
    else:
        price = "999"  # default $9.99
    
    permalink = name.lower().replace(" ", "-").replace("&", "and").replace(",", "").replace("'", "").replace("(", "").replace(")", "").replace(".", "")
    
    # Build update payload
    params = {
        'access_token': TOKEN,
        'product_id': pid,
        'price': price,
        'currency': 'usd',
        'published': 'true',
        'description': f'{name} — Gullah Geechee cultural heritage collection.',
        'custom_permalink': permalink,
    }
    
    # Use POST to /v2/products endpoint
    url = "https://api.gumroad.com/v2/products"
    data_bytes = "&".join(f"{k}={urllib.parse.quote(str(v))}" for k, v in params.items()).encode()
    
    try:
        req2 = urllib.request.Request(url, data=data_bytes,
            headers={"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/x-www-form-urlencoded"})
        with urllib.request.urlopen(req2, timeout=30) as resp2:
            result = json.loads(resp2.read().decode())
            if result.get("success"):
                prod = result.get("product", {})
                product_price = prod.get("price_cents", 0) / 100
                print(f"  OK {name}: ${product_price:.2f}")
                success_count += 1
            else:
                print(f"  FAIL {name}: {result.get('error', 'unknown')}")
                fail_count += 1
    except urllib.error.HTTPError as e:
        print(f"  ERR {name}: HTTP {e.code}")
        fail_count += 1
    except Exception as e:
        print(f"  ERR {name}: {e}")
        fail_count += 1
    
    time.sleep(1)  # Rate limiting

print(f"\nResults: {success_count} succeeded, {fail_count} failed")
