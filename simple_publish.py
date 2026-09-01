#!/usr/bin/env python3
"""Simple Gumroad publish script - publish all unpublished products."""
import json
import urllib.request
import urllib.error
import urllib.parse
import time

TOKEN = "Jf_2txZTGKVXX1Q0kS7BlscVAPe60G7bDOxtp7sqPuo"

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

print("Fetching all products...")
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

print(f"\nTotal products: {len(all_products)}")
unpublished = [p for p in all_products if not p.get('published')]
print(f"Unpublished: {len(unpublished)}")

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
    
    print("\nPublishing...")
    for p in unpublished[:5]:  # First 5 only for now
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
            'description': f'{name} — Gullah Geechee cultural heritage collection.',
            'custom_permalink': permalink,
        }
        
        try:
            result = api_post("https://api.gumroad.com/v2/products", params)
            if result.get("success"):
                prod = result.get("product", {})
                product_price = prod.get("price_cents", 0) / 100
                print(f"  OK {name}: ${product_price:.2f}")
            else:
                print(f"  FAIL {name}: {result.get('error', 'unknown')}")
        except urllib.error.HTTPError as e:
            print(f"  ERR {name}: HTTP {e.code}")
            if e.code == 429:
                print("  Waiting 60s...")
                time.sleep(60)
        time.sleep(2)

# Check sales
print("\nChecking sales...")
try:
    sales_data = api_get("https://api.gumroad.com/v2/sales")
    sales = sales_data.get('sales', [])
    total = sum(float(s.get('sale_price', 0)) for s in sales)
    print(f"Revenue: ${total:.2f} ({len(sales)} sales)")
except Exception as e:
    print(f"Error: {e}")
