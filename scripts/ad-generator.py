#!/usr/bin/env python3
"""
Gullah Geechee Biz — Ad Generator
Creates promotional ads from existing content when traffic is low.
Generates copy, visuals, and platform-ready output.
All local, no ad platforms, no spending.
"""

import json, os, random, subprocess, textwrap
from pathlib import Path
from datetime import datetime

HOME = Path.home()
SITE_DIR = HOME / "gullahgeecheebiz-site"
ADS_DIR = HOME / "generated-ads"
ADS_DIR.mkdir(parents=True, exist_ok=True)

# Content sources
EBOOKS = [
    {"slug": "gullah-resilience", "title": "The Gullah Geechee Guide to Resilience", "cat": "self-help"},
    {"slug": "gullah-mindset", "title": "The Gullah Geechee Mindset", "cat": "self-help"},
    {"slug": "gullah-identity", "title": "Finding Your Roots: A Gullah Geechee Guide to Identity", "cat": "self-help"},
    {"slug": "gullah-purpose", "title": "The Gullah Geechee Guide to Purpose", "cat": "self-help"},
    {"slug": "gullah-healing", "title": "Gullah Geechee Healing", "cat": "self-help"},
    {"slug": "gullah-courage", "title": "Gullah Geechee Courage", "cat": "self-help"},
    {"slug": "gullah-community", "title": "The Gullah Geechee Way of Community", "cat": "self-help"},
    {"slug": "gullah-entrepreneur", "title": "The Gullah Geechee Entrepreneur", "cat": "business"},
    {"slug": "lowcountry-marketing", "title": "Lowcountry Marketing", "cat": "business"},
    {"slug": "gullah-side-hustle", "title": "The Gullah Geechee Side Hustle", "cat": "business"},
    {"slug": "gullah-finance", "title": "Gullah Geechee Guide to Financial Freedom", "cat": "business"},
    {"slug": "gullah-publishing", "title": "The Gullah Geechee Guide to Self-Publishing", "cat": "business"},
    {"slug": "gullah-ecommerce", "title": "Gullah Geechee E-Commerce", "cat": "business"},
    {"slug": "gullah-kitchen-v1", "title": "The Gullah Geechee Kitchen Volume 1", "cat": "cooking"},
    {"slug": "gullah-kitchen-v2", "title": "The Gullah Geechee Kitchen Volume 2", "cat": "cooking"},
    {"slug": "gullah-sunday-dinner", "title": "Gullah Geechee Sunday Dinner", "cat": "cooking"},
    {"slug": "gullah-seafood", "title": "Gullah Geechee Seafood Cookbook", "cat": "cooking"},
    {"slug": "gullah-soul-food", "title": "Gullah Geechee Soul Food", "cat": "cooking"},
    {"slug": "gullah-desserts", "title": "Gullah Geechee Desserts", "cat": "cooking"},
    {"slug": "gullah-rice", "title": "Gullah Geechee Rice Cookbook", "cat": "cooking"},
]

RECIPES = [
    {"slug": "gullah-red-rice", "title": "Gullah Red Rice", "desc": "The signature dish of the Lowcountry"},
    {"slug": "shrimp-and-grits", "title": "Shrimp and Grits", "desc": "Classic Lowcountry breakfast"},
    {"slug": "okra-soup", "title": "Okra Soup", "desc": "Hearty Gullah Geechee tradition"},
    {"slug": "crab-cakes", "title": "Gullah Crab Cakes", "desc": "Fresh blue crab, Lowcountry style"},
    {"slug": "benne-wafers", "title": "Benne Wafers", "desc": "Sesame cookies from West Africa"},
    {"slug": "sweet-potato-pie", "title": "Sweet Potato Pie", "desc": "The queen of Gullah desserts"},
]

AD_TEMPLATES = {
    "social": [
        "Discover {title} — {desc} Download your copy today at gullahgeecheebiz.com",
        "From the Lowcountry to your screen: {title}. {desc}",
        "Authentic Gullah Geechee culture, one ebook at a time. Start with {title}",
        "What if {benefit}? {title} shows you how. Download now.",
        "The stories, recipes, and wisdom of the Gullah Geechee people. Start with {title}",
    ],
    "hook": [
        "You've never read anything like this.",
        "This is what authentic looks like.",
        "From the Sea Islands to your screen.",
        "100+ years of culture in one download.",
        "Not a history book. A living tradition.",
    ],
    "cta": [
        "Download at gullahgeecheebiz.com",
        "Get your copy at gullahgeecheebiz.com/ebooks/",
        "Available now at gullahgeecheebiz.com",
        "Start reading at gullahgeecheebiz.com",
    ]
}

BENEFITS = {
    "self-help": "you could carry the resilience of generations in your pocket",
    "business": "you could build a business that honors your heritage",
    "cooking": "you could taste the Lowcountry from your own kitchen",
}

def generate_ad_copy(ebook, platform="social"):
    """Generate ad copy for an ebook."""
    template = random.choice(AD_TEMPLATES[platform])
    benefit = BENEFITS.get(ebook["cat"], "you could explore Gullah Geechee culture")
    hook = random.choice(AD_TEMPLATES["hook"])
    cta = random.choice(AD_TEMPLATES["cta"])
    
    body = template.format(
        title=ebook["title"],
        desc=ebook.get("subtitle", f"A {ebook['cat']} guide from Gullah Geechee Biz"),
        benefit=benefit
    )
    
    return {
        "ebook": ebook["slug"],
        "title": ebook["title"],
        "category": ebook["cat"],
        "hook": hook,
        "body": body,
        "cta": cta,
        "full_ad": f"{hook}\n\n{body}\n\n{cta}",
        "platform": platform
    }

def generate_recipe_ad(recipe, platform="social"):
    """Generate ad copy for a recipe."""
    hook = random.choice(AD_TEMPLATES["hook"])
    cta = "Get the full recipe at gullahgeecheebiz.com/recipes/"
    
    body = f"Learn to make authentic {recipe['title']}. {recipe['desc']}."
    
    return {
        "recipe": recipe["slug"],
        "title": recipe["title"],
        "hook": hook,
        "body": body,
        "cta": cta,
        "full_ad": f"{hook}\n\n{body}\n\n{cta}",
        "platform": platform
    }

def generate_bundle_ad():
    """Generate an ad for the all-access bundle."""
    hook = random.choice(AD_TEMPLATES["hook"])
    cta = "Get all 100 ebooks at gullahgeecheebiz.com/ebooks/"
    
    body = "100 Gullah Geechee ebooks. Self-help, business, and cooking. One price, lifetime access."
    
    return {
        "type": "bundle",
        "hook": hook,
        "body": body,
        "cta": cta,
        "full_ad": f"{hook}\n\n{body}\n\n{cta}"
    }

def generate_ad_image_prompt(ad):
    """Generate an image generation prompt for the ad."""
    category = ad.get("category", ad.get("type", "general"))
    
    prompts = {
        "self-help": "Peaceful Lowcountry marsh at golden hour, warm light, serene water, no text, no words, no letters, just the landscape, vertical 9:16",
        "business": "Historic Penn Center campus on St. Helena Island, live oaks with Spanish moss, warm afternoon light, no text, no words, no letters, vertical 9:16",
        "cooking": "Cast iron skillet with Gullah red rice, steaming hot, rich red-orange color, fresh herbs garnish, warm kitchen lighting, no text, no words, no letters, vertical 9:16",
        "bundle": "Beautiful sweetgrass basket on weathered dock, marsh view at sunset, golden hour, no text, no words, no letters, vertical 9:16",
        "general": "Lowcountry landscape, marsh and live oaks, warm golden light, peaceful, no text, no words, no letters, vertical 9:16"
    }
    
    return prompts.get(category, prompts["general"])

def save_ad(ad, ad_type="ebook"):
    """Save generated ad to disk."""
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    slug = ad.get("slug") or ad.get("recipe") or ad.get("type", "ad")
    filename = f"{ad_type}-{slug}-{timestamp}.json"
    filepath = ADS_DIR / filename
    
    with open(filepath, "w") as f:
        json.dump(ad, f, indent=2)
    
    return filepath

def generate_ad_batch(count=5):
    """Generate a batch of ads from random content."""
    ads = []
    
    for _ in range(count):
        choice = random.random()
        
        if choice < 0.5:
            # Ebook ad
            ebook = random.choice(EBOOKS)
            ad = generate_ad_copy(ebook)
            path = save_ad(ad, "ebook")
            ads.append(ad)
        
        elif choice < 0.8:
            # Recipe ad
            recipe = random.choice(RECIPES)
            ad = generate_recipe_ad(recipe)
            path = save_ad(ad, "recipe")
            ads.append(ad)
        
        else:
            # Bundle ad
            ad = generate_bundle_ad()
            path = save_ad(ad, "bundle")
            ads.append(ad)
    
    return ads

def main():
    print("📢 Gullah Geechee Biz — Ad Generator")
    print()
    
    # Generate a batch
    count = 5
    ads = generate_ad_batch(count)
    
    print(f"   Generated {len(ads)} ads:")
    for ad in ads:
        print(f"\n  {'='*50}")
        print(f"  {ad.get('title', ad.get('type', 'Ad').upper())}")
        print(f"  {'='*50}")
        print(f"  {ad['full_ad']}")
        print()
    
    print(f"   📁 Saved to: {ADS_DIR}/")
    print(f"   Total ads in queue: {len(list(ADS_DIR.glob('*.json')))}")
    
    # Print image prompts for manual generation
    print(f"\n   🎨 Image prompts for generation:")
    for ad in ads:
        prompt = generate_ad_image_prompt(ad)
        print(f"     - {prompt[:60]}...")

if __name__ == "__main__":
    main()
