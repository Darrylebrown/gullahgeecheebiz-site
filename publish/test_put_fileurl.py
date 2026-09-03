#!/usr/bin/env python3
"""Test: PUT /products/{id} with file_url (v9 script style attach)."""
import json, os, sys, time, urllib.request, urllib.parse

BASE = '/Users/darrylsmac/gullahgeecheebiz-site'
TOKEN = None
for line in open(f'{BASE}/.env').read().splitlines():
    if line.startswith('GUMROAD_ACCESS_TOKEN='):
        TOKEN = line.split('=', 1)[1].strip().strip('"').strip("'")
API = 'https://api.gumroad.com/v2'

def req(method, url, data=None, headers=None):
    hdrs = {'Authorization': 'Bearer ' + TOKEN}
    if headers: hdrs.update(headers)
    r = urllib.request.Request(url, data=data, method=method, headers=hdrs)
    try:
        resp = urllib.request.urlopen(r, timeout=180)
        raw = resp.read()
        try: return resp.status, json.loads(raw.decode())
        except: return resp.status, raw
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()[:400]
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

pid = '77jOb-mKWRCY2c9Z6P6krw=='
epub = f'{BASE}/publish/for-distribution/google-play/pedia-vol-10.epub'
fsize = os.path.getsize(epub)

# 1. presign (NO product_id, v9 style)
st, pr = req('POST', f'{API}/files/presign?access_token={urllib.parse.quote(TOKEN)}',
             urllib.parse.urlencode({'filename': 'pedia-vol-10.epub', 'file_size': fsize}).encode(),
             {'Content-Type': 'application/x-www-form-urlencoded'})
print('presign:', st, str(pr)[:200])
parts = pr.get('parts') or []
upid, key = pr.get('upload_id'), pr.get('key')
file_url = pr.get('file_url')
with open(epub, 'rb') as f:
    content = f.read()
etags = []
for i, part in enumerate(parts):
    p_url = part.get('presigned_url') or part.get('url')
    st, h2 = s3_put(p_url, content)
    etag = (h2.get('ETag') or '').strip('"')
    etags.append({'part_number': part.get('part_number', i+1), 'etag': etag})
    print(f'PUT part {i+1}: {st} etag={etag[:16]}')
# 2. complete
body = json.dumps({'upload_id': upid, 'key': key, 'parts': etags})
st, comp = req('POST', f'{API}/files/complete?access_token={urllib.parse.quote(TOKEN)}',
               body.encode(), {'Content-Type': 'application/json'})
print('complete:', st, str(comp)[:200])
final_url = comp.get('file_url') or file_url
# 3. ATTACH via PUT /products/{id} with file_url (v9 style)
st, att = req('PUT', f'{API}/products/{urllib.parse.quote(pid)}?access_token={urllib.parse.quote(TOKEN)}',
              urllib.parse.urlencode({'file_url': final_url, 'name': 'Encyclopedia Volume 10'}).encode(),
              {'Content-Type': 'application/x-www-form-urlencoded'})
print('attach PUT:', st, str(att)[:300])
time.sleep(2)
q = urllib.parse.urlencode({'access_token': TOKEN})
st, p = req('GET', f'{API}/products/{urllib.parse.quote(pid)}?{q}')
files = (p.get('product') or {}).get('files') or []
print('VERIFY files:', [f.get('size') for f in files])
