#!/usr/bin/env python3
"""Test direct multipart POST products/{id}/files (the flow gumroad-publisher-v3 used successfully)."""
import json, os, sys, time, urllib.request, urllib.parse, uuid

BASE = '/Users/darrylsmac/gullahgeecheebiz-site'
TOKEN = None
for line in open(f'{BASE}/.env').read().splitlines():
    if line.startswith('GUMROAD_ACCESS_TOKEN='):
        TOKEN = line.split('=', 1)[1].strip().strip('"').strip("'")
API = 'https://api.gumroad.com/v2'

def multipart_post(url, field, fpath, ctype):
    with open(fpath, 'rb') as f:
        content = f.read()
    boundary = '----ggb' + uuid.uuid4().hex
    body = b''
    body += f'--{boundary}\r\n'.encode()
    body += f'Content-Disposition: form-data; name="{field}"; filename="{os.path.basename(fpath)}"\r\n'.encode()
    body += f'Content-Type: {ctype}\r\n\r\n'.encode()
    body += content + b'\r\n'
    body += f'--{boundary}--\r\n'.encode()
    req = urllib.request.Request(url, data=body, method='POST',
                                 headers={'Authorization': 'Bearer ' + TOKEN,
                                          'Content-Type': f'multipart/form-data; boundary={boundary}'})
    try:
        r = urllib.request.urlopen(req, timeout=180)
        raw = r.read()
        try: return r.status, json.loads(raw.decode())
        except: return r.status, raw
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()[:300]

pid = '77jOb-mKWRCY2c9Z6P6krw=='  # vol 10 canonical (has 2285 stub)
epub = f'{BASE}/publish/for-distribution/google-play/pedia-vol-10.epub'
q = urllib.parse.urlencode({'access_token': TOKEN})
st, resp = multipart_post(f'{API}/products/{urllib.parse.quote(pid)}/files?{q}', 'file', epub, 'application/epub+zip')
print('POST products/{id}/files ->', st, str(resp)[:400])
time.sleep(2)
# verify
req2 = urllib.request.Request(f'{API}/products/{urllib.parse.quote(pid)}?{q}', headers={'Authorization': 'Bearer ' + TOKEN})
p = json.loads(urllib.request.urlopen(req2, timeout=30).read().decode()).get('product', {})
files = p.get('files') or []
print('VERIFY files:', [(f.get('size')) for f in files])
