#!/usr/bin/env python3
"""Upload Encyclopedia Volume to Gumroad using v2 API flow."""
import json
import os
import sys
import time
import urllib.request
import urllib.error
import sqlite3
from pathlib import Path

TOKEN = open('/Users/darrylsmac/gullahgeecheebiz-site/.env').read().splitlines()
for line in TOKEN:
    if line.startswith('GUMROAD_ACCESS_TOKEN='):
        TOKEN = line.split('=', 1)[1]
        break

DB_PATH = Path('/Users/darrylsmac/gullahgeecheebiz-site/publish/publisher.db')
PROJECT_ROOT = Path('/Users/darrylsmac/gullahgeecheebiz-site')
EVENT_STREAM = Path('/Users/darrylsmac/gullahgeecheebiz-site/publish/event_stream.jsonl')

def gumroad_request(method, endpoint, data=None, body=None, headers=None):
    import urllib.parse
    url = f"https://api.gumroad.com/v2{endpoint}"
    req = urllib.request.Request(url, method=method)
    req.add_header('Authorization', f'Bearer {TOKEN}')
    if headers:
        for k, v in headers.items():
            req.add_header(k, v)
    if body:
        req.data = body if isinstance(body, bytes) else body.encode()
    elif data:
        req.data = urllib.parse.urlencode(data).encode()
        req.add_header('Content-Type', 'application/x-www-form-urlencoded')
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode())

def get_existing_volumes():
    """Get volume numbers already on Gumroad."""
    data = gumroad_request('GET', '/products')
    volumes = set()
    for p in data.get('products', []):
        name = p.get('name', '')
        if 'Encyclopedia Volume' in name:
            try:
                vol_num = int(name.split()[-1])
                volumes.add(vol_num)
            except:
                pass
    return volumes, data

def upload_volume(vol_num):
    """Upload a single volume to Gumroad using v2 flow."""
    cover_path = PROJECT_ROOT / 'publish' / 'landing-pad' / f'encyclopedia-vol-{vol_num:02d}' / 'cover.jpg'
    epub_path = PROJECT_ROOT / 'publish' / 'for-distribution' / 'google-play' / f'pedia-vol-{vol_num:02d}.epub'
    
    title = f"Encyclopedia Volume {vol_num:02d}"
    
    if not cover_path.exists():
        return {'success': False, 'error': f'Cover not found: {cover_path}'}
    if not epub_path.exists():
        return {'success': False, 'error': f'EPUB not found: {epub_path}'}
    
    # Step 1: Create product (to get product ID)
    try:
        create_resp = gumroad_request('POST', '/create_product', data={
            'name': title,
            'description': f'Gullah Geechee Encyclopedia, Volume {vol_num:02d}',
            'price': 99,
            'currency': 'usd',
            'short_name': f'encyclopedia-vol-{vol_num:02d}',
            'published': False,
            'preorder': False
        })
        if 'error' in create_resp:
            return {'success': False, 'error': create_resp['error']}
        product_id = create_resp['product']['id']
        product_short = create_resp['product'].get('custom_permalink', '')
        print(f"  Created product: {product_id}")
    except Exception as e:
        return {'success': False, 'error': str(e)}
    
    # Step 2: Get presign URL for cover
    try:
        presign_cover = gumroad_request('POST', '/files/presign', data={
            'product_id': product_id,
            'filename': 'cover.jpg'
        })
        if 'error' in presign_cover:
            return {'success': False, 'error': presign_cover['error']}
        presign_url = presign_cover['url']
        file_id_cover = presign_cover['file']['id']
        print(f"  Got presign for cover: {file_id_cover}")
    except Exception as e:
        return {'success': False, 'error': f'Cover presign failed: {e}'}
    
    # Step 3: PUT cover
    try:
        with open(cover_path, 'rb') as f:
            cover_data = f.read()
        req = urllib.request.Request(presign_url, data=cover_data, method='PUT')
        req.add_header('Content-Type', 'image/jpeg')
        with urllib.request.urlopen(req) as resp:
            print(f"  Cover upload: {resp.status}")
    except Exception as e:
        return {'success': False, 'error': f'Cover PUT failed: {e}'}
    
    # Step 4: Complete cover upload
    try:
        gumroad_request('POST', '/files/complete', data={
            'id': file_id_cover,
            'product_id': product_id
        })
        print(f"  Cover completed")
    except Exception as e:
        return {'success': False, 'error': f'Cover complete failed: {e}'}
    
    # Step 5: Get presign URL for EPUB
    try:
        presign_epub = gumroad_request('POST', '/files/presign', data={
            'product_id': product_id,
            'filename': 'encyclopedia.epub'
        })
        if 'error' in presign_epub:
            return {'success': False, 'error': presign_epub['error']}
        presign_url = presign_epub['url']
        file_id_epub = presign_epub['file']['id']
        print(f"  Got presign for epub: {file_id_epub}")
    except Exception as e:
        return {'success': False, 'error': f'EPUB presign failed: {e}'}
    
    # Step 6: PUT EPUB
    try:
        with open(epub_path, 'rb') as f:
            epub_data = f.read()
        req = urllib.request.Request(presign_url, data=epub_data, method='PUT')
        req.add_header('Content-Type', 'application/octet-stream')
        with urllib.request.urlopen(req) as resp:
            print(f"  EPUB upload: {resp.status}")
    except Exception as e:
        return {'success': False, 'error': f'EPUB PUT failed: {e}'}
    
    # Step 7: Complete EPUB upload
    try:
        gumroad_request('POST', '/files/complete', data={
            'id': file_id_epub,
            'product_id': product_id
        })
        print(f"  EPUB completed")
    except Exception as e:
        return {'success': False, 'error': f'EPUB complete failed: {e}'}
    
    # Step 8: Publish the product
    try:
        gumroad_request('POST', '/publish_product', data={
            'id': product_id
        })
        print(f"  Product published")
        
        # Verify by fetching products
        time.sleep(1)
        volumes, _ = get_existing_volumes()
        if vol_num in volumes:
            return {
                'success': True,
                'volume': vol_num,
                'product_id': product_id,
                'url': f"https://debtide0.gumroad.com/l/{product_short}",
                'gumroad_verified': True
            }
        return {'success': False, 'error': 'Product not found after publish'}
    except Exception as e:
        return {'success': False, 'error': f'Publish failed: {e}'}

def log_event(action, detail):
    event = {
        'ts': time.strftime('%Y-%m-%dT%H:%M:%S'),
        'source_bot': 'PUBLISHING_TANK_OWNER',
        'action': action,
        'detail': detail
    }
    with open(EVENT_STREAM, 'a') as f:
        f.write(json.dumps(event) + '\n')

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: upload_volume.py <volume_number>")
        sys.exit(1)
    
    vol_num = int(sys.argv[1])
    print(f"Uploading Encyclopedia Volume {vol_num:02d}...")
    
    result = upload_volume(vol_num)
    print(f"Result: {result}")
    
    if result['success']:
        log_event('upload_success', f'Volume {vol_num:02d}: {result["url"]}')
    else:
        log_event('upload_failed', f'Volume {vol_num:02d}: {result.get("error", "unknown")}')
    
    sys.exit(0 if result['success'] else 1)
