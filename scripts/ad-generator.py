#!/usr/bin/env python3
"""
<<<<<<< HEAD
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
=======
Gullah Geechee Biz — Ad Asset Generator
Creates branded ad visuals with backgrounds, logo, book covers, and text overlays
"""

import os, json
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance

OUTPUT = os.path.expanduser("~/ads")
os.makedirs(OUTPUT, exist_ok=True)

# ── Brand Colors ──
GOLD = (212, 175, 55)
DARK_GOLD = (180, 145, 40)
CREAM = (245, 240, 230)
WHITE = (255, 255, 255)
NAVY = (10, 20, 40)
BLACK = (0, 0, 0)

# ── Backgrounds ──
BACKGROUNDS = {
    "roots-rivers": "/tmp/ad-bg-1.png",
    "blood-remembers": "/tmp/ad-bg-2.png",
}

# ── Ads to Generate ──
ADS = [
    {
        "slug": "roots-rivers-promo",
        "bg": "roots-rivers",
        "title": "Roots & Rivers",
        "subtitle": "Vol. 1 · Beaufort",
        "tagline": "The first encyclopedia of Gullah Geechee history",
        "cta": "Available on Amazon Kindle",
        "format": "9:16"
    },
    {
        "slug": "blood-remembers-promo",
        "bg": "blood-remembers",
        "title": "Blood Remembers",
        "subtitle": "A novel of memory, family, and the Gullah Geechee coast",
        "tagline": "The land remembers what the books forgot",
        "cta": "Available on Amazon Kindle",
        "format": "9:16"
    },
    {
        "slug": "season-1-trailer",
        "bg": "roots-rivers",
        "title": "Season 1",
        "subtitle": "16 episodes · 16 stories",
        "tagline": "One culture that shaped America",
        "cta": "Watch now at gullahgeecheebiz.com",
        "format": "9:16"
    },
    {
        "slug": "brand-ad",
        "bg": "blood-remembers",
        "title": "Gullah Geechee Biz",
        "subtitle": "Books · Documentaries · Podcast · Merch",
        "tagline": "Preserving a culture. Telling a story.",
        "cta": "gullahgeecheebiz.com",
        "format": "9:16"
    },
    {
        "slug": "substack-promo",
        "bg": "roots-rivers",
        "title": "Free Weekly Newsletter",
        "subtitle": "Gullah Geechee history delivered to your inbox",
        "tagline": "Exclusive stories · Language lessons · Behind-the-scenes",
        "cta": "Subscribe free at kofigullahgeecheebiz.substack.com",
        "format": "9:16"
    },
]

def create_ad(ad_data):
    """Create a branded ad visual"""
    bg_path = BACKGROUNDS.get(ad_data["bg"])
    if not bg_path or not os.path.exists(bg_path):
        print(f"  [SKIP] Background not found for {ad_data['slug']}")
        return None
    
    # Load and resize background
    bg = Image.open(bg_path).convert("RGB")
    bg = bg.resize((1080, 1920), Image.Resampling.LANCZOS)
    
    # Create overlay
    overlay = Image.new("RGBA", (1080, 1920), (0, 0, 0, 0))
    overlay_draw = ImageDraw.Draw(overlay)
    
    # Dark gradient at top and bottom for text readability
    for y in range(0, 600):
        alpha = int(220 * (600 - y) / 600)
        overlay_draw.line([(0, y), (1080, y)], fill=(0, 0, 0, min(alpha, 220)))
    
    for y in range(1400, 1920):
        alpha = int(220 * (y - 1400) / 520)
        overlay_draw.line([(0, y), (1080, y)], fill=(0, 0, 0, min(alpha, 220)))
    
    # Composite
    img = Image.alpha_composite(bg.convert("RGBA"), overlay)
    draw = ImageDraw.Draw(img)
    
    # Load fonts
    try:
        font_title = ImageFont.truetype("/System/Library/Fonts/Georgia.ttf", 72)
        font_subtitle = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 36)
        font_tagline = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 28)
        font_cta = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 24)
        font_brand = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 20)
    except:
        font_title = ImageFont.load_default()
        font_subtitle = ImageFont.load_default()
        font_tagline = ImageFont.load_default()
        font_cta = ImageFont.load_default()
        font_brand = ImageFont.load_default()
    
    # ── Title ──
    title = ad_data["title"]
    # Shadow
    draw.text((542, 122), title, fill=(0, 0, 0, 200), font=font_title, anchor="mt")
    # Gold text
    draw.text((540, 120), title, fill=GOLD, font=font_title, anchor="mt")
    
    # ── Subtitle ──
    subtitle = ad_data["subtitle"]
    draw.text((540, 220), subtitle, fill=CREAM, font=font_subtitle, anchor="mt")
    
    # ── Tagline ──
    tagline = ad_data["tagline"]
    draw.text((540, 280), tagline, fill=WHITE, font=font_tagline, anchor="mt")
    
    # ── CTA Button ──
    cta = ad_data["cta"]
    cta_bbox = draw.textbbox((0, 0), cta, font=font_cta)
    cta_w = cta_bbox[2] - cta_bbox[0] + 60
    cta_h = cta_bbox[3] - cta_bbox[1] + 30
    cta_x = 540 - cta_w // 2
    cta_y = 1700
    
    # Button shadow
    draw.rounded_rectangle([cta_x + 4, cta_y + 4, cta_x + cta_w + 4, cta_y + cta_h + 4], radius=30, fill=(0, 0, 0, 120))
    # Button
    draw.rounded_rectangle([cta_x, cta_y, cta_x + cta_w, cta_y + cta_h], radius=30, fill=GOLD)
    # Button text
    draw.text((540, cta_y + cta_h // 2), cta, fill=NAVY, font=font_cta, anchor="mm")
    
    # ── Emblem Logo ──
    emblem_y = 1500
    size = 60
    draw.ellipse([540 - size, emblem_y - size, 540 + size, emblem_y + size], outline=GOLD, width=4)
    draw.ellipse([540 - size + 8, emblem_y - size + 8, 540 + size - 8, emblem_y + size - 8], outline=GOLD, width=1)
    draw.text((540, emblem_y - 10), "GGB", fill=GOLD, font=font_brand, anchor="mm")
    draw.text((540, emblem_y + 12), "★", fill=GOLD, font=font_brand, anchor="mm")
    
    # ── Brand Name ──
    draw.text((540, emblem_y + 85), "GULLAH GEECHEE BIZ", fill=GOLD, font=font_brand, anchor="mt")
    
    # ── Decorative line ──
    draw.line([(340, emblem_y + 115), (740, emblem_y + 115)], fill=GOLD, width=2)
    
    # ── Save ──
    path = os.path.join(OUTPUT, f"{ad_data['slug']}.png")
    img.convert("RGB").save(path, "PNG", optimize=True)
    return path

def main():
    print("=" * 60)
    print("  GULLAH GEECHEE BIZ — AD ASSET GENERATOR")
    print("=" * 60)
    print()
    
    for ad in ADS:
        path = create_ad(ad)
        if path:
            print(f"  ✅ {ad['slug']}.png")
        else:
            print(f"  ❌ {ad['slug']} — failed")
    
    print(f"\n  📍 {OUTPUT}")
    print(f"  📦 {len(ADS)} ad visuals ready")
    print("=" * 60)
>>>>>>> main1

if __name__ == "__main__":
    main()
