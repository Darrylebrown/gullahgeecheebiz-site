#!/usr/bin/env python3
"""Quick price fix for all Gumroad products - runs with rate limit protection"""
import json
import urllib.request
import time
from pathlib import Path

BASE = "/Users/darrylsmac/gullahgeecheebiz-site"

env = {}
with open(f"{BASE}/.env") as f:
    for line in f:
        line = line.strip()
        if line and "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip().strip('"').strip("'")

token = env.get("GUMROAD_ACCESS_TOKEN", "")

def get_price(name):
    if "Encyclopedia Volume" in name and "Box" not in name and "Vault" not in name and "License" not in name:
        return "999"
    elif "Imposter" in name or "Morning" in name or "Confidence" in name or "Purpose" in name:
        return "399"
    elif "Box Set" in name:
        return "3999"
    elif "Vault" in name:
        return "9700"
    elif "License" in name:
        return "49700"
    elif "Self-Care" in name or "Radical" in name:
        return "399"
    elif "Boundaries" in name:
        return "399"
    elif "Red Rice" in name or "Sweetgrass" in name or "Ring Shout" in name:
        return "399"
    elif "Language" in name:
        return "1499"
    else:
        return "999"

products = []
page_key = None
for i in range(10):
    url = "https://api.gumroad.com/v2/products"
    if page_key:
        url += f"?page_key={page_key}"
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    try:
        with urllib.request.urlopen(req) as r:
            data = json.loads(r.read().decode())
        products.extend(data.get('products', []))
        page_key = data.get('next_page_key')
        if not page_key:
            break
        time.sleep(0.5)
    except Exception as e:
        print(f"Error fetching products: {e}")
        break

print(f"Products to update: {len(products)}")

success = 0
failed = 0
consecutive_429 = 0

for p in products:
    pid = p["id"]
    name = p["name"]
    price_cents = get_price(name)
    
    update_data = {
        'access_token': token,
        'price': price_cents,
        'currency': 'usd',
    }
    
    url = f"https://api.gumroad.com/v2/products/{pid}"
    req = urllib.request.Request(
        url,
        data=json.dumps(update_data).encode(),
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        method="PUT"
    )
    
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            result = json.loads(r.read().decode())
            if result.get("success"):
                success += 1
                consecutive_429 = 0
                print(f"✅ {name[:40]:<40} ${float(price_cents)/100:.2f}")
            else:
                failed += 1
                print(f"❌ {name[:40]:<40} {result.get('error', 'unknown')}")
    except urllib.error.HTTPError as e:
        if e.code == 429:
            consecutive_429 += 1
            wait = 60 * consecutive_429
            print(f"⏳ Rate limited on {name[:40]}, waiting {wait}s...")
            time.sleep(wait)
            # Retry once
            try:
                with urllib.request.urlopen(req, timeout=30) as r:
                    result = json.loads(r.read().decode())
                    if result.get("success"):
                        success += 1
                        consecutive_429 = 0
                        print(f"✅ (retry) {name[:40]:<40} ${float(price_cents)/100:.2f}")
                    else:
                        failed += 1
                        print(f"❌ (retry) {name[:40]:<40} {result.get('error', 'unknown')}")
            except Exception as e2:
                failed += 1
                print(f"⚠️ {name[:40]:<40} {e2}")
        else:
            failed += 1
            print(f"❌ {name[:40]:<40} HTTP {e.code}")
    except Exception as e:
        failed += 1
        print(f"⚠️ {name[:40]:<40} {e}")
    
    time.sleep(0.8)

print(f"\n{'='*60}")
print(f"Price Update Complete:")
print(f"  ✅ Success: {success}")
print(f"  ❌ Failed: {failed}")
print(f"{'='*60}")
