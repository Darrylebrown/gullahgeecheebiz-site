#!/usr/bin/env python3
"""Upload Encyclopedia Volumes to Gumroad using v2 API."""
import json, os, time, sys
from pathlib import Path
import urllib.request
import urllib.parse

TOKEN = open('/Users/darrylsmac/gullahgeecheebiz-site/.env').read().splitlines()
for line in TOKEN:
    if line.startswith('GUMROAD_ACCESS_TOKEN='):
        TOKEN = line.split('=', 1)[1]
        break

DB_PATH = Path('/Users/darrylsmac/gullahgeecheebiz-site/publish/publisher.db')
PROJECT_ROOT = Path('/Users/darrylsmac/gullahgeecheebiz-site')

def db_query(query):
    import sqlite3
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(query)
    results = cur.fetchall()
    conn.close()
    return results

def gumroad_request(method, endpoint, data=None, file_data=None, content_type=None):
    url = f"https://api.gumroad.com/v2{endpoint}"
    req = urllib.request.Request(url, method=method)
    req.add_header('Authorization', f'Bearer {TOKEN}')
    
    if file_data and content_type:
        boundary = f'----WebKitFormBoundary{int(time.time()*1000)}'
        req.add_header('Content-Type', f'multipart/form-data; boundary={boundary}')
        
        body = b''
        for key, val in data.items():
            body += f'--{boundary}\r\nContent-Disposition: form-data; name="{key}"\r\n\r\n{val}\r\n'.encode()
        body += f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="{os.path.basename(file_data)}"\r\nContent-Type: application/octet-stream\r\n\r\n'.encode()
        body += file_data.read()
        body += f'\r\n--{boundary}--\r\n'.encode()
        req.data = body
    elif data:
        req.data = urllib.parse.urlencode(data).encode()
        req.add_header('Content-Type', 'application/x-www-form-urlencoded')
    
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode())

def get_existing_volume_numbers():
    """Get volume numbers already on Gumroad."""
    req = urllib.request.Request(
        'https://api.gumroad.com/v2/products',
        headers={'Authorization': f'Bearer {TOKEN}'}
    )
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read().decode())
    
    volumes = set()
    for p in data.get('products', []):
        name = p.get('name', '')
        if 'Encyclopedia Volume' in name:
            try:
                vol_num = int(name.split()[-1])
                volumes.add(vol_num)
            except:
                pass
    return volumes

def get_uploaded_volumes():
    """Get volume numbers already in our DB as published."""
    results = db_query("SELECT data FROM manifests WHERE state='published' AND data LIKE '%Encyclopedia Volume%'")
    volumes = set()
    for r in results:
        try:
            d = json.loads(r[0])
            vol_num = int(d['title'].split()[-1])
            volumes.add(vol_num)
        except:
            pass
    return volumes

def find_epub_volume(vol_num):
    """Find EPUB for a volume number."""
    epub_path = PROJECT_ROOT / 'publish' / 'for-distribution' / 'google-play' / f'encyclopedia-volume-{vol_num:02d}.epub'
    if epub_path.exists():
        return epub_path
    # Try alternate naming
    for f in (PROJECT_ROOT / 'publish' / 'for-distribution' / 'google-play').glob(f'*{vol_num:02d}*.epub'):
        return f
    return None

def main():
    uploaded = get_uploaded_volumes()
    gumroad_vols = get_existing_volume_numbers()
    
    print(f"Volumes in DB (published): {sorted(uploaded)}")
    print(f"Volumes on Gumroad: {sorted(gumroad_vols)}")
    
    # Find volumes not yet uploaded
    missing = set(range(1, 51)) - uploaded
    print(f"Volumes not in DB: {sorted(missing)}")
    
    # Also check which Gumroad products might be duplicates or older versions
    # The DB has entries 01-50, let's verify they're all unique
    
    # For now, just upload whatever's in DB but not on Gumroad, or vice versa
    # Strategy: Trust the DB - if it says published, verify it exists on Gumroad
    
    print("\n=== Verifying uploaded volumes ===")
    verified = 0
    for vol in sorted(uploaded):
        # Find the product on Gumroad
        found = False
        for gvol in gumroad_vols:
            if gvol == vol:
                found = True
                break
        if found:
            verified += 1
        else:
            print(f"  Vol {vol:02d}: IN DB but NOT on Gumroad - needs upload")
    
    print(f"\nVerified: {verified}/{len(uploaded)}")
    
    # Upload any that are missing
    to_upload = sorted(set(range(1, 51)) - gumroad_vols)
    print(f"\nNeed to upload to Gumroad: {len(to_upload)} volumes")
    
    if to_upload:
        print(f"First 10: {to_upload[:10]}")

if __name__ == '__main__':
    main()
