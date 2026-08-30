#!/usr/bin/env python3
"""Check Gumroad products and current state."""
import json, os
import urllib.request

TOKEN = os.environ.get('GUMROAD_ACCESS_TOKEN') or open('/Users/darrylsmac/gullahgeecheebiz-site/.env').read().splitlines()
for line in TOKEN:
    if line.startswith('GUMROAD_ACCESS_TOKEN='):
        TOKEN = line.split('=', 1)[1]
        break

print(f"Token found: {bool(TOKEN)}")

# Get current products
req = urllib.request.Request(
    'https://api.gumroad.com/v2/products',
    headers={'Authorization': f'Bearer {TOKEN}'}
)
with urllib.request.urlopen(req) as resp:
    data = json.loads(resp.read().decode())

products = data.get('products', [])
print(f"Total products on Gumroad: {len(products)}")

# Check for encyclopedia volumes
enc_volumes = [p for p in products if 'Encyclopedia Volume' in p.get('name', '')]
print(f"Encyclopedia volumes found: {len(enc_volumes)}")
for p in sorted(enc_volumes, key=lambda x: x['name']):
    print(f"  Vol {p['name'].split()[-1]:>2}: {p['name']} - {p['url']}")
