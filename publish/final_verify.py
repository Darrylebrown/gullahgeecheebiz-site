#!/usr/bin/env python3
"""Final verification: full paginated audit + HTTP 200 landing checks on every published encyclopedia product."""
import json, urllib.request, urllib.parse, time

TOKEN = None
for line in open('/Users/darrylsmac/gullahgeecheebiz-site/.env').read().splitlines():
    if line.startswith('GUMROAD_ACCESS_TOKEN='):
        TOKEN = line.split('=', 1)[1].strip().strip('"').strip("'")

def fetch(url):
    req = urllib.request.Request(url, headers={'Authorization': 'Bearer ' + TOKEN})
    for a in range(4):
        try:
            with urllib.request.urlopen(req, timeout=40) as r:
                return json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            if e.code == 429: time.sleep(6*(a+1)); continue
            raise
    raise RuntimeError('max retries')

products = []
url = 'https://api.gumroad.com/v2/products?limit=100'
while url:
    d = fetch(url)
    products.extend(d.get('products', []))
    url = d.get('next_page_url')
    if url and url.startswith('/'):
        url = 'https://api.gumroad.com' + url

print(f'TOTAL: {len(products)}')
enc = [p for p in products if p.get('name', '').startswith('Encyclopedia Volume')]
from collections import Counter
names = Counter(p['name'] for p in enc)
dupes = {n: c for n, c in names.items() if c > 1}
print(f'Encyclopedia products: {len(enc)}, unique volumes: {len(names)}, duplicated names remaining: {len(dupes)}')
if dupes: print('  DUPES:', dupes)

published = [p for p in enc if p.get('published')]
unpub = [p for p in enc if not p.get('published')]
print(f'Published encyclopedia products: {len(published)}')
print(f'Unpublished (archived dupes): {len(unpub)}')
for p in sorted(unpub, key=lambda x: x['name']):
    print(f'  UNPUBLISHED {p["name"]}')

# per-volume canonical state
byvol = {}
for p in enc:
    try: v = int(p['name'].split()[-1])
    except: continue
    byvol.setdefault(v, []).append(p)

print('\n=== Canonical per volume (published copy) ===')
bad = []
live_urls = []
for v in sorted(byvol):
    pl = byvol[v]
    pub_copies = [p for p in pl if p.get('published')]
    if len(pub_copies) != 1:
        bad.append((v, 'published copies != 1', len(pub_copies)))
        print(f'vol {v:02d}: *** {len(pub_copies)} published copies ***')
        continue
    p = pub_copies[0]
    fi = p.get('file_info') or {}
    sz = fi.get('Size')
    url = p.get('short_url') or p.get('url')
    live_urls.append(url)
    flag = 'STUB!' if (isinstance(sz, str) and 'KB' in sz and float(sz.split()[0]) < 5) else 'ok'
    print(f'vol {v:02d}: {url} | file={sz} | {flag}')

print('\n=== HTTP 200 landing checks (published volumes) ===')
ok200 = 0
for u in live_urls:
    try:
        r = urllib.request.urlopen(urllib.request.Request(u, method='HEAD'), timeout=20)
        if r.status == 200: ok200 += 1
        else: print(f'  NON-200 {r.status} {u}')
    except Exception as e:
        print(f'  ERR {u}: {getattr(e, "code", e)}')
    time.sleep(0.2)
print(f'HTTP 200 landings: {ok200}/{len(live_urls)}')

json.dump({'total': len(products), 'published_enc': len(published), 'unpublished_dupes': len(unpub),
           'http200': ok200, 'issues': [str(x) for x in bad]},
          open('/tmp/final_verify.json', 'w'), indent=1)
print('\nsaved /tmp/final_verify.json')
