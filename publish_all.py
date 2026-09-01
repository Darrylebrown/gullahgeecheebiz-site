#!/usr/bin/env python3
"""Publish all unpublished Gumroad products using the enable endpoint."""
import json
import os
import sys
import time
import urllib.request
import urllib.error

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

def api_post(url, data=None):
    body = None
    if data:
        if isinstance(data, dict):
            body = "&".join(f"{k}={urllib.parse.quote(str(v))}" for k, v in data.items()).encode()
        elif isinstance(data, str):
            body = data.encode()
    req = urllib.request.Request(url, data=body, method="POST",
        headers={"Authorization": f"Bearer {TOKEN}"} if data is None else {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/x-www-form-urlencoded"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode())

import urllib.parse

print("Fetching all products...")
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
        print(f"  Fetched {len(products)} products (total: {len(all_products)})")
        if not page_key:
            break
        time.sleep(1)
    except urllib.error.HTTPError as e:
        if e.code == 429:
            print("  Rate limited, waiting 60s...")
            time.sleep(60)
            continue
        raise
    time.sleep(1)

print(f"\nTotal products: {len(all_products)}")
unpublished = [p for p in all_products if not p.get('published')]
print(f"Unpublished: {len(unpublished)}")

# Price mapping
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

print("\nPublishing products...")
success = 0
failed = 0

for i, p in enumerate(unpublished):
    pid = p["id"]
    name = p["name"]
    price = get_price(name)
    
    print(f"  [{i+1}/{len(unpublished)}] {name[:50]}... -> ${price}")
    try:
        # Step 1: Enable the product
        result = api_post(f"https://api.gumroad.com/v2/products/{pid}/enable", {"access_token": TOKEN})
        if result.get("success"):
            # Step 2: Update price
            time.sleep(1)
            api_post(f"https://api.gumroad.com/v2/products/{pid}", {
                "access_token": TOKEN,
                "name": name,
                "price": price,
                "currency": "usd",
            })
            print(f"    OK")
            success += 1
        else:
            print(f"    FAIL: {result.get('error', 'unknown')}")
            failed += 1
    except urllib.error.HTTPError as e:
        print(f"    ERR: HTTP {e.code}")
        if e.code == 429:
            time.sleep(60)
            failed += 1
    except Exception as e:
        print(f"    ERR: {e}")
        failed += 1
    
    time.sleep(2)

print(f"\nPublished: {success} | Failed: {failed}")

# Check sales
print("\nChecking sales...")
try:
    sales_data = api_get("https://api.gumroad.com/v2/sales")
    sales = sales_data.get('sales', [])
    total = sum(float(s.get('sale_price', 0)) for s in sales)
    print(f"Revenue: ${total:.2f} ({len(sales)} sales)")
except Exception as e:
    print(f"Error: {e}")
    total = 0.0

# Final product status
print("\nFinal product status:")
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
        time.sleep(1)
    except urllib.error.HTTPError as e:
        if e.code == 429:
            time.sleep(60)
            continue
        raise
    time.sleep(1)

pub = [p for p in all_products if p.get('published')]
unpub = [p for p in all_products if not p.get('published')]
print(f"  Published: {len(pub)}")
print(f"  Unpublished: {len(unpub)}")
for p in pub:
    price = p.get('price_cents', 0) / 100
    print(f"    ✓ {p['name'][:45]} | ${price:.2f}")
