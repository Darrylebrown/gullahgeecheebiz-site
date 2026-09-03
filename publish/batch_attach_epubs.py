#!/usr/bin/env python3
"""Batch-attach real pedia EPUBs to canonical products that carry 2KB placeholder stubs.
Flow (validated on vol 10): presign -> PUT S3 -> files/complete -> PUT /products/{id} files[][url] (replaces stub).
"""
import json, os, sys, time, urllib.request, urllib.parse, glob

BASE = '/Users/darrylsmac/gullahgeecheebiz-site'
TOKEN = None
for line in open(f'{BASE}/.env').read().splitlines():
    if line.startswith('GUMROAD_ACCESS_TOKEN='):
        TOKEN = line.split('=', 1)[1].strip().strip('"').strip("'")
API = 'https://api.gumroad.com/v2'
EPUB_DIR = f'{BASE}/publish/for-distribution/google-play'

def api_req(method, url, data=None, headers=None):
    hdrs = {'Authorization': 'Bearer ' + TOKEN}
    if headers: hdrs.update(headers)
    r = urllib.request.Request(url, data=data, method=method, headers=hdrs)
    try:
        resp = urllib.request.urlopen(r, timeout=240)
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
        resp = urllib.request.urlopen(r, timeout=240)
        return resp.status, dict(resp.headers)
    except urllib.error.HTTPError as e:
        return e.code, {}
    except Exception as e:
        return -1, {}

def get_files(pid):
    q = urllib.parse.urlencode({'access_token': TOKEN})
    st, p = api_req('GET', f'{API}/products/{urllib.parse.quote(pid)}?{q}')
    return (p.get('product') or {}).get('files') or []

def attach(pid, epub_path, label):
    fsize = os.path.getsize(epub_path)
    fname = os.path.basename(epub_path)
    try:
        st, pr = api_req('POST', f'{API}/files/presign?access_token={urllib.parse.quote(TOKEN)}',
                         urllib.parse.urlencode({'filename': fname, 'file_size': fsize}).encode(),
                         {'Content-Type': 'application/x-www-form-urlencoded'})
        if not (isinstance(pr, dict) and pr.get('success')):
            return False, f'presign {st}: {str(pr)[:150]}'
        parts = pr.get('parts') or []
        upid, key = pr.get('upload_id'), pr.get('key')
        with open(epub_path, 'rb') as f:
            content = f.read()
        etags = []
        for i, part in enumerate(parts):
            p_url = part.get('presigned_url') or part.get('url')
            st, h2 = s3_put(p_url, content)
            if st not in (200, 204):
                return False, f'PUT part {i+1} {st}'
            etag = (h2.get('ETag') or '').strip('"')
            etags.append({'part_number': part.get('part_number', i+1), 'etag': etag})
        body = json.dumps({'upload_id': upid, 'key': key, 'parts': etags})
        st, comp = api_req('POST', f'{API}/files/complete?access_token={urllib.parse.quote(TOKEN)}',
                           body.encode(), {'Content-Type': 'application/json'})
        if not (isinstance(comp, dict) and comp.get('success')):
            return False, f'complete {st}: {str(comp)[:150]}'
        final_url = comp.get('file_url') or pr.get('file_url')
        params = urllib.parse.urlencode({'access_token': TOKEN, 'files[][url]': final_url})
        st, att = api_req('PUT', f'{API}/products/{urllib.parse.quote(pid)}?{params}')
        ok = isinstance(att, dict) and att.get('success')
        if not ok:
            return False, f'attach {st}: {str(att)[:150]}'
        return True, 'attached'
    except Exception as e:
        return False, str(e)

# canonical products needing real epub: vol -> pid (friendly/canonical kept product)
TARGETS = {
    '01': ('GOz5YrS8UG1GTIgLPA4bBg==', 'pedia-vol-01.epub'),
    '02': ('rY7wZ82IL3EjBLVEdqw4Xg==', 'pedia-vol-02.epub'),
    '03': ('C4YUKa7a1W8xD_iIoBtlzg==', 'pedia-vol-03.epub'),
    '04': ('u-5Y3VsfKDxeuHddwrlBLw==', 'pedia-vol-04.epub'),
    '05': ('dhYrf2rnhM7XC-X3B1ljFA==', 'pedia-vol-05.epub'),
    '12': ('z5NQaAaDhmzky9DodGk0KQ==', 'pedia-vol-12.epub'),
    '13': ('omSKYQ3l8PEFyk0gijVSTQ==', 'pedia-vol-13.epub'),
    '14': ('zOXSF56GaaWrGObMUfHmXw==', 'pedia-vol-14.epub'),
    '15': ('7cCV-zTPgILdTaPii_jn9A==', 'pedia-vol-15.epub'),
    '31': ('YcqJrhCMSWmpIJ97fmjOyA==', 'pedia-vol-31.epub'),
    '32': ('9-_nfySyW8GAN3bmtOIwgw==', 'pedia-vol-32.epub'),
    '33': ('N-NGLiWCEaUKfNqWXxKwpA==', 'pedia-vol-33.epub'),
}

results = {}
for vol, (pid, fname) in TARGETS.items():
    epub = f'{EPUB_DIR}/{fname}'
    if not os.path.exists(epub):
        results[vol] = ('SKIP', 'no local epub')
        continue
    ok, msg = attach(pid, epub, vol)
    results[vol] = ('OK' if ok else 'FAIL', msg)
    print(f'vol {vol}: {results[vol][0]} - {msg}', flush=True)
    time.sleep(1.5)

print('\n=== VERIFY ===')
for vol, (pid, fname) in TARGETS.items():
    files = get_files(pid)
    sizes = [f.get('size') for f in files]
    print(f'vol {vol}: files={sizes}')
    time.sleep(0.4)

json.dump(results, open(f'{BASE}/publish/attach_results_2026-09-02.json', 'w'), indent=1)
