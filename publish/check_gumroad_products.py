#!/usr/bin/env python3
"""Check actual Gumroad products and find Encyclopedia Volume uploads."""
import json
import os
import sys
import urllib.request

TOKEN = open('/Users/darrylsmac/gullahgeecheebiz-site/.env').read().splitlines()
for line in TOKEN:
    if line.startswith('GUMROAD_ACCESS_TOKEN='):
        token = line.split('=', 1)[1]
        break

req = urllib.request.Request(
    'https://api.gumroad.com/v2/products?limit=100',
    headers={'Authorization': f'Bearer {token}'}
)
with urllib.request.urlopen(req) as resp:
    data = json.loads(resp.read().decode())

products = data.get('products', [])
print(f"Total Gumroad products: {len(products)}")

# Find Encyclopedia Volume products
enc_products = [p for p in products if 'Encyclopedia Volume' in p.get('name', '')]
print(f"\nEncyclopedia Volumes on Gumroad: {len(enc_products)}")
for p in sorted(enc_products, key=lambda x: x['name']):
    vol_num = int(p['name'].split()[-1])
    url = p.get('short_url', '') or p.get('url', '')
    print(f"  Vol {vol_num:02d}: {url}")

# Check for pedia-vol products
pedia_products = [p for p in products if 'pedia-vol' in p.get('name', '').lower()]
print(f"\nPedia-vol products on Gumroad: {len(pedia_products)}")
