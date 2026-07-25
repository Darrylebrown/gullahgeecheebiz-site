#!/usr/bin/env python3
"""Overlay text on pin backgrounds - perfect spelling every time"""
import os, sys, json
sys.path.insert(0, '/tmp/pin-venv/lib/python3.11/site-packages')
from PIL import Image, ImageDraw, ImageFont

PIN_DIR = os.path.expanduser("~/pins-ai")
OUT_DIR = os.path.expanduser("~/pins-final")
os.makedirs(OUT_DIR, exist_ok=True)

GOLD = (212, 175, 55)
CREAM = (245, 240, 230)
WHITE = (255, 255, 255)
NAVY = (10, 20, 40)

PINS = [
    {"file": "pin-064-red-rice.png", "title": "GULLAH RED RICE", "subtitle": "The signature dish of the Lowcountry. Every Gullah kitchen has a recipe."},
    {"file": "pin-065-shrimp-grits.png", "title": "SHRIMP AND GRITS", "subtitle": "A Lowcountry classic. Gullah Geechee flavors in every bite."},
    {"file": "pin-066-okra-soup.png", "title": "OKRA SOUP", "subtitle": "West African roots. Gullah Geechee soul. A bowl of history."},
    {"file": "pin-067-benne-wafers.png", "title": "BENNE WAFERS", "subtitle": "Sesame cookies brought from West Africa. A Gullah Geechee tradition."},
    {"file": "pin-068-frogmore-stew.png", "title": "FROGMORE STEW", "subtitle": "The Lowcountry boil. Shrimp, sausage, corn, potatoes. A community feast."},
    {"file": "pin-069-fried-fish.png", "title": "FRIED FISH", "subtitle": "Fresh from the coast. Gullah Geechee fried fish, hushpuppies, and love."},
    {"file": "pin-070-bowens-island.png", "title": "BOWEN'S ISLAND", "subtitle": "Gullah Geechee seafood on Folly Beach since 1946. A Lowcountry institution."},
    {"file": "pin-071-fish-camp.png", "title": "GULLAH FISH CAMP", "subtitle": "Fresh catch, Gullah style. A fish camp tradition in the Lowcountry."},
    {"file": "pin-072-soul-food.png", "title": "SOUL FOOD KITCHEN", "subtitle": "Gullah Geechee soul food. Collards, mac and cheese, cornbread, love."},
    {"file": "pin-073-lowcountry-seafood.png", "title": "LOWCOUNTRY SEAFOOD", "subtitle": "Fresh oysters, shrimp, crab. The bounty of the Gullah Geechee coast."},
    {"file": "pin-074-charleston-soul.png", "title": "CHARLESTON SOUL FOOD", "subtitle": "Gullah Geechee flavors in the Holy City. Where tradition meets the plate."},
    {"file": "pin-075-savannah-soul.png", "title": "SAVANNAH SOUL FOOD", "subtitle": "Gullah Geechee cuisine in the Hostess City. History on every plate."},
]

def overlay_text(bg_path, title, subtitle, output_path):
    img = Image.open(bg_path).convert("RGB").resize((1080, 1920), Image.LANCZOS)
    overlay = Image.new("RGBA", (1080, 1920), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    
    # Dark gradient top and bottom
    for y in range(600):
        alpha = int(200 * (600 - y) / 600)
        draw.line([(0, y), (1080, y)], fill=(0, 0, 0, min(alpha, 200)))
    for y in range(1400, 1920):
        alpha = int(200 * (y - 1400) / 520)
        draw.line([(0, y), (1080, y)], fill=(0, 0, 0, min(alpha, 200)))
    
    img = Image.alpha_composite(img.convert("RGBA"), overlay)
    draw = ImageDraw.Draw(img)
    
    try:
        ft = ImageFont.truetype("/System/Library/Fonts/Georgia.ttf", 64)
        fs = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 28)
        fb = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 20)
    except:
        ft = fs = fb = ImageFont.load_default()
    
    # Title
    draw.text((542, 102), title, fill=(0, 0, 0, 200), font=ft, anchor="mt")
    draw.text((540, 100), title, fill=GOLD, font=ft, anchor="mt")
    
    # Subtitle
    draw.text((540, 200), subtitle, fill=WHITE, font=fs, anchor="mt")
    
    # CTA button
    cta = "Explore at gullahgeecheebiz.com"
    bbox = draw.textbbox((0, 0), cta, font=fb)
    cw, ch = bbox[2]-bbox[0]+50, bbox[3]-bbox[1]+24
    cx, cy = 540 - cw//2, 1700
    draw.rounded_rectangle([cx+3, cy+3, cx+cw+3, cy+ch+3], 25, fill=(0,0,0,100))
    draw.rounded_rectangle([cx, cy, cx+cw, cy+ch], 25, fill=GOLD)
    draw.text((540, cy+ch//2), cta, fill=NAVY, font=fb, anchor="mm")
    
    # Emblem
    ey = 1500
    draw.ellipse([540-50, ey-50, 540+50, ey+50], outline=GOLD, width=3)
    draw.text((540, ey-8), "GGB", fill=GOLD, font=fb, anchor="mm")
    draw.text((540, ey+14), "★", fill=GOLD, font=fb, anchor="mm")
    draw.text((540, ey+70), "GULLAH GEECHEE BIZ", fill=GOLD, font=fb, anchor="mt")
    draw.line([(340, ey+95), (740, ey+95)], fill=GOLD, width=2)
    
    img.convert("RGB").save(output_path, "PNG", optimize=True)
    return True

def main():
    ok, fail = 0, 0
    for pin in PINS:
        src = os.path.join(PIN_DIR, pin["file"])
        dst = os.path.join(OUT_DIR, pin["file"])
        if os.path.exists(src):
            overlay_text(src, pin["title"], pin["subtitle"], dst)
            print(f"  ✅ {pin['file']} — {pin['title']}")
            ok += 1
        else:
            print(f"  ⚠️  {pin['file']} not found")
            fail += 1
    print(f"\n  {ok} pins overlaid, {fail} skipped")
    print(f"  Output: {OUT_DIR}")

if __name__ == "__main__":
    main()
