#!/usr/bin/env python3
"""Debug Gumroad API endpoints."""
import json, os, requests, time

BASE = "/Users/darrylsmac/gullahgeecheebiz-site"
ENV = f"{BASE}/.env"
API = "https://api.gumroad.com/v2"

def load_token():
    for line in open(ENV).read().splitlines():
        if "GUMROAD_ACCESS_TOKEN" in line:
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    return None

TOKEN = load_token()
params = {"access_token": TOKEN}

# 1. Get all products with full details
print("=" * 60)
print("TESTING GUMROAD API ENDPOINTS")
print("=" * 60)

# List products
r = requests.get(f"{API}/products", params=params, timeout=30)
data = r.json()
print(f"\nGET /products: {r.status_code}")
if data.get("success"):
    products = data["products"]
    print(f"  Found {len(products)} products")
    for p in products:
        pid = p["id"]
        name = p["name"]
        files = p.get("files", [])
        print(f"  - {name} (ID: {pid[:30]}...) | files: {len(files)}")
else:
    print(f"  Error: {data}")

# 2. Test getting a single product
if products:
    p = products[0]
    pid = p["id"]
    print(f"\nTesting single product GET for: {p['name']}")
    
    # Try different URL formats
    for path in [f"/products/{pid}", f"/products/{pid}", f"/product/show", f"/products/{pid}?include_permalink_url=true"]:
        r = requests.get(f"{API}{path}", params=params, timeout=30)
        print(f"  {path}: {r.status_code}")
        if r.status_code == 200:
            print(f"    Success: {json.dumps(r.json(), indent=2)[:300]}")
        else:
            print(f"    Error: {r.text[:200]}")

# 3. Test file upload endpoint
print(f"\nTesting file upload endpoint:")
for path in ["/products/{id}/files", "/product/purchase", "/products/{id}/publish"]:
    url = f"{API}{path}".format(id=pid)
    print(f"  Testing {url}")
    r = requests.post(url, params=params, timeout=30)
    print(f"    POST: {r.status_code}")
    print(f"    Response: {r.text[:200]}")

print("\nDone!")
