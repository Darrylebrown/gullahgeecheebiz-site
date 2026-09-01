#!/usr/bin/env python3
"""Check Gumroad sales and publish remaining products."""
import json
import os
import sys
import time
import urllib.request
import urllib.error
import urllib.parse

BASE = "/Users/darrylsmac/gullahgeecheebiz-site"
TOKEN = None
for line in open(f"{BASE}/.env").read().splitlines():
    if line.startswith("GUMROAD_ACCESS_TOKEN="):
        TOKEN = line.split("=", 1)[1].strip().strip('"').strip("'")
        break

if not TOKEN:
    print("ERROR: No token found"); sys.exit(1)

def api_get(url):
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {TOKEN}"})
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode())

def api_post(url, params):
    data_bytes = "&".join(f"{k}={urllib.parse.quote(str(v))}" for k, v in params.items()).encode()
    req = urllib.request.Request(url, data=data_bytes,
        headers={"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/x-www-form-urlencoded"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode())

# Check sales
sales_url = "https://api.gumroad.com/v2/sales"
try:
    sales_data = api_get(sales_url)
    sales = sales_data.get('sales', [])
    total = sum(float(s.get('sale_price', 0)) for s in sales)
    print(f"=== SALES CHECK ===")
    print(f"Total sales: {len(sales)}")
    print(f"Revenue: ${total:.2f}")
    print(f"Target: $10,000.00")
    print(f"Gap: ${10000-total:.2f}")
except Exception as e:
    print(f"Error checking sales: {e}")
    total = 0.0

print()

# Get all products
all_products = []
page_key = None
while True:
    url = "https://api.gumroad.com/v2/products"
    if page_key:
        url += f"?page_key={page_key}"
    try:
        data = api_get(url)
        products = data.get('products', [])
        all_products.extend(products)
        page_key = data.get('next_page_key')
        if not page_key:
            break
        time.sleep(2)
    except urllib.error.HTTPError as e:
        if e.code == 429:
            print("Rate limited, waiting 60s...")
            time.sleep(60)
            continue
        raise

print(f"=== PRODUCT STATUS ===")
print(f"Total products: {len(all_products)}")
published = [p for p in all_products if p.get('published')]
unpublished = [p for p in all_products if not p.get('published')]
print(f"Published: {len(published)}")
print(f"Unpublished: {len(unpublished)}")

# Price mapping based on growth plan
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
    else:
        return "999"

# Update each unpublished product
success = 0
failed = 0
for p in unpublished:
    pid = p["id"]
    name = p["name"]
    price = get_price(name)
    permalink = name.lower().replace(" ", "-").replace("&", "and").replace(",", "").replace("'", "").replace("(", "").replace(")", "").replace(".", "")
    
    params = {
        'access_token': TOKEN,
        'product_id': pid,
        'price': price,
        'currency': 'usd',
        'published': 'true',
        'description': f'{name} — Gullah Geechee cultural heritage collection. Preserve the past. Inspire the future.',
        'custom_permalink': permalink,
    }
    
    try:
        result = api_post("https://api.gumroad.com/v2/products", params)
        if result.get("success"):
            prod = result.get("product", {})
            product_price = prod.get("price_cents", 0) / 100
            print(f"  OK {name}: ${product_price:.2f}")
            success += 1
        else:
            print(f"  FAIL {name}: {result.get('error', 'unknown')}")
            failed += 1
    except urllib.error.HTTPError as e:
        if e.code == 429:
            print(f"  RATE LIMITED: {name} - waiting 60s...")
            time.sleep(60)
            try:
                result = api_post("https://api.gumroad.com/v2/products", params)
                if result.get("success"):
                    prod = result.get("product", {})
                    product_price = prod.get("price_cents", 0) / 100
                    print(f"  OK (retry) {name}: ${product_price:.2f}")
                    success += 1
                else:
                    print(f"  FAIL (retry) {name}: {result.get('error', 'unknown')}")
                    failed += 1
            except Exception as e2:
                print(f"  ERR (retry) {name}: {e2}")
                failed += 1
        else:
            print(f"  ERR {name}: HTTP {e.code}")
            failed += 1
    except Exception as e:
        print(f"  ERR {name}: {e}")
        failed += 1
    
    time.sleep(1.5)

print(f"\n=== RESULTS ===")
print(f"Succeeded: {success}")
print(f"Failed: {failed}")
print(f"Total revenue: ${total:.2f}")
if total >= 10000:
    print("GOAL REACHED!")
else:
    print(f"Gap to goal: ${10000-total:.2f}")
