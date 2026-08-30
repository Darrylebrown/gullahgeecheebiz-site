#!/usr/bin/env python3
"""Create TikTok scripts for Gumroad products."""
from pathlib import Path
import os

BASE = Path("/Users/darrylsmac/gullahgeecheebiz-site")
TIKTOK_DIR = BASE / "tiktok-content"
TIKTOK_DIR.mkdir(exist_ok=True)

PRODUCTS = [
    {
        "name": "Gullah Geechee Encyclopedia Box Set",
        "url": "https://debtide0.gumroad.com/l/gullah-geechee-encyclopedia---complete-box-set-vol-1-25",
        "price": "$9.99",
        "hook": "I just spent 6 months compiling the most comprehensive Gullah Geechee encyclopedia ever created. 25 volumes. Every topic. All for $9.99.",
        "body": "This isn't just a book. It's 25 volumes covering the complete history, culture, language, food, music, spirituality, and traditions of the Gullah Geechee people. From Beaufort to Savannah, every county documented. This is the most complete collection of Sea Island knowledge ever assembled.",
        "cta": "Link in bio. The past is preserved. The future is funded."
    },
    {
        "name": "Heritage Vault",
        "url": "https://debtide0.gumroad.com/l/mxzynu",
        "price": "$97.00",
        "hook": "What if you could own the entire Gullah Geechee cultural archive? Ebooks, audiobooks, genealogy tools, and more.",
        "body": "The Ultimate Heritage Vault includes everything: the complete encyclopedia, audiobooks in English and Spanish, genealogy research tools, and exclusive cultural content. It's the full archive of Sea Island heritage in one purchase.",
        "cta": "Get the complete archive. Link in bio."
    },
    {
        "name": "Language & Dialect Collection",
        "url": "https://debtide0.gumroad.com/l/sywqz",
        "price": "$14.99",
        "hook": "Did you know Gullah is the only African American Creole language still spoken in the US?",
        "body": "Our Language & Dialect collection documents every aspect of Gullah speech - from West African roots to modern usage. Words like 'buh nuh' (that's not true), 'sippoo' (small), 'buckra' (white person). Each word carries centuries of history.",
        "cta": "Learn the language. Preserve the culture. Link in bio."
    },
    {
        "name": "History & Genealogy Collection",
        "url": "https://debtide0.gumroad.com/l/veybe",
        "price": "$14.99",
        "hook": "Your Gullah Geechee ancestors survived slavery, Jim Crow, and heirs' property loss. Their story deserves to be told.",
        "body": "This collection covers the complete history of Gullah Geechee communities county by county. From the Rice Kingdom to the Sea Islands, from the Combahee River Raid to Penn Center. Know your history. Honor your ancestors.",
        "cta": "Get the history. Link in bio."
    },
    {
        "name": "Traditions & Recipes Collection",
        "url": "https://debtide0.gumroad.com/l/vplxw",
        "price": "$14.99",
        "hook": "Red rice, shrimp and grits, okra soup - these aren't just Southern dishes. They're Gullah Geechee dishes with West African roots.",
        "body": "The Traditions & Recipes collection documents the food that shaped America. Every recipe tells a story of survival, creativity, and cultural preservation. From benne wafers to frogmore stew, these are the flavors of the Sea Islands.",
        "cta": "Taste the history. Link in bio."
    },
    {
        "name": "Spirituality & Folklore Collection",
        "url": "https://debtide0.gumroad.com/l/sbwja",
        "price": "$14.99",
        "hook": "Conjure, haints, the Boo Hag - Gullah Geechee spirituality is one of America's most unique cultural traditions.",
        "body": "This collection explores the spiritual world of the Gullah Geechee people. From praise houses to ring shouts, from conjure to folklore. This is a living spiritual tradition that has survived for 300 years.",
        "cta": "Explore the spirituality. Link in bio."
    },
    {
        "name": "Art & Craft Collection",
        "url": "https://debtide0.gumroad.com/l/mhlqrb",
        "price": "$14.99",
        "hook": "Sweetgrass baskets are one of the oldest African art forms in North America. This collection shows you why.",
        "body": "From Philip Simmons' wrought iron to Mary Rivers' sweetgrass baskets, the Art & Craft collection documents the masterworks of Gullah Geechee artisans. Each piece carries 300 years of tradition.",
        "cta": "See the art. Link in bio."
    },
    {
        "name": "Music & Storytelling Collection",
        "url": "https://debtide0.gumroad.com/l/vwnpk",
        "price": "$14.99",
        "hook": "Ring shout. Spirituals. Sea Island songs. The music of the Gullah Geechee people shaped American music.",
        "body": "This collection documents the musical traditions of the Sea Islands. From the ring shout - the oldest African American performance tradition - to the spirituals that became gospel, jazz, and R&B. The roots run deep.",
        "cta": "Hear the music. Link in bio."
    },
    {
        "name": "Environment & Ecology Collection",
        "url": "https://debtide0.gumroad.com/l/xgkkis",
        "price": "$14.99",
        "hook": "The Gullah Geechee people have been stewards of the Lowcountry for 300 years. They know this land better than anyone.",
        "body": "From sea turtles to blue crabs, from the Combahee River to the salt marshes, this collection documents the ecological knowledge of the Gullah Geechee people. Traditional knowledge meets modern conservation.",
        "cta": "Explore the land. Link in bio."
    }
]

for i, prod in enumerate(PRODUCTS, 1):
    script = f"""# TikTok Script {i}: {prod['name']}

[HOOK]
{prod['hook']}

[BODY]
{prod['body']}

[CTA]
{prod['cta']}

[HASHTAGS]
#GullahGeechee #GullahGeecheeBiz #SeaIslands #Lowcountry #CulturalHeritage #BlackHistory #BookTok #GullahLanguage #Geechee #SeaIslandCulture

[PRODUCT LINK]
{prod['url']}
"""
    filename = f"tiktok-script-{i:02d}-{prod['name'].replace(' ', '-').lower()}.md"
    filepath = TIKTOK_DIR / filename
    filepath.write_text(script)
    print(f"Created: {filepath.name}")

print(f"\nCreated {len(PRODUCTS)} TikTok scripts.")
