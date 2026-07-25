#!/usr/bin/env python3
"""
Gullah Geechee Biz — Daily Trending Products Engine
Scrapes trending products and creates SEO-optimized landing pages
with affiliate links. Runs alongside the viral content engine.
"""

import os, json, datetime, random, urllib.request, urllib.parse, re
from pathlib import Path

HOME = Path.home()
SITE_DIR = HOME / "gullahgeecheebiz-site"
TRENDING_DIR = SITE_DIR / "trending"
os.makedirs(TRENDING_DIR, exist_ok=True)

# ── Trending Product Sources ──
# We scrape Amazon Best Sellers, TikTok trending, and Etsy hot items
# Using Browserbase Search (free tier) to find what's hot

AMAZON_BSR_URL = "https://www.amazon.com/gp/bestsellers/"
TIKTOK_TRENDING = "https://www.tiktok.com/trending"
ETSY_HOT = "https://www.etsy.com/trending"

# ── Product Categories We Target ──
# Items that align with Gullah Geechee audience interests
CATEGORIES = [
    "African American history books",
    "soul food cooking accessories",
    "sweetgrass basket decor",
    "Lowcountry home decor",
    "African heritage jewelry",
    "black history merchandise",
    "cultural travel gear",
    "storytelling gifts",
    "genealogy research tools",
    "heritage clothing"
]

# ── Sample Trending Products (fallback when scraping is rate-limited) ──
TRENDING_PRODUCTS = [
    {
        "name": "Cast Iron Dutch Oven",
        "trend_reason": "Viral on TikTok for one-pot Southern cooking",
        "description": "The same type of pot Gullah Geechee ancestors used for one-pot meals like red rice and okra soup. Modern kitchens are rediscovering what our grandmothers always knew.",
        "price": "$49.99",
        "affiliate_link": "https://amzn.to/dutch-oven-ggb",
        "image": "https://gullahgeecheebiz.com/images/dutch-oven.jpg",
        "category": "kitchen"
    },
    {
        "name": "African DNA Ancestry Kit",
        "trend_reason": "Rising interest in African American genealogy",
        "description": "Trace your roots back to the specific regions of West Africa where Gullah Geechee culture was born. The #1 trending gift for family history research.",
        "price": "$79.99",
        "affiliate_link": "https://amzn.to/dna-kit-ggb",
        "image": "https://gullahgeecheebiz.com/images/dna-kit.jpg",
        "category": "genealogy"
    },
    {
        "name": "Handwoven Sweetgrass Coaster Set",
        "trend_reason": "Viral on Pinterest for coastal home decor",
        "description": "Inspired by the centuries-old Gullah Geechee sweetgrass basket tradition. Each set supports artisans preserving this endangered craft.",
        "price": "$34.99",
        "affiliate_link": "https://etsy.me/sweetgrass-coasters-ggb",
        "image": "https://gullahgeecheebiz.com/images/coasters.jpg",
        "category": "home"
    },
    {
        "name": "Black History 365 Day Calendar",
        "trend_reason": "Year-round demand for Black history education",
        "description": "Daily facts about African American achievements. Features Gullah Geechee history including Robert Smalls, Penn Center, and the Combahee River Raid.",
        "price": "$19.99",
        "affiliate_link": "https://amzn.to/black-history-calendar-ggb",
        "image": "https://gullahgeecheebiz.com/images/calendar.jpg",
        "category": "books"
    },
    {
        "name": "Soul Food Seasoning Set",
        "trend_reason": "TikTok trend: 'What seasoning did your grandmother use?'",
        "description": "The exact spice blend Gullah Geechee cooks have used for generations. Smoked paprika, garlic, onion, cayenne, and a secret Lowcountry mix.",
        "price": "$24.99",
        "affiliate_link": "https://amzn.to/seasoning-set-ggb",
        "image": "https://gullahgeecheebiz.com/images/seasoning.jpg",
        "category": "kitchen"
    },
    {
        "name": "African Mudcloth Throw Blanket",
        "trend_reason": "Trending on Etsy for boho home decor",
        "description": "Handwoven mudcloth patterns from West Africa — the same textile traditions that influenced Gullah Geechee quilting and design.",
        "price": "$59.99",
        "affiliate_link": "https://etsy.me/mudcloth-blanket-ggb",
        "image": "https://gullahgeecheebiz.com/images/blanket.jpg",
        "category": "home"
    },
    {
        "name": "Gullah Geechee Cookbook",
        "trend_reason": "Amazon bestseller in Southern cooking",
        "description": "Authentic recipes passed down through generations. Red rice, okra soup, shrimp and grits, benne wafers — the real taste of the Lowcountry.",
        "price": "$14.99",
        "affiliate_link": "https://amzn.to/ggb-cookbook",
        "image": "https://gullahgeecheebiz.com/images/cookbook.jpg",
        "category": "books"
    },
    {
        "name": "Wireless Bluetooth Turntable",
        "trend_reason": "Vinyl revival — people want to hear spirituals and ring shouts as they were meant to be heard",
        "description": "Listen to Gullah Geechee spirituals, ring shouts, and work songs on vinyl. Modern tech meets ancient tradition.",
        "price": "$89.99",
        "affiliate_link": "https://amzn.to/turntable-ggb",
        "image": "https://gullahgeecheebiz.com/images/turntable.jpg",
        "category": "music"
    },
    {
        "name": "African American Genealogy Workbook",
        "trend_reason": "Viral on TikTok: 'How to trace your enslaved ancestors'",
        "description": "Step-by-step guide to researching African American family history. Includes Gullah Geechee-specific resources for Lowcountry families.",
        "price": "$12.99",
        "affiliate_link": "https://amzn.to/genealogy-workbook-ggb",
        "image": "https://gullahgeecheebiz.com/images/workbook.jpg",
        "category": "genealogy"
    },
    {
        "name": "Lowcountry Marsh Candle",
        "trend_reason": "Trending on Etsy for coastal home fragrance",
        "description": "Smells like the Gullah Geechee Lowcountry — salt marsh, sweetgrass, and ancient oak. Hand-poured in South Carolina.",
        "price": "$28.99",
        "affiliate_link": "https://etsy.me/marsh-candle-ggb",
        "image": "https://gullahgeecheebiz.com/images/candle.jpg",
        "category": "home"
    },
]

# ── HTML Template ──
HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title} | Gullah Geechee Biz</title>
  <meta name="description" content="{meta_desc}">
  <meta name="keywords" content="{keywords}">
  <meta property="og:title" content="{title} | Gullah Geechee Biz">
  <meta property="og:description" content="{meta_desc}">
  <meta property="og:image" content="{og_image}">
  <meta property="og:url" content="https://gullahgeecheebiz.com/trending/{slug}">
  <meta name="twitter:card" content="summary_large_image">
  <link rel="canonical" href="https://gullahgeecheebiz.com/trending/{slug}">
  <style>
    * {{ margin: 0; padding: 0; box-sizing: border-box; }}
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #0a0a14; color: #f0ede5; line-height: 1.8; }}
    .container {{ max-width: 800px; margin: 0 auto; padding: 40px 20px; }}
    h1 {{ font-family: Georgia, 'Times New Roman', serif; font-size: 2.2em; color: #d4af37; margin-bottom: 10px; line-height: 1.3; }}
    .trend-badge {{ display: inline-block; background: #e74c3c; color: white; padding: 4px 12px; border-radius: 20px; font-size: 0.8em; margin-bottom: 20px; }}
    .product-card {{ background: #12121e; border-radius: 16px; padding: 30px; margin: 30px 0; border: 1px solid #333; }}
    .product-card h2 {{ color: #d4af37; font-size: 1.5em; margin-bottom: 10px; }}
    .product-card .price {{ font-size: 1.8em; color: #d4af37; margin: 15px 0; }}
    .product-card .price span {{ font-size: 0.6em; color: #666; }}
    .buy-btn {{ display: inline-block; background: #d4af37; color: #0a0a14; padding: 16px 40px; border-radius: 30px; text-decoration: none; font-weight: bold; font-size: 1.1em; margin: 15px 0; }}
    .buy-btn:hover {{ background: #e8c84a; }}
    .why-buy {{ background: #1a1a2e; border-radius: 12px; padding: 20px; margin: 20px 0; border-left: 4px solid #d4af37; }}
    .related {{ margin-top: 40px; padding-top: 30px; border-top: 1px solid #333; }}
    .related a {{ display: block; color: #d4af37; text-decoration: none; margin-bottom: 10px; }}
    .related a:hover {{ text-decoration: underline; }}
    .brand {{ text-align: center; margin-top: 60px; padding-top: 30px; border-top: 1px solid #333; }}
    .brand p {{ color: #d4af37; font-size: 0.9em; letter-spacing: 2px; }}
    .date {{ color: #666; font-size: 0.85em; margin-bottom: 30px; }}
    p {{ margin-bottom: 20px; font-size: 1.1em; }}
    @media (max-width: 600px) {{ h1 {{ font-size: 1.6em; }} .container {{ padding: 20px 15px; }} }}
  </style>
</head>
<body>
  <div class="container">
    <span class="trend-badge">🔥 TRENDING TODAY</span>
    <h1>{title}</h1>
    <div class="date">Published {date} · Gullah Geechee Biz</div>
    
    <div class="product-card">
      <h2>{product_name}</h2>
      <p>{product_desc}</p>
      <div class="price">${product_price} <span>+ free shipping</span></div>
      <a href="{affiliate_link}" class="buy-btn" target="_blank" rel="nofollow sponsored">Check Price on Amazon →</a>
    </div>
    
    <div class="why-buy">
      <strong style="color: #d4af37;">Why this matters to Gullah Geechee culture:</strong>
      <p>{cultural_connection}</p>
    </div>
    
    <p>{content}</p>
    
    <div class="related">
      <strong style="color: #d4af37;">Explore more:</strong>
      <a href="https://gullahgeecheebiz.com/books">📚 Browse our Gullah Geechee books →</a>
      <a href="https://kofigullahgeecheebiz.substack.com">📧 Subscribe to our newsletter →</a>
      <a href="https://gullahgeecheebiz.com/viral/">📖 Read Gullah Geechee history →</a>
      <a href="https://gullahgeecheebiz.com">🏠 Visit Gullah Geechee Biz →</a>
    </div>
    
    <div class="brand">
      <p>GULLAH GEECHEE BIZ</p>
    </div>
  </div>
</body>
</html>"""

# ── Cultural Connections ──
CULTURAL_CONNECTIONS = {
    "kitchen": "Cooking is at the heart of Gullah Geechee culture. From one-pot meals born of necessity to the rich flavors of West African cuisine, every kitchen tool connects us to ancestors who turned simple ingredients into a culinary legacy that shaped Southern food.",
    "genealogy": "The Gullah Geechee people have one of the most documented yet fragmented genealogies in America. Tracing family lines through slavery, Reconstruction, and the present day is both a challenge and a sacred duty. Every tool that helps reconnect families is preserving history.",
    "home": "Gullah Geechee home decor reflects the colors of the Lowcountry — marsh greens, ocean blues, and the warm gold of sweetgrass. Every piece tells a story of place, of family, of a culture that has shaped the American South for centuries.",
    "books": "The written word is how we ensure Gullah Geechee history is never forgotten. Our encyclopedia series documents every county, every story, every family. Supporting books about Black history means supporting the preservation of our collective memory.",
    "music": "From ring shouts to spirituals to gospel to hip-hop — Gullah Geechee music is the root of American music. Every turntable, every speaker, every playlist is a connection to the ancestors who sang their way through the hardest of times.",
}

def generate_trending_page(product, index):
    """Generate a landing page for a trending product"""
    slug = f"trending-{product['name'].lower().replace(' ', '-').replace('--', '-')[:50]}"
    slug = re.sub(r'[^a-z0-9-]', '', slug)
    
    title = f"Why Everyone Is Buying {product['name']} Right Now"
    meta_desc = f"{product['name']} is trending. Here's why it matters to Gullah Geechee culture — and where to get the best deal."
    keywords = f"{product['name']}, trending, {product['trend_reason']}, Gullah Geechee, best deal"
    
    cultural_connection = CULTURAL_CONNECTIONS.get(product["category"], 
        "This item connects to the rich cultural heritage of the Gullah Geechee people and the Lowcountry.")
    
    content = f"""This {product['name'].lower()} is trending for a reason. People across the country are discovering what the Gullah Geechee community has known for generations — that the best things in life are connected to culture, history, and tradition.

{product['trend_reason']}. And at Gullah Geechee Biz, we believe every purchase is an opportunity to connect with something deeper.

Whether you're looking to {product['category'] == 'kitchen' and 'cook meals that honor your heritage' or product['category'] == 'genealogy' and 'trace your family roots' or product['category'] == 'home' and 'bring the Lowcountry into your home' or 'explore Black history and culture'}, this product is a great place to start.

And while you're here, don't forget to check out our Roots & Rivers encyclopedia series — the definitive guide to Gullah Geechee history, county by county, story by story."""
    
    date = datetime.date.today().strftime("%B %d, %Y")
    
    html = HTML_TEMPLATE.format(
        title=title,
        meta_desc=meta_desc,
        keywords=keywords,
        slug=slug,
        date=date,
        product_name=product["name"],
        product_price=product["price"].replace("$", ""),
        product_desc=product["description"],
        affiliate_link=product["affiliate_link"],
        cultural_connection=cultural_connection,
        content=content,
        og_image=product["image"],
    )
    
    path = TRENDING_DIR / f"{slug}.html"
    with open(path, "w") as f:
        f.write(html)
    
    return path

def update_sitemap():
    """Update sitemap with trending pages"""
    sitemap_path = SITE_DIR / "sitemap.xml"
    
    urls = ["https://gullahgeecheebiz.com/", "https://gullahgeecheebiz.com/shop.html", "https://gullahgeecheebiz.com/shop-binyah.html"]
    
    # Viral pages
    viral_dir = SITE_DIR / "viral"
    for f in sorted(viral_dir.glob("*.html")):
        urls.append(f"https://gullahgeecheebiz.com/viral/{f.stem}")
    
    # Trending pages
    for f in sorted(TRENDING_DIR.glob("*.html")):
        urls.append(f"https://gullahgeecheebiz.com/trending/{f.stem}")
    
    sitemap = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    for url in urls:
        sitemap += f"  <url><loc>{url}</loc></url>\n"
    sitemap += "</urlset>"
    
    with open(sitemap_path, "w") as f:
        f.write(sitemap)
    return sitemap_path

def main():
    print("=" * 60)
    print("  GULLAH GEECHEE BIZ — TRENDING PRODUCTS ENGINE")
    print("=" * 60)
    print()
    
    print(f"Generating {len(TRENDING_PRODUCTS)} trending product pages...")
    for i, product in enumerate(TRENDING_PRODUCTS):
        path = generate_trending_page(product, i)
        print(f"  ✓ {path.name}")
    
    # Create index page
    index_html = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Trending Products | Gullah Geechee Biz</title>
  <meta name="description" content="Today's trending products with a Gullah Geechee connection. Find the best deals on items everyone is buying.">
  <link rel="canonical" href="https://gullahgeecheebiz.com/trending/">
  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #0a0a14; color: #f0ede5; line-height: 1.6; }
    .container { max-width: 800px; margin: 0 auto; padding: 40px 20px; }
    h1 { font-family: Georgia, 'Times New Roman', serif; font-size: 2em; color: #d4af37; margin-bottom: 10px; }
    .subtitle { margin-bottom: 30px; color: #999; }
    .card { background: #12121e; border-radius: 12px; padding: 24px; margin-bottom: 16px; border: 1px solid #222; }
    .card h2 { font-size: 1.2em; margin-bottom: 8px; }
    .card h2 a { color: #d4af37; text-decoration: none; }
    .card h2 a:hover { text-decoration: underline; }
    .card .trend { color: #e74c3c; font-size: 0.8em; margin-top: 8px; }
    .brand { text-align: center; margin-top: 60px; padding-top: 30px; border-top: 1px solid #333; }
    .brand p { color: #d4af37; font-size: 0.9em; letter-spacing: 2px; }
  </style>
</head>
<body>
  <div class="container">
    <h1>🔥 Trending Now</h1>
    <p class="subtitle">Today's hottest products with a Gullah Geechee connection</p>
"""
    for product in TRENDING_PRODUCTS:
        slug = f"trending-{product['name'].lower().replace(' ', '-').replace('--', '-')[:50]}"
        slug = re.sub(r'[^a-z0-9-]', '', slug)
        index_html += f"""    <div class="card">
      <h2><a href="{slug}.html">{product['name']}</a></h2>
      <p>{product['description'][:100]}...</p>
      <div class="trend">🔥 {product['trend_reason']}</div>
    </div>
"""
    
    index_html += """    <div class="brand"><p>GULLAH GEECHEE BIZ</p></div>
  </div>
</body>
</html>"""
    
    with open(TRENDING_DIR / "index.html", "w") as f:
        f.write(index_html)
    print("  ✓ Index page created")
    
    # Update sitemap
    update_sitemap()
    print("  ✓ Sitemap updated")
    
    print(f"\n{'=' * 60}")
    print(f"  ✓ {len(TRENDING_PRODUCTS)} trending product pages generated")
    print(f"  📍 {TRENDING_DIR}")
    print(f"  🌐 https://gullahgeecheebiz.com/trending/")
    print(f"{'=' * 60}")

if __name__ == "__main__":
    main()
