#!/usr/bin/env python3
"""
Gullah Geechee Biz — Membership Site Builder
Generates the public membership pages for GitHub Pages deployment.
Internal systems stay on the machine. Only these pages go live.
"""

import argparse
import datetime
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MEMBERSHIP_DIR = ROOT / "membership"
ASSETS_DIR = ROOT / "assets"
MEMBERSHIP_DIR.mkdir(exist_ok=True)
ASSETS_DIR.mkdir(exist_ok=True)

SUPPORT_LANES_START = "<!-- GGB_SUPPORT_LANES:START -->"
SUPPORT_LANES_END = "<!-- GGB_SUPPORT_LANES:END -->"
SUPPORT_LANES_STYLESHEET_RE = re.compile(
    r"\n?\s*<link rel=\"stylesheet\" href=\"/assets/support-lanes\.css\">\n",
    re.MULTILINE,
)
SUPPORT_LANES_BLOCK_RE = re.compile(
    re.escape(SUPPORT_LANES_START) + r".*?" + re.escape(SUPPORT_LANES_END) + r"\n?",
    re.DOTALL,
)
REQUIRED_STRIPE_LINKS = {
    "digital-pass-monthly",
    "digital-pass-yearly",
    "heritage-pass-monthly",
    "heritage-pass-yearly",
    "legacy-pass-monthly",
    "legacy-pass-yearly",
}


def load_stripe_links():
    """Load and validate durable Stripe Payment Links from the repo."""
    links_path = MEMBERSHIP_DIR / "stripe-links.json"
    if not links_path.exists():
        raise SystemExit(
            "Missing membership/stripe-links.json. "
            "Populate the verified buy.stripe.com Payment Links before generating."
        )

    with links_path.open(encoding="utf-8") as f:
        stripe_data = json.load(f)

    links = stripe_data.get("stripe_links", {})
    missing = sorted(REQUIRED_STRIPE_LINKS - set(links))
    if missing:
        raise SystemExit(
            "Missing Stripe Payment Links in membership/stripe-links.json: "
            + ", ".join(missing)
        )
    return links


STRIPE_LINKS = load_stripe_links()

# ─── BRAND ───
NAVY = "#0A1428"
GOLD = "#D4AF37"
CREAM = "#F5F0E6"


def membership_config_payload():
    """Stable membership config without volatile timestamp metadata."""
    return {
        "stripe_links": STRIPE_LINKS,
        "tiers": ["digital-pass", "heritage-pass", "legacy-pass"],
        "prices": {"digital": 9.99, "heritage": 19.99, "legacy": 49.99},
        "annual_prices": {"digital": 99.99, "heritage": 199.99, "legacy": 499.99},
    }


def strip_support_lanes(html):
    """Remove the generated support-lanes block before comparing builders."""
    html = SUPPORT_LANES_STYLESHEET_RE.sub("\n", html, count=1)
    html = SUPPORT_LANES_BLOCK_RE.sub("", html)
    return html.strip()


def config_matches(path, payload):
    """Compare config.json while ignoring generated_at churn."""
    if not path.exists():
        return False
    with path.open(encoding="utf-8") as f:
        existing = json.load(f)
    existing.pop("generated_at", None)
    return existing == payload


def write_text_if_changed(path, content):
    """Write only when the on-disk file differs."""
    if path.exists() and path.read_text(encoding="utf-8") == content:
        return False
    path.write_text(content, encoding="utf-8")
    return True


def build_css():
    """Build the membership CSS."""
    return f"""/* Gullah Geechee Biz — Membership Styles */
:root {{
    --navy: {NAVY};
    --gold: {GOLD};
    --cream: {CREAM};
    --white: #FFFFFF;
    --dark: #1a1a2e;
}}

* {{ margin: 0; padding: 0; box-sizing: border-box; }}

body {{
    font-family: Georgia, 'Times New Roman', serif;
    background: var(--navy);
    color: var(--cream);
    line-height: 1.6;
}}

.container {{
    max-width: 1200px;
    margin: 0 auto;
    padding: 0 20px;
}}

/* ─── HEADER ─── */
header {{
    padding: 40px 0;
    text-align: center;
    border-bottom: 1px solid rgba(212, 175, 55, 0.3);
}}

header h1 {{
    font-size: 2.5rem;
    color: var(--gold);
    letter-spacing: 3px;
    text-transform: uppercase;
}}

header p {{
    font-size: 1.1rem;
    color: var(--cream);
    margin-top: 10px;
    font-style: italic;
}}

/* ─── HERO ─── */
.hero {{
    padding: 80px 0;
    text-align: center;
    background: linear-gradient(180deg, {NAVY} 0%, #0D1B3E 100%);
}}

.hero h2 {{
    font-size: 3rem;
    color: var(--gold);
    margin-bottom: 20px;
}}

.hero p {{
    font-size: 1.2rem;
    max-width: 700px;
    margin: 0 auto 30px;
    color: var(--cream);
}}

.hero .tagline {{
    font-size: 1.4rem;
    color: var(--gold);
    font-style: italic;
    margin-bottom: 40px;
}}

/* ─── TIERS ─── */
.tiers {{
    padding: 60px 0;
}}

.tiers h2 {{
    text-align: center;
    font-size: 2rem;
    color: var(--gold);
    margin-bottom: 50px;
}}

.tier-grid {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
    gap: 30px;
}}

.tier-card {{
    background: linear-gradient(180deg, #0D1B3E 0%, {NAVY} 100%);
    border: 1px solid rgba(212, 175, 55, 0.3);
    border-radius: 12px;
    padding: 40px 30px;
    text-align: center;
    transition: transform 0.3s, border-color 0.3s;
}}

.tier-card:hover {{
    transform: translateY(-5px);
    border-color: var(--gold);
}}

.tier-card.featured {{
    border: 2px solid var(--gold);
    position: relative;
}}

.tier-card.featured::before {{
    content: "BEST VALUE";
    position: absolute;
    top: -12px;
    left: 50%;
    transform: translateX(-50%);
    background: var(--gold);
    color: var(--navy);
    padding: 4px 20px;
    border-radius: 20px;
    font-size: 0.8rem;
    font-weight: bold;
    letter-spacing: 2px;
}}

.tier-card h3 {{
    font-size: 1.5rem;
    color: var(--gold);
    margin-bottom: 10px;
}}

.tier-card .price {{
    font-size: 2.5rem;
    color: var(--white);
    margin: 20px 0;
}}

.tier-card .price span {{
    font-size: 1rem;
    color: var(--cream);
    opacity: 0.7;
}}

.tier-card .annual {{
    font-size: 0.9rem;
    color: var(--gold);
    margin-bottom: 20px;
}}

.trust-line {{
    text-align: center;
    margin-top: 28px;
    font-size: 0.9rem;
    color: var(--cream);
    opacity: 0.72;
}}

.tier-card ul {{
    list-style: none;
    text-align: left;
    margin: 20px 0;
}}

.tier-card ul li {{
    padding: 8px 0;
    color: var(--cream);
    font-size: 0.95rem;
}}

.tier-card ul li::before {{
    content: "★ ";
    color: var(--gold);
}}

.btn {{
    display: inline-block;
    padding: 14px 40px;
    background: var(--gold);
    color: var(--navy);
    text-decoration: none;
    border-radius: 30px;
    font-weight: bold;
    font-size: 1.1rem;
    font-family: Georgia, serif;
    transition: opacity 0.3s;
    margin: 5px;
}}

.btn:hover {{
    opacity: 0.9;
}}

.btn-outline {{
    background: transparent;
    border: 2px solid var(--gold);
    color: var(--gold);
}}

.btn-outline:hover {{
    background: var(--gold);
    color: var(--navy);
}}

/* ─── WHAT'S INSIDE ─── */
.inside {{
    padding: 60px 0;
    background: #0D1B3E;
}}

.inside h2 {{
    text-align: center;
    font-size: 2rem;
    color: var(--gold);
    margin-bottom: 50px;
}}

.inside-grid {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
    gap: 30px;
}}

.inside-item {{
    text-align: center;
    padding: 30px 20px;
}}

.inside-item .icon {{
    font-size: 3rem;
    margin-bottom: 15px;
}}

.inside-item h3 {{
    color: var(--gold);
    margin-bottom: 10px;
}}

.inside-item p {{
    color: var(--cream);
    font-size: 0.9rem;
    opacity: 0.8;
}}

/* ─── FAQ ─── */
.faq {{
    padding: 60px 0;
}}

.faq h2 {{
    text-align: center;
    font-size: 2rem;
    color: var(--gold);
    margin-bottom: 40px;
}}

.faq-item {{
    margin-bottom: 20px;
    border-bottom: 1px solid rgba(212, 175, 55, 0.2);
    padding-bottom: 20px;
}}

.faq-item h3 {{
    color: var(--gold);
    font-size: 1.1rem;
    margin-bottom: 10px;
    cursor: pointer;
}}

.faq-item p {{
    color: var(--cream);
    opacity: 0.8;
}}

/* ─── FOOTER ─── */
footer {{
    padding: 40px 0;
    text-align: center;
    border-top: 1px solid rgba(212, 175, 55, 0.3);
}}

footer p {{
    color: var(--cream);
    opacity: 0.6;
    font-size: 0.9rem;
}}

footer .gold {{
    color: var(--gold);
}}

/* ─── RESPONSIVE ─── */
@media (max-width: 768px) {{
    .hero h2 {{ font-size: 2rem; }}
    .tier-grid {{ grid-template-columns: 1fr; }}
    header h1 {{ font-size: 1.8rem; }}
}}
"""


def build_membership_page():
    """Build the main membership landing page."""
    tiers = [
        {
            "name": "Digital Pass",
            "price": "$9.99",
            "period": "/month",
            "annual": "$99.99/year ($8.33/mo)",
            "annual_link": STRIPE_LINKS["digital-pass-yearly"],
            "monthly_link": STRIPE_LINKS["digital-pass-monthly"],
            "features": [
                "Full pin archive — 100 new pins daily",
                "Digital guides for every Gullah Geechee town",
                "Complete recipe archive",
                "Interactive corridor map",
                "Daily digest email",
                "New ebook every month",
            ],
            "featured": False,
        },
        {
            "name": "Heritage Pass",
            "price": "$19.99",
            "period": "/month",
            "annual": "$199.99/year ($16.67/mo)",
            "annual_link": STRIPE_LINKS["heritage-pass-yearly"],
            "monthly_link": STRIPE_LINKS["heritage-pass-monthly"],
            "features": [
                "Everything in Digital Pass",
                "New ebook every week",
                "Audio atlas — cultural audio pieces",
                "Early access to encyclopedia volumes",
                "Behind-the-scenes content",
                "Ad-free experience",
            ],
            "featured": True,
        },
        {
            "name": "Legacy Pass",
            "price": "$49.99",
            "period": "/month",
            "annual": "$499.99/year ($41.67/mo)",
            "annual_link": STRIPE_LINKS["legacy-pass-yearly"],
            "monthly_link": STRIPE_LINKS["legacy-pass-monthly"],
            "features": [
                "Everything in Heritage Pass",
                "Name in encyclopedia acknowledgments",
                "Quarterly live Q&A with the publisher",
                "Exclusive documentary access",
                "First access to all new content",
                "Direct line to the team",
            ],
            "featured": False,
        },
    ]

    inside_items = [
        ("📌", "Daily Pins", "100 new Pinterest pins every day. Towns, food, traditions, figures, and historic sites from across the Gullah Geechee Corridor."),
        ("📚", "Ebook Library", "New ebooks added regularly. Gullah Geechee history, cuisine, language, art, and culture. Authored by Darryl Elliott Brown."),
        ("🗺️", "Corridor Map", "Interactive map of every significant Gullah Geechee site from North Carolina to Florida. Photos, history, and links."),
        ("🍽️", "Recipe Archive", "The definitive collection of Gullah Geechee recipes. Red rice, gumbo, benne wafers, shrimp and grits, and more."),
        ("🎧", "Audio Atlas", "Short cultural audio pieces. Stories, language, music, and traditions. The sound of the Sea Islands."),
        ("📖", "Digital Guides", "Free downloadable guides for every town in the Gullah Geechee Corridor. Your pocket guide to the culture."),
    ]

    faqs = [
        ("What is Gullah Geechee Biz?", "Gullah Geechee Biz is a cultural preservation and publishing platform dedicated to documenting, celebrating, and sharing Gullah Geechee history, traditions, language, and cuisine with the world."),
        ("How does the membership work?", "Choose a tier, subscribe via Stripe, and get instant access to the member area. Your membership supports the ongoing work of cultural preservation and content creation."),
        ("Can I switch tiers?", "Yes. Upgrade or downgrade at any time through the Stripe customer portal. Changes take effect immediately."),
        ("Is there a free trial?", "Yes. All tiers include a 7-day free trial. Cancel anytime before the trial ends and you won't be charged."),
        ("What content do I get access to?", "Every tier includes access to the full pin archive, digital guides, recipe archive, and corridor map. Higher tiers add ebooks, audio atlas, and exclusive content."),
        ("How often is new content added?", "Pins are added daily. Ebooks are added weekly. Audio pieces are added daily. Guides and recipes are added weekly. The corridor map is updated monthly."),
        ("Can I cancel anytime?", "Yes. Cancel through the Stripe customer portal. Your access continues until the end of your billing period."),
        ("Where does the money go?", "Membership revenue directly supports Gullah Geechee cultural preservation, content creation, and the ongoing work of documenting and sharing this vital American culture."),
    ]

    tier_cards = ""
    for tier in tiers:
        featured_class = " featured" if tier["featured"] else ""
        features = "\n".join(f'                <li>{f}</li>' for f in tier["features"])
        
        tier_cards += f"""
            <div class="tier-card{featured_class}">
                <h3>{tier['name']}</h3>
                <div class="price">{tier['price']}<span>{tier['period']}</span></div>
                <div class="annual">{tier['annual']}</div>
                <ul>
                    {features}
                </ul>
                <a href="{tier['monthly_link']}" class="btn" aria-label="Subscribe to {tier['name']} monthly, {tier['price']} per month">Subscribe Monthly</a>
                <a href="{tier['annual_link']}" class="btn btn-outline" aria-label="Subscribe to {tier['name']} annually, {tier['annual']}">Subscribe Annual</a>
            </div>"""

    inside_items_html = "\n".join(
        f"""
            <div class="inside-item">
                <div class="icon">{icon}</div>
                <h3>{title}</h3>
                <p>{desc}</p>
            </div>""" for icon, title, desc in inside_items
    )

    faq_html = "\n".join(
        f"""
            <div class="faq-item">
                <h3>{q}</h3>
                <p>{a}</p>
            </div>""" for q, a in faqs
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Membership — Gullah Geechee Biz</title>
    <meta name="description" content="Join the Gullah Geechee Biz membership. Access daily pins, ebooks, digital guides, recipes, audio atlas, and more. Support cultural preservation.">
    <link rel="stylesheet" href="/assets/membership.css">
</head>
<body>
    <header>
        <div class="container">
            <h1>Gullah Geechee Biz</h1>
            <p>Preserving a Culture. Telling a Story.</p>
        </div>
    </header>

    <section class="hero">
        <div class="container">
            <h2>Join the Circle</h2>
            <p class="tagline">The culture is the inspiration. The quality is the respect we show it.</p>
            <p>Access the largest and most comprehensive collection of Gullah Geechee cultural content ever assembled. Daily pins. Weekly ebooks. Digital guides. Recipes. Audio. Maps. All in one place.</p>
        </div>
    </section>

    <section class="tiers">
        <div class="container">
            <h2>Choose Your Path</h2>
            <div class="tier-grid">
                {tier_cards}
            </div>
            <p class="trust-line">Secure payment via Stripe. Cancel anytime from the Stripe customer portal.</p>
        </div>
    </section>

    <section class="inside">
        <div class="container">
            <h2>What's Inside</h2>
            <div class="inside-grid">
                {inside_items_html}
            </div>
        </div>
    </section>

    <section class="faq">
        <div class="container">
            <h2>Frequently Asked Questions</h2>
            {faq_html}
        </div>
    </section>

    <footer>
        <div class="container">
            <p>© {datetime.date.today().year} <span class="gold">Gullah Geechee Biz</span>. All rights reserved.</p>
            <p>Preserving a Culture. Telling a Story.</p>
        </div>
    </footer>
</body>
</html>"""


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--check",
        action="store_true",
        help="Exit non-zero if the committed membership assets are out of date.",
    )
    args = parser.parse_args()

    print("=" * 60)
    print("  GULLAH GEECHEE BIZ — MEMBERSHIP SITE BUILDER")
    print("=" * 60)
    print()

    css_path = ASSETS_DIR / "membership.css"
    html_path = MEMBERSHIP_DIR / "index.html"
    config_path = MEMBERSHIP_DIR / "config.json"

    css = build_css()
    html = build_membership_page()
    config = membership_config_payload()

    stale = []

    css_changed = css_path.exists() is False or css_path.read_text(encoding="utf-8") != css
    if css_changed:
        stale.append("assets/membership.css")
        if not args.check:
            write_text_if_changed(css_path, css)
    print(f"  {'⚠️' if css_changed and args.check else '✅'} CSS: {css_path}")

    committed_html = html_path.read_text(encoding="utf-8") if html_path.exists() else ""
    html_changed = not html_path.exists() or strip_support_lanes(committed_html) != html.strip()
    if html_changed:
        stale.append("membership/index.html")
        if not args.check:
            write_text_if_changed(html_path, html)
            subprocess.run(
                [sys.executable, str(ROOT / "scripts" / "build-support-lanes.py")],
                check=True,
                cwd=ROOT,
            )
    print(f"  {'⚠️' if html_changed and args.check else '✅'} Page: {html_path}")

    config_changed = not config_matches(config_path, config)
    if config_changed:
        stale.append("membership/config.json")
        if not args.check:
            payload = dict(config)
            payload["generated_at"] = datetime.datetime.now().isoformat()
            config_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"  {'⚠️' if config_changed and args.check else '✅'} Config: {config_path}")

    print()
    print("  pages ready at:")
    print(f"     {MEMBERSHIP_DIR}/")
    print(f"     {css_path}")

    if args.check:
        if stale:
            print()
            print("  Out of date:")
            for rel in stale:
                print(f"     {rel}")
            print()
            print("  Run: python3 scripts/build-membership.py")
            print("=" * 60)
            return 1
        print()
        print("  Membership assets are in sync.")
        print("=" * 60)
        return 0

    print()
    print("  Membership pages regenerated from membership/stripe-links.json")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
