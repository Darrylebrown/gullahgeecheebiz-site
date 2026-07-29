#!/usr/bin/env python3
"""
Gullah Geechee Biz — Stripe Ebook Checkout Generator
Creates Stripe payment links for all 100 ebooks.
Customer pays → Stripe verifies → instant download.
"""

import json, os, subprocess, sys, time
from pathlib import Path

HOME = os.path.expanduser("~")
SITE_DIR = os.path.join(HOME, "gullahgeecheebiz-site")
STRIPE_SECRET = None

# Try to get Stripe key
env_path = os.path.join(HOME, ".hermes", ".env")
if os.path.exists(env_path):
    with open(env_path) as f:
        for line in f:
            if line.startswith("STRIPE_SECRET_KEY="):
                STRIPE_SECRET = line.strip().split("=", 1)[1].strip().strip('"').strip("'")

if not STRIPE_SECRET:
    # Try publish-automation env
    env_path2 = os.path.join(HOME, "publish-automation", ".env")
    if os.path.exists(env_path2):
        with open(env_path2) as f:
            for line in f:
                if "STRIPE" in line and "sk_live" in line:
                    parts = line.strip().split("=", 1)
                    if len(parts) > 1:
                        STRIPE_SECRET = parts[1].strip().strip('"').strip("'")

EBOOKS = [
    {"slug": "gullah-resilience", "title": "The Gullah Geechee Guide to Resilience", "price": 999},
    {"slug": "gullah-mindset", "title": "The Gullah Geechee Mindset", "price": 999},
    {"slug": "gullah-identity", "title": "Finding Your Roots: A Gullah Geechee Guide to Identity", "price": 999},
    {"slug": "gullah-purpose", "title": "The Gullah Geechee Guide to Purpose", "price": 999},
    {"slug": "gullah-gratitude", "title": "Gullah Geechee Gratitude", "price": 999},
    {"slug": "gullah-healing", "title": "Gullah Geechee Healing", "price": 999},
    {"slug": "gullah-calm", "title": "The Gullah Geechee Guide to Calm", "price": 999},
    {"slug": "gullah-joy", "title": "Gullah Geechee Joy", "price": 999},
    {"slug": "gullah-grief", "title": "Gullah Geechee Wisdom for Grief", "price": 999},
    {"slug": "gullah-courage", "title": "Gullah Geechee Courage", "price": 999},
    {"slug": "gullah-patience", "title": "The Gullah Geechee Art of Patience", "price": 999},
    {"slug": "gullah-community", "title": "The Gullah Geechee Way of Community", "price": 999},
    {"slug": "gullah-wisdom", "title": "Gullah Geechee Wisdom for Daily Living", "price": 999},
    {"slug": "gullah-fatherhood", "title": "Gullah Geechee Fatherhood", "price": 999},
    {"slug": "gullah-motherhood", "title": "Gullah Geechee Motherhood", "price": 999},
    {"slug": "gullah-forgiveness", "title": "Gullah Geechee Forgiveness", "price": 999},
    {"slug": "gullah-hope", "title": "Gullah Geechee Hope", "price": 999},
    {"slug": "gullah-elders", "title": "Honoring Gullah Geechee Elders", "price": 999},
    {"slug": "gullah-marriage", "title": "Gullah Geechee Marriage", "price": 999},
    {"slug": "gullah-grandparenting", "title": "Gullah Geechee Grandparenting", "price": 999},
    {"slug": "gullah-aging", "title": "Gullah Geechee Guide to Aging Well", "price": 999},
    {"slug": "gullah-mental-health", "title": "Gullah Geechee Guide to Mental Health", "price": 999},
    {"slug": "gullah-sabbath", "title": "The Gullah Geechee Sabbath", "price": 999},
    {"slug": "gullah-relationships", "title": "Gullah Geechee Relationships", "price": 999},
    {"slug": "gullah-morning", "title": "Gullah Geechee Morning Rituals", "price": 999},
    {"slug": "gullah-bedtime", "title": "Gullah Geechee Bedtime Rituals", "price": 999},
    {"slug": "gullah-spring", "title": "Gullah Geechee Spring", "price": 999},
    {"slug": "gullah-summer", "title": "Gullah Geechee Summer", "price": 999},
    {"slug": "gullah-autumn", "title": "Gullah Geechee Autumn", "price": 999},
    {"slug": "gullah-winter", "title": "Gullah Geechee Winter", "price": 999},
    {"slug": "gullah-entrepreneur", "title": "The Gullah Geechee Entrepreneur", "price": 999},
    {"slug": "lowcountry-marketing", "title": "Lowcountry Marketing", "price": 999},
    {"slug": "gullah-side-hustle", "title": "The Gullah Geechee Side Hustle", "price": 999},
    {"slug": "gullah-finance", "title": "Gullah Geechee Guide to Financial Freedom", "price": 999},
    {"slug": "gullah-publishing", "title": "The Gullah Geechee Guide to Self-Publishing", "price": 999},
    {"slug": "gullah-ecommerce", "title": "Gullah Geechee E-Commerce", "price": 999},
    {"slug": "gullah-tourism", "title": "Gullah Geechee Tourism Guide", "price": 999},
    {"slug": "gullah-craft-business", "title": "The Gullah Geechee Craft Business Guide", "price": 999},
    {"slug": "gullah-food-business", "title": "Starting a Gullah Geechee Food Business", "price": 999},
    {"slug": "gullah-cooperative", "title": "The Gullah Geechee Cooperative", "price": 999},
    {"slug": "gullah-freelance", "title": "The Gullah Geechee Freelancer", "price": 999},
    {"slug": "gullah-real-estate", "title": "Gullah Geechee Guide to Real Estate", "price": 999},
    {"slug": "gullah-nonprofit", "title": "Starting a Gullah Geechee Nonprofit", "price": 999},
    {"slug": "gullah-investing", "title": "Gullah Geechee Investing", "price": 999},
    {"slug": "gullah-consulting", "title": "The Gullah Geechee Consultant", "price": 999},
    {"slug": "gullah-remote-work", "title": "Gullah Geechee Guide to Remote Work", "price": 999},
    {"slug": "gullah-budget", "title": "The Gullah Geechee Budget", "price": 999},
    {"slug": "gullah-credit", "title": "Gullah Geechee Guide to Credit", "price": 999},
    {"slug": "gullah-debt", "title": "Gullah Geechee Guide to Debt Freedom", "price": 999},
    {"slug": "gullah-retirement", "title": "Gullah Geechee Guide to Retirement", "price": 999},
    {"slug": "gullah-taxes", "title": "Gullah Geechee Guide to Taxes", "price": 999},
    {"slug": "gullah-insurance", "title": "Gullah Geechee Guide to Insurance", "price": 999},
    {"slug": "gullah-estate", "title": "Gullah Geechee Guide to Estate Planning", "price": 999},
    {"slug": "gullah-farming", "title": "The Gullah Geechee Farmer", "price": 999},
    {"slug": "gullah-fishing", "title": "The Gullah Geechee Fisherman", "price": 999},
    {"slug": "gullah-catering", "title": "Starting a Gullah Geechee Catering Business", "price": 999},
    {"slug": "gullah-bed-breakfast", "title": "Starting a Gullah Geechee Bed and Breakfast", "price": 999},
    {"slug": "gullah-art-gallery", "title": "Starting a Gullah Geechee Art Gallery", "price": 999},
    {"slug": "gullah-museum", "title": "Starting a Gullah Geechee Museum", "price": 999},
    {"slug": "gullah-podcast", "title": "Starting a Gullah Geechee Podcast", "price": 999},
    {"slug": "gullah-youtube", "title": "Starting a Gullah Geechee YouTube Channel", "price": 999},
    {"slug": "gullah-newsletter", "title": "Starting a Gullah Geechee Newsletter", "price": 999},
    {"slug": "gullah-etsy", "title": "Selling Gullah Geechee Products on Etsy", "price": 999},
    {"slug": "gullah-wholesale", "title": "The Gullah Geechee Guide to Wholesale", "price": 999},
    {"slug": "gullah-kitchen-v1", "title": "The Gullah Geechee Kitchen Volume 1", "price": 999},
    {"slug": "gullah-kitchen-v2", "title": "The Gullah Geechee Kitchen Volume 2", "price": 999},
    {"slug": "gullah-sunday-dinner", "title": "Gullah Geechee Sunday Dinner", "price": 999},
    {"slug": "gullah-seafood", "title": "Gullah Geechee Seafood Cookbook", "price": 999},
    {"slug": "gullah-soul-food", "title": "Gullah Geechee Soul Food", "price": 999},
    {"slug": "gullah-desserts", "title": "Gullah Geechee Desserts", "price": 999},
    {"slug": "gullah-one-pot", "title": "Gullah Geechee One-Pot Meals", "price": 999},
    {"slug": "gullah-holiday", "title": "Gullah Geechee Holiday Cookbook", "price": 999},
    {"slug": "gullah-vegetarian", "title": "Gullah Geechee Vegetarian", "price": 999},
    {"slug": "gullah-breakfast", "title": "Gullah Geechee Breakfast", "price": 999},
    {"slug": "gullah-preserving", "title": "Gullah Geechee Guide to Preserving", "price": 999},
    {"slug": "gullah-grilling", "title": "Gullah Geechee Grilling", "price": 999},
    {"slug": "gullah-sauces", "title": "Gullah Geechee Sauces and Seasonings", "price": 999},
    {"slug": "gullah-baking", "title": "Gullah Geechee Baking", "price": 999},
    {"slug": "gullah-drinks", "title": "Gullah Geechee Drinks and Beverages", "price": 999},
    {"slug": "gullah-rice", "title": "Gullah Geechee Rice Cookbook", "price": 999},
    {"slug": "gullah-cast-iron", "title": "Gullah Geechee Cast Iron Cooking", "price": 999},
    {"slug": "gullah-slow-cooker", "title": "Gullah Geechee Slow Cooker Recipes", "price": 999},
    {"slug": "gullah-30-minute", "title": "Gullah Geechee 30-Minute Meals", "price": 999},
    {"slug": "gullah-meal-prep", "title": "Gullah Geechee Meal Prep", "price": 999},
    {"slug": "gullah-kids-cook", "title": "Gullah Geechee Kids Cookbook", "price": 999},
    {"slug": "gullah-appetizers", "title": "Gullah Geechee Appetizers", "price": 999},
    {"slug": "gullah-summer-cooking", "title": "Gullah Geechee Summer Cooking", "price": 999},
    {"slug": "gullah-winter-cooking", "title": "Gullah Geechee Winter Cooking", "price": 999},
    {"slug": "gullah-cajun", "title": "Gullah Geechee and Cajun Cooking", "price": 999},
    {"slug": "gullah-caribbean", "title": "Gullah Geechee and Caribbean Cooking", "price": 999},
    {"slug": "gullah-west-african", "title": "Gullah Geechee and West African Cooking", "price": 999},
    {"slug": "gullah-fermentation", "title": "Gullah Geechee Fermentation", "price": 999},
    {"slug": "gullah-gluten-free", "title": "Gullah Geechee Gluten-Free Cooking", "price": 999},
    {"slug": "gullah-vegan", "title": "Gullah Geechee Vegan Cooking", "price": 999},
    {"slug": "gullah-keto", "title": "Gullah Geechee Keto Cooking", "price": 999},
    {"slug": "gullah-paleo", "title": "Gullah Geechee Paleo Cooking", "price": 999},
    {"slug": "gullah-air-fryer", "title": "Gullah Geechee Air Fryer Recipes", "price": 999},
    {"slug": "gullah-instant-pot", "title": "Gullah Geechee Instant Pot Recipes", "price": 999},
    {"slug": "gullah-camping", "title": "Gullah Geechee Camp Cooking", "price": 999},
]

def create_stripe_product(book):
    """Create a Stripe product and price for an ebook."""
    if not STRIPE_SECRET:
        return None, None
    
    # Create product
    result = subprocess.run([
        "curl", "-s", "-X", "POST", "https://api.stripe.com/v1/products",
        "-u", f"{STRIPE_SECRET}:",
        "-d", f"name={book['title']}",
        "-d", "type=good",
        "-d", f"metadata[ebook_slug]={book['slug']}",
        "-d", "metadata[source]=ebook-generator"
    ], capture_output=True, text=True)
    
    try:
        product = json.loads(result.stdout)
        product_id = product.get("id")
        if not product_id:
            return None, None
        
        # Create price
        price_result = subprocess.run([
            "curl", "-s", "-X", "POST", "https://api.stripe.com/v1/prices",
            "-u", f"{STRIPE_SECRET}:",
            "-d", f"product={product_id}",
            "-d", f"unit_amount={book['price']}",
            "-d", "currency=usd"
        ], capture_output=True, text=True)
        
        price = json.loads(price_result.stdout)
        price_id = price.get("id")
        
        return product_id, price_id
    except:
        return None, None

def create_checkout_link(price_id, book):
    """Create a Stripe checkout session and return the URL."""
    if not price_id or not STRIPE_SECRET:
        return None
    
    result = subprocess.run([
        "curl", "-s", "-X", "POST", "https://api.stripe.com/v1/checkout/sessions",
        "-u", f"{STRIPE_SECRET}:",
        "-d", "mode=payment",
        "-d", f"line_items[0][price]={price_id}",
        "-d", "line_items[0][quantity]=1",
        "-d", "success_url=https://gullahgeecheebiz.com/redeem/success.html?session_id={CHECKOUT_SESSION_ID}&ebook=" + book['slug'],
        "-d", "cancel_url=https://gullahgeecheebiz.com/shop.html",
        "-d", f"metadata[ebook_slug]={book['slug']}"
    ], capture_output=True, text=True)
    
    try:
        session = json.loads(result.stdout)
        return session.get("url")
    except:
        return None

def main():
    if not STRIPE_SECRET:
        print("❌ No Stripe secret key found. Set STRIPE_SECRET_KEY in .hermes/.env")
        sys.exit(1)
    
    print(f"📚 Creating Stripe products for {len(EBOOKS)} ebooks...")
    print(f"   (This will take a few minutes)")
    print()
    
    results = []
    
    for i, book in enumerate(EBOOKS, 1):
        print(f"  [{i}/{len(EBOOKS)}] {book['title']}...", end=" ", flush=True)
        
        product_id, price_id = create_stripe_product(book)
        if not product_id:
            print("❌")
            continue
        
        checkout_url = create_checkout_link(price_id, book)
        if checkout_url:
            print("✅")
            results.append({
                "slug": book["slug"],
                "title": book["title"],
                "price": book["price"],
                "product_id": product_id,
                "price_id": price_id,
                "checkout_url": checkout_url
            })
        else:
            print("⚠️  no checkout URL")
    
    # Save results
    output_path = os.path.join(SITE_DIR, "downloads", "stripe-links.json")
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)
    
    print(f"\n📊 Results: {len(results)}/{len(EBOOKS)} checkout links created")
    print(f"📍 Saved to: {output_path}")
    
    # Print a few sample links
    print(f"\n📎 Sample links:")
    for r in results[:5]:
        print(f"  {r['title']}: {r['checkout_url']}")


if __name__ == "__main__":
    main()
