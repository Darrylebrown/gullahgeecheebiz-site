#!/usr/bin/env python3
"""Attach a real EPUB to an existing Gumroad product via v2 presign flow (correct ETag handling).
Usage: attach_epub.py <product_id> <epub_path>
Verifies by re-GET: file count/size changes.
"""
import json, os, sys, time, urllib.request, urllib.parse, hashlib

BASE = '/Users/darrylsmac/gullahgeecheebiz-site'
TOKEN = None
for line in open(f'{BASE}/.env').read().splitlines():
    if line.startswith('GUMROAD_ACCESS_TOKEN='):
        TOKEN = line.split('=', 1)[1].strip().strip('"').strip("'")
API = 'https://api.gumroad.com/v2'

def http(method, url, data=None, headers=None):
    for a in range(5):
        try:
            if method == 'PUT':
                r = urllib.request.Request(url, data=data, method='PUT', headers=headers or {})
            else:
                r = urllib.request.Request(url, data=data, method=method, headers=headers or {})
            with urllib.request.urlopen(r, timeout=120) as resp:
                raw = resp.read()
                try: return resp.status, json.loads(raw.decode()), dict(resp.headers)
                except: return resp.status, raw, dict(resp.headers)
        except urllib.error.HTTPError as e:
            if e.code == 429:
                time.sleep(10 * (a + 1)); continue
            return e.code, e.read().decode()[:300], {}
        except Exception as e:
            return -1, str(e), {}
    return -1, 'max retries', {}

def get_product(pid):
    q = urllib.parse.urlencode({'access_token': TOKEN})
    req = urllib.request.Request(f'{API}/products/{urllib.parse.quote(pid)}?{q}',
                                 headers={'Authorization': 'Bearer ' + TOKEN})
    return json.loads(urllib.request.urlopen(req, timeout=60).read().decode()).get('product', {})

def attach(pid, epub_path):
    fsize = os.path.getsize(epub_path)
    fname = os.path.basename(epub_path)
    print(f'attaching {fname} ({fsize}B) to {pid[:12]}...')

    # 1. presign (with product_id)
    code, presign, h = http('POST', f'{API}/files/presign?access_token={urllib.parse.quote(TOKEN)}',
                            urllib.parse.urlencode({'product_id': pid, 'filename': fname,
                                                    'file_size': fsize,
                                                    'file_type': 'application/epub+zip'}).encode(),
                            {'Content-Type': 'application/x-www-form-urlencoded'})
    if not isinstance(presign, dict) or not presign.get('success'):
        print(f'presign FAILED {code}: {presign}'); return False
    parts = presign.get('parts') or []
    upid = presign.get('upload_id'); key = presign.get('key')
    if not parts or not upid or not key:
        print(f'presign missing data: keys={list(presign.keys())}'); return False
    print(f'presign OK ({len(parts)} part(s))')

    # 2. PUT part(s), capture real ETags
    etags = []
    for i, part in enumerate(parts):
        p_url = part['presigned_url']
        with open(epub_path, 'rb') as f:
            data = f.read() if len(parts) == 1 else f.read()
        code, resp, h2 = http('PUT', p_url, data, {'Content-Type': 'application/epub+zip'})
        if code not in (200, 204):
            print(f'PUT part {i+1} FAILED {code}: {str(resp)[:200]}'); return False
        etag = (h2.get('ETag') or h2.get('Etag') or '').strip('"')
        if not etag:
            print(f'NO ETag in PUT response headers: {list(h2.keys())}'); return False
        etags.append({'part_number': part.get('part_number', i + 1), 'etag': etag})
        print(f'  part {i+1} PUT {code}, etag={etag[:20]}...')

    # 3. complete with real etags
    body = json.dumps({'upload_id': upid, 'key': key, 'parts': etags})
    code, resp, h = http('POST', f'{API}/files/complete?access_token={urllib.parse.quote(TOKEN)}',
                         body.encode(), {'Content-Type': 'application/json'})
    if not isinstance(resp, dict) or not resp.get('success'):
        print(f'complete FAILED {code}: {str(resp)[:300]}'); return False
    print(f'complete OK: {str(resp)[:200]}')

    # 4. verify
    time.sleep(2)
    p = get_product(pid)
    files = p.get('files') or []
    print(f'VERIFY: {len(files)} file(s) now:')
    for f in files:
        print(f'   name={f.get("name")} size={f.get("size")} url={str(f.get("url"))[:70]}')
    return True

if __name__ == '__main__':
    pid = sys.argv[1]
    epub = sys.argv[2]
    ok = attach(pid, epub)
    sys.exit(0 if ok else 1)
