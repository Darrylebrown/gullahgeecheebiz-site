#!/usr/bin/env python3
"""Verify every encyclopedia volume's LIVE Gumroad state: published flag, URL, HTTP landing, attached files.
Checks canonical presence + duplicate published products per volume."""
import json, os, sys, time, sqlite3, urllib.request, urllib.parse

BASE = '/Users/darrylsmac/gullahgeecheebiz-site'
TOKEN = None
for line in open(f'{BASE}/.env').read().splitlines():
    if line.startswith('GUMROAD_ACCESS_TOKEN='):
        TOKEN = line.split('=', 1)[1].strip().strip('"').strip("'")
API = 'https://api.gumroad.com/v2'

def api_get(path):
    url = f'{API}{path}&access_token={urllib.parse.quote(TOKEN)}'
    req = urllib.request.Request(url, headers={'Authorization': 'Bearer ' + TOKEN})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            raw = e.read().decode()[:200]
            if e.code == 429:
                time.sleep(5); continue
            return {'error': e.code, 'body': raw}
        except Exception as e:
            time.sleep(5)
    return {'error': 'timeout'}

def http_status(url):
    try:
        req = urllib.request.Request(url, method='HEAD')
        with urllib.request.urlopen(req, timeout=45) as r:
            return r.status
    except urllib.error.HTTPError as e:
        return e.code
    except Exception as e:
        return f'ERR'

# 1) enumerate all products w/ cursor pagination
seen = set(); prods = []
page_key = None
for _ in range(60):
    q = {'access_token': TOKEN}
    if page_key:
        q['page_key'] = page_key
    url = f'{API}/products?' + urllib.parse.urlencode(q)
    try:
        with urllib.request.urlopen(url, timeout=60) as r:
            d = json.loads(r.read().decode())
    except Exception as e:
        print('LIST ERR', e); break
    for p in d.get('products', []):
        if p.get('id') not in seen:
            seen.add(p.get('id')); prods.append(p)
    nxt = d.get('next_page_url')
    if not nxt: break
    page_key = urllib.parse.parse_qs(urllib.parse.urlparse(nxt).query).get('page_key', [None])[0]
    if not page_key: break
    time.sleep(0.35)

enc = {}
for p in prods:
    name = p.get('name', '')
    if 'Encyclopedia Volume' in name:
        try: v = int(name.split()[-1])
        except ValueError: continue
        enc.setdefault(v, []).append(p)

# canonical URLs from DB (for HTTP landing check on the recorded store URL)
conn = sqlite3.connect(f'{BASE}/publish/publisher.db')
rows = conn.execute("SELECT data FROM manifests WHERE data LIKE '%Encyclopedia Volume%'").fetchall()
db_urls = {}
for (data,) in rows:
    jd = json.loads(data)
    t = jd.get('title', '')
    if 'Volume' not in t: continue
    import re
    m = re.search(r'Volume (\d+)', t)
    if not m: continue
    v = int(m.group(1))
    if jd.get('gumroad_url'): db_urls.setdefault(v, set()).add(jd['gumroad_url'])

print(f"{'vol':>3} {'n':>2} {'pub':>3} {'files_ok':>8} {'live_urls':>20} statuses")
summary = {'live_published': 0, 'vols_with_dupes': 0, 'missing': []}
for v in sorted(enc):
    plist = enc[v]
    detailed = []
    for p in plist:
        g = api_get(f'/products/{urllib.parse.quote(p["id"])}')
        prod = g.get('product', {}) if isinstance(g, dict) else {}
        pub = bool(prod.get('published'))
        url = prod.get('short_url') or prod.get('url') or ''
        files = prod.get('files') or []
        big = sum(1 for f in files if (f.get('size') or 0) > 100000)
        fnames = [f.get('file_name', '') for f in files][:3]
        detailed.append({'id': p['id'], 'pub': pub, 'url': url, 'nfiles': len(files), 'big': big, 'fnames': fnames})
    pubs = [d for d in detailed if d['pub']]
    statuses = []
    for d in pubs:
        st = http_status(d['url']) if d['url'] else 'NOURL'
        statuses.append(f"{st}:{d['url'].split('/')[-1]}")
        d['http'] = st
    print(f"{v:>3} {len(plist):>2} {len(pubs):>3} {sum(d['big']>0 for d in pubs):>8} {'; '.join(u.split('/')[-1] for u in db_urls.get(v, []))[:40]:>20} {' '.join(statuses)}")
    if len(pubs) > 1:
        summary['vols_with_dupes'] += 1
    if pubs:
        summary['live_published'] += 1
# volumes DB says published but absent from live account entirely
db_vols = set(db_urls.keys())
live_vols = set(enc.keys())
summary['missing_from_account'] = sorted(db_vols - live_vols)
print('\nSUMMARY:', json.dumps(summary))
json.dump({str(v): [{'id': d['id'], 'pub': d['pub'], 'url': d['url'], 'nfiles': d['nfiles'], 'big': d['big'], 'fnames': d['fnames'], 'http': d.get('http')} for d in enc[v]] for v in sorted(enc)},
          open(f'{BASE}/publish/gumroad_encyclopedia_verified_2026-09-02.json', 'w'), indent=1)
print('wrote gumroad_encyclopedia_verified_2026-09-02.json')
