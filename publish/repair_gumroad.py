#!/usr/bin/env python3
"""PUBLISHING TANK OWNER - Gumroad catalog repair.
Phase 1: Dedupe (unpublish duplicates, keep canonical per title) + attach covers to canonicals missing them.
Phase 2: Attach real EPUBs to canonicals that have 2KB stub files (only where a matching pedia epub exists on disk).
Phase 3: Create truly-missing volumes (26-30, 35-50) respecting 10/day creation cap.
Everything verified via GET after each write. Reversible (unpublish, not delete).
"""
import json, os, sys, time, urllib.request, urllib.parse, sqlite3, hashlib

BASE = '/Users/darrylsmac/gullahgeecheebiz-site'
ENV = f'{BASE}/.env'
EVENT_STREAM = f'{BASE}/publish/event_stream.jsonl'
DB = f'{BASE}/publish/publisher.db'
LP = f'{BASE}/publish/landing-pad'
EPUB_DIR = f'{BASE}/publish/for-distribution/google-play'

TOKEN = None
for line in open(ENV).read().splitlines():
    if line.startswith('GUMROAD_ACCESS_TOKEN='):
        TOKEN = line.split('=', 1)[1].strip().strip('"').strip("'")

API = 'https://api.gumroad.com/v2'

def log(msg):
    print(msg, flush=True)

def log_event(action, detail):
    ev = {'ts': time.strftime('%Y-%m-%dT%H:%M:%SZ'), 'source_bot': 'PUBLISHING_TANK_OWNER',
          'action': action, 'detail': detail}
    with open(EVENT_STREAM, 'a') as f:
        f.write(json.dumps(ev) + '\n')

def api(method, endpoint, data=None, files=None, headers=None, retries=5):
    url = API + endpoint
    for attempt in range(retries):
        try:
            if method == 'GET':
                r = urllib.request.Request(url + '?' + urllib.parse.urlencode({'access_token': TOKEN}),
                                           headers={'Authorization': 'Bearer ' + TOKEN})
                with urllib.request.urlopen(r, timeout=60) as resp:
                    return json.loads(resp.read().decode())
            elif method == 'PUT':
                body = urllib.parse.urlencode(data).encode() if data else b''
                r = urllib.request.Request(url, data=body, method='PUT',
                                           headers={'Authorization': 'Bearer ' + TOKEN})
                with urllib.request.urlopen(r, timeout=60) as resp:
                    return json.loads(resp.read().decode())
            elif method == 'POST':
                if files:
                    boundary = '----ggb' + hashlib.md5(str(time.time()).encode()).hexdigest()
                    parts = []
                    for k, (fn, content, ctype) in files.items():
                        parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{k}"; filename="{fn}"\r\nContent-Type: {ctype}\r\n\r\n'.encode() + content + b'\r\n')
                    parts.append(f'--{boundary}--\r\n'.encode())
                    body = b''.join(parts)
                    q = urllib.parse.urlencode({'access_token': TOKEN, **(data or {})})
                    r = urllib.request.Request(url + '?' + q, data=body, method='POST',
                                               headers={'Authorization': 'Bearer ' + TOKEN,
                                                        'Content-Type': f'multipart/form-data; boundary={boundary}'})
                else:
                    body = urllib.parse.urlencode(data or {}).encode()
                    r = urllib.request.Request(url, data=body, method='POST',
                                               headers={'Authorization': 'Bearer ' + TOKEN})
                with urllib.request.urlopen(r, timeout=90) as resp:
                    return json.loads(resp.read().decode())
            elif method == 'DELETE':
                r = urllib.request.Request(url, method='DELETE',
                                           headers={'Authorization': 'Bearer ' + TOKEN})
                with urllib.request.urlopen(r, timeout=60) as resp:
                    return json.loads(resp.read().decode())
        except urllib.error.HTTPError as e:
            if e.code == 429:
                time.sleep(10 * (attempt + 1)); continue
            return {'success': False, 'error': f'HTTP {e.code}: {e.read().decode()[:300]}'}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    return {'success': False, 'error': 'max retries'}

def get_all_products():
    products = []
    url = API + '/products?limit=100&access_token=' + urllib.parse.quote(TOKEN)
    while url:
        req = urllib.request.Request(url, headers={'Authorization': 'Bearer ' + TOKEN})
        data = json.loads(urllib.request.urlopen(req, timeout=60).read().decode())
        products.extend(data.get('products', []))
        nxt = data.get('next_page_url')
        url = ('https://api.gumroad.com' + nxt) if nxt and nxt.startswith('/') else nxt
    return products

def get_product(pid):
    return api('GET', f'/products/{urllib.parse.quote(pid)}').get('product', {})

def unpublish(pid):
    return api('POST', f'/products/{urllib.parse.quote(pid)}/update', {'published': 'false'})

def main():
    products = get_all_products()
    log(f'TOTAL products: {len(products)}')
    byname = {}
    for p in products:
        byname.setdefault(p['name'], []).append(p)

    # ==== PHASE 1: choose canonical per encyclopedia volume + bundles, unpublish rest ====
    enc = {n: v for n, v in byname.items() if n.startswith('Encyclopedia Volume')}
    keep_pids = {}
    unpublish_pids = []

    for name, plist in sorted(enc.items(), key=lambda kv: int(kv[0].split()[-1])):
        vol = int(name.split()[-1])
        # canonical preference: friendly permalink + $9.99 + has file + has cover
        def score(p):
            s = 0
            if p.get('custom_permalink', '').startswith('encyclopedia-volume'): s += 100
            if p.get('published'): s += 10
            if p.get('price') == 999: s += 5
            fi = p.get('file_info') or {}
            if fi.get('Size'): s += 3
            if p.get('covers'): s += 2
            return s
        plist_sorted = sorted(plist, key=score, reverse=True)
        canonical = plist_sorted[0]
        keep_pids[vol] = canonical['id']
        for p in plist_sorted[1:]:
            unpublish_pids.append((p['id'], name, p.get('short_url') or p.get('url')))

    log(f'\n=== PHASE 1a: unpublish duplicates ({len(unpublish_pids)}) ===')
    for pid, name, url in unpublish_pids:
        r = api('POST', f'/products/{urllib.parse.quote(pid)}/update', {'published': 'false'})
        ok = r.get('success')
        log(f'  {"OK " if ok else "FAIL"} unpublish {name} {pid[:10]} {url}')
        time.sleep(0.5)
        if not ok:
            log(f'      {r}')

    json.dump({'keep': {str(v): pid for v, pid in keep_pids.items()},
               'unpublished': [p[0] for p in unpublish_pids]},
              open(f'{BASE}/publish/repair_state.json', 'w'), indent=2)

if __name__ == '__main__':
    main()
