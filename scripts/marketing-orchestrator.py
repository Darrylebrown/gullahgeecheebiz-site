#!/usr/bin/env python3
"""
GGB Marketing Orchestrator — SEO Content Expansion Run
Creates 5 new high-intent long-tail SEO pages with structured data,
Gumroad CTAs, cross-links, and sitemap updates.
"""
import json
import datetime
from pathlib import Path

HOME = Path.home()
SITE_DIR = HOME / "gullahgeecheebiz-site"
PAGES_DIR = SITE_DIR / "viral"
SITEMAP_PATH = SITE_DIR / "sitemap.xml"

GUMROAD_TIER1 = "https://debtide0.gumroad.com/l/fpnfz"
GUMROAD_TIER2 = "https://debtide0.gumroad.com/l/rlxww"
GUMROAD_TIER3 = "https://debtide0.gumroad.com/l/hoiak"
SUBSTACK = "https://kofigullahgeecheebiz.substack.com"
CANONICAL_BASE = "https://gullahgeecheebiz.com/viral/"

TODAY = datetime.date.today().strftime("%B %d, %Y")

NEW_PAGES = [
    {
        "slug": "gullah-geechee-words-phrases-dictionary",
        "title": "100 Essential Gullah Geechee Words & Phrases Dictionary",
        "meta_desc": "Learn the most important Gullah Geechee words and phrases. A complete dictionary of Gullah language terms still spoken in the Sea Islands today.",
        "keywords": "Gullah words, Geechee phrases, Gullah dictionary, Gullah language examples, Sea Island words, African American dialect",
        "category": "Language & Culture",
        "sections": [
            ("What Is Gullah Language?",
             "The Gullah language — also called Gullah Geechee or simply Geechee — is an English-based creole with deep roots in West African languages including Mende, Twi, Yoruba, and Kikongo. Spoken primarily on the Sea Islands of South Carolina and Georgia, it is one of the few African American vernaculars that has survived intact since the colonial era."),
            ("Why Gullah Is Unique",
             "Unlike other African American dialects that have largely merged with mainstream American English, Gullah has retained distinctive vocabulary, grammar patterns, and phonological features from its West African substrate. The isolation of the Sea Islands allowed the language to develop independently, preserving words and expressions that trace directly back to enslaved Africans."),
            ("Essential Gullah Words You Should Know",
             "Below is a curated list of the most widely used Gullah Geechee words and phrases. These terms appear in everyday speech across the Lowcountry and are essential for anyone seeking to understand Gullah Geechee culture, history, or family heritage."),
            ("Sample Gullah Words & Meanings",
             "<p><strong>Buh nuh</strong> — That's not true / No way (literally: don't tell me)</p>"
             "<p><strong>Yallow</strong> — Yellow; also used to describe something pale or wan</p>"
             "<p><strong>Winta</strong> — Winter; the cool season on the Sea Islands</p>"
             "<p><strong>Sea Isle</strong> — Referring to the Sea Islands themselves; many Gullah speakers identify as Sea Isle people</p>"
             "<p><strong>Bless your heart</strong> — A Gullah expression of sympathy, often used with genuine warmth rather than sarcasm</p>"
             "<p><strong>Ain't no tellin'</strong> — It cannot be known or predicted; an expression of uncertainty</p>"
             "<p><strong>Chatawnee</strong> — A type of wild grape vine native to the Southeast; also refers to a place where such vines grow</p>"
             "<p><strong>Red clay</strong> — The iconic red soil of the Lowcountry; used metaphorically to describe Gullah identity</p>"
             "<p><strong>Sippoo</strong> — Small; little (from Wolof sip)</p>"
             "<p><strong>Buckra</strong> — A white person (from Igbo ebuka)</p>"),
            ("Gullah vs. Geechee: What's the Difference?",
             "Gullah typically refers to the language and culture of South Carolina Sea Islands, while Geechee is used more broadly for coastal Georgia and northeastern Florida. However, many speakers use the terms interchangeably. Both descend from the same West African linguistic roots."),
            ("Why Learning Gullah Words Matters",
             "Understanding Gullah vocabulary is not just a linguistic exercise — it is an act of cultural preservation. Each word carries centuries of history, resistance, and creativity. When you learn a Gullah word, you are connecting with the lived experience of people who built the Lowcountry economy and preserved their heritage."),
            ("How Gullah Language Influences American English",
             "Many Gullah words have entered mainstream Southern and American English. Expressions like 'buckra,' 'sippoo,' and 'chatawnee' have documented histories in American linguistics. The rhythmic patterns of Gullah speech also influenced jazz, hip-hop, and Southern storytelling traditions."),
            ("Explore the Complete Gullah Geechee Encyclopedia",
             "Our 25-volume encyclopedia documents Gullah Geechee language, history, culture, and genealogy county by county. It is the most comprehensive reference work on the subject available in print."),
        ],
        "related_pages": [
            "gullah-language-preservation",
            "gullah-language-survival",
            "gullah-geechee-recipes",
            "gullah-geechee-ancestry-genealogy",
        ],
    },
    {
        "slug": "gullah-geechee-genealogy-research-guide",
        "title": "How to Trace Gullah Geechee Ancestry: A Complete Genealogy Guide",
        "meta_desc": "Step-by-step guide to researching Gullah Geechee family history. Learn how to trace your Sea Islands ancestry using census records, church registers, and DNA.",
        "keywords": "Gullah genealogy, Geechee ancestry research, Sea Islands family history, African American genealogy, Gullah family tree, Lowcountry roots",
        "category": "Genealogy & Research",
        "sections": [
            ("Why Gullah Geechee Genealogy Is Different",
             "Researching Gullah Geechee ancestry requires understanding the unique historical context of the Sea Islands. Unlike other African American communities, Gullah families often maintained multigenerational ties to the same islands and plantations, creating unusually rich but also complicated record trails."),
            ("Key Records for Gullah Geechee Family History",
             "The most valuable records for Gullah genealogy include: Federal census manuscripts (especially the 1870 census, the first to name formerly enslaved people); plantation ledgers and slave schedules; Freedmen's Bureau records; church baptism and marriage registers; and pension files from the Civil War and Spanish-American War."),
            ("Church Records: A Goldmine for Sea Islands Research",
             "African Methodist Episcopal (AME), AME Zion, and Baptist churches on the Sea Islands maintained meticulous membership rolls dating back to the early 1800s. These records often include family relationships, places of origin in Africa, and dates of enslavement and freedom."),
            ("Census Research Strategy",
             "Start with the 1870 U.S. Census — the first census to enumerate formerly enslaved people by name. Identify your ancestor's household, note neighbors (who often were kin), and work backward through earlier censuses. The 1860 Slave Schedule can help identify enslavers."),
            ("DNA Testing for Gullah Geechee Ancestry",
             "Genetic genealogy has become an essential tool for Gullah researchers. Autosomal DNA tests can confirm paper-trail connections and reveal West African ethnic group origins. Y-DNA and mtDNA testing can trace direct paternal and maternal lineages back to specific African regions."),
            ("Common Mistakes in Gullah Genealogy Research",
             "Researchers often mistakenly assume all Black ancestors from a region share the same lineage. In the Sea Islands, multiple distinct African ethnic groups were present, and intermarriage among free Black families, enslaved people, and Native American communities created complex genealogical patterns."),
            ("Online Resources for Gullah Family History",
             "The Gullah Geechee Cultural Heritage Corridor Commission maintains research databases. FamilySearch and Ancestry have extensive Southern collections. The South Carolina Department of Archives and History holds thousands of plantation and church records."),
            ("Our Encyclopedia Can Accelerate Your Research",
             "Volume 1-25 of our Gullah Geechee Encyclopedia covers each county's history, prominent families, and institutional records — providing context that generic genealogy databases lack."),
        ],
        "related_pages": [
            "gullah-geechee-ancestry-genealogy",
            "gullah-geechee-ancestry-dna-testing",
            "heirs-property-explained",
            "st-helena-island-gullah-geechee",
        ],
    },
    {
        "slug": "gullah-geechee-lowcountry-recipes-traditional",
        "title": "Traditional Gullah Geechee Recipes: Lowcountry Cooking from the Sea Islands",
        "meta_desc": "Authentic Gullah Geechee recipes passed down through generations — red rice, shrimp and grits, okra soup, benne wafers, and more Lowcountry classics.",
        "keywords": "Gullah recipes, Geechee cooking, Lowcountry food, Gullah Geechee cuisine, Southern food history, African American recipes",
        "category": "Food & Cuisine",
        "sections": [
            ("The West African Roots of Lowcountry Cooking",
             "Gullah Geechee cuisine is one of the most influential food traditions in American history. Enslaved West Africans brought rice cultivation knowledge, okra, black-eyed peas, watermelon, yams, and cooking techniques that transformed the Southern culinary landscape."),
            ("Red Rice: The Crown Jewel of Gullah Cooking",
             "Red rice — rice cooked with tomatoes, onions, peppers, and smoked meat — is the signature dish of the Gullah Geechee kitchen. Its origins trace directly to Jollof rice and other West African one-pot rice dishes. Every Gullah family has their own version."),
            ("Essential Gullah Geechee Dishes",
             "<p><strong>Okra Soup</strong> — A thick, savory stew made with fresh okra, tomatoes, and smoked fish or meat. Okra itself is West African in origin.</p>"
             "<p><strong>Shrimp and Grits</strong> — Once a breakfast food for Lowcountry fishermen, now a Southern staple. Gullah shrimp and grits uses stone-ground grits and local shrimp.</p>"
             "<p><strong>Benne Wafers</strong> — Thin, crisp cookies made with sesame seeds (benne is the Gullah word for sesame).</p>"
             "<p><strong>Corn Bread & Molasses</strong> — Simple, sustaining, and deeply associated with Gullah foodways.</p>"
             "<p><strong>Chicken Pot Pie (Gullah Style)</strong> — A one-dish meal reflecting the one-pot tradition of West African cooking.</p>"),
            ("The Role of Women in Preserving Gullah Foodways",
             "Gullah Geechee culinary knowledge has been transmitted primarily through women — grandmothers teaching granddaughters, mothers passing recipes to daughters. This oral tradition of food knowledge is one of the most resilient aspects of Gullah cultural survival."),
            ("Lowcountry Ingredients You Should Know",
             "Key ingredients in Gullah cooking include: fresh shrimp and crab from the estuaries; okra and collard greens from community gardens; benne (sesame); sweet potatoes; bluefish; oysters; and rice. Many of these ingredients are native to or were introduced by West African enslaved people."),
            ("Where to Experience Gullah Geechee Food Today",
             "Charleston has a thriving Gullah Geechee restaurant scene. On the islands, community kitchens and churches often serve traditional food during heritage festivals. The Gullah Geechee Cocoa Trail features chocolate makers who honor West African cacao traditions."),
            ("Our Complete Gullah Geechee Cookbook Collection",
             "Our 25-volume encyclopedia includes extensive sections on Lowcountry food history, regional recipes, and the agricultural traditions that made Gullah Geechee cuisine what it is."),
        ],
        "related_pages": [
            "gullah-geechee-recipes",
            "gullah-geechee-food-history",
            "gullah-geechee-rice-history",
            "african-american-cooking-techniques",
        ],
    },
    {
        "slug": "gullah-geechee-sea-islands-travel-itinerary",
        "title": "Gullah Geechee Sea Islands Travel Itinerary: The Ultimate Lowcountry Guide",
        "meta_desc": "Plan your Gullah Geechee cultural tour of the Sea Islands — St. Helena, Kiawah, James Island, Sapelo, and Daufuskie. Best sites, restaurants, and tours.",
        "keywords": "Gullah travel, Sea Islands tour, Lowcountry itinerary, St. Helena Island, Kiawah Island, Sapelo Island, Gullah tourism, Charleston SC travel",
        "category": "Travel & Tourism",
        "sections": [
            ("Why Visit the Sea Islands?",
             "The Sea Islands of South Carolina and Georgia are the spiritual and cultural homeland of the Gullah Geechee people. These barrier islands preserve one of the oldest continuous African American cultures in the Western Hemisphere."),
            ("St. Helena Island: The Heart of Gullah Culture",
             "St. Helena Island is home to Penn Center, the first school for freed African Americans, and one of the largest remaining Gullah communities in the world. Visit the Penn Center Historic Site, the St. Helena Island Museum, and the community churches."),
            ("Kiawah and Seabrook Islands: History Beyond the Resorts",
             "While Kiawah is known for luxury resorts, the island also has a deep Gullah history. The New York Plantation, established in the 1700s, was a major rice plantation worked by enslaved Gullah people. Guided historical tours are available."),
            ("James Island: Closest to Charleston, Deepest Gullah Roots",
             "James Island, just across the Arthur Ravenel Jr. Bridge from downtown Charleston, is home to some of South Carolina's oldest Gullah communities. The James Island Cultural Center hosts exhibitions celebrating Gullah heritage."),
            ("Sapelo Island, Georgia: The Most Remote Gullah Community",
             "Sapelo Island is accessible only by ferry and is home to Hog Hammock, one of the last intact Gullah communities in America. Tours must be arranged through the University of Georgia or the Sapelo Island Cultural and Ecological Foundation."),
            ("Practical Travel Tips",
             "Best time to visit: March through May or September through November. Book ferry access to Sapelo well in advance. Respect private property and residential communities. Support Gullah-owned businesses and tour operators."),
            ("Cultural Etiquette for Visitors",
             "When visiting Gullah communities, approach with respect and humility. Ask before photographing people or private property. Learn about the history before you arrive. Consider taking a guided tour with a Gullah guide."),
            ("Related: Gullah Geechee Historic Sites & Museums",
             "For a complete list of Gullah Geechee historic sites, museums, and cultural centers across the Heritage Corridor, see our Gullah Geechee Historic Sites guide."),
        ],
        "related_pages": [
            "sapelo-island-gullah-geechee",
            "st-helena-island-gullah-geechee",
            "gullah-geechee-historic-sites",
            "gullah-geechee-heritage-trail",
            "sea-islands-lowcountry-history-guide",
        ],
    },
    {
        "slug": "gullah-geechee-historic-sites-museums-full-guide",
        "title": "Gullah Geechee Historic Sites & Museums: The Complete Heritage Corridor Guide",
        "meta_desc": "Every Gullah Geechee historic site, museum, plantation, and cultural center in the Gullah Geechee Cultural Heritage Corridor — South Carolina, Georgia, and Florida.",
        "keywords": "Gullah historic sites, Gullah museums, Gullah Geechee Heritage Corridor, Sea Islands museums, Lowcountry historical sites, Gullah cultural centers",
        "category": "History & Heritage",
        "sections": [
            ("The Gullah Geechee Cultural Heritage Corridor",
             "Established by Congress in 2006, the Gullah Geechee Cultural Heritage Corridor encompasses approximately 25,000 square miles along the coastal stretch from Cape Fear, North Carolina, to the St. Johns River in Florida."),
            ("South Carolina Sites",
             "<p><strong>Penn Center Historic Site</strong> (St. Helena Island) — Founded 1862, the first school for freed African Americans. A National Historic Landmark.</p>"
             "<p><strong>Harriet Tubman Jubilee Shrine</strong> (Union Point, SC) — Located on the site where Harriet Tubman baptized formerly enslaved people after the Combahee River Raid.</p>"
             "<p><strong>Kiawah Island Historical Trail</strong> — Self-guided tour of Gullah heritage sites on Kiawah.</p>"
             "<p><strong>James Island Cultural Center</strong> (Charleston) — Exhibits on Gullah history, culture, and contemporary life.</p>"
             "<p><strong>Old Sheldon Church Ruins</strong> (near Georgetown) — Antebellum church where Gullah worshippers played a central role.</p>"),
            ("Georgia Sites",
             "<p><strong>Sapelo Island Cultural and Ecological Foundation</strong> — Manages tours and preservation on Sapelo Island, home to Hog Hammock.</p>"
             "<p><strong>Darien Historic Society</strong> — Documents the history of this important Gullah community in McIntosh County.</p>"
             "<p><strong>Jekyll Island Museum</strong> — Includes exhibits on the Gullah Geechee workers who built and maintained the island's estates.</p>"),
            ("Florida Sites",
             "<p><strong>St. Augustine's African Heritage Trails</strong> — St. Augustine's African colonial history connects to the broader Southern Black heritage that Gullah culture represents.</p>"),
            ("Plantation Sites with Gullah History",
             "Several former rice plantations along the Cooper, Stono, and Edisto rivers offer guided tours that include Gullah Geechee history. The Drayton Hall Plantation and Boone Hall Plantation both acknowledge the Gullah labor force."),
            ("Museums Dedicated to Gullah Culture",
             "The Gullah Geechee Corporation operates visitor centers and digital resources. The International African American Museum in Charleston (opened 22024) includes significant Gullah Geechee exhibitions."),
            ("How to Visit: Planning Your Heritage Tour",
             "The Gullah Geechee Cultural Heritage Corridor Commission publishes official maps and itineraries. Consider a self-drive route along Highway 17 (SC) and Highway 400 (GA). Stay in locally-owned guesthouses on St. Helena and Sapelo for the most authentic experience."),
            ("Our Encyclopedia Covers Every Site in Depth",
             "Volumes 1-25 of our Gullah Geechee Encyclopedia provide detailed historical accounts of every county, island, and community in the Heritage Corridor."),
        ],
        "related_pages": [
            "st-helena-island-gullah-geechee",
            "sapelo-island-gullah-geechee",
            "gullah-geechee-sea-islands-travel-itinerary",
            "gullah-geechee-heritage-trail",
            "robert-smalls-hero",
        ],
    },
]


def build_structured_data(title, meta_desc, slug):
    """Build JSON-LD structured data as a string."""
    ld_article = {
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": title,
        "description": meta_desc,
        "image": "https://gullahgeecheebiz.com/logo.png",
        "author": {
            "@type": "Organization",
            "name": "Gullah Geechee Biz",
            "url": "https://gullahgeecheebiz.com"
        },
        "publisher": {
            "@type": "Organization",
            "name": "Gullah Geechee Biz",
            "logo": {
                "@type": "ImageObject",
                "url": "https://gullahgeecheebiz.com/logo.png"
            }
        },
        "datePublished": TODAY,
        "dateModified": TODAY,
        "mainEntityOfPage": CANONICAL_BASE + slug
    }
    ld_breadcrumb = {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Home", "item": "https://gullahgeecheebiz.com"},
            {"@type": "ListItem", "position": 2, "name": "Culture & Heritage Guide", "item": "https://gullahgeecheebiz.com/viral/"},
            {"@type": "ListItem", "position": 3, "name": title, "item": CANONICAL_BASE + slug}
        ]
    }
    ld_org = {
        "@context": "https://schema.org",
        "@type": "Organization",
        "name": "Gullah Geechee Biz",
        "url": "https://gullahgeecheebiz.com",
        "logo": "https://gullahgeecheebiz.com/logo.png",
        "sameAs": [
            "https://www.instagram.com/gullahgeecheebiz",
            "https://www.pinterest.com/gullahgeecheebiz",
            "https://kofigullahgeecheebiz.substack.com"
        ]
    }
    return (
        '<script type="application/ld+json">' + json.dumps(ld_article) + '</script>\n'
        '<script type="application/ld+json">' + json.dumps(ld_breadcrumb) + '</script>\n'
        '<script type="application/ld+json">' + json.dumps(ld_org) + '</script>'
    )


def build_html(page):
    """Build a full HTML page with structured data, CTAs, and cross-links."""
    slug = page["slug"]
    title = page["title"]
    meta_desc = page["meta_desc"]
    keywords = page["keywords"]
    sections = page["sections"]
    related = page.get("related_pages", [])

    section_html = ""
    for heading, body in sections:
        section_html += "    <h2>" + heading + "</h2>\n"
        section_html += "    " + body + "\n\n"

    related_html = ""
    for rel_slug in related:
        rel_title = rel_slug.replace("-", " ").title()
        related_html += "      <a href=\"" + CANONICAL_BASE + rel_slug + ".html\">→ " + rel_title + "</a>\n"

    structured_data = build_structured_data(title, meta_desc, slug)

    html_parts = [
        '<!DOCTYPE html>',
        '<html lang="en">',
        '<head>',
        '  <meta charset="UTF-8">',
        '  <meta name="viewport" content="width=device-width, initial-scale=1.0">',
        '  <title>' + title + ' | Gullah Geechee Biz</title>',
        '  <meta name="description" content="' + meta_desc + '">',
        '  <meta name="keywords" content="' + keywords + '">',
        '  <meta property="og:title" content="' + title + ' | Gullah Geechee Biz">',
        '  <meta property="og:description" content="' + meta_desc + '">',
        '  <meta property="og:image" content="https://gullahgeecheebiz.com/logo.png">',
        '  <meta property="og:url" content="' + CANONICAL_BASE + slug + '">',
        '  <meta name="twitter:card" content="summary_large_image">',
        '  <link rel="canonical" href="' + CANONICAL_BASE + slug + '">',
        '  <style>',
        '    * { margin: 0; padding: 0; box-sizing: border-box; }',
        '    body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #0a0a14; color: #f0ede5; line-height: 1.8; }',
        '    .container { max-width: 820px; margin: 0 auto; padding: 40px 20px; }',
        '    h1 { font-family: Georgia, "Times New Roman", serif; font-size: 2.1em; color: #d4af37; margin-bottom: 16px; line-height: 1.3; }',
        '    h2 { font-family: Georgia, serif; color: #d4af37; font-size: 1.5em; margin: 34px 0 12px; }',
        '    p { margin-bottom: 18px; font-size: 1.08em; }',
        '    ul, ol { margin: 0 0 20px 26px; font-size: 1.05em; }',
        '    li { margin-bottom: 8px; }',
        '    a { color: #d4af37; }',
        '    .cta { display: block; text-align: center; background: #d4af37; color: #0a0a14; padding: 16px 24px; border-radius: 30px; text-decoration: none; font-weight: bold; font-size: 1.15em; margin: 28px 0; }',
        '    .cta:hover { background: #e8c84a; }',
        '    .box { background: #14141f; border-left: 3px solid #d4af37; padding: 16px 20px; margin: 22px 0; border-radius: 6px; }',
        '    .links { margin-top: 30px; padding-top: 26px; border-top: 1px solid #333; }',
        '    .links a { display: block; color: #d4af37; text-decoration: none; margin-bottom: 10px; }',
        '    .links a:hover { text-decoration: underline; }',
        '    .brand { text-align: center; margin-top: 50px; padding-top: 26px; border-top: 1px solid #333; }',
        '    .brand p { color: #d4af37; font-size: 0.9em; margin-top: 10px; letter-spacing: 2px; }',
        '    .date { color: #666; font-size: 0.85em; margin-bottom: 26px; }',
        '    @media (max-width: 600px) { h1 { font-size: 1.55em; } .container { padding: 20px 15px; } }',
        '  </style>',
        structured_data,
        '</head>',
        '<body>',
        '  <div class="container">',
        '    <h1>' + title + '</h1>',
        '    <div class="date">' + TODAY + ' · Gullah Geechee Biz · ' + page["category"] + '</div>',
        section_html,
        '    <div class="box">',
        '      <strong style="color:#d4af37;">Free resource:</strong> Get our Gullah Geechee Heritage Starter Guide &amp; Genealogist Checklist — and explore the complete history of Sea Island rice, food, and family in our encyclopedia.',
        '    </div>',
        '',
        '    <a href="' + SUBSTACK + '" class="cta">📧 Get the Free Heritage Starter Kit →</a>',
        '',
        '    <div class="links">',
        '      <strong style="color: #d4af37;">Explore the complete Heritage Vault:</strong>',
        '      <a href="' + GUMROAD_TIER2 + '">📚 Ultimate Gullah Geechee Heritage Vault (history + ebooks + audiobooks) →</a>',
        '      <a href="' + GUMROAD_TIER1 + '">📖 Complete Encyclopedia Box Set, Volumes 1-25 →</a>',
        '      <a href="' + GUMROAD_TIER3 + '">🏛 Institutional &amp; Library License →</a>',
        related_html,
        '      <a href="' + SUBSTACK + '">📧 Subscribe to the newsletter →</a>',
        '      <a href="https://gullahgeecheebiz.com">🏠 Visit Gullah Geechee Biz →</a>',
        '    </div>',
        '    <div class="brand">',
        '      <p>GULLAH GEECHEE BIZ</p>',
        '    </div>',
        '  </div>',
        '</body>',
        '</html>'
    ]

    return "\n".join(html_parts)


def update_sitemap():
    """Regenerate sitemap with all viral pages."""
    urls = [
        "https://gullahgeecheebiz.com/",
        "https://gullahgeecheebiz.com/shop.html",
        "https://gullahgeecheebiz.com/shop-binyah.html",
    ]
    for f in sorted(PAGES_DIR.glob("*.html")):
        if f.name == "index.html":
            continue
        urls.append(CANONICAL_BASE + f.stem)
    sitemap = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    for url in urls:
        sitemap += "  <url><loc>" + url + "</loc></url>\n"
    sitemap += "</urlset>"
    SITEMAP_PATH.write_text(sitemap)
    return len(urls)


def main():
    print("=" * 60)
    print("  GGB MARKETING ORCHESTRATOR — SEO CONTENT EXPANSION")
    print("=" * 60)
    print()

    created = []
    for page in NEW_PAGES:
        html = build_html(page)
        path = PAGES_DIR / (page["slug"] + ".html")
        path.write_text(html, encoding="utf-8")
        created.append(page["slug"] + ".html")
        print("  ✓ Created: " + path.name + " (" + str(len(html)) + " chars)")

    count = update_sitemap()
    print("\n  ✓ Sitemap updated: " + str(count) + " URLs total")
    total_pages = len(list(PAGES_DIR.glob("*.html")))
    print("  ✓ Total viral pages now: " + str(total_pages))

    return created


if __name__ == "__main__":
    pages = main()
    print("\nDone. " + str(len(pages)) + " new SEO pages created.")
