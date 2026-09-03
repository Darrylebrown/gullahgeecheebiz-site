#!/usr/bin/env python3
"""Fetch full detail for canonical encyclopedia products: price, files (names/sizes), covers, permalink."""
import json, urllib.request, time

TOKEN = None
for line in open('/Users/darrylsmac/gullahgeecheebiz-site/.env').read().splitlines():
    if line.startswith('GUMROAD_ACCESS_TOKEN='):
        TOKEN = line.split('=', 1)[1].strip().strip('"').strip("'")

# full ids from audit (canonical candidates = friendly permalink ones where they exist)
IDS = {
    'vol-01': 'GOz5YrS8UGvYkLmx7ZJQrg==', 'vol-02': 'rY7wZ82IL3ZZfUyYYGSQlQ==', 'vol-03': 'C4YUKa7a1WfVxxNnR3U_ww==',
    'vol-04': 'u-5Y3VsfKDv1DlL8tR-yUQ==', 'vol-05': 'dhYrf2rnhMukFZ8R3SMTEw==', 'vol-06': 'NQ5Ku1L8n0QkPTCJKOT7Fw==',
    'vol-07': 'lTYgq5rjOPWJj4VKkHRCjQ==', 'vol-08': 'hQ8smpava5w4-T7zqCU9-g==', 'vol-09': 'znfCFCBSdHxBcRNGYbScXg==',
    'vol-10': '77jOb-mKWRo3D2dVSsGJ3g==', 'vol-11': 'n5dAVx33Ul4N1hD-vbY3ng==', 'vol-12': 'z5NQaAaDhmPGn8WqCVUVKw==',
    'vol-13': 'omSKYQ3l8PmDGbMSzVf5uA==', 'vol-14': 'zOXSF56Gaa5a6c9E7wSZXQ==', 'vol-15': '7cCV-zTPgIABVMYsy4L-lA==',
    'vol-16': 'qEeteNnnod3oTZ2tlMH6sQ==', 'vol-17': 'Lc4eRybml2bFV1ZcHX6vKg==', 'vol-18': 'wwnZGNY12URqZ5DXfbRe_g==',
    'vol-19': 'NdkC8AAd9JnRZJ2WyLqYbA==', 'vol-20': '1l1-5vaRjuMZHyBMgUifdw==', 'vol-21': 'vXF6wnR3BjLJ3p7G1dbEQQ==',
    'vol-22': 'HshTDWPtXbf9ZSS2v8uOig==', 'vol-23': 'ozzNTr9qeRcXfzVqLhYtCw==', 'vol-24': '3rmVEKj1MEeVJqBm2xIwhQ==',
    'vol-25': 'hwP7G7x3p2njjw2nVbA7sA==', 'vol-31': 'YcqJrhCMSW1YHVQ3_5nJPw==', 'vol-32': '9-_nfySyW8mZmMy8PVh_9w==',
    'vol-33': 'N-NGLiWCEahbK4U4J9t1ew==', 'vol-34': 'Q9hSxksisgkkdbtbhIz0LQ==',
}

def fetch(pid):
    url = f'https://api.gumroad.com/v2/products/{pid}'
    req = urllib.request.Request(url, headers={'Authorization': 'Bearer ' + TOKEN})
    for a in range(4):
        try:
            with urllib.request.urlopen(req, timeout=40) as r:
                return json.loads(r.read().decode()).get('product', {})
        except Exception as e:
            if getattr(e, 'code', None) == 429:
                time.sleep(6 * (a + 1)); continue
            return {'error': str(e)}

for label, pid in IDS.items():
    p = fetch(pid)
    if 'error' in p:
        print(label, 'ERR', p['error']); continue
    fi = p.get('file_info') or {}
    print(f"--- {label} | {p.get('name')} | id={pid}")
    print(f"    price={p.get('price')} custom={p.get('customizable_price')} published={p.get('published')} permalink={p.get('custom_permalink')} url={p.get('short_url') or p.get('url')}")
    print(f"    file_info: {json.dumps(fi)[:400]}")
    print(f"    covers: {len(p.get('covers') or [])} main_cover={p.get('main_cover_id')} thumbnail={p.get('thumbnail_url')}")
    time.sleep(0.4)
