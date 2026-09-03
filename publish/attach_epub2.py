#!/usr/bin/env python3
"""Attach EPUB to existing product: presign -> PUT -> complete -> POST products/{id}/files {file_url}.
Verified via GET after."""
import json, os, sys, time, urllib.request, urllib.parse

BASE = '/Users/darrylsmac/gullahgeecheebiz-site'
TOKEN = None
for line in open(f'{BASE}/.env').read().splitlines():
    if line.startswith('GUMROAD_ACCESS_TOKEN='):
        TOKEN = line.split('=', 1)[1].strip().strip('"').strip("'")
API = 'https://api.gumroad.com/v2'

def http_req(method, url, data=None, headers=None, ctype=None):
    hdrs = {'Authorization': 'Bearer ' + TOKEN}
    if ctype: hdrs['Content-Type'] = ctype
    if headers: hdrs.update(headers)
    req = urllib.request.Request(url, data=data, method=method, headers=hdrs)
    try:
        r = urllib.request.urlopen(req, timeout=180)
        raw = r.read()
        try: return r.status, json.loads(raw.decode())
        except: return r.status, raw
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()[:400]
    except Exception as e:
        return -1, str(e)

def attach(pid, epub_path, retries=3):
    fsize = os.path.getsize(epub_path)
    fname = os.path.basename(epub_path)
    for attempt in range(retries):
        # 1. presign
        st, pr = http_req('POST', f'{API}/files/presign?access_token={urllib.parse.quote(TOKEN)}',
                          urllib.parse.urlencode({'filename': fname, 'file_size': fsize}).encode(),
                          ctype='application/x-www-form-urlencoded')
        if not (isinstance(pr, dict) and pr.get('success')):
            print(f'  presign fail {st}: {str(pr)[:200]}'); time.sleep(5); continue
        upid = pr['upload_id']; key = pr['key']
        parts = pr.get('parts') or []
        purl = parts[0]['presigned_url'] if parts else pr.get('url')
        with open(epub_path, 'rb') as f:
            data = f.read()
        # 2. PUT
        st, resp = http_req('PUT', purl, data, ctype='application/epub+zip')
        if st not in (200, 204):
            print(f'  PUT fail {st}'); time.sleep(5); continue
        # 3. complete (with parts+etag like v9 flow)
        etag = ''
        # grab etag from a PUT response header is unavailable in this helper; use complete without parts (v2 simple)
        st, comp = http_req('POST', f'{API}/files/complete?access_token={urllib.parse.quote(TOKEN)}',
                            urllib.parse.urlencode({'upload_id': upid, 'key': key}).encode(),
                            ctype='application/x-www-form-urlencoded')
        if not (isinstance(comp, dict) and comp.get('success')):
            # try multipart-style complete with etag from parts structure
            print(f'  complete fail {st}: {str(comp)[:200]}')
            time.sleep(5); continue
        final_url = comp.get('file_url') or pr.get('file_url')
        print(f'  file ready: {final_url[:80]}')
        # 4. ATTACH
        st, att = http_req('POST', f'{API}/products/{urllib.parse.quote(pid)}/files?access_token={urllib.parse.quote(TOKEN)}',
                           urllib.parse.urlencode({'file_url': final_url}).encode(),
                           ctype='application/x-www-form-urlencoded')
        print(f'  attach: {st} {str(att)[:200]}')
        time.sleep(2)
        # verify
        q = urllib.parse.urlencode({'access_token': TOKEN})
        st, p = http_req('GET', f'{API}/products/{urllib.parse.quote(pid)}?{q}')
        files = (p.get('product') or {}).get('files') or []
        sizes = [f.get('size') for f in files]
        print(f'  VERIFY: {len(files)} files sizes={sizes}')
        return True if any(s and s > 5000 for s in sizes) else False
    return False

if __name__ == '__main__':
    pid = sys.argv[1]; epub = sys.argv[2]
    print(f'ATTACH {epub} -> {pid}')
    ok = attach(pid, epub)
    print('RESULT:', 'OK' if ok else 'FAILED')
    sys.exit(0 if ok else 1)
