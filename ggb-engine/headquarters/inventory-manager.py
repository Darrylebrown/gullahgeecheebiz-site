#!/usr/bin/env python3
"""
GGB Inventory Manager — stock monitoring, auto-refill triggers, and
new-series generation for all stores: Stripe, Etsy, Shopify, KDP.
Monitors stock levels and auto-generates replacement content when low.
"""
import json, sys, uuid, random, sqlite3
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, List

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from headquarters.engine import HQDatabase, CONTENT_DIR, STUDIO_DIR, LOGS_DIR
from publisher import REPO_ROOT

# ─── Store Registry ────────────────────────────────────────────────────────

STORES = {
    "stripe": {
        "name": "Stripe Checkout",
        "url": "https://buy.stripe.com",
        "products": 99,
        "min_stock": 100,
        "refill_threshold": 90,
        "refill_action": "generate_new_ebook",
    },
    "etsy": {
        "name": "Etsy Shop",
        "url": "etsy.com/shop/gullahgeecheebiz",
        "products": 100,
        "min_stock": 100,
        "refill_threshold": 90,
        "refill_action": "generate_new_ebook",
    },
    "shopify": {
        "name": "Shopify Store",
        "url": "shopify.com",
        "products": 106,
        "min_stock": 100,
        "refill_threshold": 90,
        "refill_action": "generate_new_ebook",
    },
    "kdp": {
        "name": "KDP Direct",
        "url": "kdp.amazon.com",
        "products": 7,
        "min_stock": 7,
        "refill_threshold": 5,
        "refill_action": "generate_new_edition",
    },
    "wholesale": {
        "name": "Wholesale (Bookstores/Libraries)",
        "url": "/wholesale/",
        "products": 0,
        "min_stock": 10,
        "refill_threshold": 5,
        "refill_action": "generate_wholesale_pack",
        "description": "Bulk digital packs for bookstores, libraries, educators. 55% margins, 10+ copy minimum.",
    },
}

# ─── Book Series Templates ────────────────────────────────────────────────

SERIES_TEMPLATES = {
    "self-help": {
        "prefix": "The Gullah Geechee Guide to",
        "topics": [
            "Abundance", "Acceptance", "Adaptability", "Balance", "Boundaries",
            "Change", "Clarity", "Compassion", "Confidence", "Connection",
            "Contentment", "Creativity", "Curiosity", "Determination", "Dignity",
            "Discipline", "Empathy", "Encouragement", "Endurance", "Faith",
            "Flexibility", "Focus", "Freedom", "Generosity", "Gentleness",
            "Grace", "Gratitude", "Growth", "Harmony", "Healing",
            "Honesty", "Hope", "Humility", "Imagination", "Independence",
            "Inner Peace", "Inspiration", "Integrity", "Joy", "Kindness",
            "Knowledge", "Leadership", "Letting Go", "Listening", "Love",
            "Mindfulness", "Motivation", "Nurturing", "Openness", "Optimism",
            "Patience", "Perseverance", "Presence", "Purpose", "Reflection",
            "Resilience", "Respect", "Rest", "Sacredness", "Self-Care",
            "Serenity", "Service", "Silence", "Simplicity", "Sincerity",
            "Stillness", "Strength", "Surrender", "Thankfulness", "Trust",
            "Truth", "Understanding", "Unity", "Vision", "Vulnerability",
            "Wisdom", "Wonder", "Worthiness", "Yearning", "Zeal",
        ],
    },
    "business": {
        "prefix": "Gullah Geechee",
        "topics": [
            "Branding Guide", "Business Planning", "Community Commerce",
            "Cooperative Economics", "Cultural Entrepreneurship", "Digital Marketing",
            "E-Commerce Strategy", "Financial Literacy", "Grant Writing",
            "Heritage Business", "Impact Investing", "Job Creation",
            "Land Ownership", "Local Economy", "Market Research",
            "Microenterprise", "Networking", "Online Presence", "Partnerships",
            "Pricing Strategy", "Product Development", "Rural Business",
            "Sales Techniques", "Social Enterprise", "Startup Guide",
            "Sustainable Business", "Tax Planning", "Tourism Ventures",
            "Value Creation", "Wealth Building",
        ],
    },
    "cooking": {
        "prefix": "Gullah Geechee",
        "topics": [
            "Appetizers", "Baking", "Barbecue", "Beans and Rice",
            "Beverages", "Bread", "Breakfast", "Cajun Fusion",
            "Camp Cooking", "Canning", "Caribbean Fusion", "Cast Iron",
            "Casseroles", "Celebration Meals", "Comfort Food", "Condiments",
            "Cookies", "Cornbread", "Crab", "Desserts",
            "Dips and Spreads", "Dumplings", "Fasting Meals", "Fermentation",
            "Fish", "Fritters", "Fruit Desserts", "Game Cooking",
            "Grains", "Gravies", "Greens", "Grilling",
            "Gumbos", "Heritage Recipes", "Holiday Meals", "Ice Cream",
            "Jams and Jellies", "Kid-Friendly", "Leftover Makeovers", "Lunch Ideas",
            "Meal Prep", "Meatless", "One-Pot Meals", "Oyster Recipes",
            "Party Platters", "Pickling", "Pies", "Poultry",
            "Puddings", "Quick Breads", "Roasting", "Salads",
            "Sandwiches", "Sauces", "Seafood", "Seasonings",
            "Shellfish", "Shrimp", "Side Dishes", "Slow Cooker",
            "Smoothies", "Snacks", "Soups", "Stews",
            "Stuffed Vegetables", "Summer Cooking", "Sunday Dinner", "Syrups",
            "Tarts", "Thanksgiving", "Vegetables", "West African Fusion",
            "Winter Cooking", "Yams and Sweet Potatoes",
        ],
    },
}

class InventoryManager:
    """Monitors stock across all stores and auto-triggers refills."""

    def __init__(self, db: HQDatabase = None):
        self.db = db or HQDatabase()
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(str(self.db.db_path))
        conn.execute("""
            CREATE TABLE IF NOT EXISTS inventory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                store TEXT NOT NULL,
                product_id TEXT,
                product_name TEXT,
                stock_count INTEGER DEFAULT 0,
                min_stock INTEGER DEFAULT 100,
                refill_threshold INTEGER DEFAULT 90,
                last_refill_at TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS refill_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                store TEXT NOT NULL,
                action TEXT NOT NULL,
                product_count INTEGER,
                triggered_by TEXT DEFAULT 'auto',
                status TEXT DEFAULT 'pending',
                created_at TEXT NOT NULL,
                completed_at TEXT
            )
        """)
        conn.commit()
        conn.close()

    def check_all_stores(self) -> Dict:
        """Check stock levels across all stores and return status."""
        results = {}
        for store_key, store_info in STORES.items():
            results[store_key] = self._check_store(store_key, store_info)
        return results

    def _check_store(self, store_key: str, store_info: Dict) -> Dict:
        """Check a single store's stock level."""
        current = store_info["products"]
        threshold = store_info["refill_threshold"]
        min_stock = store_info["min_stock"]

        status = {
            "store": store_info["name"],
            "current_stock": current,
            "min_stock": min_stock,
            "threshold": threshold,
            "status": "healthy",
            "needs_refill": False,
            "action": None,
        }

        if current < threshold:
            deficit = min_stock - current
            status["status"] = "low_stock"
            status["needs_refill"] = True
            status["action"] = store_info["refill_action"]
            status["deficit"] = deficit
            status["suggested_refill"] = max(deficit, 10)  # at least 10 new products

        return status

    def auto_refill(self, store_key: str, count: int = 10) -> Dict:
        """Auto-generate new products to refill a store."""
        store_info = STORES.get(store_key)
        if not store_info:
            return {"error": f"Unknown store: {store_key}"}

        action = store_info["refill_action"]
        conn = sqlite3.connect(str(self.db.db_path))

        if action == "generate_new_ebook":
            # Pick a series and generate new titles
            series = random.choice(list(SERIES_TEMPLATES.keys()))
            template = SERIES_TEMPLATES[series]
            available = [t for t in template["topics"]]
            selected = random.sample(available, min(count, len(available)))

            new_products = []
            for topic in selected:
                title = f"{template['prefix']} {topic}"
                slug = f"gullah-{topic.lower().replace(' ', '-')}"
                new_products.append({
                    "title": title,
                    "slug": slug,
                    "series": series,
                    "price": random.choice([3.99, 4.99, 5.99, 6.99, 7.99, 8.99, 9.99]),
                    "drm": "No",
                    "select": "Off",
                })

            # Log the refill
            conn.execute(
                "INSERT INTO refill_log (store, action, product_count, status, created_at) VALUES (?, ?, ?, 'generated', ?)",
                (store_key, action, len(new_products), datetime.now(timezone.utc).isoformat())
            )
            conn.commit()

            # Save the new product list
            output = CONTENT_DIR / f"refill-{store_key}-{datetime.now().strftime('%Y%m%d-%H%M')}.json"
            output.write_text(json.dumps({
                "store": store_key,
                "action": action,
                "count": len(new_products),
                "products": new_products,
                "generated": datetime.now(timezone.utc).isoformat(),
            }, indent=2))

            self.db.log_content("inventory", "refill", f"Refill {store_key}: {len(new_products)} products", str(output))

            return {
                "status": "refilled",
                "store": store_key,
                "action": action,
                "count": len(new_products),
                "series": series,
                "products": new_products,
                "output": str(output),
            }

        if action == "generate_wholesale_pack":
            # Generate bulk wholesale packs for bookstores/libraries
            wholesale_packs = [
                {"title": "Gullah Geechee Starter Pack", "count": 10, "price": 49.99, "description": "10 best-selling ebooks for new bookstores"},
                {"title": "Gullah Geechee Complete Collection", "count": 50, "price": 199.99, "description": "Full catalog for libraries and educators"},
                {"title": "Gullah Geechee Cookbook Bundle", "count": 10, "price": 39.99, "description": "10 cookbook titles for culinary sections"},
                {"title": "Gullah Geechee Self-Help Bundle", "count": 10, "price": 39.99, "description": "10 self-help titles for personal development"},
                {"title": "Gullah Geechee Business Bundle", "count": 10, "price": 39.99, "description": "10 business titles for entrepreneurs"},
                {"title": "Gullah Geechee Encyclopedia Pack", "count": 5, "price": 29.99, "description": "5 encyclopedia volumes for academic libraries"},
                {"title": "Gullah Geechee Ambassador Pack", "count": 25, "price": 99.99, "description": "25 titles for community organizations"},
                {"title": "Gullah Geechee Educator Pack", "count": 15, "price": 59.99, "description": "15 titles for schools and educators"},
            ]
            selected = random.sample(wholesale_packs, min(count, len(wholesale_packs)))
            new_products = selected

            conn.execute(
                "INSERT INTO refill_log (store, action, product_count, status, created_at) VALUES (?, ?, ?, 'generated', ?)",
                (store_key, action, len(new_products), datetime.now(timezone.utc).isoformat())
            )
            conn.commit()

            output = CONTENT_DIR / f"refill-{store_key}-{datetime.now().strftime('%Y%m%d-%H%M')}.json"
            output.write_text(json.dumps({
                "store": store_key,
                "action": action,
                "count": len(new_products),
                "packs": new_products,
                "generated": datetime.now(timezone.utc).isoformat(),
            }, indent=2))

            self.db.log_content("inventory", "refill", f"Refill {store_key}: {len(new_products)} wholesale packs", str(output))

            return {
                "status": "refilled",
                "store": store_key,
                "action": action,
                "count": len(new_products),
                "packs": new_products,
                "output": str(output),
            }

        return {"error": f"Unknown refill action: {action}"}

    def full_scan_and_refill(self) -> Dict:
        """Scan all stores and auto-refill any that are below threshold."""
        scan = self.check_all_stores()
        refills = {}

        for store_key, status in scan.items():
            if status.get("needs_refill"):
                deficit = status.get("deficit", 10)
                refill_count = max(deficit, 10)
                refills[store_key] = self.auto_refill(store_key, refill_count)
            else:
                refills[store_key] = {"status": "skipped", "reason": "stock_healthy"}

        return {
            "scan": scan,
            "refills": refills,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def inventory_report(self) -> Dict:
        """Full inventory report across all stores."""
        scan = self.check_all_stores()
        conn = sqlite3.connect(str(self.db.db_path))
        refill_history = conn.execute(
            "SELECT store, action, product_count, status, created_at FROM refill_log ORDER BY id DESC LIMIT 20"
        ).fetchall()
        conn.close()

        return {
            "stores": scan,
            "total_products": sum(s["current_stock"] for s in scan.values()),
            "stores_needing_refill": sum(1 for s in scan.values() if s.get("needs_refill")),
            "refill_history": [
                {"store": r[0], "action": r[1], "count": r[2], "status": r[3], "at": r[4]}
                for r in refill_history
            ],
            "available_topics": {
                series: len(template["topics"])
                for series, template in SERIES_TEMPLATES.items()
            },
        }


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="GGB Inventory Manager")
    parser.add_argument("--json", action="store_true")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("scan", help="Check stock across all stores")
    sub.add_parser("report", help="Full inventory report")
    sub.add_parser("refill-all", help="Auto-refill all low-stock stores")

    refill = sub.add_parser("refill", help="Refill a specific store")
    refill.add_argument("store", choices=list(STORES.keys()), help="Store to refill")
    refill.add_argument("--count", type=int, default=10, help="Number of products to generate")

    args = parser.parse_args()
    mgr = InventoryManager()

    if args.command == "scan":
        result = mgr.check_all_stores()
    elif args.command == "report":
        result = mgr.inventory_report()
    elif args.command == "refill-all":
        result = mgr.full_scan_and_refill()
    elif args.command == "refill":
        result = mgr.auto_refill(args.store, args.count)

    if args.json:
        print(json.dumps(result, indent=2, default=str))
    else:
        if isinstance(result, dict):
            if "stores" in result:
                print("=== Inventory Report ===")
                print(f"Total products: {result['total_products']}")
                print(f"Stores needing refill: {result['stores_needing_refill']}")
                print()
                for store_key, status in result["stores"].items():
                    icon = "⚠️" if status.get("needs_refill") else "✅"
                    print(f"  {icon} {status['store']}: {status['current_stock']} / {status['min_stock']} (threshold: {status['threshold']})")
                print()
                print("Available topics for refill:")
                for series, count in result.get("available_topics", {}).items():
                    print(f"  {series}: {count} topics")
                if result.get("refill_history"):
                    print("\nRecent refills:")
                    for r in result["refill_history"][:5]:
                        print(f"  {r['at'][:10]} | {r['store']:>8} | {r['count']} products | {r['status']}")
            elif "scan" in result:
                print("=== Auto-Refill Results ===")
                for store_key, status in result["scan"].items():
                    icon = "⚠️" if status.get("needs_refill") else "✅"
                    print(f"  {icon} {status['store']}: {status['current_stock']} / {status['min_stock']}")
                print()
                for store_key, refill in result["refills"].items():
                    if refill.get("status") == "refilled":
                        print(f"  🔄 Refilled {store_key}: {refill['count']} new {refill['series']} products")
                    else:
                        print(f"  ✅ {store_key}: {refill.get('reason', 'ok')}")
            elif "needs_refill" in result:
                icon = "⚠️" if result.get("needs_refill") else "✅"
                print(f"{icon} {result['store']}: {result['current_stock']} / {result['min_stock']}")
                if result.get("needs_refill"):
                    print(f"  Deficit: {result['deficit']}")
                    print(f"  Suggested refill: {result['suggested_refill']} new products")
                    print(f"  Action: {result['action']}")
            elif result.get("status") == "refilled":
                if "packs" in result:
                    print(f"🔄 Refilled {result['store']} with {result['count']} wholesale packs")
                    print(f"  Output: {result['output']}")
                    for p in result.get("packs", [])[:5]:
                        print(f"  - {p['title']} (${p['price']} — {p['count']} titles)")
                else:
                    print(f"🔄 Refilled {result['store']} with {result['count']} new {result.get('series', '')} products")
                    print(f"  Output: {result['output']}")
                    for p in result.get("products", [])[:5]:
                        print(f"  - {p['title']} (${p['price']})")
                    if len(result.get("products", [])) > 5:
                        print(f"  ... and {len(result['products']) - 5} more")
            else:
                for k, v in result.items():
                    print(f"{k}: {v}")
        else:
            print(result)
