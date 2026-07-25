#!/usr/bin/env python3
"""
Gullah Geechee Biz — Viral Page Engine
Generates and publishes SEO-optimized pages for trending topics.
Each page drives traffic to books, merch, Substack, and documentaries.
"""

import os, json, subprocess, random, datetime, textwrap, re
from pathlib import Path

HOME = Path.home()
SITE_DIR = HOME / "gullahgeecheebiz-site"
PAGES_DIR = SITE_DIR / "viral"
os.makedirs(PAGES_DIR, exist_ok=True)

# ── Trending Topics (refreshed daily) ──
# These are evergreen viral-adjacent topics tied to Gullah Geechee culture
TRENDING = [
    {
        "slug": "heirs-property-explained",
        "title": "What Is Heirs' Property? A Gullah Geechee Explainer",
        "keywords": ["heirs property", "land ownership", "Gullah Geechee land rights", "family land"],
        "content": """
Heirs' property is land passed down through generations without a formal will. In the Gullah Geechee community, this has been the primary way families have held onto their land since Reconstruction.

But without clear legal title, this land is vulnerable. Developers, corporations, and even government agencies have used partition sales to force families off land they've owned for over a century.

The Gullah Geechee Cultural Heritage Corridor has lost over 70% of its original land base. Heirs' property is at the center of this crisis.

Our documentary series Season 1 covers this in depth. Our books trace the history county by county. And our Substack keeps you updated on the fight to protect Gullah Geechee land.
""",
        "cta": "Watch the Heirs' Property documentary →",
        "cta_link": "https://gullahgeecheebiz.com/season-1",
        "book_link": "https://gullahgeecheebiz.com/books",
        "substack_link": "https://kofigullahgeecheebiz.substack.com"
    },
    {
        "slug": "sweetgrass-baskets-history",
        "title": "Sweetgrass Baskets: The 300-Year-Old Art Form Going Viral",
        "keywords": ["sweetgrass baskets", "Gullah Geechee art", "African American crafts", "Lowcountry culture"],
        "content": """
Sweetgrass baskets are one of the oldest African art forms in North America. Brought to the Lowcountry by enslaved West Africans, this coiled basket tradition has been passed down through generations of Gullah Geechee women.

Today, these baskets sell for hundreds to thousands of dollars. They've been featured in museums, celebrity homes, and design magazines worldwide. But the tradition is at risk — sweetgrass itself is becoming scarce due to coastal development.

The Gullah Geechee Biz Travel Magazine covers the communities where this art form thrives. Our books document the history. And our podcast interviews the artisans keeping the tradition alive.
""",
        "cta": "Explore Gullah Geechee art →",
        "cta_link": "https://gullahgeecheebiz.com/books",
        "book_link": "https://gullahgeecheebiz.com/books",
        "substack_link": "https://kofigullahgeecheebiz.substack.com"
    },
    {
        "slug": "gullah-language-survival",
        "title": "The Gullah Language Is Still Spoken — Here's Why It Matters",
        "keywords": ["Gullah language", "Geechee language", "African American dialect", "Sea Islands culture"],
        "content": """
The Gullah language is a English-based creole with direct roots in West African languages like Mende, Twi, and Yoruba. It developed on the Sea Islands of South Carolina and Georgia during the transatlantic slave trade.

Today, only a few thousand fluent speakers remain. But there's a resurgence. Linguists, educators, and Gullah Geechee communities are working to preserve and teach the language to new generations.

Our Roots & Rivers encyclopedia documents Gullah language history county by county. Our podcast features native speakers. And our Substack shares language lessons and cultural context.
""",
        "cta": "Learn Gullah language history →",
        "cta_link": "https://gullahgeecheebiz.com/books",
        "book_link": "https://gullahgeecheebiz.com/books",
        "substack_link": "https://kofigullahgeecheebiz.substack.com"
    },
    {
        "slug": "penn-center-history",
        "title": "Penn Center: The School That Changed Gullah Geechee History",
        "keywords": ["Penn Center", "St. Helena Island", "Gullah Geechee education", "civil rights history"],
        "content": """
Penn Center on St. Helena Island was one of the first schools in the United States established to educate formerly enslaved African Americans. Founded in 1862, it became a cornerstone of Gullah Geechee education and community life.

During the Civil Rights Movement, Penn Center was one of the only places in the South where interracial groups could meet safely. Dr. Martin Luther King Jr. and the Southern Christian Leadership Conference held retreats there.

Today, Penn Center is a National Historic Landmark and a living testament to Gullah Geechee resilience. Our Travel Magazine covers St. Helena Island in depth. Our books trace the full history.
""",
        "cta": "Read about St. Helena Island →",
        "cta_link": "https://gullahgeecheebiz.com/books",
        "book_link": "https://gullahgeecheebiz.com/books",
        "substack_link": "https://kofigullahgeecheebiz.substack.com"
    },
    {
        "slug": "gullah-geechee-food-history",
        "title": "How Gullah Geechee Cuisine Shaped Southern Food",
        "keywords": ["Gullah Geechee food", "Lowcountry cuisine", "soul food history", "African American cooking"],
        "content": """
Red rice, okra soup, shrimp and grits, benne wafers — these aren't just Southern dishes. They're Gullah Geechee dishes with direct roots in West African cooking traditions.

Enslaved Gullah Geechee people brought rice cultivation expertise that made South Carolina the rice capital of America. They brought okra, black-eyed peas, and watermelon from Africa. They created one-pot meals that became the foundation of Southern cuisine.

Today, Gullah Geechee chefs are reclaiming this culinary heritage. Our Travel Magazine covers the best Gullah Geechee restaurants. Our books document food history. And our podcast interviews the chefs keeping these traditions alive.
""",
        "cta": "Explore Gullah Geechee food →",
        "cta_link": "https://gullahgeecheebiz.com/books",
        "book_link": "https://gullahgeecheebiz.com/books",
        "substack_link": "https://kofigullahgeecheebiz.substack.com"
    },
    {
        "slug": "robert-smalls-hero",
        "title": "Robert Smalls: The Gullah Geechee Hero Who Stole a Confederate Ship",
        "keywords": ["Robert Smalls", "Gullah Geechee hero", "Civil War history", "African American naval history"],
        "content": """
In 1862, an enslaved Gullah Geechee man named Robert Smalls commandeered a Confederate transport ship, the CSS Planter, sailed it past Confederate checkpoints, and delivered it to the Union Navy — along with its cannons and munitions.

He freed himself, his crew, and their families. He went on to serve in the Union Navy, became a successful businessman, and was elected to the U.S. House of Representatives.

Robert Smalls is one of the greatest American heroes you've never heard of. Our Season 1 documentary covers his story in depth. Our books trace his life and legacy. And our podcast explores the Gullah Geechee heroes history forgot.
""",
        "cta": "Watch the Robert Smalls documentary →",
        "cta_link": "https://gullahgeecheebiz.com/season-1",
        "book_link": "https://gullahgeecheebiz.com/books",
        "substack_link": "https://kofigullahgeecheebiz.substack.com"
    },
    {
        "slug": "sea-islands-climate-change",
        "title": "The Sea Islands Are Sinking — A Gullah Geechee Crisis",
        "keywords": ["Sea Islands", "climate change", "Gullah Geechee displacement", "coastal erosion"],
        "content": """
The Sea Islands of South Carolina and Georgia are on the front lines of climate change. Rising sea levels, stronger hurricanes, and coastal erosion threaten the very land the Gullah Geechee community has called home for centuries.

Hilton Head, St. Helena, Edisto, Daufuskie — these islands are losing ground. And with the land goes the culture. Cemeteries are flooding. Historic sites are eroding. Communities are being forced to relocate.

This is the most urgent story in Gullah Geechee history today. Our documentary series covers it. Our books document what's being lost. And our Substack tracks the fight to save the Sea Islands.
""",
        "cta": "Learn about the Sea Islands →",
        "cta_link": "https://gullahgeecheebiz.com/books",
        "book_link": "https://gullahgeecheebiz.com/books",
        "substack_link": "https://kofigullahgeecheebiz.substack.com"
    },
    {
        "slug": "gullah-geechee-music-origins",
        "title": "From Ring Shouts to Hip-Hop: Gullah Geechee Music's Hidden Influence",
        "keywords": ["Gullah Geechee music", "ring shout", "African American music history", "spirituals"],
        "content": """
The ring shout — an African-derived dance and worship tradition — is the oldest surviving African American musical practice in North America. And it was preserved by the Gullah Geechee.

From ring shouts came spirituals. From spirituals came gospel, blues, jazz, and eventually R&B and hip-hop. The Gullah Geechee people didn't just preserve African music — they shaped the entire trajectory of American music.

Our documentary series features Gullah Geechee music traditions. Our books document the cultural history. And our podcast plays the music and tells the stories behind it.
""",
        "cta": "Explore Gullah Geechee music →",
        "cta_link": "https://gullahgeecheebiz.com/season-1",
        "book_link": "https://gullahgeecheebiz.com/books",
        "substack_link": "https://kofigullahgeecheebiz.substack.com"
    },
    {
        "slug": "combahee-river-raid",
        "title": "The Combahee River Raid: Harriet Tubman's Greatest Mission",
        "keywords": ["Combahee River Raid", "Harriet Tubman", "Gullah Geechee history", "Civil War"],
        "content": """
In June 1863, Harriet Tubman became the first woman to lead a major military operation in American history. The Combahee River Raid freed over 700 enslaved people in the South Carolina Lowcountry — most of them Gullah Geechee.

The raid was a turning point in the Civil War. It proved that Black soldiers could fight and win. It also showed the Union that the Gullah Geechee people were ready to fight for their own freedom.

Our Season 1 documentary covers the Combahee River Raid in detail. Our books trace the history of the river and the communities along it. And our Substack shares stories of Gullah Geechee resistance.
""",
        "cta": "Watch the Combahee River Raid documentary →",
        "cta_link": "https://gullahgeecheebiz.com/season-1",
        "book_link": "https://gullahgeecheebiz.com/books",
        "substack_link": "https://kofigullahgeecheebiz.substack.com"
    },
    {
        "slug": "gullah-geechee-tourism",
        "title": "Beyond the Resorts: Authentic Gullah Geechee Tourism Guide",
        "keywords": ["Gullah Geechee tourism", "Lowcountry travel", "cultural tourism", "Sea Islands travel"],
        "content": """
Hilton Head, Charleston, Savannah — millions of tourists visit the Lowcountry every year. Most never experience the real Gullah Geechee culture.

But there's a growing movement toward authentic cultural tourism. Travelers want more than golf courses and beach resorts. They want to meet the people, taste the food, and learn the history that makes the Lowcountry unique.

Our Travel Magazine covers the best Gullah Geechee experiences — from sweetgrass basket demonstrations on St. Helena to Gullah cuisine tours in Charleston. Our books are the definitive guides. And our podcast takes you inside the communities.
""",
        "cta": "Plan your Gullah Geechee trip →",
        "cta_link": "https://gullahgeecheebiz.com/books",
        "book_link": "https://gullahgeecheebiz.com/books",
        "substack_link": "https://kofigullahgeecheebiz.substack.com"
    },
]

# ── HTML Template ──
HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title} | Gullah Geechee Biz</title>
  <meta name="description" content="{description}">
  <meta name="keywords" content="{keywords}">
  <meta property="og:title" content="{title} | Gullah Geechee Biz">
  <meta property="og:description" content="{description}">
  <meta property="og:image" content="https://gullahgeecheebiz.com/logo.png">
  <meta property="og:url" content="https://gullahgeecheebiz.com/viral/{slug}">
  <meta name="twitter:card" content="summary_large_image">
  <link rel="canonical" href="https://gullahgeecheebiz.com/viral/{slug}">
  <style>
    * {{ margin: 0; padding: 0; box-sizing: border-box; }}
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #0a0a14; color: #f0ede5; line-height: 1.8; }}
    .container {{ max-width: 800px; margin: 0 auto; padding: 40px 20px; }}
    h1 {{ font-family: Georgia, 'Times New Roman', serif; font-size: 2.2em; color: #d4af37; margin-bottom: 20px; line-height: 1.3; }}
    p {{ margin-bottom: 20px; font-size: 1.1em; }}
    .cta {{ display: inline-block; background: #d4af37; color: #0a0a14; padding: 16px 32px; border-radius: 30px; text-decoration: none; font-weight: bold; font-size: 1.1em; margin: 20px 0; }}
    .cta:hover {{ background: #e8c84a; }}
    .links {{ margin-top: 40px; padding-top: 30px; border-top: 1px solid #333; }}
    .links a {{ display: block; color: #d4af37; text-decoration: none; margin-bottom: 10px; font-size: 1em; }}
    .links a:hover {{ text-decoration: underline; }}
    .brand {{ text-align: center; margin-top: 60px; padding-top: 30px; border-top: 1px solid #333; }}
    .brand img {{ width: 60px; height: 60px; border-radius: 50%; border: 2px solid #d4af37; }}
    .brand p {{ color: #d4af37; font-size: 0.9em; margin-top: 10px; letter-spacing: 2px; }}
    .date {{ color: #666; font-size: 0.85em; margin-bottom: 30px; }}
    @media (max-width: 600px) {{ h1 {{ font-size: 1.6em; }} .container {{ padding: 20px 15px; }} }}
  </style>
</head>
<body>
  <div class="container">
    <h1>{title}</h1>
    <div class="date">Published {date} · Gullah Geechee Biz</div>
    {content_html}
    <a href="{cta_link}" class="cta">{cta}</a>
    <div class="links">
      <strong style="color: #d4af37;">Explore more:</strong>
      <a href="{book_link}">📚 Browse our books →</a>
      <a href="{substack_link}">📧 Subscribe to our newsletter →</a>
      <a href="https://gullahgeecheebiz.com">🏠 Visit Gullah Geechee Biz →</a>
    </div>
    <div class="brand">
      <img src="https://gullahgeecheebiz.com/logo.png" alt="Gullah Geechee Biz">
      <p>GULLAH GEECHEE BIZ</p>
    </div>
  </div>
</body>
</html>"""

def generate_page(topic):
    """Generate an HTML page for a trending topic"""
    slug = topic["slug"]
    title = topic["title"]
    keywords = ", ".join(topic["keywords"])
    description = topic["content"].strip().split("\n")[0][:160]
    
    # Convert content to HTML paragraphs
    paragraphs = [p.strip() for p in topic["content"].strip().split("\n\n")]
    content_html = "\n".join(f"    <p>{p}</p>" for p in paragraphs if p)
    
    date = datetime.date.today().strftime("%B %d, %Y")
    
    html = HTML_TEMPLATE.format(
        title=title,
        description=description,
        keywords=keywords,
        slug=slug,
        date=date,
        content_html=content_html,
        cta=topic["cta"],
        cta_link=topic["cta_link"],
        book_link=topic["book_link"],
        substack_link=topic["substack_link"],
    )
    
    path = PAGES_DIR / f"{slug}.html"
    with open(path, "w") as f:
        f.write(html)
    
    return path

def update_sitemap():
    """Update the sitemap with all viral pages"""
    sitemap_path = SITE_DIR / "sitemap.xml"
    
    urls = []
    # Existing pages
    urls.append("https://gullahgeecheebiz.com/")
    urls.append("https://gullahgeecheebiz.com/shop.html")
    urls.append("https://gullahgeecheebiz.com/shop-binyah.html")
    
    # Viral pages
    for f in sorted(PAGES_DIR.glob("*.html")):
        slug = f.stem
        urls.append(f"https://gullahgeecheebiz.com/viral/{slug}")
    
    sitemap = '<?xml version="1.0" encoding="UTF-8"?>\n'
    sitemap += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    for url in urls:
        sitemap += f"  <url><loc>{url}</loc></url>\n"
    sitemap += "</urlset>"
    
    with open(sitemap_path, "w") as f:
        f.write(sitemap)
    
    return sitemap_path

def main():
    print("=" * 60)
    print("  GULLAH GEECHEE BIZ — VIRAL PAGE ENGINE")
    print("=" * 60)
    print()
    
    # Generate all pages
    print(f"Generating {len(TRENDING)} viral pages...")
    for topic in TRENDING:
        path = generate_page(topic)
        print(f"  ✓ {path.name}")
    
    # Update sitemap
    sitemap = update_sitemap()
    print(f"\n  ✓ Sitemap updated: {sitemap.name}")
    
    # Create index page
    index_html = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Viral Topics | Gullah Geechee Biz</title>
  <meta name="description" content="Trending topics in Gullah Geechee culture, history, and heritage.">
  <link rel="canonical" href="https://gullahgeecheebiz.com/viral/">
  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #0a0a14; color: #f0ede5; line-height: 1.6; }
    .container { max-width: 800px; margin: 0 auto; padding: 40px 20px; }
    h1 { font-family: Georgia, 'Times New Roman', serif; font-size: 2em; color: #d4af37; margin-bottom: 10px; }
    p { margin-bottom: 30px; color: #999; }
    .card { background: #12121e; border-radius: 12px; padding: 24px; margin-bottom: 16px; border: 1px solid #222; }
    .card h2 { font-size: 1.2em; margin-bottom: 8px; }
    .card h2 a { color: #d4af37; text-decoration: none; }
    .card h2 a:hover { text-decoration: underline; }
    .card p { color: #aaa; font-size: 0.9em; margin-bottom: 0; }
    .brand { text-align: center; margin-top: 60px; padding-top: 30px; border-top: 1px solid #333; }
    .brand p { color: #d4af37; font-size: 0.9em; letter-spacing: 2px; }
  </style>
</head>
<body>
  <div class="container">
    <h1>Gullah Geechee Culture</h1>
    <p>Trending topics in Gullah Geechee history, culture, and heritage</p>
"""
    
    for topic in TRENDING:
        index_html += f"""    <div class="card">
      <h2><a href="{topic['slug']}.html">{topic['title']}</a></h2>
      <p>{topic['content'].strip().split(chr(10))[0][:120]}...</p>
    </div>
"""
    
    index_html += """    <div class="brand">
      <p>GULLAH GEECHEE BIZ</p>
    </div>
  </div>
</body>
</html>"""
    
    with open(PAGES_DIR / "index.html", "w") as f:
        f.write(index_html)
    print("  ✓ Index page created")
    
    print(f"\n{'=' * 60}")
    print(f"  ✓ {len(TRENDING)} viral pages ready")
    print(f"  📍 {PAGES_DIR}")
    print(f"  🌐 https://gullahgeecheebiz.com/viral/")
    print(f"{'=' * 60}")

if __name__ == "__main__":
    main()
