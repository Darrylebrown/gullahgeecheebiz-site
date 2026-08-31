#!/usr/bin/env python3
"""Publish all unpublished Gumroad products."""
import urllib.request
import json
import time
from pathlib import Path

# Read token from .env
env_path = Path('/Users/darrylsmac/gullahgeecheebiz-site/.env')
token = None
with open(env_path, 'r') as f:
    for line in f:
        if line.startswith('GUMROAD_ACCESS_TOKEN='):
            token = line.strip().split('=', 1)[1]
            break

print(f"Token loaded: {bool(token)}")

# Fetch all products
all_products = []
page_key = None
while True:
    url = 'https://api.gumroad.com/v2/products?limit=50'
    if page_key:
        url += f'&page_key={page_key}'
    req = urllib.request.Request(url, headers={'Authorization': f'Bearer {token}'})
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read().decode())
    products = data.get('products', [])
    all_products.extend(products)
    page_key = data.get('next_page_key')
    if not page_key:
        break

print(f"Total products found: {len(all_products)}")
unpublished = [p for p in all_products if not p.get('published')]
print(f"Unpublished: {len(unpublished)}")

published_count = 0
failed_count = 0

for p in unpublished:
    product_id = p['id']
    name = p['name']
    
    # Add description if missing
    description = p.get('description', '')
    if not description:
        description = f"{name} by Darryl Elliott Brown. Publisher: Gullah Geechee Biz. Digital ebook in EPUB format."
    
    # Update product data - tags as ARRAY (critical!)
    update_data = {
        'access_token': token,
        'description': description,
        'published': 'true',
        'tags': ['gullah', 'geechee', 'encyclopedia', 'history', 'culture', 'southern', 'african american']
    }
    
    url = f"https://api.gumroad.com/v2/products/{product_id}"
    req = urllib.request.Request(
        url,
        data=json.dumps(update_data).encode(),
        headers={'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'},
        method='PUT'
    )
    
    try:
        with urllib.request.urlopen(req) as resp:
            result = json.loads(resp.read().decode())
            if result.get('success'):
                published_count += 1
                print(f"  ✅ Published: {name}")
            else:
                failed_count += 1
                print(f"  ❌ Failed: {name} - {result}")
    except Exception as e:
        failed_count += 1
        print(f"  ⚠️ Error publishing {name}: {e}")
    
    time.sleep(0.5)  # Rate limiting

print(f"\n✅ Published {published_count} products")
print(f"❌ Failed {failed_count} products")
