#!/usr/bin/env python3
"""GGB Revenue Orchestrator - Quick Publish Script (Optimized)"""
import json
import os
import sys
import time
import sqlite3
import urllib.request
import urllib.error
import urllib.parse
from datetime import datetime, timezone

BASE = "/Users/darrylsmac/gullahgeecheebiz-site"
TOKEN = None
for line in open(f"{BASE}/.env").read().splitlines():
    if line.startswith("GUMROAD_ACCESS_TOKEN="):
        TOKEN = line.split("=", 1)[1].strip().strip('"').strip("'")
        break

if not TOKEN:
    print("ERROR: No token found"); sys.exit(1)

BRAIN_DB = f"{BASE}/ggb-engine/headquarters/brain.db"

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

print("=" * 60)
print("GGB REVENUE ORCHESTRATOR - QUICK RUN")
print("=" * 60)
print(f"Date: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')}")
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
    print("\n" + "=" * 60)
    print("GOAL REACHED! Total: ${:.2f}".format(total))
    print("=" * 60)
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
        time.sleep(0.5)
    except urllib.error.HTTPError as e:
        if e.code == 429:
            print("  Rate limited, waiting 30s...")
            time.sleep(30)
            continue
        raise

print(f"\nTotal products: {len(all_products)}")
unpublished = [p for p in all_products if not p.get('published')]
print(f"Unpublished: {len(unpublished)}")

# Step 4: Publish unpublished products
if unpublished:
    def get_price(name):
        if "Encyclopedia Volume" in name and "Box" not in name and "Vault" not in name and "License" not in name:
            return "999"
        elif "Imposter" in name or "Morning" in name or "Confidence" in name or "Purpose" in name:
            return "399"
        elif "Box Set" in name:
            return "3999"
        elif "Vault" in name:
            return "9700"
        elif "License" in name:
            return "49700"
        else:
            return "999"
    
    print("\n>>> PUBLISHING PRODUCTS...")
    success = 0
    failed = 0
    consecutive_failures = 0
    
    for i, p in enumerate(unpublished):
        pid = p["id"]
        name = p["name"]
        price = get_price(name)
        permalink = name.lower().replace(" ", "-").replace("&", "and").replace(",", "").replace("'", "").replace("(", "").replace(")", "").replace(".", "")
        
        params = {
            'access_token': TOKEN,
            'product_id': pid,
            'price': price,
            'currency': 'usd',
            'published': 'true',
            'description': f'{name} — Gullah Geechee cultural heritage collection. Preserve the past. Inspire the future.',
            'custom_permalink': permalink,
        }
        
        print(f"  [{i+1}/{len(unpublished)}] Publishing: {name}")
        try:
            result = api_post("https://api.gumroad.com/v2/products", params)
            if result.get("success"):
                prod = result.get("product", {})
                product_price = prod.get("price_cents", 0) / 100
                print(f"    OK: ${product_price:.2f}")
                success += 1
                consecutive_failures = 0
                log_event("product_published", f"Published: {name} at ${product_price:.2f}")
            else:
                print(f"    FAIL: {result.get('error', 'unknown')}")
                failed += 1
                consecutive_failures += 1
        except urllib.error.HTTPError as e:
            if e.code == 429:
                wait_time = 60
                print(f"    RATE LIMITED - waiting {wait_time}s...")
                log_event("rate_limit", f"Rate limited on {name}, waiting {wait_time}s")
                time.sleep(wait_time)
                # Retry once
                try:
                    result = api_post("https://api.gumroad.com/v2/products", params)
                    if result.get("success"):
                        prod = result.get("product", {})
                        product_price = prod.get("price_cents", 0) / 100
                        print(f"    OK (retry): ${product_price:.2f}")
                        success += 1
                        consecutive_failures = 0
                        log_event("product_published", f"Published (retry): {name} at ${product_price:.2f}")
                    else:
                        print(f"    FAIL (retry): {result.get('error', 'unknown')}")
                        failed += 1
                        consecutive_failures += 1
                except Exception as e2:
                    print(f"    ERR (retry): {e2}")
                    failed += 1
                    consecutive_failures += 1
            else:
                print(f"    ERR: HTTP {e.code}")
                failed += 1
                consecutive_failures += 1
        except Exception as e:
            print(f"    ERR: {e}")
            failed += 1
            consecutive_failures += 1
        
        # Rate limit protection - back off after consecutive failures
        if consecutive_failures >= 2:
            print(f"    Too many failures ({consecutive_failures}), backing off for 60s...")
            time.sleep(60)
            consecutive_failures = 0
        
        time.sleep(0.5)
    
    print(f"\nPublished: {success} | Failed: {failed}")
else:
    print("All products already published!")

# Step 5: Final sales check
print("\n>>> FINAL SALES CHECK...")
try:
    sales_data = api_get("https://api.gumroad.com/v2/sales")
    sales = sales_data.get('sales', [])
    total = sum(float(s.get('sale_price', 0)) for s in sales)
    print(f"Revenue: ${total:.2f} ({len(sales)} sales)")
except Exception as e:
    print(f"Error: {e}")
    total = 0.0

# Step 6: Summary
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
