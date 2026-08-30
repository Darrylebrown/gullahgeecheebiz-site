#!/usr/bin/env python3
"""Verify actual Gumroad products and check for missing uploads."""
import json
import os
import sys
import sqlite3
import hashlib
import shutil
import urllib.request
import urllib.error

TOKEN = os.getenv('GUMROAD_ACCESS_TOKEN') or open('/Users/darrylsmac/gullahgeecheebiz-site/.env').read()
for line in TOKEN.splitlines():
    if line.startswith('GUMROAD_ACCESS_TOKEN='):
        token = line.split('=', 1)[1].strip()
        break
else:
    print("ERROR: No GUMROAD_ACCESS_TOKEN found"); sys.exit(1)

# Fetch actual Gumroad products
req = urllib.request.Request(
    'https://api.gumroad.com/v2/products',
    headers={'Authorization': f'Bearer {token}'}
)
resp = urllib.request.urlopen(req)
data = json.loads(resp.read().decode())
products = data.get('products', [])
print(f"Total live Gumroad products: {len(products)}")

# Build set of live product IDs and titles
live_ids = {p['id'] for p in products}
live_titles = {p['name'] for p in products}
print(f"\nLive product IDs: {sorted(live_ids)}")
print(f"\nAll live product names:")
for p in sorted(products, key=lambda x: x['name']):
    print(f"  {p['id']} | {p['name']} | {p.get('published_at','N/A')}")

# Check DB for Encyclopedia Volume entries
conn = sqlite3.connect('/Users/darrylsmac/gullahgeecheebiz-site/publish/publisher.db')
db_entries = conn.execute("""
    SELECT id, title FROM manifests 
    WHERE json_extract(data, '$.title') LIKE 'Encyclopedia Volume %'
    GROUP BY json_extract(data, '$.title')
""").fetchall()
print(f"\nDB Encyclopedia Volume entries: {len(db_entries)} unique titles")

# Check for duplicates
dup_check = conn.execute("""
    SELECT json_extract(data, '$.title') as title, COUNT(*) as cnt
    FROM manifests 
    WHERE json_extract(data, '$.title') LIKE 'Encyclopedia Volume %'
    GROUP BY json_extract(data, '$.title')
    HAVING cnt > 1
""").fetchall()
print(f"Duplicate titles in DB: {len(dup_check)}")
for t, c in dup_check:
    print(f"  {t}: {c} entries")

# Check which volumes have landing-pad dirs
import glob
landing_dirs = glob.glob('/Users/darrylsmac/gullahgeecheebiz-site/publish/landing-pad/encyclopedia-vol-*')
print(f"\nLanding pad dirs found: {len(landing_dirs)}")
for d in sorted(landing_dirs):
    print(f"  {d}")
    # Check for cover.jpg and epubs
    cover = os.path.join(d, 'cover.jpg')
    epub = os.path.join(d, '*.epub')
    print(f"    cover.jpg exists: {os.path.exists(cover)}")

# Check for epub files in landing-pad
epub_files = []
for root, dirs, files in os.walk('/Users/darrylsmac/gullahgeecheebiz-site/publish/landing-pad'):
    for f in files:
        if f.endswith('.epub'):
            epub_files.append(os.path.join(root, f))
print(f"\nEPUBs in landing-pad: {len(epub_files)}")
for e in sorted(epub_files)[:20]:
    print(f"  {e}")

# Also check for-distribution for encyclopedia EPUBs
dist_epubs = glob.glob('/Users/darrylsmac/gullahgeecheebiz-site/publish/for-distribution/google-play/pedia-vol-*.epub')
print(f"\nPedia-vol EPUBs in for-distribution: {len(dist_epubs)}")
for e in sorted(dist_epubs)[:30]:
    print(f"  {os.path.basename(e)}")

conn.close()
