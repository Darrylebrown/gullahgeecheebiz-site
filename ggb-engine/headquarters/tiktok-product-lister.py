#!/usr/bin/env python3
"""
GGB TikTok Shop Product Lister — generates complete, ready-to-list product pages
for TikTok Shop from approved packages. Pricing optimized for 5% commission.
Copy-paste ready. No manual creation needed.
"""
import json, sys, uuid, sqlite3, random
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from publisher import PublishEngine, REPO_ROOT
from headquarters.engine import LOGS_DIR

TIKTOK_DB = LOGS_DIR / "tiktok-lister.db"
OUTPUT_DIR = REPO_ROOT / "publish" / "tiktok-shop"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ─── Pricing Strategy ──────────────────────────────────────────────────
# TikTok takes 5% commission + ~3% payment processing
# Target: $6-8 net profit per book after fees + shipping

PRICING_TIERS = {
    "ebook": {
        "base_price": 4.99,
        "tiktok_fee_pct": 0.05,
        "processing_fee_pct": 0.03,
        "processing_fee_flat": 0.30,
        "shipping_cost": 0,
        "net_profit": 4.99 - (4.99 * 0.05) - (4.99 * 0.03) - 0.30,
        "recommended_price": 4.99,
    },
    "audiobook": {
        "base_price": 9.99,
        "tiktok_fee_pct": 0.05,
        "processing_fee_pct": 0.03,
        "processing_fee_flat": 0.30,
        "shipping_cost": 0,
        "net_profit": 9.99 - (9.99 * 0.05) - (9.99 * 0.03) - 0.30,
        "recommended_price": 9.99,
    },
    "bundle": {
        "base_price": 14.99,
        "tiktok_fee_pct": 0.05,
        "processing_fee_pct": 0.03,
        "processing_fee_flat": 0.30,
        "shipping_cost": 0,
        "net_profit": 14.99 - (14.99 * 0.05) - (14.99 * 0.03) - 0.30,
        "recommended_price": 14.99,
    },
}

# ─── Category Mapping ───────────────────────────────────────────────────

TIKTOK_CATEGORIES = {
    "self-help": "Books & Audible > Self-Help",
    "business": "Books & Audible > Business & Finance",
    "cooking": "Books & Audible > Cookbooks",
    "history": "Books & Audible > History",
    "culture": "Books & Audible > Cultural & Heritage",
    "spiritual": "Books & Audible > Religion & Spirituality",
    "default": "Books & Audible > General",
}

# ─── Description Templates ─────────────────────────────────────────────

DESCRIPTION_TEMPLATES = [
    """📚 {title}

Discover the rich heritage of the Gullah Geechee people in this essential guide. Written by Darryl Elliott Brown, this book draws on centuries of wisdom from the Sea Islands of South Carolina and Georgia.

What you'll learn:
• The history and traditions of the Gullah Geechee people
• Practical wisdom passed down through generations
• Cultural connections between West Africa and the Lowcountry
• How to apply Gullah Geechee principles in your daily life

Perfect for anyone interested in African American history, Southern culture, or personal growth.

🔹 Instant download
🔹 Read on any device
🔹 70% of proceeds support Gullah Geechee cultural preservation

#GullahGeechee #BlackHistory #Lowcountry #SeaIslands #CulturalHeritage""",

    """🌟 New Release: {title}

The Gullah Geechee community has preserved African traditions for over 400 years. Now, this wisdom is available in an easy-to-read guide.

Inside you'll find:
✅ Step-by-step guidance
✅ Cultural context and history
✅ Practical exercises
✅ Stories from the Sea Islands

This book is more than a guide — it's a connection to a living culture that has survived against all odds.

Download instantly on Google Play Books, Amazon Kindle, or your favorite device.

#GullahGeechee #NewBook #CulturalWisdom #SelfHelp #BlackExcellence""",

    """📖 {title} — A Gullah Geechee Guide

For over four centuries, the Gullah Geechee people have preserved the traditions, language, and wisdom of their West African ancestors. This book brings that wisdom to you.

Whether you're new to Gullah Geechee culture or looking to deepen your understanding, this guide offers:

✨ Clear explanations of key concepts
✨ Historical context and cultural significance
✨ Practical applications for modern life
✨ Beautifully designed for easy reading

Join thousands of readers who have discovered the power of Gullah Geechee wisdom.

Available now on all major platforms.

#GullahGeechee #BookRecommendation #CulturalHeritage #LowcountryLife""",
]

# ─── Product Lister ────────────────────────────────────────────────────

class TikTokProductLister:
    """Generates complete TikTok Shop product listings from approved packages."""

    def __init__(self):
        self.engine = PublishEngine()
        self._init_db()
        self.stats = {"listed": 0, "errors": 0}

    def _init_db(self):
        conn = sqlite3.connect(str(TIKTOK_DB))
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS listings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                manifest_id TEXT NOT NULL,
                title TEXT NOT NULL,
                price REAL NOT NULL,
                category TEXT NOT NULL,
                status TEXT DEFAULT 'generated',
                listing_file TEXT,
                created_at TEXT NOT NULL,
                UNIQUE(manifest_id)
            )
        """)
        conn.commit()
        conn.close()

    def get_approved_books(self) -> List[Dict]:
        """Get all approved/live books from publisher DB."""
        conn = sqlite3.connect(str(self.engine.db.db_path))
        rows = conn.execute(
            "SELECT manifest_id, data FROM manifests WHERE state IN ('approved', 'live')"
        ).fetchall()
        conn.close()
        books = []
        for mid, data in rows:
            manifest = json.loads(data)
            title = manifest.get("title", {}).get("canonical", "Unknown")
            slug = manifest.get("slug", mid[:20])
            price = manifest.get("publishing", {}).get("price", 4.99)
            books.append({"manifest_id": mid, "title": title, "slug": slug, "price": price})
        return books

    def generate_listing(self, book: Dict) -> Dict:
        """Generate a complete TikTok Shop product listing."""
        title = book["title"]
        price = book["price"]
        manifest_id = book["manifest_id"]

        # Determine category
        slug_lower = book["slug"].lower()
        category = TIKTOK_CATEGORIES["default"]
        for key, cat in TIKTOK_CATEGORIES.items():
            if key in slug_lower:
                category = cat
                break

        # Calculate TikTok-optimized price
        tier = PRICING_TIERS["ebook"]
        tiktok_fee = price * tier["tiktok_fee_pct"]
        processing_fee = price * tier["processing_fee_pct"] + tier["processing_fee_flat"]
        net_profit = price - tiktok_fee - processing_fee

        # Pick a description template
        description = random.choice(DESCRIPTION_TEMPLATES).format(title=title)

        # Generate hashtags
        hashtags = [
            "#GullahGeechee", "#BookTok", "#NewBook", "#SelfHelp",
            "#BlackHistory", "#CulturalHeritage", "#Lowcountry",
            "#BookRecommendation", "#ReadingList", "#TikTokShop",
        ]

        # Build the complete listing
        listing = {
            "product_name": title,
            "author": "Darryl Elliott Brown",
            "publisher": "Gullah Geechee Biz",
            "price": price,
            "currency": "USD",
            "category": category,
            "description": description,
            "hashtags": hashtags,
            "shipping": {
                "weight": "0.5 lbs",
                "dimensions": "6 x 0.5 x 9 inches",
                "handling_time": "1-2 business days",
            },
            "pricing_breakdown": {
                "list_price": price,
                "tiktok_commission_pct": f"{tier['tiktok_fee_pct']*100}%",
                "tiktok_commission": round(tiktok_fee, 2),
                "processing_fee": round(processing_fee, 2),
                "net_profit_per_sale": round(net_profit, 2),
            },
            "promotional_scripts": [],
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

        # Add promotional scripts from bot army if available
        promo_dir = REPO_ROOT / "publish" / "promotion" / "googleplay"
        if promo_dir.exists():
            safe_title = title.replace(" ", "-").replace(":", "").replace("'", "")[:30]
            for f in sorted(promo_dir.glob(f"{safe_title}*")):
                listing["promotional_scripts"].append({
                    "file": str(f),
                    "type": f.stem.split("-")[-1] if "-" in f.stem else "promo",
                })

        # Save listing file
        safe_filename = title.replace(" ", "-").replace(":", "").replace("'", "")[:40]
        filepath = OUTPUT_DIR / f"{safe_filename}-tiktok-listing.json"
        filepath.write_text(json.dumps(listing, indent=2))

        # Also save a human-readable version
        readme_path = OUTPUT_DIR / f"{safe_filename}-TIKTOK-LISTING.md"
        readme = f"""# TikTok Shop Listing — {title}

## Product Details
- **Name:** {title}
- **Author:** Darryl Elliott Brown
- **Price:** ${price:.2f} USD
- **Category:** {category}
- **Format:** Digital download

## Pricing Breakdown
- List price: ${price:.2f}
- TikTok commission (5%): ${tiktok_fee:.2f}
- Processing fee: ${processing_fee:.2f}
- **Net profit per sale: ${net_profit:.2f}**

## Description
{description}

## Hashtags
{' '.join(hashtags)}

## Promotional Scripts Available
{len(listing['promotional_scripts'])} scripts ready in publish/promotion/googleplay/

## How to List on TikTok Shop
1. Go to https://shop.tiktok.com
2. Click "Add Product"
3. Copy the name, description, and price from above
4. Set category to: {category}
5. Add hashtags to your promotional videos
6. Publish and start selling!

---
Generated by GGB TikTok Shop Product Lister at {datetime.now(timezone.utc).isoformat()}
"""
        readme_path.write_text(readme)

        # Log to DB
        conn = sqlite3.connect(str(TIKTOK_DB))
        conn.execute("""
            INSERT OR REPLACE INTO listings (manifest_id, title, price, category, status, listing_file, created_at)
            VALUES (?, ?, ?, ?, 'generated', ?, ?)
        """, (manifest_id, title, price, category, str(filepath), datetime.now(timezone.utc).isoformat()))
        conn.commit()
        conn.close()

        self.stats["listed"] += 1
        return {
            "title": title,
            "price": price,
            "net_profit": round(net_profit, 2),
            "category": category,
            "listing_file": str(filepath),
            "readme_file": str(readme_path),
            "scripts_available": len(listing["promotional_scripts"]),
        }

    def list_all(self) -> Dict:
        """Generate listings for all approved books."""
        books = self.get_approved_books()
        print(f"\n  🛍️ GGB TikTok Shop Product Lister")
        print(f"  ────────────────────────────────")
        print(f"  Books to list: {len(books)}")
        print()

        results = []
        for book in books:
            result = self.generate_listing(book)
            results.append(result)
            print(f"  ✅ {result['title'][:50]:50} | ${result['price']:.2f} | ${result['net_profit']:.2f} net")

        print(f"\n  ────────────────────────────────")
        print(f"  Total listings: {self.stats['listed']}")
        print(f"  Output: {OUTPUT_DIR}")
        print(f"  Next: Copy listings from {OUTPUT_DIR} to TikTok Shop")

        return {
            "total": len(books),
            "listed": self.stats["listed"],
            "errors": self.stats["errors"],
            "output_dir": str(OUTPUT_DIR),
            "results": results,
        }

    def status(self) -> Dict:
        """Lister status."""
        conn = sqlite3.connect(str(TIKTOK_DB))
        total = conn.execute("SELECT COUNT(*) FROM listings").fetchone()[0]
        by_category = conn.execute("SELECT category, COUNT(*) FROM listings GROUP BY category").fetchall()
        conn.close()
        return {
            "total_listings": total,
            "by_category": {r[0]: r[1] for r in by_category},
            "output_dir": str(OUTPUT_DIR),
        }


# ─── CLI ─────────────────────────────────────────────────────────────────

def cli():
    import argparse
    parser = argparse.ArgumentParser(description="GGB TikTok Shop Product Lister")
    parser.add_argument("--json", action="store_true")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("list-all", help="Generate listings for all approved books")
    sub.add_parser("status", help="Lister status")

    args = parser.parse_args()
    lister = TikTokProductLister()

    if args.command == "list-all":
        result = lister.list_all()
    elif args.command == "status":
        result = lister.status()

    if args.json:
        print(json.dumps(result, indent=2, default=str))
    else:
        if isinstance(result, dict):
            for k, v in result.items():
                if isinstance(v, list):
                    print(f"{k}: {len(v)} items")
                    for item in v[:3]:
                        if isinstance(item, dict):
                            print(f"  {item.get('title', '')[:40]:40} | ${item.get('price', 0):.2f}")
                else:
                    print(f"{k}: {v}")
        else:
            print(result)

    return 0

if __name__ == "__main__":
    sys.exit(cli())
