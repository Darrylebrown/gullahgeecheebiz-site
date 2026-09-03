#!/usr/bin/env python3
"""PUBLISHING TANK OWNER - Gumroad catalog repair (run 2026-09-02).
Verified reality: 101 products. All Vols 01-25 & 31-34 EXIST with duplicates;
Vols 26-30 & 35-50 absent. Some published listings carry 2KB placeholder stubs
while the real 600KB book sits on an unpublished duplicate copy.

Plan per volume:
  - canonical = best copy (friendly permalink >> real file > pedia file > cover > $9.99)
  - ensure canonical is PUBLISHED, all other copies UNPUBLISHED (reversible)
Box Set / Site License / Heritage Vault: keep the copy that has a cover, unpublish rest.
"""
import json, os, time, urllib.request, urllib.parse, sys

BASE = '/Users/darrylsmac/gullahgeecheebiz-site'
EVENT_STREAM = f'{BASE}/publish/event_stream.jsonl'
TOKEN = None
for line in open(f'{BASE}/.env').read().splitlines():
    if line.startswith('GUMROAD_ACCESS_TOKEN='):
        TOKEN = line.split('=', 1)[1].strip().strip('"').strip("'")
API = 'https://api.gumroad.com/v2'

def log(m):
    print(m, flush=True)

def log_event(action, detail):
    ev = {'ts': time.strftime('%Y-%m-%dT%H:%M:%SZ'), 'source_bot': 'PUBLISHING_TANK_OWNER',
          'action': action, 'detail': detail}
    with open(EVENT_STREAM, 'a') as f:
        f.write(json.dumps(ev) + '\n')

def api_call(method, endpoint, data=None, retries=5):
    url = f'{API}{endpoint}'
    for attempt in range(retries):
        try:
            if method == 'GET':
                q = urllib.parse.urlencode({'access_token': TOKEN})
                req = urllib.request.Request(f'{url}?{q}', headers={'Authorization': 'Bearer ' + TOKEN})
            else:
                body = urllib.parse.urlencode(data or {}).encode()
                q = urllib.parse.urlencode({'access_token': TOKEN})
                req = urllib.request.Request(f'{url}?{q}', data=body, method=method,
                                             headers={'Authorization': 'Bearer ' + TOKEN})
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            if e.code == 429:
                time.sleep(10 * (attempt + 1)); continue
            return {'success': False, 'error': f'HTTP {e.code}: {e.read().decode()[:250]}'}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    return {'success': False, 'error': 'max retries'}

def get_product(pid):
    r = api_call('GET', f'/products/{urllib.parse.quote(pid)}')
    return r.get('product', {})

def set_published(pid, published):
    ep = '/enable' if published else '/disable'
    return api_call('PUT', f'/products/{urllib.parse.quote(pid)}{ep}', {})

def file_size(p):
    files = p.get('files') or []
    return max((f.get('size') or 0) for f in files) if files else 0

def score(p):
    """Higher = better canonical. Friendly permalink copies are the promoted URLs."""
    s = 0
    perm = (p.get('custom_permalink') or '').lower()
    if perm.startswith('encyclopedia-volume'):
        s += 200                      # promoted canonical URL — must stay live
    fs = file_size(p)
    if fs >= 100000:
        s += 80                       # real full book
    elif fs >= 6000:
        s += 40                       # pedia 5-chapter epub
    else:
        s += 0                        # 2KB placeholder stub
    if p.get('covers'):
        s += 10
    if p.get('price') == 999:
        s += 5
    if p.get('published'):
        s += 3
    return s

def main():
    state = json.load(open('/tmp/gumroad_state_detail.json'))
    products = {}
    for o in state:
        products.setdefault(o['name'], []).append(o)
    # refresh with fresh published flags & files
    fresh = []
    for o in state:
        d = get_product(o['id'])
        if d and 'error' not in d:
            o['published'] = d.get('published')
            o['covers'] = d.get('covers') or []
            o['price'] = d.get('price')
            o['permalink'] = d.get('custom_permalink')
            o['custom_permalink'] = d.get('custom_permalink')
            o['files'] = d.get('files') or []
        fresh.append(o)
        time.sleep(0.25)

    log(f'Total products refreshed: {len(fresh)}')
    byname = {}
    for o in fresh:
        byname.setdefault(o['name'], []).append(o)

    plan = []   # (name, canonical_id, [dupe_ids])
    for name, plist in sorted(byname.items()):
        if len(plist) <= 1:
            continue
        plist_sorted = sorted(plist, key=score, reverse=True)
        canon = plist_sorted[0]
        dupes = plist_sorted[1:]
        plan.append((name, canon, dupes))

    log(f'\n=== Cleanup plan: {len(plan)} duplicated product names ===')
    to_unpublish = []
    to_publish = []
    for name, canon, dupes in plan:
        fs_c = file_size(canon)
        log(f'{name}: keep {canon["id"][:12]} (pub={canon["published"]}, {fs_c}B, perm={canon.get("permalink")}) '
            f'+ unpublish {len(dupes)} dupes')
        if not canon['published']:
            to_publish.append(canon['id'])
        for d in dupes:
            if d['published']:
                to_unpublish.append(d['id'])

    log(f'\n=== Phase A: publish canonical copies ({len(to_publish)}) ===')
    for pid in to_publish:
        r = set_published(pid, True)
        ok = r.get('success')
        log(f'  {"OK " if ok else "FAIL"} publish {pid}')
        time.sleep(0.6)
        if not ok:
            log(f'      {r}')

    log(f'\n=== Phase B: unpublish duplicate copies ({len(to_unpublish)}) ===')
    ok_count = 0
    for pid in to_unpublish:
        r = set_published(pid, False)
        ok = r.get('success')
        if ok:
            ok_count += 1
        log(f'  {"OK " if ok else "FAIL"} unpublish {pid}')
        time.sleep(0.6)
        if not ok:
            log(f'      {r}')

    log(f'\nPublished canonicals: {len(to_publish)}, Unpublished dupes: {ok_count}/{len(to_unpublish)}')

    # persist + events
    summary = {
        'ts': time.strftime('%Y-%m-%dT%H:%M:%SZ'),
        'published_canonicals': to_publish,
        'unpublished_dupes_ok': ok_count,
        'unpublished_dupes_total': len(to_unpublish),
    }
    json.dump(summary, open(f'{BASE}/publish/repair_2026-09-02.json', 'w'), indent=2)
    log_event('gumroad_cleanup', f'published {len(to_publish)} canonicals, unpublished {ok_count}/{len(to_unpublish)} duplicates')
    log('Done.')

if __name__ == '__main__':
    main()
