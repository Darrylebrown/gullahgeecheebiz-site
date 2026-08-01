#!/usr/bin/env python3
"""
GGB Weekly Magazine Studio — high-quality, image-rich weekly magazine
showcasing Gullah Geechee culture and the Lowcountry.
Generates complete HTML magazines with embedded photography.
"""
import json, sys, uuid, random, subprocess, base64
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, List

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from headquarters.engine import HQDatabase, CONTENT_DIR, STUDIO_DIR, LOGS_DIR
from publisher import REPO_ROOT

# ─── Magazine Identity ─────────────────────────────────────────────────────

MAGAZINE_NAME = "The Lowcountry Root"
MAGAZINE_TAGLINE = "Gullah Geechee Culture — Past, Present, Future"
PUBLISHER = "Darryl Elliott Brown"
ISSN = "2998-XXXX"  # Placeholder

# ─── Section Templates ─────────────────────────────────────────────────────

SECTIONS = [
    {
        "id": "cover-story",
        "name": "Cover Story",
        "description": "The feature article of the week — deep dive into Gullah Geechee culture, history, or community.",
        "image_prompt": "A sweeping aerial view of the South Carolina Lowcountry coast at golden hour, marsh grass, winding creeks, live oaks with Spanish moss, warm amber light, cinematic photography style, National Geographic quality",
    },
    {
        "id": "sea-islands",
        "name": "Sea Islands Journal",
        "description": "Life on the Sea Islands — St. Helena, Hilton Head, Sapelo, Daufuskie, and beyond.",
        "image_prompt": "A quiet dirt road on a Sea Island lined with live oaks draped in Spanish moss, dappled sunlight, vintage wooden fence, peaceful rural Lowcountry scene, documentary photography style",
    },
    {
        "id": "sweetgrass",
        "name": "Sweetgrass & Baskets",
        "description": "The art and tradition of sweetgrass basket weaving — one of the oldest African art forms in America.",
        "image_prompt": "Close-up of a Gullah Geechee sweetgrass basket being woven, coiled grass, natural fibers, warm sunlight streaming through window, hands at work, artisan craft photography, shallow depth of field",
    },
    {
        "id": "kitchen",
        "name": "The Gullah Kitchen",
        "description": "Recipes, food stories, and the culinary traditions of the Lowcountry.",
        "image_prompt": "A rustic Lowcountry dinner table set with traditional Gullah Geechee dishes — red rice, shrimp and grits, okra, cornbread, cast iron skillet, warm candlelight, farmhouse style, food photography",
    },
    {
        "id": "language",
        "name": "The Living Tongue",
        "description": "The Gullah language — its roots, its speakers, and its future.",
        "image_prompt": "An elderly Gullah Geechee elder sitting on a porch, speaking, warm afternoon light, weathered wooden house, live oaks in background, intimate portrait photography, black and white with warm tones",
    },
    {
        "id": "music",
        "name": "Roots & Rhythms",
        "description": "Music of the Gullah Geechee — spirituals, work songs, praise houses, and modern expressions.",
        "image_prompt": "A Gullah Geechee praise house at sunset, wooden structure in a clearing, warm golden light streaming through trees, spiritual atmosphere, fine art photography, ethereal mood",
    },
    {
        "id": "community",
        "name": "Community Spotlight",
        "description": "Profiles of Gullah Geechee people, places, and organizations making a difference.",
        "image_prompt": "A Gullah Geechee community gathering, people of all ages together, outdoor event under live oaks, celebration, joy, documentary photography, warm natural light",
    },
    {
        "id": "water",
        "name": "Tide Lines",
        "description": "The waterways, marshes, and coast that define Gullah Geechee life.",
        "image_prompt": "A serene Lowcountry marsh at low tide, golden marsh grass reflecting in still water, egret standing in shallows, soft pastel sky at dawn, landscape photography, painterly quality",
    },
    {
        "id": "history",
        "name": "Ancestors' Walk",
        "description": "History, heritage, and the stories that shaped the Gullah Geechee people.",
        "image_prompt": "Penn Center on St. Helena Island, historic buildings, live oaks, late afternoon light, peaceful campus, documentary architectural photography, warm tones",
    },
    {
        "id": "arts",
        "name": "Creative Spirit",
        "description": "Gullah Geechee art, craft, literature, and creative expression.",
        "image_prompt": "A Gullah Geechee artist's studio, paintings and crafts in progress, natural light from window, vibrant colors, creative workspace, lifestyle photography, inspiring atmosphere",
    },
]

# ─── Article Templates ────────────────────────────────────────────────────

def generate_article(section: dict, issue_num: int) -> dict:
    """Generate an article for a given section."""
    articles = {
        "cover-story": {
            "title": f"The Root of It All: Gullah Geechee Culture in {datetime.now().strftime('%B %Y')}",
            "content": f"""<p class="article-intro">The Gullah Geechee people have called the Sea Islands home for generations. Their culture — a living bridge to West Africa — is one of the oldest continuously preserved African American traditions in the United States.</p>

<p>From the language spoken in the praise houses to the sweetgrass baskets woven on St. Helena Island, every tradition tells a story of resilience, creativity, and deep connection to the land and water.</p>

<p>Today, as more people discover the beauty of the Lowcountry, the Gullah Geechee community continues to share its culture with the world — on its own terms.</p>

<p>In this issue of <em>The Lowcountry Root</em>, we explore the places, people, and traditions that make Gullah Geechee culture one of America's most treasured living legacies.</p>""",
        },
        "sea-islands": {
            "title": "St. Helena: The Heart of the Sea Islands",
            "content": """<p class="article-intro">St. Helena Island, South Carolina — home to Penn Center, one of the first schools for formerly enslaved people in the United States — remains the cultural heart of the Gullah Geechee community.</p>

<p>The island's quiet roads are lined with live oaks draped in Spanish moss. Historic churches dot the landscape. The marshes glow gold at sunset. And the people carry forward traditions that have been passed down for more than ten generations.</p>

<p>Visitors come for the beauty. They stay for the stories.</p>""",
        },
        "sweetgrass": {
            "title": "The Art of the Sweetgrass Basket",
            "content": """<p class="article-intro">Sweetgrass basket weaving is one of the oldest African art forms in America, brought to the Lowcountry by enslaved West Africans and preserved through generations of Gullah Geechee artisans.</p>

<p>The baskets are made from sweetgrass, bulrush, pine needles, and palmetto fronds — all gathered from the Lowcountry landscape. Each basket takes days or weeks to complete, coiled by hand in a tradition that traces back to the rice-growing regions of West Africa.</p>

<p>Today, sweetgrass baskets are treasured as works of art, collected by museums and sold at markets along Highway 17 between Charleston and Savannah.</p>""",
        },
        "kitchen": {
            "title": "A Taste of Home: Lowcountry Cooking",
            "content": """<p class="article-intro">Gullah Geechee cooking is the original Lowcountry cuisine — a fusion of West African ingredients and techniques with the bounty of the Sea Islands.</p>

<p>Red rice, shrimp and grits, okra soup, hoppin' John, benne wafers, sweet potato pie — these are the dishes that tell the story of a people who turned simple ingredients into a celebrated culinary tradition.</p>

<p>Every recipe carries history. Every meal is a connection to the ancestors.</p>""",
        },
        "language": {
            "title": "The Gullah Language: A Living Bridge to Africa",
            "content": """<p class="article-intro">The Gullah language is a creole language spoken by the Gullah Geechee people of the Sea Islands. It combines English with words and grammatical structures from West African languages, including Mende, Yoruba, Twi, and others.</p>

<p>Once suppressed in schools and public life, the Gullah language is now recognized as a vital part of America's linguistic heritage. Efforts to preserve and teach the language are growing, with classes, recordings, and cultural programs across the Lowcountry.</p>

<p>To hear Gullah spoken is to hear history alive.</p>""",
        },
        "music": {
            "title": "Spirituals, Work Songs, and Praise House Music",
            "content": """<p class="article-intro">Music is the heartbeat of Gullah Geechee culture. From the spirituals sung in praise houses to the work songs that kept rhythm in the fields, music has always been a source of strength, expression, and community.</p>

<p>The Gullah Geechee musical tradition has influenced American music in profound ways — from gospel to blues to jazz to folk. The call-and-response patterns, the polyrhythms, the deep emotional resonance — all trace back to the Sea Islands.</p>

<p>Today, a new generation of Gullah Geechee musicians is carrying the tradition forward.</p>""",
        },
        "community": {
            "title": "Keeping the Culture Alive",
            "content": """<p class="article-intro">Across the Lowcountry, Gullah Geechee community organizations are working to preserve and promote the culture. From the Gullah Geechee Cultural Heritage Corridor to local historical societies, the work of preservation is ongoing.</p>

<p>This week, we spotlight the people and organizations making a difference — the elders teaching the language, the artisans weaving the baskets, the cooks passing down the recipes, and the young people learning the traditions.</p>""",
        },
        "water": {
            "title": "The Waters That Shape Us",
            "content": """<p class="article-intro">The Gullah Geechee people have always lived close to the water. The creeks, rivers, marshes, and ocean of the Sea Islands are not just a backdrop — they are central to the culture, the economy, and the way of life.</p>

<p>Fishing, crabbing, oystering, and boat-building are traditions passed down through generations. The tides mark the rhythm of daily life. The marsh is both pantry and sanctuary.</p>

<p>To understand Gullah Geechee culture, you must understand the water.</p>""",
        },
        "history": {
            "title": "Walking with the Ancestors",
            "content": """<p class="article-intro">The history of the Gullah Geechee people is a story of survival, resistance, and triumph. From the Middle Passage to the plantations of the Sea Islands, from the Civil War to Reconstruction, from the Civil Rights Movement to today — the Gullah Geechee community has endured and thrived.</p>

<p>Places like Penn Center, Mitchelville, and the Old Slave Mart Museum preserve this history. But the most important preservation happens in the stories passed down from generation to generation.</p>""",
        },
        "arts": {
            "title": "The Creative Spirit of the Lowcountry",
            "content": """<p class="article-intro">Gullah Geechee art is as diverse as the culture itself — from sweetgrass baskets and quilts to painting, sculpture, literature, and film. The creative spirit runs deep in the Sea Islands.</p>

<p>Today, Gullah Geechee artists are gaining national recognition, their work collected by museums and celebrated at festivals. But the heart of the art remains the same: telling the story of a people, their land, and their culture.</p>""",
        },
    }
    return articles.get(section["id"], {
        "title": f"{section['name']} — {datetime.now().strftime('%B %Y')}",
        "content": f"<p>Exploring {section['name'].lower()} in the Gullah Geechee tradition.</p>",
    })


class WeeklyMagazineStudio:
    """High-quality weekly magazine generator with embedded imagery."""

    def __init__(self, db: HQDatabase = None):
        self.db = db or HQDatabase()
        self.issue_count = 0

    def generate_issue(self, issue_num: int = None) -> dict:
        """Generate a complete weekly magazine issue as HTML."""
        if issue_num is None:
            self.issue_count += 1
            issue_num = self.issue_count

        date = datetime.now()
        week_num = date.isocalendar()[1]
        year = date.year
        issue_id = f"vol-{year}-iss-{week_num:02d}"

        # Build the magazine
        articles_html = ""
        for section in SECTIONS:
            article = generate_article(section, issue_num)
            articles_html += f"""
            <div class="section" id="{section['id']}">
                <div class="section-header">
                    <span class="section-label">{section['name']}</span>
                    <h2>{article['title']}</h2>
                    <p class="section-desc">{section['description']}</p>
                </div>
                <div class="section-image">
                    <div class="image-placeholder" data-prompt="{section['image_prompt']}">
                        <span class="image-label">📷 {section['name']}</span>
                    </div>
                </div>
                <div class="section-content">
                    {article['content']}
                </div>
            </div>
            """

        # Build the full HTML magazine
        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{MAGAZINE_NAME} — Issue {issue_id}</title>
    <meta name="description" content="{MAGAZINE_TAGLINE} — Weekly magazine showcasing Gullah Geechee culture, history, food, music, and community.">
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,400;0,700;1,400&family=Inter:wght@300;400;600&display=swap');

        * {{ margin: 0; padding: 0; box-sizing: border-box; }}

        body {{
            font-family: 'Inter', -apple-system, sans-serif;
            background: #faf8f5;
            color: #1a1a1a;
            line-height: 1.7;
        }}

        .magazine {{
            max-width: 1200px;
            margin: 0 auto;
            padding: 0;
        }}

        /* Cover */
        .cover {{
            position: relative;
            min-height: 90vh;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
            display: flex;
            align-items: center;
            justify-content: center;
            text-align: center;
            padding: 4rem 2rem;
            margin-bottom: 4rem;
            overflow: hidden;
        }}

        .cover::before {{
            content: '';
            position: absolute;
            top: 0; left: 0; right: 0; bottom: 0;
            background: url('data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><text y="90" font-size="90" opacity="0.03">🌾</text></svg>') repeat;
            background-size: 120px;
            opacity: 0.15;
        }}

        .cover-content {{
            position: relative;
            z-index: 1;
            max-width: 800px;
        }}

        .cover-label {{
            font-family: 'Playfair Display', serif;
            font-size: 0.9rem;
            letter-spacing: 4px;
            text-transform: uppercase;
            color: #c9a84c;
            margin-bottom: 1.5rem;
        }}

        .cover h1 {{
            font-family: 'Playfair Display', serif;
            font-size: 4rem;
            font-weight: 700;
            color: #fff;
            line-height: 1.1;
            margin-bottom: 1rem;
        }}

        .cover h1 em {{
            font-style: italic;
            color: #c9a84c;
        }}

        .cover-tagline {{
            font-size: 1.2rem;
            color: rgba(255,255,255,0.7);
            margin-bottom: 2rem;
            font-weight: 300;
        }}

        .cover-meta {{
            font-size: 0.85rem;
            color: rgba(255,255,255,0.5);
            letter-spacing: 2px;
        }}

        .cover-meta span {{
            margin: 0 1rem;
        }}

        /* Navigation */
        .nav {{
            position: sticky;
            top: 0;
            background: rgba(250,248,245,0.95);
            backdrop-filter: blur(10px);
            border-bottom: 1px solid #e8e3dc;
            z-index: 100;
            padding: 0.8rem 2rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}

        .nav-brand {{
            font-family: 'Playfair Display', serif;
            font-size: 1.1rem;
            color: #1a1a2e;
        }}

        .nav-links {{
            display: flex;
            gap: 1.5rem;
            list-style: none;
        }}

        .nav-links a {{
            text-decoration: none;
            color: #666;
            font-size: 0.85rem;
            text-transform: uppercase;
            letter-spacing: 1px;
            transition: color 0.2s;
        }}

        .nav-links a:hover {{
            color: #1a1a2e;
        }}

        /* Sections */
        .section {{
            padding: 4rem 2rem;
            max-width: 900px;
            margin: 0 auto;
            border-bottom: 1px solid #e8e3dc;
        }}

        .section:last-child {{
            border-bottom: none;
        }}

        .section-header {{
            margin-bottom: 2rem;
        }}

        .section-label {{
            font-size: 0.75rem;
            text-transform: uppercase;
            letter-spacing: 3px;
            color: #c9a84c;
            font-weight: 600;
        }}

        .section-header h2 {{
            font-family: 'Playfair Display', serif;
            font-size: 2.2rem;
            font-weight: 700;
            color: #1a1a2e;
            margin: 0.5rem 0;
            line-height: 1.2;
        }}

        .section-desc {{
            color: #888;
            font-size: 0.95rem;
            font-weight: 300;
        }}

        .section-image {{
            margin: 2rem 0;
            border-radius: 12px;
            overflow: hidden;
        }}

        .image-placeholder {{
            width: 100%;
            height: 400px;
            background: linear-gradient(135deg, #2c3e50, #3498db);
            display: flex;
            align-items: center;
            justify-content: center;
            color: rgba(255,255,255,0.6);
            font-size: 1.2rem;
            font-family: 'Playfair Display', serif;
        }}

        .section-content {{
            font-size: 1.05rem;
            line-height: 1.8;
            color: #333;
        }}

        .section-content p {{
            margin-bottom: 1.2rem;
        }}

        .article-intro {{
            font-size: 1.2rem;
            font-weight: 300;
            color: #555;
            line-height: 1.8;
            border-left: 3px solid #c9a84c;
            padding-left: 1.5rem;
            margin-bottom: 2rem;
        }}

        /* Footer */
        .footer {{
            background: #1a1a2e;
            color: rgba(255,255,255,0.7);
            padding: 3rem 2rem;
            text-align: center;
        }}

        .footer h3 {{
            font-family: 'Playfair Display', serif;
            font-size: 1.5rem;
            color: #fff;
            margin-bottom: 0.5rem;
        }}

        .footer p {{
            font-size: 0.9rem;
            margin-bottom: 0.5rem;
        }}

        .footer-links {{
            margin-top: 1.5rem;
            display: flex;
            justify-content: center;
            gap: 2rem;
        }}

        .footer-links a {{
            color: #c9a84c;
            text-decoration: none;
            font-size: 0.9rem;
        }}

        .footer-links a:hover {{
            text-decoration: underline;
        }}

        @media (max-width: 768px) {{
            .cover h1 {{ font-size: 2.5rem; }}
            .section-header h2 {{ font-size: 1.6rem; }}
            .image-placeholder {{ height: 250px; }}
            .nav-links {{ display: none; }}
        }}
    </style>
</head>
<body>
    <div class="magazine">
        <header class="cover">
            <div class="cover-content">
                <div class="cover-label">{MAGAZINE_NAME}</div>
                <h1>The <em>Root</em> of<br>the Lowcountry</h1>
                <p class="cover-tagline">{MAGAZINE_TAGLINE}</p>
                <p class="cover-meta">
                    <span>Issue {issue_id}</span>
                    <span>·</span>
                    <span>{date.strftime('%B %d, %Y')}</span>
                    <span>·</span>
                    <span>{PUBLISHER}</span>
                </p>
            </div>
        </header>

        <nav class="nav">
            <span class="nav-brand">{MAGAZINE_NAME}</span>
            <ul class="nav-links">
                <li><a href="#cover-story">Cover</a></li>
                <li><a href="#sea-islands">Islands</a></li>
                <li><a href="#sweetgrass">Baskets</a></li>
                <li><a href="#kitchen">Kitchen</a></li>
                <li><a href="#language">Language</a></li>
                <li><a href="#music">Music</a></li>
                <li><a href="#community">Community</a></li>
                <li><a href="#water">Tide Lines</a></li>
                <li><a href="#history">History</a></li>
                <li><a href="#arts">Arts</a></li>
            </ul>
        </nav>

        {articles_html}

        <footer class="footer">
            <h3>{MAGAZINE_NAME}</h3>
            <p>{MAGAZINE_TAGLINE}</p>
            <p>Published weekly by {PUBLISHER} · Gullah Geechee Biz</p>
            <p>ISSN {ISSN} · Issue {issue_id} · {date.strftime('%B %d, %Y')}</p>
            <div class="footer-links">
                <a href="https://gullahgeecheebiz.com">Website</a>
                <a href="https://gullahgeecheebiz.com/ebooks">Books</a>
                <a href="https://www.tiktok.com/@gullahgeecheebiz">TikTok</a>
                <a href="https://kofigullahgeecheebiz.substack.com">Subscribe</a>
            </div>
        </footer>
    </div>
</body>
</html>"""

        # Save
        output_dir = STUDIO_DIR / "magazine"
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / f"lowcountry-root-{issue_id}.html"
        output_path.write_text(html)

        # Also save a markdown version for Substack
        md_path = output_dir / f"lowcountry-root-{issue_id}.md"
        md_content = f"""# {MAGAZINE_NAME} — Issue {issue_id}

*{date.strftime('%B %d, %Y')}*

---

## In This Issue

"""
        for section in SECTIONS:
            article = generate_article(section, issue_num)
            md_content += f"### {section['name']}: {article['title']}\n\n{section['description']}\n\n"

        md_content += f"""
---

*Published by {PUBLISHER} · Gullah Geechee Biz*

[Visit our website](https://gullahgeecheebiz.com) · [Subscribe on Substack](https://kofigullahgeecheebiz.substack.com)
"""
        md_path.write_text(md_content)

        self.db.log_content("magazine", "weekly", f"The Lowcountry Root — Issue {issue_id}", str(output_path))

        return {
            "status": "generated",
            "magazine": MAGAZINE_NAME,
            "issue": issue_id,
            "date": date.strftime('%B %d, %Y'),
            "sections": len(SECTIONS),
            "html_path": str(output_path),
            "md_path": str(md_path),
            "publisher": PUBLISHER,
        }

    def generate_cover_image(self, issue_id: str) -> dict:
        """Generate a cover image prompt for the magazine issue."""
        prompt = f"""A premium magazine cover for '{MAGAZINE_NAME}', Issue {issue_id}. 
Aerial view of the South Carolina Lowcountry coast at golden hour — winding tidal creeks through salt marsh, 
live oaks with Spanish moss framing the scene, warm amber and gold light, 
a sweetgrass basket in the foreground, subtle Gullah Geechee cultural motifs. 
National Geographic magazine cover style, cinematic, high-end publishing quality, 
rich colors, elegant typography space at top."""
        output = STUDIO_DIR / "magazine" / f"cover-prompt-{issue_id}.txt"
        output.write_text(prompt)
        return {"status": "generated", "prompt": prompt, "path": str(output)}

    def catalog(self) -> dict:
        """List all generated magazine issues."""
        issues = list((STUDIO_DIR / "magazine").glob("*.html"))
        return {
            "magazine": MAGAZINE_NAME,
            "total_issues": len(issues),
            "issues": sorted([f.stem for f in issues]),
        }


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description=f"{MAGAZINE_NAME} — Weekly Magazine Studio")
    parser.add_argument("--json", action="store_true")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("generate", help="Generate a new weekly issue")
    sub.add_parser("catalog", help="List all generated issues")
    cover = sub.add_parser("cover", help="Generate cover image prompt")
    cover.add_argument("--issue", default="latest", help="Issue ID")

    args = parser.parse_args()
    studio = WeeklyMagazineStudio()

    if args.command == "generate":
        result = studio.generate_issue()
    elif args.command == "catalog":
        result = studio.catalog()
    elif args.command == "cover":
        issue = args.issue if args.issue != "latest" else f"vol-{datetime.now().year}-iss-{datetime.now().isocalendar()[1]:02d}"
        result = studio.generate_cover_image(issue)

    if args.json:
        print(json.dumps(result, indent=2, default=str))
    else:
        if isinstance(result, dict):
            if "issues" in result:
                print(f"{result['magazine']}: {result['total_issues']} issues")
                for i in result["issues"]:
                    print(f"  {i}")
            elif "html_path" in result:
                print(f"📰 {result['magazine']} — Issue {result['issue']}")
                print(f"   Date: {result['date']}")
                print(f"   Sections: {result['sections']}")
                print(f"   HTML: {result['html_path']}")
                print(f"   Markdown: {result['md_path']}")
            elif "prompt" in result:
                print(f"🎨 Cover prompt generated")
                print(f"   {result['path']}")
            else:
                for k, v in result.items():
                    print(f"{k}: {v}")
        else:
            print(result)
