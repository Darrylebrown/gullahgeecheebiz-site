#!/usr/bin/env python3
"""Full detail dump for canonical products: files (with names), covers, price. Compare dup pairs 12-22."""
import json, urllib.request, time

products = json.load(open('/tmp/gumroad_full.json'))
TOKEN = None
for line in open('/Users/darrylsmac/gullahgeecheebiz-site/.env').read().splitlines():
    if line.startswith('GUMROAD_ACCESS_TOKEN='):
        TOKEN = line.split('=', 1)[1].strip().strip('"').strip("'")

def fetch(pid):
    url = f'https://api.gumroad.com/v2/products/{pid}'
    req = urllib.request.Request(url, headers={'Authorization': 'Bearer ' + TOKEN})
    for a in range(4):
        try:
            with urllib.request.urlopen(req, timeout=40) as r:
                return json.loads(r.read().decode()).get('product', {})
        except Exception as e:
            if getattr(e, 'code', None) == 429:
                time.sleep(6 * (a + 1)); continue
            return {'error': str(e)}

# vol -> list of (id, url)
from collections import defaultdict
byvol = defaultdict(list)
for p in products:
    n = p.get('name', '')
    if n.startswith('Encyclopedia Volume'):
        try: vol = int(n.split()[-1])
        except ValueError: continue
        byvol[vol].append(p)

# show detail for canonical (friendly permalink) vols 06-11, 31-34 + BOTH copies for 12-22 + singles 01-05,23-25
show_vols = list(range(1, 26)) + list(range(31, 35))
for vol in show_vols:
    for p in byvol[vol]:
        pid = p['id']
        d = fetch(pid)
        if 'error' in d:
            print(f"vol {vol:02d} {pid[:10]} ERR {d['error']}"); continue
        fi = d.get('file_info') or {}
        files = fi.get('files') if isinstance(fi, dict) else None
        if files is None:
            # file_info may be {name: {..}} or {'files': [...]} depending on API shape
            files = fi
        price = d.get('price')
        covers = d.get('covers') or []
        print(f"vol {vol:02d} | {pid} | ${price/100 if isinstance(price,int) else price} | pub={d.get('published')} | permalink={d.get('custom_permalink')}")
        print(f"    file_info keys: {list(fi.keys()) if isinstance(fi,dict) else fi}")
        print(f"    fi raw: {json.dumps(fi)[:500]}")
        print(f"    covers: {len(covers)} | main_cover_id={d.get('main_cover_id')} | thumb={str(d.get('thumbnail_url'))[:80]}")
    time.sleep(0.3)
