#!/usr/bin/env python3
"""
GGB SEO Engine — built into the production pipeline.
Every piece of content gets auto-SEO'd, promoted, tracked, and infused
with optimized metadata before it even launches.
"""
import json, sys, uuid, sqlite3, re
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from publisher import REPO_ROOT
from headquarters.engine import LOGS_DIR

SEO_DB = LOGS_DIR / "seo-engine.db"

# ─── Keyword Banks ────────────────────────────────────────────────────────

PRIMARY_KEYWORDS = {
    "book": [
        "Gullah Geechee books", "African American history", "Lowcountry culture",
        "Sea Islands heritage", "Gullah Geechee culture", "Black history books",
        "South Carolina history", "Georgia coast history", "Gullah language",
        "African diaspora literature",
    ],
    "audiobook": [
        "Gullah Geechee audiobooks", "African American audiobooks", "Lowcountry stories",
        "Black history audiobooks", "Gullah Geechee narration", "cultural audiobooks",
        "Sea Islands audiobooks", "African diaspora audio",
    ],
    "ad": [
        "Gullah Geechee tourism", "Lowcountry travel", "Sea Islands vacation",
        "Charleston culture", "Savannah heritage", "Gullah Geechee experience",
        "African American travel", "cultural tourism",
    ],
    "commercial": [
        "Gullah Geechee commercial", "Lowcountry advertising", "cultural marketing",
        "African American media", "diverse advertising", "heritage branding",
    ],
    "movie": [
        "Gullah Geechee documentary", "Sea Islands film", "African American documentary",
        "Lowcountry film", "cultural documentary", "Black history film",
    ],
    "pin": [
        "Gullah Geechee art", "Lowcountry decor", "Sea Islands crafts",
        "sweetgrass baskets", "African American art", "cultural pins",
    ],
    "music": [
        "Gullah Geechee music", "African American spirituals", "Lowcountry sounds",
        "Sea Islands music", "Gullah gospel", "cultural music",
    ],
    "magazine": [
        "Gullah Geechee magazine", "Lowcountry lifestyle", "Sea Islands culture",
        "African American magazine", "cultural publication", "heritage magazine",
    ],
}

SECONDARY_KEYWORDS = [
    "Gullah Geechee", "Lowcountry", "Sea Islands", "African diaspora",
    "cultural heritage", "Black history", "South Carolina", "Georgia coast",
    "sweetgrass", "rice culture", "spirituals", "praise house",
    "Penn Center", "St. Helena Island", "Hilton Head", "Charleston",
    "Savannah", "Daufuskie", "Sapelo Island", "Gullah language",
    "Geechee", "African retentions", "West African", "Middle Passage",
    "Reconstruction", "Sea Island cotton", "heirs property",
    "Gullah cuisine", "red rice", "okra", "seafood",
    "basket weaving", "net making", "oral history", "storytelling",
]

HASHTAGS = {
    "book": ["#GullahGeechee", "#BlackHistory", "#Lowcountry", "#SeaIslands", "#CulturalHeritage", "#AfricanAmericanHistory", "#NewBook", "#BookLaunch"],
    "audiobook": ["#GullahGeechee", "#Audiobook", "#BlackHistory", "#Lowcountry", "#Listening", "#CulturalHeritage", "#NewRelease"],
    "ad": ["#GullahGeechee", "#Lowcountry", "#Travel", "#Culture", "#Experience", "#Discover", "#Heritage"],
    "commercial": ["#GullahGeechee", "#Commercial", "#Lowcountry", "#Brand", "#Culture", "#Marketing", "#Heritage"],
    "movie": ["#GullahGeechee", "#Documentary", "#Film", "#BlackHistory", "#Lowcountry", "#SeaIslands", "#Watch"],
    "pin": ["#GullahGeechee", "#Art", "#Lowcountry", "#Crafts", "#Decor", "#SeaIslands", "#Inspiration"],
    "music": ["#GullahGeechee", "#Music", "#Spirituals", "#Gospel", "#Lowcountry", "#Sounds", "#NewMusic"],
    "magazine": ["#GullahGeechee", "#Magazine", "#Lowcountry", "#Culture", "#Read", "#Heritage", "#Subscribe"],
}

# ─── SEO Engine ──────────────────────────────────────────────────────────

class SEOEngine:
    """Built-in SEO engine for the production pipeline."""

    def __init__(self):
        self._init_db()
        self.stats = {"optimized": 0, "promoted": 0, "tracked": 0}

    def _init_db(self):
        conn = sqlite3.connect(str(SEO_DB))
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS seo_packages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                slug TEXT NOT NULL UNIQUE,
                content_type TEXT NOT NULL,
                primary_keywords TEXT,
                secondary_keywords TEXT,
                hashtags TEXT,
                meta_description TEXT,
                canonical_url TEXT,
                schema_markup TEXT,
                seo_score REAL DEFAULT 0,
                promoted INTEGER DEFAULT 0,
                promoted_at TEXT,
                tracked INTEGER DEFAULT 0,
                created_at TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS seo_tracking (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                slug TEXT NOT NULL,
                metric TEXT NOT NULL,
                value REAL DEFAULT 0,
                recorded_at TEXT NOT NULL
            )
        """)
        conn.commit()
        conn.close()

    def optimize(self, title: str, slug: str, content_type: str,
                 description: str = "", keywords: List[str] = None) -> Dict:
        """Optimize a package for SEO: keywords, metadata, schema, hashtags."""
        primary = PRIMARY_KEYWORDS.get(content_type, PRIMARY_KEYWORDS["book"])
        secondary = SECONDARY_KEYWORDS[:10]
        hashtags = HASHTAGS.get(content_type, HASHTAGS["book"])

        # Build meta description
        meta_desc = description or f"Discover {title}. A {content_type} from Gullah Geechee Biz exploring the rich cultural heritage of the Sea Islands."
        if len(meta_desc) > 160:
            meta_desc = meta_desc[:157] + "..."

        # Build canonical URL
        canonical = f"https://gullahgeecheebiz.com/{slug}"

        # Build schema.org markup
        schema = {
            "@context": "https://schema.org",
            "@type": "Book" if content_type == "book" else "CreativeWork",
            "name": title,
            "author": {"@type": "Person", "name": "Darryl Elliott Brown"},
            "publisher": {"@type": "Organization", "name": "Gullah Geechee Biz"},
            "description": meta_desc,
            "keywords": ", ".join(primary[:5]),
            "inLanguage": "en-US",
            "datePublished": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        }

        # Calculate SEO score
        score = 0
        if primary: score += 30
        if secondary: score += 20
        if meta_desc: score += 15
        if canonical: score += 10
        if schema: score += 15
        if hashtags: score += 10
        seo_score = min(score, 100)

        # Store in DB
        conn = sqlite3.connect(str(SEO_DB))
        conn.execute("""
            INSERT OR REPLACE INTO seo_packages
            (title, slug, content_type, primary_keywords, secondary_keywords,
             hashtags, meta_description, canonical_url, schema_markup,
             seo_score, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            title, slug, content_type,
            json.dumps(primary), json.dumps(secondary),
            json.dumps(hashtags), meta_desc, canonical,
            json.dumps(schema), seo_score,
            datetime.now(timezone.utc).isoformat()
        ))
        conn.commit()
        conn.close()

        self.stats["optimized"] += 1
        return {
            "title": title,
            "slug": slug,
            "content_type": content_type,
            "seo_score": seo_score,
            "primary_keywords": primary[:5],
            "hashtags": hashtags[:5],
            "meta_description": meta_desc,
            "canonical_url": canonical,
        }

    def promote(self, slug: str, channels: List[str] = None) -> Dict:
        """Pre-launch promotion: generate social posts, schedule content."""
        if channels is None:
            channels = ["tiktok", "instagram", "pinterest", "twitter"]

        conn = sqlite3.connect(str(SEO_DB))
        row = conn.execute("SELECT title, content_type, hashtags FROM seo_packages WHERE slug=?", (slug,)).fetchone()
        conn.close()

        if not row:
            return {"error": "Package not found in SEO DB"}

        title, content_type, hashtags_json = row
        hashtags = json.loads(hashtags_json) if hashtags_json else []

        # Generate pre-launch content for each channel
        promotions = {}
        for channel in channels:
            if channel == "tiktok":
                promotions[channel] = {
                    "script": f"Coming soon: {title}. Follow for the launch! {' '.join(hashtags[:3])}",
                    "type": "teaser",
                    "schedule": "3 days before launch",
                }
            elif channel == "instagram":
                promotions[channel] = {
                    "caption": f"📖 Coming soon: {title}\n\nA new {content_type} from Gullah Geechee Biz.\n\n{' '.join(hashtags[:5])}",
                    "type": "carousel",
                    "schedule": "5 days before launch",
                }
            elif channel == "pinterest":
                promotions[channel] = {
                    "pin_title": title,
                    "description": f"Coming soon from Gullah Geechee Biz. {' '.join(hashtags[:3])}",
                    "type": "pin",
                    "schedule": "7 days before launch",
                }
            elif channel == "twitter":
                promotions[channel] = {
                    "tweet": f"Something special is coming. {title} — launching soon from Gullah Geechee Biz. {' '.join(hashtags[:2])}",
                    "type": "teaser",
                    "schedule": "2 days before launch",
                }

        # Mark as promoted
        conn = sqlite3.connect(str(SEO_DB))
        conn.execute("UPDATE seo_packages SET promoted=1, promoted_at=? WHERE slug=?",
                     (datetime.now(timezone.utc).isoformat(), slug))
        conn.commit()
        conn.close()

        self.stats["promoted"] += 1
        return {
            "title": title,
            "slug": slug,
            "channels": channels,
            "promotions": promotions,
        }

    def track(self, slug: str, metric: str = "impression", value: float = 1.0) -> Dict:
        """Track a metric for a package."""
        conn = sqlite3.connect(str(SEO_DB))
        conn.execute("INSERT INTO seo_tracking (slug, metric, value, recorded_at) VALUES (?, ?, ?, ?)",
                     (slug, metric, value, datetime.now(timezone.utc).isoformat()))
        conn.execute("UPDATE seo_packages SET tracked=1 WHERE slug=?", (slug,))
        conn.commit()
        conn.close()
        self.stats["tracked"] += 1
        return {"slug": slug, "metric": metric, "value": value}

    def get_seo_report(self, days: int = 30) -> Dict:
        """Get SEO performance report."""
        conn = sqlite3.connect(str(SEO_DB))
        total = conn.execute("SELECT COUNT(*) FROM seo_packages").fetchone()[0]
        promoted = conn.execute("SELECT COUNT(*) FROM seo_packages WHERE promoted=1").fetchone()[0]
        avg_score = conn.execute("SELECT AVG(seo_score) FROM seo_packages").fetchone()[0] or 0

        # Top packages by SEO score
        top = conn.execute(
            "SELECT title, content_type, seo_score FROM seo_packages ORDER BY seo_score DESC LIMIT 10"
        ).fetchall()

        # Tracking stats
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        impressions = conn.execute(
            "SELECT SUM(value) FROM seo_tracking WHERE metric='impression' AND recorded_at > ?",
            (cutoff,)
        ).fetchone()[0] or 0
        clicks = conn.execute(
            "SELECT SUM(value) FROM seo_tracking WHERE metric='click' AND recorded_at > ?",
            (cutoff,)
        ).fetchone()[0] or 0

        conn.close()

        return {
            "total_optimized": total,
            "total_promoted": promoted,
            "average_seo_score": round(avg_score, 1),
            "impressions_30d": int(impressions),
            "clicks_30d": int(clicks),
            "top_packages": [{"title": r[0], "type": r[1], "score": r[2]} for r in top],
        }

    def optimize_package(self, pkg_dir: Path, title: str, content_type: str = "book") -> Dict:
        """Full SEO treatment for a package in the landing pad."""
        slug = pkg_dir.name

        # Read existing description if available
        description = ""
        draft = pkg_dir / "KDP-DRAFT.md"
        if draft.exists():
            text = draft.read_text()
            for line in text.split("\n"):
                if line.startswith("## Description"):
                    description = line.replace("## Description", "").strip()
                    break

        # 1. Optimize
        seo = self.optimize(title, slug, content_type, description)

        # 2. Write SEO metadata to package
        (pkg_dir / "SEO.md").write_text(f"""# SEO Metadata — {title}

## SEO Score: {seo['seo_score']}/100

## Primary Keywords
{', '.join(seo['primary_keywords'])}

## Meta Description
{seo['meta_description']}

## Canonical URL
{seo['canonical_url']}

## Hashtags
{' '.join(seo['hashtags'])}

## Schema Markup
```json
{json.dumps(json.loads(seo.get('schema_markup', '{}') if isinstance(seo.get('schema_markup'), str) else '{}'), indent=2) if isinstance(seo.get('schema_markup'), str) else json.dumps(seo.get('schema_markup', {}), indent=2)}
```

*Optimized by GGB SEO Engine at {datetime.now(timezone.utc).isoformat()}*
""")

        # 3. Promote (pre-launch)
        promo = self.promote(slug)

        # 4. Track initial impression
        self.track(slug, "impression", 1.0)

        return {
            "title": title,
            "slug": slug,
            "seo_score": seo["seo_score"],
            "promoted_channels": list(promo.get("promotions", {}).keys()),
            "tracked": True,
        }

    def scan_and_optimize(self) -> Dict:
        """Scan landing pad and optimize all packages."""
        landing_pad = REPO_ROOT / "publish" / "landing-pad"
        if not landing_pad.exists():
            return {"error": "Landing pad not found"}

        results = []
        for pkg_dir in sorted(landing_pad.iterdir()):
            if not pkg_dir.is_dir():
                continue

            # Determine content type from slug prefix
            slug = pkg_dir.name
            content_type = "book"
            for ct in ["audiobook", "ad", "commercial", "movie", "pin", "music", "magazine"]:
                if slug.startswith(ct):
                    content_type = ct
                    break

            # Get title from KDP-DRAFT or slug
            title = slug.replace("-", " ").title()
            draft = pkg_dir / "KDP-DRAFT.md"
            if draft.exists():
                for line in draft.read_text().split("\n"):
                    if line.startswith("# "):
                        title = line.replace("# ", "").replace("📚", "").replace("🎧", "").replace("📢", "").replace("📺", "").replace("🎬", "").replace("📌", "").replace("🎵", "").replace("📰", "").strip()
                        break

            result = self.optimize_package(pkg_dir, title, content_type)
            results.append(result)

        return {"optimized": len(results), "results": results}


# ─── CLI ─────────────────────────────────────────────────────────────────

def cli():
    import argparse
    parser = argparse.ArgumentParser(description="GGB SEO Engine")
    parser.add_argument("--json", action="store_true")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("report", help="SEO performance report")
    sub.add_parser("scan", help="Scan and optimize all packages in landing pad")

    optimize = sub.add_parser("optimize", help="Optimize a single package")
    optimize.add_argument("slug", help="Package slug")
    optimize.add_argument("--title", required=True)
    optimize.add_argument("--type", default="book", choices=list(PRIMARY_KEYWORDS.keys()))

    promote = sub.add_parser("promote", help="Pre-launch promote a package")
    promote.add_argument("slug")

    args = parser.parse_args()
    engine = SEOEngine()

    if args.command == "report":
        result = engine.get_seo_report()
    elif args.command == "scan":
        result = engine.scan_and_optimize()
    elif args.command == "optimize":
        landing_pad = REPO_ROOT / "publish" / "landing-pad"
        pkg_dir = landing_pad / args.slug
        if not pkg_dir.exists():
            result = {"error": f"Package not found: {args.slug}"}
        else:
            result = engine.optimize_package(pkg_dir, args.title, args.type)
    elif args.command == "promote":
        result = engine.promote(args.slug)

    if args.json:
        print(json.dumps(result, indent=2, default=str))
    else:
        if isinstance(result, dict):
            if "total_optimized" in result:
                print(f"🔍 GGB SEO Engine — Report")
                print(f"   Optimized: {result['total_optimized']}")
                print(f"   Promoted: {result['total_promoted']}")
                print(f"   Avg SEO Score: {result['average_seo_score']}/100")
                print(f"   Impressions (30d): {result['impressions_30d']}")
                print(f"   Clicks (30d): {result['clicks_30d']}")
                print(f"\n   Top Packages:")
                for p in result.get("top_packages", [])[:5]:
                    print(f"     {p['title'][:45]:45} | {p['type']:>12} | Score: {p['score']}/100")
            elif "optimized" in result:
                print(f"🔍 SEO Engine — Scanned {result['optimized']} packages")
                for r in result.get("results", [])[:5]:
                    print(f"   {r['title'][:45]:45} | Score: {r['seo_score']}/100 | Promoted: {', '.join(r.get('promoted_channels', []))}")
            elif "seo_score" in result:
                print(f"🔍 {result['title']}")
                print(f"   SEO Score: {result['seo_score']}/100")
                print(f"   Promoted: {', '.join(result.get('promoted_channels', []))}")
                print(f"   Tracked: {result['tracked']}")
            elif "promotions" in result:
                print(f"📢 Pre-Launch Promotion: {result['title']}")
                for ch, p in result.get("promotions", {}).items():
                    print(f"   {ch}: {p.get('type', 'teaser')} — {p.get('schedule', '')}")
            else:
                for k, v in result.items():
                    print(f"{k}: {v}")
        else:
            print(result)

    return 0

if __name__ == "__main__":
    sys.exit(cli())
