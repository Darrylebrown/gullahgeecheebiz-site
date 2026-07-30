#!/usr/bin/env python3
"""
Gullah Geechee Biz — Shopify Product Feed Generator
Creates CSV product feed for Shopify PDF store with bundles.
"""

import csv, json, os
from pathlib import Path
from datetime import date

HOME = Path.home()
OUT_DIR = HOME / "shopify-products"
OUT_DIR.mkdir(parents=True, exist_ok=True)

EBOOKS = [
    {"slug": "gullah-resilience", "title": "The Gullah Geechee Guide to Resilience", "cat": "self-help"},
    {"slug": "gullah-mindset", "title": "The Gullah Geechee Mindset", "cat": "self-help"},
    {"slug": "gullah-identity", "title": "Finding Your Roots: A Gullah Geechee Guide to Identity", "cat": "self-help"},
    {"slug": "gullah-purpose", "title": "The Gullah Geechee Guide to Purpose", "cat": "self-help"},
    {"slug": "gullah-gratitude", "title": "Gullah Geechee Gratitude", "cat": "self-help"},
    {"slug": "gullah-healing", "title": "Gullah Geechee Healing", "cat": "self-help"},
    {"slug": "gullah-calm", "title": "The Gullah Geechee Guide to Calm", "cat": "self-help"},
    {"slug": "gullah-joy", "title": "Gullah Geechee Joy", "cat": "self-help"},
    {"slug": "gullah-grief", "title": "Gullah Geechee Wisdom for Grief", "cat": "self-help"},
    {"slug": "gullah-courage", "title": "Gullah Geechee Courage", "cat": "self-help"},
    {"slug": "gullah-patience", "title": "The Gullah Geechee Art of Patience", "cat": "self-help"},
    {"slug": "gullah-community", "title": "The Gullah Geechee Way of Community", "cat": "self-help"},
    {"slug": "gullah-wisdom", "title": "Gullah Geechee Wisdom for Daily Living", "cat": "self-help"},
    {"slug": "gullah-fatherhood", "title": "Gullah Geechee Fatherhood", "cat": "self-help"},
    {"slug": "gullah-motherhood", "title": "Gullah Geechee Motherhood", "cat": "self-help"},
    {"slug": "gullah-forgiveness", "title": "Gullah Geechee Forgiveness", "cat": "self-help"},
    {"slug": "gullah-hope", "title": "Gullah Geechee Hope", "cat": "self-help"},
    {"slug": "gullah-elders", "title": "Honoring Gullah Geechee Elders", "cat": "self-help"},
    {"slug": "gullah-marriage", "title": "Gullah Geechee Marriage", "cat": "self-help"},
    {"slug": "gullah-grandparenting", "title": "Gullah Geechee Grandparenting", "cat": "self-help"},
    {"slug": "gullah-aging", "title": "Gullah Geechee Guide to Aging Well", "cat": "self-help"},
    {"slug": "gullah-mental-health", "title": "Gullah Geechee Guide to Mental Health", "cat": "self-help"},
    {"slug": "gullah-sabbath", "title": "The Gullah Geechee Sabbath", "cat": "self-help"},
    {"slug": "gullah-relationships", "title": "Gullah Geechee Relationships", "cat": "self-help"},
    {"slug": "gullah-morning", "title": "Gullah Geechee Morning Rituals", "cat": "self-help"},
    {"slug": "gullah-bedtime", "title": "Gullah Geechee Bedtime Rituals", "cat": "self-help"},
    {"slug": "gullah-spring", "title": "Gullah Geechee Spring", "cat": "self-help"},
    {"slug": "gullah-summer", "title": "Gullah Geechee Summer", "cat": "self-help"},
    {"slug": "gullah-autumn", "title": "Gullah Geechee Autumn", "cat": "self-help"},
    {"slug": "gullah-winter", "title": "Gullah Geechee Winter", "cat": "self-help"},
    {"slug": "gullah-gratitude-journal", "title": "The Gullah Geechee Gratitude Journal", "cat": "self-help"},
    {"slug": "gullah-entrepreneur", "title": "The Gullah Geechee Entrepreneur", "cat": "business"},
    {"slug": "lowcountry-marketing", "title": "Lowcountry Marketing", "cat": "business"},
    {"slug": "gullah-side-hustle", "title": "The Gullah Geechee Side Hustle", "cat": "business"},
    {"slug": "gullah-finance", "title": "Gullah Geechee Guide to Financial Freedom", "cat": "business"},
    {"slug": "gullah-publishing", "title": "The Gullah Geechee Guide to Self-Publishing", "cat": "business"},
    {"slug": "gullah-ecommerce", "title": "Gullah Geechee E-Commerce", "cat": "business"},
    {"slug": "gullah-tourism", "title": "Gullah Geechee Tourism Guide", "cat": "business"},
    {"slug": "gullah-craft-business", "title": "The Gullah Geechee Craft Business Guide", "cat": "business"},
    {"slug": "gullah-food-business", "title": "Starting a Gullah Geechee Food Business", "cat": "business"},
    {"slug": "gullah-cooperative", "title": "The Gullah Geechee Cooperative", "cat": "business"},
    {"slug": "gullah-freelance", "title": "The Gullah Geechee Freelancer", "cat": "business"},
    {"slug": "gullah-real-estate", "title": "Gullah Geechee Guide to Real Estate", "cat": "business"},
    {"slug": "gullah-nonprofit", "title": "Starting a Gullah Geechee Nonprofit", "cat": "business"},
    {"slug": "gullah-investing", "title": "Gullah Geechee Investing", "cat": "business"},
    {"slug": "gullah-consulting", "title": "The Gullah Geechee Consultant", "cat": "business"},
    {"slug": "gullah-remote-work", "title": "Gullah Geechee Guide to Remote Work", "cat": "business"},
    {"slug": "gullah-budget", "title": "The Gullah Geechee Budget", "cat": "business"},
    {"slug": "gullah-credit", "title": "Gullah Geechee Guide to Credit", "cat": "business"},
    {"slug": "gullah-debt", "title": "Gullah Geechee Guide to Debt Freedom", "cat": "business"},
    {"slug": "gullah-retirement", "title": "Gullah Geechee Guide to Retirement", "cat": "business"},
    {"slug": "gullah-taxes", "title": "Gullah Geechee Guide to Taxes", "cat": "business"},
    {"slug": "gullah-insurance", "title": "Gullah Geechee Guide to Insurance", "cat": "business"},
    {"slug": "gullah-estate", "title": "Gullah Geechee Guide to Estate Planning", "cat": "business"},
    {"slug": "gullah-farming", "title": "The Gullah Geechee Farmer", "cat": "business"},
    {"slug": "gullah-fishing", "title": "The Gullah Geechee Fisherman", "cat": "business"},
    {"slug": "gullah-catering", "title": "Starting a Gullah Geechee Catering Business", "cat": "business"},
    {"slug": "gullah-bed-breakfast", "title": "Starting a Gullah Geechee Bed and Breakfast", "cat": "business"},
    {"slug": "gullah-art-gallery", "title": "Starting a Gullah Geechee Art Gallery", "cat": "business"},
    {"slug": "gullah-museum", "title": "Starting a Gullah Geechee Museum", "cat": "business"},
    {"slug": "gullah-podcast", "title": "Starting a Gullah Geechee Podcast", "cat": "business"},
    {"slug": "gullah-youtube", "title": "Starting a Gullah Geechee YouTube Channel", "cat": "business"},
    {"slug": "gullah-newsletter", "title": "Starting a Gullah Geechee Newsletter", "cat": "business"},
    {"slug": "gullah-etsy", "title": "Selling Gullah Geechee Products on Etsy", "cat": "business"},
    {"slug": "gullah-wholesale", "title": "The Gullah Geechee Guide to Wholesale", "cat": "business"},
    {"slug": "gullah-kitchen-v1", "title": "The Gullah Geechee Kitchen Volume 1", "cat": "cooking"},
    {"slug": "gullah-kitchen-v2", "title": "The Gullah Geechee Kitchen Volume 2", "cat": "cooking"},
    {"slug": "gullah-sunday-dinner", "title": "Gullah Geechee Sunday Dinner", "cat": "cooking"},
    {"slug": "gullah-seafood", "title": "Gullah Geechee Seafood Cookbook", "cat": "cooking"},
    {"slug": "gullah-soul-food", "title": "Gullah Geechee Soul Food", "cat": "cooking"},
    {"slug": "gullah-desserts", "title": "Gullah Geechee Desserts", "cat": "cooking"},
    {"slug": "gullah-one-pot", "title": "Gullah Geechee One-Pot Meals", "cat": "cooking"},
    {"slug": "gullah-holiday", "title": "Gullah Geechee Holiday Cookbook", "cat": "cooking"},
    {"slug": "gullah-vegetarian", "title": "Gullah Geechee Vegetarian", "cat": "cooking"},
    {"slug": "gullah-breakfast", "title": "Gullah Geechee Breakfast", "cat": "cooking"},
    {"slug": "gullah-preserving", "title": "Gullah Geechee Guide to Preserving", "cat": "cooking"},
    {"slug": "gullah-grilling", "title": "Gullah Geechee Grilling", "cat": "cooking"},
    {"slug": "gullah-sauces", "title": "Gullah Geechee Sauces and Seasonings", "cat": "cooking"},
    {"slug": "gullah-baking", "title": "Gullah Geechee Baking", "cat": "cooking"},
    {"slug": "gullah-drinks", "title": "Gullah Geechee Drinks and Beverages", "cat": "cooking"},
    {"slug": "gullah-rice", "title": "Gullah Geechee Rice Cookbook", "cat": "cooking"},
    {"slug": "gullah-cast-iron", "title": "Gullah Geechee Cast Iron Cooking", "cat": "cooking"},
    {"slug": "gullah-slow-cooker", "title": "Gullah Geechee Slow Cooker Recipes", "cat": "cooking"},
    {"slug": "gullah-30-minute", "title": "Gullah Geechee 30-Minute Meals", "cat": "cooking"},
    {"slug": "gullah-meal-prep", "title": "Gullah Geechee Meal Prep", "cat": "cooking"},
    {"slug": "gullah-kids-cook", "title": "Gullah Geechee Kids Cookbook", "cat": "cooking"},
    {"slug": "gullah-appetizers", "title": "Gullah Geechee Appetizers", "cat": "cooking"},
    {"slug": "gullah-summer-cooking", "title": "Gullah Geechee Summer Cooking", "cat": "cooking"},
    {"slug": "gullah-winter-cooking", "title": "Gullah Geechee Winter Cooking", "cat": "cooking"},
    {"slug": "gullah-cajun", "title": "Gullah Geechee and Cajun Cooking", "cat": "cooking"},
    {"slug": "gullah-caribbean", "title": "Gullah Geechee and Caribbean Cooking", "cat": "cooking"},
    {"slug": "gullah-west-african", "title": "Gullah Geechee and West African Cooking", "cat": "cooking"},
    {"slug": "gullah-fermentation", "title": "Gullah Geechee Fermentation", "cat": "cooking"},
    {"slug": "gullah-gluten-free", "title": "Gullah Geechee Gluten-Free Cooking", "cat": "cooking"},
    {"slug": "gullah-vegan", "title": "Gullah Geechee Vegan Cooking", "cat": "cooking"},
    {"slug": "gullah-keto", "title": "Gullah Geechee Keto Cooking", "cat": "cooking"},
    {"slug": "gullah-paleo", "title": "Gullah Geechee Paleo Cooking", "cat": "cooking"},
    {"slug": "gullah-air-fryer", "title": "Gullah Geechee Air Fryer Recipes", "cat": "cooking"},
    {"slug": "gullah-instant-pot", "title": "Gullah Geechee Instant Pot Recipes", "cat": "cooking"},
    {"slug": "gullah-camping", "title": "Gullah Geechee Camp Cooking", "cat": "cooking"},
]

# Bundle definitions
BUNDLES = [
    {
        "handle": "self-help-bundle",
        "title": "Self-Help Collection (31 Ebooks)",
        "description": "Complete Gullah Geechee self-help library. Resilience, mindset, identity, purpose, healing, and more. 31 ebooks, one price.",
        "price": 49.99,
        "tags": ["bundle", "self-help", "value pack"],
        "type": "Bundle"
    },
    {
        "handle": "business-bundle",
        "title": "Business Collection (34 Ebooks)",
        "description": "Complete Gullah Geechee business library. Entrepreneurship, marketing, finance, real estate, and more. 34 ebooks, one price.",
        "price": 49.99,
        "tags": ["bundle", "business", "value pack"],
        "type": "Bundle"
    },
    {
        "handle": "cooking-bundle",
        "title": "Cooking Collection (35 Ebooks)",
        "description": "Complete Gullah Geechee cooking library. Red rice, gumbo, seafood, desserts, and more. 35 ebooks, one price.",
        "price": 49.99,
        "tags": ["bundle", "cooking", "value pack"],
        "type": "Bundle"
    },
    {
        "handle": "all-access-pass",
        "title": "All-Access Pass (100 Ebooks)",
        "description": "Every Gullah Geechee Biz ebook. Self-help, business, and cooking — 100 titles. One-time purchase, lifetime access.",
        "price": 99.99,
        "tags": ["bundle", "all-access", "complete collection"],
        "type": "Bundle"
    },
    {
        "handle": "pick-3-pack",
        "title": "Pick Any 3 Ebooks",
        "description": "Choose any 3 ebooks from the catalog. Mix and match across categories.",
        "price": 12.99,
        "tags": ["bundle", "pick 3", "value"],
        "type": "Bundle"
    },
    {
        "handle": "pick-5-pack",
        "title": "Pick Any 5 Ebooks",
        "description": "Choose any 5 ebooks from the catalog. Best value for exploring multiple topics.",
        "price": 19.99,
        "tags": ["bundle", "pick 5", "best value"],
        "type": "Bundle"
    }
]

def generate_shopify_csv():
    """Generate Shopify-compatible CSV with all products and bundles."""
    csv_path = OUT_DIR / "shopify-products.csv"
    
    # Shopify CSV headers
    headers = [
        "Handle", "Title", "Body (HTML)", "Vendor", "Type",
        "Tags", "Published", "Option1 Name", "Option1 Value",
        "Variant SKU", "Variant Price", "Variant Requires Shipping",
        "Variant Weight (g)", "Variant Inventory Tracker",
        "Variant Inventory Qty", "Variant Fulfillment Service",
        "SEO Title", "SEO Description", "Google Shopping / Google Product Category",
        "Status"
    ]
    
    with open(csv_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        
        # Individual ebooks
        for book in EBOOKS:
            title = book["title"]
            # Clean title for handle
            handle = book["slug"]
            desc = f"Digital ebook by Darryl Elliott Brown. Published by Gullah Geechee Biz. Instant download after purchase."
            tags = f"ebook, {book['cat']}, gullah geechee, digital download, pdf"
            
            writer.writerow([
                handle, title, desc, "Gullah Geechee Biz",
                "Ebook", tags, "TRUE",
                "Title", title,
                book["slug"], "4.99", "FALSE",
                "0", "shopify", "999", "manual",
                f"{title} - Gullah Geechee Biz",
                f"Digital download: {title} by Darryl Elliott Brown",
                "Digital Media", "active"
            ])
        
        # Bundles
        for bundle in BUNDLES:
            desc = f"<p>{bundle['description']}</p><p>Instant digital download. No shipping. No returns.</p>"
            tags = ", ".join(bundle["tags"])
            
            writer.writerow([
                bundle["handle"], bundle["title"], desc, "Gullah Geechee Biz",
                bundle["type"], tags, "TRUE",
                "Title", bundle["title"],
                bundle["handle"], f"{bundle['price']:.2f}", "FALSE",
                "0", "shopify", "999", "manual",
                f"{bundle['title']} - Gullah Geechee Biz",
                bundle["description"],
                "Digital Media", "active"
            ])
    
    return csv_path

def generate_bundle_json():
    """Generate JSON with bundle contents for reference."""
    bundle_data = []
    
    for bundle in BUNDLES:
        entry = {
            "handle": bundle["handle"],
            "title": bundle["title"],
            "price": bundle["price"],
            "description": bundle["description"]
        }
        
        if bundle["handle"] == "self-help-bundle":
            entry["includes"] = [b["slug"] for b in EBOOKS if b["cat"] == "self-help"]
        elif bundle["handle"] == "business-bundle":
            entry["includes"] = [b["slug"] for b in EBOOKS if b["cat"] == "business"]
        elif bundle["handle"] == "cooking-bundle":
            entry["includes"] = [b["slug"] for b in EBOOKS if b["cat"] == "cooking"]
        elif bundle["handle"] == "all-access-pass":
            entry["includes"] = [b["slug"] for b in EBOOKS]
        else:
            entry["includes"] = []
        
        bundle_data.append(entry)
    
    json_path = OUT_DIR / "bundles.json"
    with open(json_path, "w") as f:
        json.dump(bundle_data, f, indent=2)
    
    return json_path

def main():
    print("🛍️  Gullah Geechee Biz — Shopify Product Feed Generator")
    print()
    
    csv_path = generate_shopify_csv()
    json_path = generate_bundle_json()
    
    # Count
    total_products = len(EBOOKS) + len(BUNDLES)
    
    print(f"📊 Generated {total_products} products:")
    print(f"   • {len(EBOOKS)} individual ebooks at $4.99 each")
    print(f"   • {len(BUNDLES)} bundle offers:")
    for b in BUNDLES:
        print(f"     - {b['title']} — ${b['price']:.2f}")
    print()
    print(f"📄 CSV: {csv_path}")
    print(f"📋 JSON: {json_path}")
    print()
    print("📝 To import into Shopify:")
    print("   1. Go to Shopify Admin → Products → Import")
    print(f"   2. Upload {csv_path}")
    print("   3. Set up digital download delivery (Shopify Digital Downloads app)")
    print("   4. Publish to store")

if __name__ == "__main__":
    main()
