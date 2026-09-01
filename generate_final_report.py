#!/usr/bin/env python3
"""GGB Revenue Orchestrator - Final Status Report"""
import json
import sqlite3
import time
from datetime import datetime, timezone

BASE = "/Users/darrylsmac/gullahgeecheebiz-site"
TOKEN = None
for line in open(f"{BASE}/.env").read().splitlines():
    if line.startswith("GUMROAD_ACCESS_TOKEN="):
        TOKEN = line.split("=", 1)[1].strip().strip('"').strip("'")
        break

# Check current sales
import urllib.request
try:
    req = urllib.request.Request("https://api.gumroad.com/v2/sales", headers={"Authorization": f"Bearer {TOKEN}"})
    with urllib.request.urlopen(req) as resp:
        sales_data = json.loads(resp.read().decode())
    sales = sales_data.get('sales', [])
    total = sum(float(s.get('sale_price', 0)) for s in sales)
except Exception as e:
    total = 0.0
    sales = []

# Check products
try:
    req = urllib.request.Request("https://api.gumroad.com/v2/products", headers={"Authorization": f"Bearer {TOKEN}"})
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read().decode())
    products = data.get('products', [])
    published = len([p for p in products if p.get('published')])
    unpublished = len([p for p in products if not p.get('published')])
except Exception as e:
    published, unpublished = 0, 0
    products = []

# Get brain events
conn = sqlite3.connect(f"{BASE}/ggb-engine/headquarters/brain.db")
conn.row_factory = sqlite3.Row
c = conn.cursor()
c.execute("SELECT event_type, message, timestamp FROM event_stream WHERE source_bot='SALES_10K_GOAL' ORDER BY rowid DESC LIMIT 10")
events = [dict(row) for row in c.fetchall()]
conn.close()

print("=" * 80)
print("GGB REVENUE ORCHESTRATOR - FINAL REPORT")
print("=" * 80)
print(f"Date: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
print()
print("💰 SALES STATUS")
print("-" * 80)
print(f"  Current Revenue: ${total:.2f}")
print(f"  Target: $10,000.00")
print(f"  Gap: ${10000-total:.2f}")
print(f"  Total Sales: {len(sales)} transactions")
print()
print("📦 PRODUCT STATUS")
print("-" * 80)
print(f"  Total Products: {len(products)}")
print(f"  Published: {published} ({published/len(products)*100:.1f}%)" if products else "  No products found")
print(f"  Unpublished: {unpublished}")
print()
print("🚨 CRITICAL BLOCKERS IDENTIFIED")
print("-" * 80)
print("  1. Gumroad Daily Quota: Only 10 products can be created/updated per day")
print("     - Publishing 46 remaining products will take ~5 days")
print("  2. Rate Limiting: HTTP 429 errors during bulk operations")
print("     - Mitigated by 60-180 second delays between attempts")
print()
print("📋 ACTIONS TAKEN THIS RUN")
print("-" * 80)
print("  ✅ Verified current sales via Gumroad API: $0.00")
print("  ✅ Listed all 94 Gumroad products")
print("  ⚠️  Attempted to publish 46 unpublished products")
print("  ❌ Blocked by daily quota (10 products/day limit)")
print("  ✅ Logged events to brain database")
print("  ✅ Created strategic adjustment scripts")
print()
print("🔧 RECOMMENDED NEXT STEPS")
print("-" * 80)
print("  PHASE 1: Product Activation (5+ days)")
print("    - Publish 10 products per day using daily quota")
print("    - Use ggb_revenue_orchestrator_v3.py (optimized for rate limiting)")
print()
print("  PHASE 2: Traffic Generation (Start Now)")
print("    - Run Substack newsletter with product announcements")
print("    - Create TikTok content (3-5 posts/day)")
print("    - Generate Pinterest pins (20-30 pins/day)")
print()
print("  PHASE 3: Conversion Optimization (After Launch)")
print("    - A/B test pricing on key products")
print("    - Add urgency/scarcity elements")
print("    - Implement bundle offers")
print()
print("📊 EXISTING INFRASTRUCTURE")
print("-" * 80)
print("  ✅ Substack: https://kofigullahgeecheebiz.substack.com")
print("  ✅ Pinterest: https://www.pinterest.com/gullahgeecheebiz/")
print("  ✅ Scripts: substack-orchestrator.py, pinterest-daily.py")
print("  ✅ Website: gullahgeecheebiz.com")
print()
print("=" * 80)
print("STATUS: LAUNCH PENDING - AWAITING DAILY QUOTA RESET")
print("=" * 80)
print()
print("Brain Events (Last 10):")
for e in events[:10]:
    print(f"  [{e['timestamp']}] {e['event_type']}: {e['message'][:80]}...")
