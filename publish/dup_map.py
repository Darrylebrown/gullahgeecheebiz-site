#!/usr/bin/env python3
"""Pick canonical encyclopedia product per volume from full catalog snapshot; show details."""
import json, urllib.request, time

products = json.load(open('/tmp/gumroad_full.json'))
TOKEN = None
for line in open('/Users/darrylsmac/gullahgeecheebiz-site/.env').read().splitlines():
    if line.startswith('GUMROAD_ACCESS_TOKEN='):
        TOKEN = line.split('=', 1)[1].strip().strip('"').strip("'")

enc = [p for p in products if p.get('name', '').startswith('Encyclopedia Volume')]
print(f"Encyclopedia products total: {len(enc)}")

from collections import defaultdict
byvol = defaultdict(list)
for p in enc:
    try:
        vol = int(p['name'].split()[-1])
    except ValueError:
        continue
    byvol[vol].append(p)

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

for vol in sorted(byvol):
    plist = byvol[vol]
    if len(plist) == 1:
        print(f"vol {vol:02d}: single — {plist[0]['id']} | {plist[0].get('short_url')}")
        continue
    print(f"vol {vol:02d}: {len(plist)} copies")
    for p in plist:
        print(f"    {p['id']} | pub={p.get('published')} | url={p.get('short_url') or p.get('url')}")
