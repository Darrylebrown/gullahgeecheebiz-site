#!/usr/bin/env python3
"""
GGB Sales Orchestrator - Autonomous Revenue Generation
Continues working toward $10,000 sales goal
"""
import json
import urllib.request
import time
from pathlib import Path
from datetime import datetime, timezone

BASE_DIR = Path("/Users/darrylsmac/gullahgeecheebiz-site")
ENV_FILE = BASE_DIR / ".env"
EVENT_STREAM = BASE_DIR / "publish" / "event_stream.jsonl"

def log_event(action, detail):
    event = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "source_bot": "SALES_10K_GOAL",
        "action": action,
        "detail": detail
    }
    with open(EVENT_STREAM, "a", encoding="utf-8") as f:
        f.write(json.dumps(event) + "\n")
    print(f"[EVENT] {action}: {detail}")

def get_token():
    token = None
    with open(ENV_FILE, 'r') as f:
        for line in f:
            if line.startswith('GUMROAD_ACCESS_TOKEN='):
                token = line.strip().split('=', 1)[1]
                break
    return token

def check_sales():
    token = get_token()
    req = urllib.request.Request(
        "https://api.gumroad.com/v2/sales",
        headers={"Authorization": f"Bearer {token}"}
    )
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read().decode())
    sales = data.get('sales', [])
    total = sum(s.get('sale_price_cents', 0) for s in sales)
    return len(sales), total / 100

def check_products():
    token = get_token()
    all_products = []
    page_key = None
    while True:
        url = 'https://api.gumroad.com/v2/products?limit=50'
        if page_key:
            url += f'&page_key={page_key}'
        req = urllib.request.Request(url, headers={'Authorization': f'Bearer {token}'})
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode())
        products = data.get('products', [])
        all_products.extend(products)
        page_key = data.get('next_page_key')
        if not page_key:
            break
    return all_products

def main():
    print(f"\n{'='*60}")
    print(f"🎯 GGB SALES ORCHESTRATOR")
    print(f"   {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print(f"{'='*60}\n")
    
    # Check current sales
    sales_count, total_revenue = check_sales()
    print(f"💰 Current Sales: ${total_revenue:.2f} / $10,000.00")
    print(f"📊 Sales Count: {sales_count}")
    
    if total_revenue >= 10000:
        log_event("goal_reached", f"Target achieved! Total: ${total_revenue:.2f}")
        print("\n✅ GOAL REACHED! $10,000 in sales achieved!")
        return
    
    # Check product status
    products = check_products()
    published = [p for p in products if p.get('published')]
    unpublished = [p for p in products if not p.get('published')]
    
    print(f"\n📦 Products: {len(products)} total ({len(published)} published, {len(unpublished)} unpublished)")
    
    # Log status
    log_event("status_check", f"Revenue: ${total_revenue:.2f}, Products: {len(products)}, Published: {len(published)}")
    
    # If there are unpublished products, publish them
    if unpublished:
        print(f"\n🚀 Publishing {len(unpublished)} products...")
        for p in unpublished[:5]:  # Publish first 5 as test
            product_id = p['id']
            name = p['name']
            description = p.get('description', '') or f"{name} by Darryl Elliott Brown"
            
            update_data = {
                'access_token': get_token(),
                'description': description,
                'published': 'true',
                'tags': ['gullah', 'geechee', 'encyclopedia', 'history', 'culture']
            }
            
            url = f"https://api.gumroad.com/v2/products/{product_id}"
            req = urllib.request.Request(
                url,
                data=json.dumps(update_data).encode(),
                headers={'Authorization': f"Bearer {get_token()}", 'Content-Type': 'application/json'},
                method='PUT'
            )
            
            try:
                with urllib.request.urlopen(req) as resp:
                    result = json.loads(resp.read().decode())
                    if result.get('success'):
                        print(f"  ✅ {name}")
            except Exception as e:
                print(f"  ❌ {name}: {e}")
            
            time.sleep(0.5)
    
    # Generate more content
    print(f"\n📝 Generating marketing content...")
    viral_dir = BASE_DIR / "viral"
    tiktok_dir = BASE_DIR / "publish" / "promotion" / "googleplay"
    
    # Create additional TikTok scripts
    existing_scripts = list(tiktok_dir.glob("*tiktok*.md"))
    script_count = len(existing_scripts)
    
    if script_count < 50:
        new_scripts = []
        for i in range(script_count + 1, min(script_count + 11, 51)):
            script = f"""TikTok Script #{i}

🎬 HOOK: "The Gullah Geechee people are the direct link to West Africa in America."

📝 BODY: "Their language, food, crafts, and spiritual practices preserve 300+ years of history. This isn't just culture — it's resilience.

The complete encyclopedia captures it all. 25 volumes. One collection."

💰 CTA: "Get the full collection at gullahgeecheebiz.com"

🏷️ HASHTAGS:
#gullah #geechee #history #blackhistory #culture #education"""
            new_scripts.append(script)
        
        output_file = tiktok_dir / f"tiktok-scripts-batch{int(script_count/10)+1}.md"
        output_file.write_text("\n\n".join(new_scripts), encoding="utf-8")
        print(f"  ✅ Created {len(new_scripts)} new TikTok scripts")
    
    print(f"\n📈 Next steps:")
    print(f"   • Drive traffic through social media")
    print(f"   • Monitor sales conversion")
    print(f"   • Optimize product listings")
    print(f"   • Scale content production")
    
    print(f"\n{'='*60}")
    print(f"Current: ${total_revenue:.2f} | Target: $10,000.00 | Remaining: ${10000 - total_revenue:.2f}")
    print(f"{'='*60}\n")

if __name__ == "__main__":
    main()
