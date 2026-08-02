#!/usr/bin/env python3
"""
GGB Google Play Books Bot Army — autonomous promotion bots.
Generates promotional content, SEO signals, social posts, and review prompts
specifically for Google Play Books listings. Content-only — no auto-posting.
"""
import json, sys, uuid, sqlite3, random
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import Dict, List

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from publisher import REPO_ROOT
from headquarters.engine import LOGS_DIR

GPB_DB = LOGS_DIR / "googleplay-bots.db"
OUTPUT_DIR = REPO_ROOT / "publish" / "promotion" / "googleplay"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ─── Bot Templates ──────────────────────────────────────────────────────

BOT_TEMPLATES = {
    "tiktok-script": {
        "name": "TikTok Promo Script",
        "icon": "🎵",
        "prompts": [
            "Discover {title} — a Gullah Geechee guide available now on Google Play Books. Link in bio!",
            "Want to learn {title}? Get the book on Google Play Books today. #GullahGeechee",
            "The wisdom of the Sea Islands is now on Google Play Books. Grab {title} today!",
            "Your guide to {title} is just a tap away on Google Play Books. Download now!",
        ],
        "hashtags": ["#GullahGeechee", "#GooglePlayBooks", "#NewBook", "#ReadMore", "#BookTok"],
    },
    "instagram-post": {
        "name": "Instagram Promo Post",
        "icon": "📸",
        "prompts": [
            "📚 New on Google Play Books: {title}\n\nDiscover the rich heritage of the Gullah Geechee people. Available now on Google Play Books.\n\n#GullahGeechee #GooglePlayBooks #NewRelease #Bookstagram",
            "🌟 Just released on Google Play Books!\n\n{title} — your guide to Gullah Geechee wisdom and culture.\n\nDownload today and start your journey.\n\n#GullahGeechee #GooglePlay #CulturalHeritage",
        ],
        "hashtags": ["#GullahGeechee", "#GooglePlayBooks", "#Bookstagram", "#NewRelease", "#CulturalHeritage"],
    },
    "pinterest-pin": {
        "name": "Pinterest Promo Pin",
        "icon": "📌",
        "prompts": [
            "{title} — A Gullah Geechee Guide | Available on Google Play Books",
            "Learn {title} with this essential guide. On Google Play Books now.",
            "The Sea Islands' wisdom is now digital. Get {title} on Google Play Books.",
        ],
        "hashtags": ["#GullahGeechee", "#GooglePlayBooks", "#BookRecommendation", "#ReadingList"],
    },
    "twitter-post": {
        "name": "X/Twitter Promo Post",
        "icon": "🐦",
        "prompts": [
            "Just published {title} on Google Play Books. Check it out! 📚 #GullahGeechee",
            "New on Google Play Books: {title}. A guide to Gullah Geechee wisdom. #NewBook",
            "The culture lives on. {title} is now available on Google Play Books. #GullahGeechee",
        ],
        "hashtags": ["#GullahGeechee", "#GooglePlayBooks", "#NewBook", "#Reading"],
    },
    "review-prompt": {
        "name": "Review Prompt",
        "icon": "⭐",
        "prompts": [
            "Loved {title}? Leave a review on Google Play Books and help others discover Gullah Geechee culture!",
            "Enjoyed reading {title}? Rate it on Google Play Books — every review helps!",
            "Your review of {title} on Google Play Books helps preserve Gullah Geechee heritage. Leave one today!",
        ],
        "hashtags": ["#GullahGeechee", "#GooglePlayBooks", "#BookReview", "#SupportIndieAuthors"],
    },
    "seo-article": {
        "name": "SEO Article Snippet",
        "icon": "📝",
        "prompts": [
            "Looking for {title}? This Gullah Geechee guide is now available on Google Play Books. With 70% royalties and global distribution to 75+ countries, it's never been easier to share Sea Islands wisdom with the world.",
            "Discover {title} on Google Play Books. Written by Darryl Elliott Brown, this guide draws on centuries of Gullah Geechee tradition. Available for instant download on Android and web.",
            "The Gullah Geechee community's latest release, {title}, is now on Google Play Books. Reach readers in 75+ countries with this essential cultural guide.",
        ],
        "hashtags": ["#GullahGeechee", "#GooglePlayBooks", "#SelfPublishing", "#IndieAuthor"],
    },
    "email-blast": {
        "name": "Email Promotion",
        "icon": "📧",
        "prompts": [
            "Subject: New Release: {title} on Google Play Books\n\nDear Reader,\n\nWe're excited to announce that {title} is now available on Google Play Books! Download instantly on your Android device or read online.\n\nGet your copy today and explore the rich heritage of the Gullah Geechee people.\n\nWarmly,\nDarryl Elliott Brown\nGullah Geechee Biz",
            "Subject: {title} — Now on Google Play Books\n\nHello,\n\nGreat news! {title} has just been published on Google Play Books. Available in 75+ countries with instant download.\n\nThank you for supporting Gullah Geechee culture.\n\nBest,\nDarryl Elliott Brown",
        ],
        "hashtags": [],
    },
}

# ─── Bot Army ────────────────────────────────────────────────────────────

class GooglePlayBotArmy:
    """Army of bots that generate promotional content for Google Play Books."""

    def __init__(self):
        self._init_db()
        self.stats = {"generated": 0, "errors": 0}

    def _init_db(self):
        conn = sqlite3.connect(str(GPB_DB))
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS promotions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                bot_type TEXT NOT NULL,
                content TEXT NOT NULL,
                hashtags TEXT,
                created_at TEXT NOT NULL
            )
        """)
        conn.commit()
        conn.close()

    def get_pending_books(self) -> List[Dict]:
        """Get all approved/live books from publisher DB."""
        try:
            import sqlite3
            from publisher import DB_PATH
            conn = sqlite3.connect(str(DB_PATH))
            rows = conn.execute(
                "SELECT manifest_id, data FROM manifests WHERE state IN ('approved', 'live')"
            ).fetchall()
            conn.close()
            books = []
            for mid, data in rows:
                manifest = json.loads(data)
                title = manifest.get("title", {}).get("canonical", "Unknown")
                books.append({"manifest_id": mid, "title": title})
            return books
        except:
            return []

    def generate_promotions(self, title: str, manifest_id: str = "") -> List[Dict]:
        """Generate all promotional content for a single book."""
        results = []
        for bot_key, bot in BOT_TEMPLATES.items():
            try:
                prompt = random.choice(bot["prompts"]).format(title=title)
                hashtags = " ".join(bot["hashtags"])
                content = f"{bot['icon']} {bot['name']}\n\n{prompt}\n\n{hashtags}"

                # Save to file
                safe_title = title.replace(" ", "-").replace(":", "").replace("'", "")[:30]
                filename = f"{safe_title}-{bot_key}-{uuid.uuid4().hex[:6]}.md"
                filepath = OUTPUT_DIR / filename
                filepath.write_text(content)

                # Log to DB
                conn = sqlite3.connect(str(GPB_DB))
                conn.execute(
                    "INSERT INTO promotions (title, bot_type, content, hashtags, created_at) VALUES (?, ?, ?, ?, ?)",
                    (title, bot_key, content, json.dumps(bot["hashtags"]), datetime.now(timezone.utc).isoformat())
                )
                conn.commit()
                conn.close()

                self.stats["generated"] += 1
                results.append({"bot": bot_key, "file": str(filepath), "status": "generated"})
            except Exception as e:
                self.stats["errors"] += 1
                results.append({"bot": bot_key, "error": str(e)})

        return results

    def army_swarm(self) -> Dict:
        """Run the full bot army — generate promotions for all books."""
        books = self.get_pending_books()
        print(f"\n  🤖 GGB Google Play Books Bot Army")
        print(f"  ────────────────────────────────")
        print(f"  Books: {len(books)}")
        print(f"  Bot types: {len(BOT_TEMPLATES)}")
        print()

        all_results = []
        for book in books:
            title = book["title"]
            results = self.generate_promotions(title, book["manifest_id"])
            all_results.extend(results)
            print(f"  ✅ {title[:50]:50} | {len(results)} promotions")

        print(f"\n  ────────────────────────────────")
        print(f"  Total promotions generated: {self.stats['generated']}")
        print(f"  Errors: {self.stats['errors']}")
        print(f"  Output: {OUTPUT_DIR}")

        return {
            "books": len(books),
            "bot_types": len(BOT_TEMPLATES),
            "generated": self.stats["generated"],
            "errors": self.stats["errors"],
            "output_dir": str(OUTPUT_DIR),
        }

    def status(self) -> Dict:
        """Bot army status."""
        conn = sqlite3.connect(str(GPB_DB))
        total = conn.execute("SELECT COUNT(*) FROM promotions").fetchone()[0]
        by_type = conn.execute("SELECT bot_type, COUNT(*) FROM promotions GROUP BY bot_type").fetchall()
        conn.close()
        return {
            "total_promotions": total,
            "by_type": {r[0]: r[1] for r in by_type},
            "bot_types": len(BOT_TEMPLATES),
            "output_dir": str(OUTPUT_DIR),
        }


# ─── CLI ─────────────────────────────────────────────────────────────────

def cli():
    import argparse
    parser = argparse.ArgumentParser(description="GGB Google Play Books Bot Army")
    parser.add_argument("--json", action="store_true")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("swarm", help="Run the full bot army")
    sub.add_parser("status", help="Bot army status")

    args = parser.parse_args()
    army = GooglePlayBotArmy()

    if args.command == "swarm":
        result = army.army_swarm()
    elif args.command == "status":
        result = army.status()

    if args.json:
        print(json.dumps(result, indent=2, default=str))
    else:
        if isinstance(result, dict):
            for k, v in result.items():
                if isinstance(v, list):
                    print(f"{k}: {len(v)} items")
                else:
                    print(f"{k}: {v}")
        else:
            print(result)

    return 0

if __name__ == "__main__":
    sys.exit(cli())
