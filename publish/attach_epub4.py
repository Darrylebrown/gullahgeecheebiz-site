#!/usr/bin/env python3
"""Proven v2 flow per official docs:
presign -> PUT S3 (no auth) -> files/complete -> PUT /products/{id} with files[][url]=FILE_URL
"""
import json, os, sys, time, urllib.request, urllib.parse

BASE = '/Users/darrylsmac/gullahgeecheebiz-site'
TOKEN = None
for line in open(f'{BASE}/.env').read().splitlines():
    if line.startswith('GUMROAD_ACCESS_TOKEN='):
        TOKEN = line.split('=', 1)[1].strip().strip('"').strip("'")
API = 'https://api.gumroad.com/v2'

def api_req(method, url, data=None, headers=None):
    hdrs = {'Authorization': 'Bearer ' + TOKEN}
    if headers: hdrs.update(headers)
    r = urllib.request.Request(url, data=data, method=method, headers=hdrs)
    try:
        resp = urllib.request.urlopen(r, timeout=180)
        raw = resp.read()
        try: return resp.status, json.loads(raw.decode())
        except: return resp.status, raw
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()[:500]
    except Exception as e:
        return -1, str(e)

def s3_put(url, content):
    r = urllib.request.Request(url, data=content, method='PUT',
                               headers={'Content-Type': 'application/epub+zip'})
    try:
        resp = urllib.request.urlopen(r, timeout=180)
        return resp.status, dict(resp.headers)
    except urllib.error.HTTPError as e:
        return e.code, {}
    except Exception as e:
        return -1, {}

def attach(pid, epub_path):
    fsize = os.path.getsize(epub_path)
    fname = os.path.basename(epub_path)
    # 1. presign (NO product_id needed per docs; file_url must start with seller prefix)
    st, pr = api_req('POST', f'{API}/files/presign?access_token={urllib.parse.quote(TOKEN)}',
                     urllib.parse.urlencode({'filename': fname, 'file_size': fsize}).encode(),
                     {'Content-Type': 'application/x-www-form-urlencoded'})
    if not (isinstance(pr, dict) and pr.get('success')):
        print(f'presign FAIL {st}: {str(pr)[:300]}'); return False
    parts = pr.get('parts') or []
    upid = pr.get('upload_id'); key = pr.get('key')
    with open(epub_path, 'rb') as f:
        content = f.read()
    etags = []
    for i, part in enumerate(parts):
        p_url = part.get('presigned_url') or part.get('url')
        st, h2 = s3_put(p_url, content)
        if st not in (200, 204):
            print(f'PUT part {i+1} FAIL {st}'); return False
        etag = (h2.get('ETag') or '').strip('"')
        etags.append({'part_number': part.get('part_number', i+1), 'etag': etag})
        print(f'PUT part {i+1}: {st}')
    # 2. complete
    body = json.dumps({'upload_id': upid, 'key': key, 'parts': etags})
    st, comp = api_req('POST', f'{API}/files/complete?access_token={urllib.parse.quote(TOKEN)}',
                       body.encode(), {'Content-Type': 'application/json'})
    if not (isinstance(comp, dict) and comp.get('success')):
        print(f'complete FAIL {st}: {str(comp)[:300]}'); return False
    final_url = comp.get('file_url') or pr.get('file_url')
    print(f'file_url: {final_url[:100]}')
    # 3. ATTACH via PUT with files[][url] (full replacement of the stub)
    params = urllib.parse.urlencode({'access_token': TOKEN, 'files[][url]': final_url})
    st, att = api_req('PUT', f'{API}/products/{urllib.parse.quote(pid)}?{params}')
    print(f'attach PUT: {st} {str(att)[:300]}')
    time.sleep(2)
    q = urllib.parse.urlencode({'access_token': TOKEN})
    st, p = api_req('GET', f'{API}/products/{urllib.parse.quote(pid)}?{q}')
    files = (p.get('product') or {}).get('files') or []
    print('VERIFY files:', [f.get('size') for f in files])
    return True

if __name__ == '__main__':
    pid, epub = sys.argv[1], sys.argv[2]
    print(f'=== {os.path.basename(epub)} -> {pid[:12]} ===')
    attach(pid, epub)
