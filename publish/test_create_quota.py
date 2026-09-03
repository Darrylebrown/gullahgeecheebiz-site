#!/usr/bin/env python3
"""Create ONE missing volume (draft) to test the 10/day creation quota.
Uses real pedia epub + published=false draft; report result; do NOT publish yet.
"""
import json, os, urllib.request, urllib.parse

BASE = '/Users/darrylsmac/gullahgeecheebiz-site'
TOKEN = None
for line in open(f'{BASE}/.env').read().splitlines():
    if line.startswith('GUMROAD_ACCESS_TOKEN='):
        TOKEN = line.split('=', 1)[1].strip().strip('"').strip("'")
API = 'https://api.gumroad.com/v2'

body = urllib.parse.urlencode({
    'name': 'Encyclopedia Volume 26',
    'description': 'Encyclopedia Volume 26 — Gullah Geechee cultural heritage collection. Preserve the past. Inspire the future.',
    'price': '999',
    'currency': 'usd',
    'customizable_price': 'true',
    'published': 'false',
}).encode()
req = urllib.request.Request(f'{API}/products?access_token={urllib.parse.quote(TOKEN)}', data=body, method='POST',
                             headers={'Authorization': 'Bearer ' + TOKEN,
                                      'Content-Type': 'application/x-www-form-urlencoded'})
try:
    r = urllib.request.urlopen(req, timeout=60)
    d = json.loads(r.read().decode())
    p = d.get('product', {})
    print('CREATE OK:', p.get('id'), p.get('name'), '| published:', p.get('published'))
except urllib.error.HTTPError as e:
    print('CREATE ERR:', e.code, e.read().decode()[:400])
