#!/usr/bin/env python3
"""
GGB Revenue Orchestrator - Publish products and drive sales
"""
import json
import os
import sys
import time
import sqlite3
import urllib.request
import urllib.error
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path

BASE = "/Users/darrylsmac/gullahgeecheebiz-site"
TOKEN = None
for line in open(f"{BASE}/.env").read().splitlines():
    if line.startswith("GUMROAD_ACCESS_TOKEN="):
        TOKEN = line.split("=", 1)[1].strip().strip('"').strip("'")
        break

if not TOKEN:
    print("ERROR: No token found"); sys.exit(1)

BRAIN_DB = f"{BASE}/ggb-engine/headquarters/brain.db"
EPUB_DIR = Path(f"{BASE}/publish/for-distribution/google-play")

def log_event(event_type, message, data=None):
    try:
        conn = sqlite3.connect(BRAIN_DB)
        c = conn.cursor()
        c.execute(
            "INSERT INTO event_stream (timestamp, source_bot, event_type, message, data) VALUES (?, ?, ?, ?, ?)",
            (datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S'), 'SALES_10K_GOAL', event_type, message, json.dumps(data or {}))
        )
        conn.commit()
        conn.close()
        print(f"[LOG] {event_type}: {message}")
    except Exception as e:
        print(f"[DB ERROR] {e}")

def api_get(url):
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {TOKEN}"})
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode())

def api_post(url, params):
    data_bytes = "&".join(f"{k}={urllib.parse.quote(str(v))}" for k, v in params.items()).encode()
    req = urllib.request.Request(url, data=data_bytes,
        headers={"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/x-www-form-urlencoded"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode())

def api_delete(url):
    req = urllib.request.Request(url, method="DELETE", headers={"Authorization": f"Bearer {TOKEN}"})
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode())

def upload_file(product_id, epub_path):
    """Upload EPUB file to product"""
    if not epub_path.exists():
        return False, f"File not found: {epub_path}"
    
    filename = epub_path.name
    with open(epub_path, 'rb') as f:
        file_data = f.read()
    
    boundary = f"boundary{int(time.time())}"
    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'
        f"Content-Type: application/epub+zip\r\n\r\n"
    ).encode() + file_data + f"\r\n--{boundary}--\r\n".encode()
    
    url = f"https://api.gumroad.com/v2/products/{product_id}/files?access_token={TOKEN}"
    req = urllib.request.Request(url, data=body,
        headers={"Authorization": f"Bearer {TOKEN}", "Content-Type": f"multipart/form-data; boundary={boundary}"})
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            result = json.loads(resp.read().decode())
            return result.get('success'), result.get('error', '')
    except Exception as e:
        return False, str(e)

def find_epub(title):
    """Find matching EPUB for title"""
    title_lower = title.lower()
    # Try exact match patterns
    candidates = []
    for epub in EPUB_DIR.glob("*.epub"):
        epub_name = epub.name.lower().replace('.epub', '')
        # Check if title keywords match
        words = title_lower.split()
        matches = sum(1 for w in words if w in epub_name or any(w in ep for ep in epub_name.split('-')))
        if matches > 0:
            candidates.append((matches, epub))
    
    if candidates:
        candidates.sort(reverse=True)
        return candidates[0][1]
    
    # Try partial matches
    for word in title_lower.split()[:3]:
        if len(word) > 3:
            for epub in EPUB_DIR.glob(f"*{word.replace(' ', '-')}.epub"):
                return epub
            for epub in EPUB_DIR.glob(f"*{word}.epub"):
                return epub
    
    return None

def get_price(name):
    if "Encyclopedia Volume" in name or "Encyclopedia" in name:
        return "999"
    elif "Imposter" in name or "Morning" in name or "Confidence" in name or "Purpose" in name:
        return "399"
    elif "Box Set" in name or "Complete" in name:
        return "3999"
    elif "Vault" in name:
        return "9700"
    elif "License" in name:
        return "49700"
    else:
        return "999"

print("=" * 60)
print("GGB REVENUE ORCHESTRATOR - PUBLISHING & SALES CHECK")
print("=" * 60)
print(f"Target: $10,000.00")
print()

# Step 1: Check sales
print(">>> CHECKING SALES...")
try:
    sales_data = api_get("https://api.gumroad.com/v2/sales")
    sales = sales_data.get('sales', [])
    total = sum(float(s.get('sale_price', 0)) for s in sales)
    print(f"Sales: {len(sales)} | Revenue: ${total:.2f}")
    log_event("sales_check", f"Sales: ${total:.2f} from {len(sales)} transactions")
except Exception as e:
    print(f"Error checking sales: {e}")
    total = 0.0

# Step 2: Check if goal reached
if total >= 10000:
    print(f"\n{'='*60}")
    print(f"GOAL REACHED! Total: ${total:.2f}")
    print(f"{'='*60}")
    log_event("goal_reached", f"Revenue goal of $10,000 reached with ${total:.2f}")
    sys.exit(0)

gap = 10000 - total
print(f"Gap to goal: ${gap:.2f}")

# Step 3: Get all products
print("\n>>> GETTING PRODUCTS...")
all_products = []
page_key = None
while True:
    url = "https://api.gumroad.com/v2/products"
    if page_key:
        url += f"?page_key={page_key}"
    try:
        data = api_get(url)
        products = data.get('products', [])
        all_products.extend(products)
        page_key = data.get('next_page_key')
        print(f"  Fetched {len(products)} products (total: {len(all_products)})")
        if not page_key:
            break
        time.sleep(1)
    except urllib.error.HTTPError as e:
        if e.code == 429:
            print("  Rate limited, waiting 60s...")
            time.sleep(60)
            continue
        raise
    time.sleep(1)

print(f"\nTotal products: {len(all_products)}")
unpublished = [p for p in all_products if not p.get('published')]
print(f"Unpublished: {len(unpublished)}")

# Step 4: Delete and recreate unpublished products
if unpublished:
    print("\n>>> FIXING PUBLICATION STATE...")
    print("  Products are in invalid state (no URL, not published)")
    print("  Deleting and recreating with proper content...")
    
    for i, p in enumerate(unpublished):
        pid = p["id"]
        name = p["name"]
        price = get_price(name)
        
        print(f"  [{i+1}/{len(unpublished)}] Processing: {name}")
        
        # Find EPUB
        epub = find_epub(name)
        if epub:
            print(f"    Found EPUB: {epub.name}")
        else:
            print(f"    ⚠️  No matching EPUB found")
        
        # Delete old product
        try:
            del_result = api_delete(f"https://api.gumroad.com/v2/products/{pid}")
            if del_result.get('success'):
                print(f"    Deleted old product")
            else:
                print(f"    Delete failed: {del_result.get('error', 'unknown')}")
        except Exception as e:
            print(f"    Delete error: {e}")
        
        time.sleep(2)
        
        # Create new product
        permalink = name.lower().replace(" ", "-").replace("&", "and").replace(",", "").replace("'", "").replace("(", "").replace(")", "").replace(".", "")
        
        new_data = {
            'name': name[:100],
            'description': f'{name} — Gullah Geechee cultural heritage collection. Preserve the past. Inspire the future.',
            'price': price,
            'currency': 'usd',
            'customizable_price': 'true',
            'published': 'true',
            'require_shipping': 'false',
            'custom_permalink': permalink,
        }
        
        try:
            create_result = api_post("https://api.gumroad.com/v2/products", new_data)
            if create_result.get('success'):
                new_prod = create_result.get('product', {})
                new_pid = new_prod.get('id')
                print(f"    Created: ${price/100:.2f}")
                print(f"    Product ID: {new_pid}")
                
                # Upload file if available
                if epub:
                    print(f"    Uploading: {epub.name}")
                    upload_success, upload_error = upload_file(new_pid, epub)
                    if upload_success:
                        print(f"    ✅ File uploaded")
                    else:
                        print(f"    ⚠️  Upload failed: {upload_error}")
                
                time.sleep(1.5)
            else:
                print(f"    Create failed: {create_result.get('error', 'unknown')}")
                time.sleep(10)
        except urllib.error.HTTPError as e:
            if e.code == 429:
                print(f"    RATE LIMITED - waiting 90s...")
                time.sleep(90)
                # Retry once
                try:
                    create_result = api_post("https://api.gumroad.com/v2/products", new_data)
                    if create_result.get('success'):
                        new_prod = create_result.get('product', {})
                        new_pid = new_prod.get('id')
                        print(f"    Created (retry): ${price/100:.2f}")
                        if epub:
                            upload_success, upload_error = upload_file(new_pid, epub)
                            if upload_success:
                                print(f"    ✅ File uploaded")
                    else:
                        print(f"    Create failed (retry): {create_result.get('error', 'unknown')}")
                except Exception as e2:
                    print(f"    Retry error: {e2}")
            else:
                print(f"    HTTP Error {e.code}: {e}")
                time.sleep(10)
        except Exception as e:
            print(f"    Error: {e}")
            time.sleep(5)
    
    # Wait for rate limit to reset
    print("\n  Waiting for rate limit reset...")
    time.sleep(10)

# Step 5: Verify publication state
print("\n>>> VERIFYING PUBLICATION STATE...")
try:
    verify_data = api_get("https://api.gumroad.com/v2/products")
    products = verify_data.get('products', [])
    published = len([p for p in products if p.get('published')])
    unpublished_now = len([p for p in products if not p.get('published')])
    print(f"  Published: {published}/{len(products)}")
    print(f"  Unpublished: {unpublished_now}/{len(products)}")
    
    if published == len(products) and published > 0:
        print("  ✅ All products now published!")
        log_event("all_published", f"All {published} products published")
    else:
        print("  ⚠️  Some products still unpublished")
        for p in products:
            if not p.get('published'):
                print(f"    - {p['name']}")
except Exception as e:
    print(f"  Verification error: {e}")

# Step 6: Final sales check
print("\n>>> FINAL SALES CHECK...")
try:
    sales_data = api_get("https://api.gumroad.com/v2/sales")
    sales = sales_data.get('sales', [])
    total = sum(float(s.get('sale_price', 0)) for s in sales)
    print(f"Revenue: ${total:.2f} ({len(sales)} sales)")
except Exception as e:
    print(f"Error: {e}")
    total = 0.0

# Step 7: Summary
print("\n" + "=" * 60)
print("STATUS SUMMARY")
print("=" * 60)
print(f"Total Products: {len(all_products)}")
final_published = len([p for p in all_products if p.get('published')])
print(f"Published: {final_published}")
print(f"Current Revenue: ${total:.2f}")
print(f"Target: $10,000.00")
print(f"Gap: ${10000-total:.2f}")

log_event("status_update", f"Products: {len(all_products)}, Published: {final_published}, Revenue: ${total:.2f}, Gap: ${10000-total:.2f}")

if total >= 10000:
    print("\nGOAL REACHED!")
    log_event("goal_reached", f"Revenue goal of $10,000 reached with ${total:.2f}")
else:
    print("\nGoal not yet reached. Will continue next run.")
    print("\nNext actions:")
    print("  1. Verify all products are published")
    print("  2. Drive traffic to product pages")
    print("  3. Promote on social media channels")
    print("  4. Consider paid advertising to accelerate sales")
