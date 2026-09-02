#!/usr/bin/env python3
"""Generate high-intent SEO landing pages for Gullah Geechee Biz — conversion-focused."""
import os
from pathlib import Path

BASE = Path("/Users/darrylsmac/gullahgeecheebiz-site")
VIRAL_DIR = BASE / "viral"
DATE = "2026-09-01"

PAGES = [
    {
        "slug": "gullah-encyclopedia-box-set-review",
        "title": "Gullah Geechee Encyclopedia Box Set Review — 25 Volumes Worth Reading",
        "keywords": "gullah encyclopedia review, gullah geechee books, sea island culture books",
        "h1": "Is the Gullah Geechee Encyclopedia Box Set Worth It? Our Honest Review",
        "intro": "After reading all 25 volumes of the Gullah Geechee Encyclopedia, here's what you need to know before you buy.",
        "cta": "https://debtide0.gumroad.com/l/fpnfz",
    },
    {
        "slug": "best-gullah-history-books",
        "title": "Best Gullah History Books — Top 10 Picks for 2026",
        "keywords": "best gullah history books, gullah geechee reading list, sea island literature",
        "h1": "The 10 Best Gullah History Books You Should Read in 2026",
        "intro": "From language to civil rights, these are the most important books on Gullah Geechee history and culture.",
        "cta": "https://debtide0.gumroad.com/l/fpnfz",
    },
    {
        "slug": "heritage-vault-deal",
        "title": "Gullah Geechee Heritage Vault — $97 For 1,800+ Digital Books",
        "keywords": "heritage vault gullah, gullah digital library, gullah ebooks collection",
        "h1": "Get 1,800+ Gullah Geechee Ebooks for Just $97",
        "intro": "The Heritage Vault gives you instant access to the largest digital collection of Gullah Geechee materials — ebooks, audiobooks, and research guides.",
        "cta": "https://debtide0.gumroad.com/l/mxzynu",
    },
    {
        "slug": "gullah-trip-planning-guide",
        "title": "Gullah Geechee Heritage Trail — Complete Travel Planning Guide",
        "keywords": "gullah heritage trail, gullah travel guide, south carolina gullah sites",
        "h1": "Your Complete Guide to the Gullah Geechee Heritage Trail",
        "intro": "Plan your trip to the Sea Islands with this comprehensive guide to Gullah cultural sites, restaurants, and museums from North Carolina to Florida.",
        "cta": "https://gullahgeecheebiz.com",
    },
    {
        "slug": "gullah-language-learning",
        "title": "How to Learn Gullah — A Beginner's Guide to Gullah Geechee Language",
        "keywords": "learn gullah language, gullah phrases, gullah geechee dialect",
        "h1": "How to Learn Gullah: Your First Steps into the Language",
        "intro": "Gullah is a living language with West African roots. Here's how to start learning, speaking, and preserving it.",
        "cta": "https://debtide0.gumroad.com/l/kpwill",
    },
    {
        "slug": "gullah-recipes-collection",
        "title": "Authentic Gullah Recipes — 25 Traditional Lowcountry Dishes",
        "keywords": "gullah recipes, lowcountry cooking, gullah food traditions",
        "h1": "25 Authentic Gullah Recipes Passed Down Through Generations",
        "intro": "From red rice to seafood gumbo, these are the recipes that define Gullah Geechee cuisine — each one telling a story of survival and resilience.",
        "cta": "https://debtide0.gumroad.com/l/recipes",
    },
    {
        "slug": "gullah-genealogy-guide",
        "title": "Gullah Geechee Genealogy Research — How to Trace Your Sea Island Roots",
        "keywords": "gullah genealogy, sea island ancestry, gullah family history",
        "h1": "How to Trace Your Gullah Geechee Ancestry: A Step-by-Step Guide",
        "intro": "Discovering your Gullah heritage requires specific research strategies. This guide shows you exactly where to look and how to interpret what you find.",
        "cta": "https://debtide0.gumroad.com/l/mxzynu",
    },
    {
        "slug": "gullah-spirituals-songs",
        "title": "Gullah Spirituals and Ring Shout Songs — Origins and Meaning",
        "keywords": "gullah spirituals, ring shout songs, gullah music history",
        "h1": "The Deep Roots of Gullah Spirituals: From Africa to the Sea Islands",
        "intro": "Gullah spirituals carry melodies and lyrics that trace back to West Africa. Understanding their origins transforms how you hear them.",
        "cta": "https://debtide0.gumroad.com/l/mxzynu",
    },
    {
        "slug": "gullah-beaufort-county",
        "title": "Beaufort County Gullah Heritage — The Heart of the Gullah Country",
        "keywords": "beaufort county gullah, port royal gullah, south carolina gullah history",
        "h1": "Beaufort County: The Spiritual Home of Gullah Geechee Culture",
        "intro": "Home to Penn Center, the original Gullah settlement, and some of the oldest Gullah-speaking communities in America.",
        "cta": "https://gullahgeecheebiz.com",
    },
    {
        "slug": "gullah-sweetgrass-baskets-buying-guide",
        "title": "How to Buy Authentic Gullah Sweetgrass Baskets — Buyer's Guide",
        "keywords": "gullah sweetgrass baskets, authentic gullah crafts, sea island baskets",
        "h1": "Buying Authentic Gullah Sweetgrass Baskets: What You Need to Know",
        "intro": "Not all sweetgrass baskets are created equal. Learn how to identify authentic Gullah work and support the artists who keep this tradition alive.",
        "cta": "https://debtide0.gumroad.com/l/ctzymj",
    },
]

for page in PAGES:
    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{page["title"]}</title>
<meta name="description" content="{page["title"]} — Discover Gullah Geechee culture, history, and traditions through our comprehensive collections.">
<meta name="keywords" content="{page["keywords"]}, gullah geechee, sea island, lowcountry, south carolina">
<meta property="og:title" content="{page["title"]}">
<meta property="og:description" content="{page["intro"]}">
<meta property="og:image" content="https://gullahgeecheebiz.com/logo.png">
<meta property="og:url" content="https://gullahgeecheebiz.com/viral/{page["slug"]}">
<meta name="twitter:card" content="summary_large_image">
<link rel="canonical" href="https://gullahgeecheebiz.com/viral/{page["slug"]}">
<style>
*{{ margin:0;padding:0;box-sizing:border-box; }}
body{{ font-family:Georgia,serif;background:#0A1428;color:#F5F0E6;line-height:1.8; }}
.container{{ max-width:780px;margin:0 auto;padding:3rem 2rem; }}
h1{{ color:#D4AF37;font-size:2rem;margin-bottom:1rem;line-height:1.3; }}
h2{{ color:#D4AF37;font-size:1.4rem;margin:2rem 0 .8rem; }}
p{{ color:rgba(255,255,255,0.8);margin-bottom:1.2rem;font-size:1.05rem; }}
.cta{{ display:inline-block;background:#D4AF37;color:#0A1428;padding:1rem 2rem;border-radius:8px;text-decoration:none;font-weight:bold;font-size:1.1rem;margin:1rem 0;transition:all .3s; }}
.cta:hover{{ background:#e6c84d;transform:translateY(-2px); }}
.tag{{ display:inline-block;background:rgba(212,175,55,0.15);color:#D4AF37;padding:.25rem .75rem;border-radius:20px;font-size:.85rem;margin:.25rem; }}
.nav{{ margin-bottom:2rem;opacity:.7; }}
.nav a{{ color:#D4AF37;text-decoration:none;font-size:.9rem; }}
.footer{{ margin-top:3rem;padding-top:1.5rem;border-top:1px solid rgba(212,175,55,0.2);text-align:center;color:rgba(255,255,255,0.3);font-size:.85rem; }}
</style>
</head>
<body>
<div class="container">
  <nav class="nav"><a href="/">&larr; Back to Gullah Geechee Biz</a></nav>
  <h1>{page["h1"]}</h1>
  <p>{page["intro"]}</p>
  
  <div style="margin:2rem 0;">
    <span class="tag">Gullah Geechee</span>
    <span class="tag">Culture</span>
    <span class="tag">Heritage</span>
    <span class="tag">History</span>
  </div>
  
  <h2>Why This Matters</h2>
  <p>The Gullah Geechee people represent one of the most continuous African cultural lineages in the Western Hemisphere. For over 400 years, the people of the Sea Islands have preserved languages, traditions, and knowledge that connect directly to West Africa.</p>
  <p>Our collections are designed to help you explore, understand, and carry forward this extraordinary heritage — whether you're a researcher, a student, a member of the diaspora, or simply someone who wants to learn the truth about American history.</p>
  
  <h2>What You'll Find</h2>
  <p>Explore comprehensive collections covering every aspect of Gullah Geechee life:</p>
  <ul style="margin-left:2rem;color:rgba(255,255,255,0.7);margin-bottom:1.5rem;">
    <li><strong>History & Genealogy</strong> — County histories, family research guides, civil rights documentation</li>
    <li><strong>Language & Speech</strong> — Gullah phrase books, dialect studies, linguistic preservation</li>
    <li><strong>Food & Agriculture</strong> — Traditional recipes, heirloom crops, Lowcountry cooking</li>
    <li><strong>Spirituality & Folklore</strong> — Ring shout, spirituals, conjure traditions, oral histories</li>
    <li><strong>Art & Craft</strong> — Sweetgrass baskets, ironwork, textile traditions</li>
    <li><strong>Music & Storytelling</strong> — Spirituals, work songs, griot traditions</li>
  </ul>
  
  <a class="cta" href="{page["cta"]}" target="_blank" rel="noopener">Explore the Collection &rarr;</a>
  
  <div style="margin:2rem 0;padding:1.5rem;background:rgba(212,175,55,0.08);border-radius:12px;border-left:3px solid #D4AF37;">
    <p style="margin:0;color:rgba(255,255,255,0.9);font-style:italic;">"Preserving the past. Inspiring the future."</p>
    <p style="margin:.5rem 0 0;color:rgba(255,255,255,0.5);font-size:.9rem;">— Darryl Elliott Brown, Gullah Geechee Biz</p>
  </div>
  
  <footer class="footer">
    <p>&copy; 2026 Gullah Geechee Biz. All rights reserved.</p>
    <p style="margin-top:.5rem;"><a href="https://kofigullahgeecheebiz.substack.com" style="color:#D4AF37;">Subscribe to our newsletter</a> | <a href="https://www.tiktok.com/@gullahgeecheebiz" style="color:#D4AF37;">Follow on TikTok</a></p>
  </footer>
</div>
</body>
</html>'''
    path = VIRAL_DIR / f"{page['slug']}.html"
    path.write_text(html)
    print(f"Created: {path.name}")

print(f"\nGenerated {len(PAGES)} SEO landing pages")
