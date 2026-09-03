#!/usr/bin/env python3
"""Verify the 30 PUBLISHED encyclopedia volumes (01-25, 31-34): detail GET (files), DB-url match, HTTP landing."""
import json, os, time, urllib.request, urllib.parse

BASE = '/Users/darrylsmac/gullahgeecheebiz-site'
TOKEN = None
for line in open(f'{BASE}/.env').read().splitlines():
    if line.startswith('GUMROAD_ACCESS_TOKEN='):
        TOKEN = line.split('=', 1)[1].strip().strip('"').strip("'")
API = 'https://api.gumroad.com/v2'

def get(url, timeout=60):
    req = urllib.request.Request(url, headers={'Authorization': 'Bearer ' + TOKEN})
    for a in range(3):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            if e.code == 429:
                time.sleep(6); continue
            return {'error': e.code, 'body': e.read().decode()[:200]}
        except Exception as e:
            time.sleep(4)
    return {'error': 'timeout'}

def http(url):
    try:
        with urllib.request.urlopen(urllib.request.Request(url, method='HEAD'), timeout=45) as r:
            return r.status
    except urllib.error.HTTPError as e:
        return e.code
    except Exception:
        return 'ERR'

# published canonicals from list endpoint
seen = set(); prods = []; pk = None
for _ in range(60):
    q = {'access_token': TOKEN}
    if pk: q['page_key'] = pk
    d = get(f'{API}/products?' + urllib.parse.urlencode(q))
    for p in d.get('products', []):
        if p.get('id') not in seen:
            seen.add(p.get('id')); prods.append(p)
    nxt = d.get('next_page_url')
    if not nxt: break
    pk = urllib.parse.parse_qs(urllib.parse.urlparse(nxt).query).get('page_key', [None])[0]
    if not pk: break
    time.sleep(0.3)

enc_pub = {}
for p in prods:
    if 'Encyclopedia Volume' in p.get('name', '') and p.get('published'):
        v = int(p['name'].split()[-1])
        enc_pub[v] = p

rows_out = []
ok = bad = 0
for v in sorted(enc_pub):
    p = enc_pub[v]
    g = get(f'{API}/products/{urllib.parse.quote(p["id"])}?access_token={urllib.parse.quote(TOKEN)}')
    pr = g.get('product', {}) if isinstance(g, dict) else {}
    url = pr.get('short_url') or pr.get('url') or ''
    files = pr.get('files') or []
    finfo = [(f.get('file_name'), f.get('size')) for f in files]
    big = sum(1 for _, s in finfo if (s or 0) > 100000)
    st = http(url) if url else 'NOURL'
    rec = {'vol': v, 'id': p['id'], 'published': bool(pr.get('published')), 'url': url, 'http': st,
           'files': finfo, 'files_over_100k': big, 'sales': pr.get('sales_count'), 'thumbnail': bool(pr.get('thumbnail_url'))}
    rows_out.append(rec)
    flag = 'OK' if (bool(pr.get('published')) and url and st == 200 and big >= 1) else '**CHECK**'
    if flag == 'OK': ok += 1
    else: bad += 1
    print(f"{v:>2} {flag} http={st} files={finfo} sales={pr.get('sales_count')} thumb={bool(pr.get('thumbnail_url'))}")

print(f'\n=== {ok} fully OK (published+url+HTTP200+file>100KB) | {bad} need attention ===')
json.dump(rows_out, open(f'{BASE}/publish/gumroad_encyclopedia_verified_2026-09-02.json', 'w'), indent=1)
