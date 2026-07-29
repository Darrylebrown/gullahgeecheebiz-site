#!/usr/bin/env python3
"""
Gullah Geechee Biz — Digital Download Code Generator
Generates unique redemption codes for ebook distribution to bookstores.
Codes are one-time use, trackable by store.
"""

import os, json, hashlib, secrets, string
from datetime import date, datetime

HOME = os.path.expanduser("~")
SITE_DIR = os.path.join(HOME, "gullahgeecheebiz-site")
CODES_DIR = os.path.join(SITE_DIR, "downloads", "codes")
os.makedirs(CODES_DIR, exist_ok=True)

CODES_FILE = os.path.join(CODES_DIR, "codes.json")
REDEEMED_FILE = os.path.join(CODES_DIR, "redeemed.json")

# Available ebooks
EBOOKS = [
    {"slug": "gullah-resilience", "title": "The Gullah Geechee Guide to Resilience"},
    {"slug": "gullah-mindset", "title": "The Gullah Geechee Mindset"},
    {"slug": "gullah-identity", "title": "Finding Your Roots: A Gullah Geechee Guide to Identity"},
    {"slug": "gullah-purpose", "title": "The Gullah Geechee Guide to Purpose"},
    {"slug": "gullah-gratitude", "title": "Gullah Geechee Gratitude"},
    {"slug": "gullah-healing", "title": "Gullah Geechee Healing"},
    {"slug": "gullah-calm", "title": "The Gullah Geechee Guide to Calm"},
    {"slug": "gullah-joy", "title": "Gullah Geechee Joy"},
    {"slug": "gullah-grief", "title": "Gullah Geechee Wisdom for Grief"},
    {"slug": "gullah-courage", "title": "Gullah Geechee Courage"},
    {"slug": "gullah-patience", "title": "The Gullah Geechee Art of Patience"},
    {"slug": "gullah-community", "title": "The Gullah Geechee Way of Community"},
    {"slug": "gullah-wisdom", "title": "Gullah Geechee Wisdom for Daily Living"},
    {"slug": "gullah-fatherhood", "title": "Gullah Geechee Fatherhood"},
    {"slug": "gullah-motherhood", "title": "Gullah Geechee Motherhood"},
    {"slug": "gullah-forgiveness", "title": "Gullah Geechee Forgiveness"},
    {"slug": "gullah-hope", "title": "Gullah Geechee Hope"},
    {"slug": "gullah-elders", "title": "Honoring Gullah Geechee Elders"},
    {"slug": "gullah-marriage", "title": "Gullah Geechee Marriage"},
    {"slug": "gullah-grandparenting", "title": "Gullah Geechee Grandparenting"},
    {"slug": "gullah-aging", "title": "Gullah Geechee Guide to Aging Well"},
    {"slug": "gullah-mental-health", "title": "Gullah Geechee Guide to Mental Health"},
    {"slug": "gullah-sabbath", "title": "The Gullah Geechee Sabbath"},
    {"slug": "gullah-relationships", "title": "Gullah Geechee Relationships"},
    {"slug": "gullah-morning", "title": "Gullah Geechee Morning Rituals"},
    {"slug": "gullah-bedtime", "title": "Gullah Geechee Bedtime Rituals"},
    {"slug": "gullah-spring", "title": "Gullah Geechee Spring"},
    {"slug": "gullah-summer", "title": "Gullah Geechee Summer"},
    {"slug": "gullah-autumn", "title": "Gullah Geechee Autumn"},
    {"slug": "gullah-winter", "title": "Gullah Geechee Winter"},
    {"slug": "gullah-entrepreneur", "title": "The Gullah Geechee Entrepreneur"},
    {"slug": "lowcountry-marketing", "title": "Lowcountry Marketing"},
    {"slug": "gullah-side-hustle", "title": "The Gullah Geechee Side Hustle"},
    {"slug": "gullah-finance", "title": "Gullah Geechee Guide to Financial Freedom"},
    {"slug": "gullah-publishing", "title": "The Gullah Geechee Guide to Self-Publishing"},
    {"slug": "gullah-ecommerce", "title": "Gullah Geechee E-Commerce"},
    {"slug": "gullah-tourism", "title": "Gullah Geechee Tourism Guide"},
    {"slug": "gullah-craft-business", "title": "The Gullah Geechee Craft Business Guide"},
    {"slug": "gullah-food-business", "title": "Starting a Gullah Geechee Food Business"},
    {"slug": "gullah-cooperative", "title": "The Gullah Geechee Cooperative"},
    {"slug": "gullah-freelance", "title": "The Gullah Geechee Freelancer"},
    {"slug": "gullah-real-estate", "title": "Gullah Geechee Guide to Real Estate"},
    {"slug": "gullah-nonprofit", "title": "Starting a Gullah Geechee Nonprofit"},
    {"slug": "gullah-investing", "title": "Gullah Geechee Investing"},
    {"slug": "gullah-consulting", "title": "The Gullah Geechee Consultant"},
    {"slug": "gullah-remote-work", "title": "Gullah Geechee Guide to Remote Work"},
    {"slug": "gullah-budget", "title": "The Gullah Geechee Budget"},
    {"slug": "gullah-credit", "title": "Gullah Geechee Guide to Credit"},
    {"slug": "gullah-debt", "title": "Gullah Geechee Guide to Debt Freedom"},
    {"slug": "gullah-retirement", "title": "Gullah Geechee Guide to Retirement"},
    {"slug": "gullah-taxes", "title": "Gullah Geechee Guide to Taxes"},
    {"slug": "gullah-insurance", "title": "Gullah Geechee Guide to Insurance"},
    {"slug": "gullah-estate", "title": "Gullah Geechee Guide to Estate Planning"},
    {"slug": "gullah-farming", "title": "The Gullah Geechee Farmer"},
    {"slug": "gullah-fishing", "title": "The Gullah Geechee Fisherman"},
    {"slug": "gullah-catering", "title": "Starting a Gullah Geechee Catering Business"},
    {"slug": "gullah-bed-breakfast", "title": "Starting a Gullah Geechee Bed and Breakfast"},
    {"slug": "gullah-art-gallery", "title": "Starting a Gullah Geechee Art Gallery"},
    {"slug": "gullah-museum", "title": "Starting a Gullah Geechee Museum"},
    {"slug": "gullah-podcast", "title": "Starting a Gullah Geechee Podcast"},
    {"slug": "gullah-youtube", "title": "Starting a Gullah Geechee YouTube Channel"},
    {"slug": "gullah-newsletter", "title": "Starting a Gullah Geechee Newsletter"},
    {"slug": "gullah-etsy", "title": "Selling Gullah Geechee Products on Etsy"},
    {"slug": "gullah-wholesale", "title": "The Gullah Geechee Guide to Wholesale"},
    {"slug": "gullah-kitchen-v1", "title": "The Gullah Geechee Kitchen Volume 1"},
    {"slug": "gullah-kitchen-v2", "title": "The Gullah Geechee Kitchen Volume 2"},
    {"slug": "gullah-sunday-dinner", "title": "Gullah Geechee Sunday Dinner"},
    {"slug": "gullah-seafood", "title": "Gullah Geechee Seafood Cookbook"},
    {"slug": "gullah-soul-food", "title": "Gullah Geechee Soul Food"},
    {"slug": "gullah-desserts", "title": "Gullah Geechee Desserts"},
    {"slug": "gullah-one-pot", "title": "Gullah Geechee One-Pot Meals"},
    {"slug": "gullah-holiday", "title": "Gullah Geechee Holiday Cookbook"},
    {"slug": "gullah-vegetarian", "title": "Gullah Geechee Vegetarian"},
    {"slug": "gullah-breakfast", "title": "Gullah Geechee Breakfast"},
    {"slug": "gullah-preserving", "title": "Gullah Geechee Guide to Preserving"},
    {"slug": "gullah-grilling", "title": "Gullah Geechee Grilling"},
    {"slug": "gullah-sauces", "title": "Gullah Geechee Sauces and Seasonings"},
    {"slug": "gullah-baking", "title": "Gullah Geechee Baking"},
    {"slug": "gullah-drinks", "title": "Gullah Geechee Drinks and Beverages"},
    {"slug": "gullah-rice", "title": "Gullah Geechee Rice Cookbook"},
    {"slug": "gullah-cast-iron", "title": "Gullah Geechee Cast Iron Cooking"},
    {"slug": "gullah-slow-cooker", "title": "Gullah Geechee Slow Cooker Recipes"},
    {"slug": "gullah-30-minute", "title": "Gullah Geechee 30-Minute Meals"},
    {"slug": "gullah-meal-prep", "title": "Gullah Geechee Meal Prep"},
    {"slug": "gullah-kids-cook", "title": "Gullah Geechee Kids Cookbook"},
    {"slug": "gullah-appetizers", "title": "Gullah Geechee Appetizers"},
    {"slug": "gullah-summer-cooking", "title": "Gullah Geechee Summer Cooking"},
    {"slug": "gullah-winter-cooking", "title": "Gullah Geechee Winter Cooking"},
    {"slug": "gullah-cajun", "title": "Gullah Geechee and Cajun Cooking"},
    {"slug": "gullah-caribbean", "title": "Gullah Geechee and Caribbean Cooking"},
    {"slug": "gullah-west-african", "title": "Gullah Geechee and West African Cooking"},
    {"slug": "gullah-fermentation", "title": "Gullah Geechee Fermentation"},
    {"slug": "gullah-gluten-free", "title": "Gullah Geechee Gluten-Free Cooking"},
    {"slug": "gullah-vegan", "title": "Gullah Geechee Vegan Cooking"},
    {"slug": "gullah-keto", "title": "Gullah Geechee Keto Cooking"},
    {"slug": "gullah-paleo", "title": "Gullah Geechee Paleo Cooking"},
    {"slug": "gullah-air-fryer", "title": "Gullah Geechee Air Fryer Recipes"},
    {"slug": "gullah-instant-pot", "title": "Gullah Geechee Instant Pot Recipes"},
    {"slug": "gullah-camping", "title": "Gullah Geechee Camp Cooking"},
]

def generate_code(store_name, ebook_slug, quantity=1):
    """Generate unique redemption codes."""
    codes = []
    for _ in range(quantity):
        random = secrets.token_hex(8).upper()
        code = f"GGB-{random[:4]}-{random[4:8]}-{random[8:12]}"
        codes.append({
            "code": code,
            "ebook_slug": ebook_slug,
            "store": store_name,
            "created": str(date.today()),
            "redeemed": False,
            "redeemed_at": None,
            "redeemed_by": None
        })
    return codes

def save_codes(new_codes):
    """Save codes to the codes file."""
    existing = []
    if os.path.exists(CODES_FILE):
        with open(CODES_FILE) as f:
            existing = json.load(f)
    existing.extend(new_codes)
    with open(CODES_FILE, "w") as f:
        json.dump(existing, f, indent=2)
    return len(new_codes)

def list_ebooks():
    """Print available ebooks."""
    print(f"\n📚 Available Ebooks ({len(EBOOKS)} total):")
    for i, book in enumerate(EBOOKS, 1):
        print(f"  {i:3d}. {book['title']}")

def main():
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python3 generate-codes.py <command> [args]")
        print("")
        print("Commands:")
        print("  list                    — List all ebooks")
        print("  generate <store> <slug> [qty] — Generate codes")
        print("  status                  — Show code usage stats")
        print("  redeem <code> <email>   — Mark a code as redeemed")
        return
    
    cmd = sys.argv[1]
    
    if cmd == "list":
        list_ebooks()
    
    elif cmd == "generate":
        if len(sys.argv) < 4:
            print("Usage: python3 generate-codes.py generate <store_name> <ebook_slug> [quantity]")
            return
        store = sys.argv[2]
        slug = sys.argv[3]
        qty = int(sys.argv[4]) if len(sys.argv) > 4 else 1
        
        # Validate slug
        valid = [b["slug"] for b in EBOOKS]
        if slug not in valid:
            print(f"❌ Unknown ebook slug: {slug}")
            print(f"   Run 'python3 generate-codes.py list' to see all slugs")
            return
        
        codes = generate_code(store, slug, qty)
        count = save_codes(codes)
        
        print(f"\n✅ Generated {count} code(s) for {store}")
        print(f"   Ebook: {slug}")
        for c in codes:
            print(f"   Code: {c['code']}")
    
    elif cmd == "status":
        if not os.path.exists(CODES_FILE):
            print("No codes generated yet.")
            return
        with open(CODES_FILE) as f:
            codes = json.load(f)
        
        total = len(codes)
        redeemed = sum(1 for c in codes if c["redeemed"])
        active = total - redeemed
        
        print(f"\n📊 Code Status:")
        print(f"   Total codes:    {total}")
        print(f"   Redeemed:       {redeemed}")
        print(f"   Active:         {active}")
        
        # By store
        stores = {}
        for c in codes:
            s = c["store"]
            if s not in stores:
                stores[s] = {"total": 0, "redeemed": 0}
            stores[s]["total"] += 1
            if c["redeemed"]:
                stores[s]["redeemed"] += 1
        
        print(f"\n   By Store:")
        for s, d in sorted(stores.items()):
            print(f"     {s}: {d['redeemed']}/{d['total']} redeemed")
    
    elif cmd == "redeem":
        if len(sys.argv) < 4:
            print("Usage: python3 generate-codes.py redeem <code> <email>")
            return
        code = sys.argv[2].upper()
        email = sys.argv[3]
        
        if not os.path.exists(CODES_FILE):
            print("No codes file found.")
            return
        
        with open(CODES_FILE) as f:
            codes = json.load(f)
        
        found = None
        for c in codes:
            if c["code"] == code:
                found = c
                break
        
        if not found:
            print(f"❌ Code not found: {code}")
            return
        
        if found["redeemed"]:
            print(f"❌ Code already redeemed on {found['redeemed_at']}")
            return
        
        found["redeemed"] = True
        found["redeemed_at"] = str(datetime.now())
        found["redeemed_by"] = email
        
        with open(CODES_FILE, "w") as f:
            json.dump(codes, f, indent=2)
        
        print(f"✅ Code {code} redeemed by {email}")
        print(f"   Ebook: {found['ebook_slug']}")
        print(f"   Store: {found['store']}")

if __name__ == "__main__":
    main()
