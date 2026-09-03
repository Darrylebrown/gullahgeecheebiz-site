#!/usr/bin/env python3
"""Full live-state snapshot: for each product - name, id, published, price, file size/name, covers count."""
import json, urllib.request, urllib.parse, time

TOKEN = None
for line in open('/Users/darrylsmac/gullahgeecheebiz-site/.env').read().splitlines():
    if line.startswith('GUMROAD_ACCESS_TOKEN='):
        TOKEN = line.split('=', 1)[1].strip().strip('"').strip("'")

def fetch(pid):
    url = f'https://api.gumroad.com/v2/products/{urllib.parse.quote(pid)}'
    req = urllib.request.Request(url, headers={'Authorization': 'Bearer ' + TOKEN})
    for a in range(4):
        try:
            with urllib.request.urlopen(req, timeout=40) as r:
                return json.loads(r.read().decode()).get('product', {})
        except Exception as e:
            if getattr(e, 'code', None) == 429:
                time.sleep(6 * (a + 1)); continue
            return {'error': str(e)}

# use saved full catalog for ids
products = json.load(open('/tmp/gumroad_full.json'))
out = []
for p in products:
    d = fetch(p['id'])
    if 'error' in d:
        out.append({'name': p['name'], 'id': p['id'], 'error': d['error']})
        continue
    files = d.get('files') or []
    finfo = []
    for f in files:
        finfo.append({'name': f.get('name') or f.get('original_name'), 'size': f.get('size'),
                      'url': (f.get('url') or '')[:90]})
    out.append({
        'name': p['name'], 'id': p['id'], 'published': d.get('published'),
        'price': d.get('price'), 'permalink': d.get('custom_permalink'),
        'url': d.get('short_url') or d.get('url'),
        'n_files': len(files), 'files': finfo,
        'n_covers': len(d.get('covers') or []),
    })
    time.sleep(0.3)

json.dump(out, open('/tmp/gumroad_state_detail.json', 'w'), indent=1)
print(f'saved {len(out)} products to /tmp/gumroad_state_detail.json')
for o in sorted(out, key=lambda x: x['name']):
    fs = ','.join(f"{f['name']}:{f['size']}" for f in o.get('files', [])) or 'NOFILE'
    print(f"{o['name'][:55]:55} | {'pub' if o['published'] else 'UNP':3} | ${(o['price'] or 0)/100:5.2f} | {o['n_covers']}cov | {fs[:80]}")
