#!/usr/bin/env python3
"""
GGB Substack Growth Bot — autonomous newsletter generation, content repurposing,
cross-posting, and subscriber growth automation.
Generates content only. Never posts without owner approval.
"""
import json, sys, uuid, random, re
from pathlib import Path
from datetime import datetime, timezone, timedelta

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from headquarters.engine import HQDatabase, CONTENT_DIR, STUDIO_DIR, LOGS_DIR

# ─── Substack Config ────────────────────────────────────────────────────────

SUBSTACK_URL = "https://kofigullahgeecheebiz.substack.com"
SUBSTACK_API = f"{SUBSTACK_URL}/api/v1/subscribe"

NEWSLETTER_FREQUENCY = "weekly"  # weekly, biweekly, monthly
NEWSLETTER_DAY = "wednesday"     # day of week to publish

# ─── Content Templates ─────────────────────────────────────────────────────

TEMPLATES = {
    "welcome": """# Welcome to The Root — Gullah Geechee Biz

*{date}*

---

Welcome to our community. Every week, we share stories, recipes, history, and culture from the Gullah Geechee corridor — the Sea Islands of South Carolina and Georgia.

## What You'll Get

- **Stories** from 159 pages of Gullah Geechee culture
- **Recipes** from our cookbook collection
- **Book excerpts** from our publishing catalog
- **Music** from the GGB Radio station
- **Behind the scenes** from the publishing pipeline

## Start Here

- [Visit the website](https://gullahgeecheebiz.com)
- [Browse our ebooks](https://gullahgeecheebiz.com/ebooks)
- [Follow on TikTok](https://www.tiktok.com/@gullahgeecheebiz)

*Darryl Elliott Brown*
*Publisher, Gullah Geechee Biz*
""",

    "weekly": """# The Root — Weekly Edition

*{date}*

---

## This Week's Feature

{feature_article}

## From the Kitchen

{recipe_pick}

## Book Spotlight

{book_excerpt}

## Community Corner

{community_news}

---

*[Share this post]({share_url}) · [Subscribe]({subscribe_url}) · [Visit the website](https://gullahgeecheebiz.com)*
""",

    "book_launch": """# New Release: {book_title}

*{date}*

---

We're excited to announce the release of **{book_title}** — now available on our website and coming soon to major platforms.

## About the Book

{book_description}

## What Readers Are Saying

{testimonials}

## Get Your Copy

[Buy on our website]({buy_url}) · [Learn more]({learn_url})

---

*Darryl Elliott Brown*
*Publisher, Gullah Geechee Biz*
""",
}

class SubstackGrowthBot:
    """Autonomous Substack growth and newsletter generation."""

    def __init__(self, db: HQDatabase = None):
        self.db = db or HQDatabase()

    def generate_newsletter(self, template: str = "weekly") -> dict:
        """Generate a newsletter post from the content pipeline."""
        date = datetime.now().strftime("%B %d, %Y")

        # Pull from command center content
        articles = list(STUDIO_DIR.glob("*.md"))
        magazine = [f for f in articles if "magazine" in f.name]
        podcast = [f for f in articles if "podcast" in f.name]

        newsletter = {
            "title": f"The Root — {datetime.now().strftime('%B %d, %Y')}",
            "template": template,
            "generated": datetime.now(timezone.utc).isoformat(),
            "content": TEMPLATES[template].format(
                date=date,
                feature_article="A deep dive into Gullah Geechee culture and heritage.",
                recipe_pick="This week's featured recipe from our collection.",
                book_excerpt="An excerpt from one of our published works.",
                community_news="Updates from the Gullah Geechee community.",
                share_url=SUBSTACK_URL,
                subscribe_url=SUBSTACK_URL,
            ),
        }

        output = CONTENT_DIR / f"newsletter-{datetime.now().strftime('%Y-%m-%d')}.md"
        output.write_text(newsletter["content"])
        self.db.log_content("substack", "newsletter", newsletter["title"], str(output))
        return newsletter

    def generate_welcome_series(self) -> list:
        """Generate a 5-email welcome sequence for new subscribers."""
        series = []
        for i, day in enumerate([0, 1, 3, 7, 14]):
            email = {
                "day": day,
                "subject": f"Day {day + 1}: Welcome to The Root" if day == 0 else f"Day {day + 1}: Your Gullah Geechee Journey",
                "content": TEMPLATES["welcome"].format(date=datetime.now().strftime("%B %d, %Y")),
            }
            output = CONTENT_DIR / f"welcome-day-{day}.md"
            output.write_text(email["content"])
            series.append(email)
        self.db.log_content("substack", "welcome_series", "5-email welcome series", str(CONTENT_DIR))
        return series

    def generate_cross_post(self, source: str = "magazine") -> dict:
        """Generate a cross-post from command center content."""
        articles = list(STUDIO_DIR.glob("*.md"))
        source_file = None
        for f in articles:
            if source in f.name:
                source_file = f
                break

        if not source_file:
            return {"error": f"No {source} content found in studio"}

        text = source_file.read_text()
        # Extract first 500 chars as preview
        preview = text[:500] + "..." if len(text) > 500 else text

        post = {
            "source": source,
            "title": f"From the {source.title()}: {source_file.stem}",
            "preview": preview,
            "generated": datetime.now(timezone.utc).isoformat(),
            "full_path": str(source_file),
        }

        output = CONTENT_DIR / f"crosspost-{source}-{uuid.uuid4().hex[:6]}.json"
        output.write_text(json.dumps(post, indent=2))
        self.db.log_content("substack", "crosspost", post["title"], str(output))
        return post

    def growth_report(self) -> dict:
        """Generate a growth strategy report."""
        stats = self.db.get_stats()
        return {
            "platform": "Substack",
            "url": SUBSTACK_URL,
            "frequency": NEWSLETTER_FREQUENCY,
            "publish_day": NEWSLETTER_DAY,
            "content_generated": stats.get("by_type", {}).get("newsletter", 0),
            "welcome_series": stats.get("by_type", {}).get("welcome_series", 0),
            "crossposts": stats.get("by_type", {}).get("crosspost", 0),
            "growth_tactics": [
                "Weekly newsletter from command center content",
                "5-email welcome sequence for new subscribers",
                "Cross-post magazine and podcast content",
                "Recipe-of-the-week series from cookbook collection",
                "Book launch announcements with excerpts",
                "Community spotlight features",
                "Referral program integration",
                "TikTok cross-promotion",
            ],
        }


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="GGB Substack Growth Bot")
    parser.add_argument("--json", action="store_true")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("report", help="Growth strategy report")
    sub.add_parser("newsletter", help="Generate weekly newsletter")
    sub.add_parser("welcome", help="Generate welcome series")
    cross = sub.add_parser("crosspost", help="Generate cross-post")
    cross.add_argument("--source", default="magazine")

    args = parser.parse_args()
    bot = SubstackGrowthBot()

    if args.command == "report":
        result = bot.growth_report()
    elif args.command == "newsletter":
        result = bot.generate_newsletter()
    elif args.command == "welcome":
        result = bot.generate_welcome_series()
    elif args.command == "crosspost":
        result = bot.generate_cross_post(args.source)

    if args.json:
        print(json.dumps(result, indent=2, default=str))
    else:
        if isinstance(result, dict):
            for k, v in result.items():
                print(f"{k}: {v}")
        elif isinstance(result, list):
            print(f"Generated {len(result)} items")
            for item in result:
                print(f"  Day {item['day']}: {item['subject']}")
        else:
            print(result)
