#!/usr/bin/env python3
"""Test cover attach: direct_uploads -> PUT bytes -> POST /products/{id}/covers {url}
Actually simplest: covers endpoint takes a PUBLIC URL, or thumbnail takes signed_blob_id.
Try: 1) POST /direct_uploads?purpose=covers_or_media to get signed url + blob id
     2) PUT bytes to signed url
     3) POST /products/{id}/thumbnail with signed_blob_id  (thumbnail accepts signed blob)
Covers docs only show url param, thumbnail shows signed_blob_id OR url. Try thumbnail first.
"""
import json, os, sys, time, urllib.request, urllib.parse, uuid

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
        resp = urllib.request.urlopen(r, timeout=120)
        raw = resp.read()
        try: return resp.status, json.loads(raw.decode())
        except: return resp.status, raw
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()[:300]
    except Exception as e:
        return -1, str(e)

def raw_put(url, content, ctype):
    r = urllib.request.Request(url, data=content, method='PUT', headers={'Content-Type': ctype})
    try:
        resp = urllib.request.urlopen(r, timeout=120)
        return resp.status, dict(resp.headers)
    except urllib.error.HTTPError as e:
        return e.code, {}
    except Exception as e:
        return -1, {}

pid = 'NQ5Ku1L8n0X0BkRPAtmu_g=='  # vol 06 canonical
cover = f'{BASE}/publish/landing-pad/encyclopedia-vol-06/cover.jpg'
with open(cover, 'rb') as f:
    content = f.read()
print(f'cover size: {len(content)}')

# 1. reserve direct upload
for purpose in ['media', 'cover', 'product_cover']:
    st, r = api_req('POST', f'{API}/direct_uploads?access_token={urllib.parse.quote(TOKEN)}',
                    urllib.parse.urlencode({'purpose': purpose, 'filename': 'cover.jpg',
                                            'content_type': 'image/jpeg',
                                            'size': len(content)}).encode(),
                    {'Content-Type': 'application/x-www-form-urlencoded'})
    print(f'direct_uploads purpose={purpose}: {st} {str(r)[:300]}')
    if isinstance(r, dict) and r.get('success'):
        signed_url = r.get('url') or r.get('signed_url')
        blob_id = r.get('signed_blob_id') or r.get('blob_id') or r.get('id')
        print(f'  got url={str(signed_url)[:100]} blob={blob_id}')
        if signed_url:
            st2, h2 = raw_put(signed_url, content, 'image/jpeg')
            print(f'  PUT bytes: {st2}')
        # try attaching via thumbnail + covers
        if blob_id:
            st3, r3 = api_req('POST', f'{API}/products/{urllib.parse.quote(pid)}/thumbnail?access_token={urllib.parse.quote(TOKEN)}',
                              urllib.parse.urlencode({'signed_blob_id': blob_id}).encode(),
                              {'Content-Type': 'application/x-www-form-urlencoded'})
            print(f'  thumbnail: {st3} {str(r3)[:200]}')
            # covers endpoint only accepts url; skip
        break
