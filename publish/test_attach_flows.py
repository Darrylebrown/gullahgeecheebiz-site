#!/usr/bin/env python3
"""Test attach flows on vol10 canonical (77jOb-mKWR...): needs real epub + cover.
Tests: (1) cover via POST /products/{id}/asset?type=cover, (2) epub via v2 presign flow.
"""
import json, os, time, urllib.request, urllib.parse, hashlib, zipfile, io

BASE = '/Users/darrylsmac/gullahgeecheebiz-site'
TOKEN = None
for line in open(f'{BASE}/.env').read().splitlines():
    if line.startswith('GUMROAD_ACCESS_TOKEN='):
        TOKEN = line.split('=', 1)[1].strip().strip('"').strip("'")

API = 'https://api.gumroad.com/v2'
PID = '77jOb-mKWRCY2c9Z6P6krw=='   # vol 10 canonical
COVER = f'{BASE}/publish/landing-pad/encyclopedia-vol-10/cover.jpg'
EPUB = f'{BASE}/publish/for-distribution/google-play/pedia-vol-10.epub'

def log(m): print(m, flush=True)

def http(method, url, data=None, files=None, headers=None, retries=4):
    for a in range(retries):
        try:
            if method == 'GET':
                r = urllib.request.Request(url, headers=headers or {})
            elif method == 'PUT':
                r = urllib.request.Request(url, data=data, method='PUT', headers=headers or {})
            else:
                r = urllib.request.Request(url, data=data, method=method, headers=headers or {})
            with urllib.request.urlopen(r, timeout=90) as resp:
                raw = resp.read()
                try: return resp.status, json.loads(raw.decode())
                except: return resp.status, raw
        except urllib.error.HTTPError as e:
            if e.code == 429:
                time.sleep(8 * (a + 1)); continue
            return e.code, e.read().decode()[:400]
        except Exception as e:
            return -1, str(e)
    return -1, 'max retries'

# --- TEST 1: cover via asset endpoint ---
log('=== TEST 1: cover via /products/{id}/asset?type=cover ===')
with open(COVER, 'rb') as f:
    content = f.read()
boundary = '----ggbtest' + hashlib.md5(str(time.time()).encode()).hexdigest()
parts = []
parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="cover"; filename="cover.jpg"\r\nContent-Type: image/jpeg\r\n\r\n'.encode() + content + b'\r\n')
parts.append(f'--{boundary}--\r\n'.encode())
body = b''.join(parts)
q = urllib.parse.urlencode({'access_token': TOKEN, 'type': 'cover'})
code, resp = http('POST', f'{API}/products/{urllib.parse.quote(PID)}/asset?{q}', body,
                  headers={'Content-Type': f'multipart/form-data; boundary={boundary}'})
log(f'asset endpoint -> {code}: {str(resp)[:300]}')

# verify cover
code2, p = http('GET', f'{API}/products/{urllib.parse.quote(PID)}?access_token={urllib.parse.quote(TOKEN)}')
prod = p.get('product', {}) if isinstance(p, dict) else {}
log(f'after asset: covers={len(prod.get("covers") or [])} main_cover={prod.get("main_cover_id")}')

# --- TEST 2: epub via v2 presign (files/presign w/ product_id) ---
log('\n=== TEST 2: epub via v2 presign ===')
fsize = os.path.getsize(EPUB)
code, presign = http('POST', f'{API}/files/presign?access_token={urllib.parse.quote(TOKEN)}',
                     urllib.parse.urlencode({
                         'product_id': PID, 'filename': os.path.basename(EPUB),
                         'file_size': fsize, 'file_type': 'application/epub+zip'}).encode())
log(f'presign -> {code}: {str(presign)[:400]}')
if isinstance(presign, dict) and presign.get('success'):
    parts_l = presign.get('parts') or []
    upid = presign.get('upload_id')
    key = presign.get('key')
    if parts_l and upid and key:
        p_url = parts_l[0]['presigned_url']
        with open(EPUB, 'rb') as f:
            epub_data = f.read()
        code3, resp3 = http('PUT', p_url, epub_data, headers={'Content-Type': 'application/epub+zip'})
        log(f'PUT -> {code3}')
        if code3 in (200, 204):
            etag = resp3 if isinstance(resp3, bytes) else b''
            code4, resp4 = http('POST', f'{API}/files/complete?access_token={urllib.parse.quote(TOKEN)}',
                                json.dumps({'upload_id': upid, 'key': key,
                                            'parts': [{'part_number': 1, 'etag': 'etag-placeholder'}]}).encode(),
                                headers={'Content-Type': 'application/json'})
            log(f'complete -> {code4}: {str(resp4)[:300]}')
    else:
        log(f'presign missing parts/upload_id/key: {list(presign.keys())}')
else:
    log(f'presign failed: {presign}')

time.sleep(1)
code5, p5 = http('GET', f'{API}/products/{urllib.parse.quote(PID)}?access_token={urllib.parse.quote(TOKEN)}')
prod5 = p5.get('product', {}) if isinstance(p5, dict) else {}
files = prod5.get('files') or []
log(f'after epub flow: {len(files)} files')
for f in files:
    log(f'   file: size={f.get("size")} url={str(f.get("url"))[:80]}')
