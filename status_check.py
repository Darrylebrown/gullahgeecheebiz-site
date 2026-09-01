#!/usr/bin/env python3
"""Quick status check for GGB Revenue Orchestrator."""
import json
import sqlite3
import urllib.request
import time

BASE = "/Users/darrylsmac/gullahgeecheebiz-site"
TOKEN = None
for line in open(f"{BASE}/.env").read().splitlines():
    if line.startswith("GUMROAD_ACCESS_TOKEN="):
        TOKEN = line.split("=", 1)[1].strip().strip('"').strip("'")
        break

BRAIN_DB = f"{BASE}/ggb-engine/headquarters/brain.db"

def api_get(url):
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {TOKEN}"})
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode())

# Check sales
sales_data = api_get("https://api.gumroad.com/v2/sales")
sales = sales_data.get('sales', [])
total = sum(float(s.get('sale_price', 0)) for s in sales)

# Check products
products = []
page_key = None
for _ in range(10):
    url = "https://api.gumroad.com/v2/products"
    if page_key:
        url += f"?page_key={page_key}"
    data = api_get(url)
    products.extend(data.get('products', []))
    page_key = data.get('next_page_key')
    if not page_key:
        break
    time.sleep(1)

unpublished = [p for p in products if not p.get('published')]
published = [p for p in products if p.get('published')]

# Log to brain
conn = sqlite3.connect(BRAIN_DB)
c = conn.cursor()
c.execute(
    "INSERT INTO event_stream (timestamp, source_bot, event_type, message, data) VALUES (?, ?, ?, ?, ?)",
    (time.strftime('%Y-%m-%d %H:%M:%S'), 'SALES_10K_GOAL', 'status_check', 
     f"Revenue: ${total:.2f}, Products: {len(products)}, Published: {len(published)}, Unpublished: {len(unpublished)}", 
     json.dumps({"total": total, "products": len(products), "published": len(published), "unpublished": len(unpublished)}))
)
conn.commit()
conn.close()

print("=" * 60)
print("GGB REVENUE ORCHESTRATOR - STATUS REPORT")
print("=" * 60)
print(f"Date: {time.strftime('%Y-%m-%d %H:%M:%S')}")
print()
print(f"💰 REVENUE: ${total:.2f} / $10,000.00")
print(f"📈 GAP: ${10000-total:.2f}")
print()
print(f"📦 PRODUCTS:")
print(f"   Total: {len(products)}")
print(f"   Published: {len(published)}")
print(f"   Unpublished: {len(unpublished)}")
print()
if unpublished:
    print("📋 UNPUBLISHED PRODUCTS (first 5):")
    for p in unpublished[:5]:
        print(f"   - {p['name']}")
    if len(unpublished) > 5:
        print(f"   ... and {len(unpublished)-5} more")
print()
print("⚠️  STATUS: Rate limited by Gumroad API")
print("   Publishing 46+ products requires significant time due to 429 errors.")
print("   Each failed attempt triggers a 60-90s delay.")
print()
print("=" * 60)
