#!/usr/bin/env python3
"""
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

if __name__ == "__main__":
    main()
