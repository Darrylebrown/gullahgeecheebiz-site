#!/usr/bin/env python3
"""Quick status check - sales and products"""
import json
import urllib.request
import os

base = "/Users/darrylsmac/gullahgeecheebiz-site"
token = None
with open(f"{base}/.env") as f:
    for line in f:
        if line.startswith("GUMROAD_ACCESS_TOKEN="):
            token = line.split("=", 1)[1].strip().strip('"').strip("'")
            break

if not token:
    print("No token found")
    exit(1)

url = f"https://api.gumroad.com/v2/sales?access_token={token}"
try:
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = json.loads(resp.read().decode())
        sales = data.get('sales', [])
        total = sum(float(s.get('sale_price', 0)) for s in sales)
        print(f"Sales: {len(sales)} transactions")
        print(f"Revenue: ${total:.2f}")
except Exception as e:
    print(f"Error: {e}")

url2 = f"https://api.gumroad.com/v2/products?access_token={token}"
try:
    req2 = urllib.request.Request(url2, headers={"Authorization": f"Bearer {token}"})
    with urllib.request.urlopen(req2, timeout=15) as resp:
        data2 = json.loads(resp.read().decode())
        products = data2.get('products', [])
        published = len([p for p in products if p.get('published')])
        unpublished = len([p for p in products if not p.get('published')])
        print(f"\nProducts: {len(products)} total")
        print(f"Published: {published}")
        print(f"Unpublished: {unpublished}")
except Exception as e:
    print(f"Products Error: {e}")
