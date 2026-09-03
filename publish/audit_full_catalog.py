#!/usr/bin/env python3
"""Full paginated Gumroad catalog audit + per-product file/cover state."""
import json, urllib.request, urllib.parse, time

TOKEN = None
for line in open('/Users/darrylsmac/gullahgeecheebiz-site/.env').read().splitlines():
    if line.startswith('GUMROAD_ACCESS_TOKEN='):
        TOKEN = line.split('=', 1)[1].strip().strip('"').strip("'")
        break

def fetch(url):
    req = urllib.request.Request(url, headers={'Authorization': 'Bearer ' + TOKEN})
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=40) as resp:
                return json.loads(resp.read().decode())
        except Exception as e:
            if getattr(e, 'code', None) == 429:
                time.sleep(8 * (attempt + 1))
                continue
            raise

products = []
url = 'https://api.gumroad.com/v2/products?limit=100'
while url:
    data = fetch(url)
    products.extend(data.get('products', []))
    url = data.get('next_page_url')
    if url and url.startswith('/'):
        url = 'https://api.gumroad.com' + url

print(f"TOTAL products (all pages): {len(products)}")
by_name = {}
for p in products:
    n = p.get('name', '')
    by_name.setdefault(n, []).append(p)

enc = {k: v for k, v in sorted(by_name.items()) if 'encyclopedia' in k.lower() or 'pedia-vol' in k.lower() or 'box set' in k.lower() or 'site license' in k.lower() or 'heritage vault' in k.lower()}
print(f"\n=== Encyclopedia-ish product names ({len(enc)} unique names, {sum(len(v) for v in enc.values())} products) ===")
for name, plist in enc.items():
    for p in plist:
        files = p.get('file_info', {})
        nfiles = len(files) if isinstance(files, dict) else 0
        print(f"  {name} | id={p['id'][:10]} | pub={p.get('published')} | files={nfiles} | sales={p.get('sales_count')} | {p.get('short_url') or p.get('url')}")

print(f"\n=== Other products ===")
for name, plist in sorted(by_name.items()):
    if name in enc: continue
    for p in plist:
        print(f"  {name} | id={p['id'][:10]} | pub={p.get('published')} | sales={p.get('sales_count')} | {p.get('short_url') or p.get('url')}")
