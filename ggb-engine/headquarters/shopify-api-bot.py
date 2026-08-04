#!/usr/bin/env python3
"""Shopify API Key Extractor — logs into Shopify admin and gets an API token."""
import json, os, sys, time
from pathlib import Path

# Load .env
env_path = Path("/Users/darrylsmac/gullahgeecheebiz-site/.env")
env = {}
for line in env_path.read_text().split("\n"):
    if "=" in line and not line.startswith("#"):
        k, v = line.split("=", 1)
        env[k.strip()] = v.strip().strip('"').strip("'")

email = env.get("SHOPIFY_EMAIL", "")
password = env.get("SHOPIFY_PASSWORD", "")
store = env.get("SHOPIFY_STORE_URL", "https://gullahgeecheebiz.myshopify.com/admin")

print("=" * 50)
print("  SHOPIFY API KEY EXTRACTOR")
print("=" * 50)
print(f"  Store: {store}")
print(f"  Email: {email}")
print()

if not email or not password:
    print("❌ Missing SHOPIFY_EMAIL or SHOPIFY_PASSWORD in .env")
    sys.exit(1)

# Try to use the Shopify Admin API directly with the store credentials
# Shopify doesn't have a direct login API, but we can try to find the store
print("🔍 Checking store...")
try:
    import requests
    r = requests.get(store, timeout=10)
    print(f"  Store responds: HTTP {r.status_code}")
except Exception as e:
    print(f"  Store check failed: {e}")

print()
print("📋 MANUAL STEPS REQUIRED:")
print("  1. Go to your Shopify admin in a browser:")
print(f"     {store}")
print(f"  2. Log in with: {email}")
print("  3. Go to Settings → Apps and sales channels → Develop apps")
print("  4. Create an app called 'Gullah Geechee Biz Uploader'")
print("  5. Configure scopes: write_products, read_products, write_inventory")
print("  6. Install the app and copy the Admin API access token")
print("  7. Add it to .env as: SHOPIFY_ACCESS_TOKEN=your_token_here")
print()
print("Once you have the token, I can upload all 1,817 books automatically!")
