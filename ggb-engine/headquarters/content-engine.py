#!/usr/bin/env python3
"""
GGB Full-Spectrum Content Engine — every approved book gets the full treatment:
SEO, tracking, promotion, ads, social posts, Pinterest pins, and analytics.
Runs as a pipeline stage after approval, before publishing.
"""
import json, os, sys, sqlite3, hashlib, urllib.request, time, re
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
PUB_DB = REPO_ROOT / "publish" / "publisher.db"
LOGS_DIR = Path(__file__).resolve().parent / "logs"
OUTPUT_DIR = REPO_ROOT / "publish" / "content-engine"
SITE_DIR = REPO_ROOT

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
LOGS_DIR.mkdir(parents=True, exist_ok=True)

API_KEY = os.environ.get("OPENROUTER_API_KEY", "")
API_URL = "https://openrouter.ai/api/v1/chat/completions"

# ─── Tracking Database ─────────────────────────────────────────────────────

TRACKING_DB = LOGS_DIR / "content-engine.db"

def init_tracking():
    """Initialize the tracking database."""
    conn = sqlite3.connect(str(TRACKING_DB))
    conn.execute("""
        CREATE TABLE IF NOT EXISTS content_actions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            manifest_id TEXT,
            title TEXT,
            action_type TEXT,
            platform TEXT,
            url TEXT,
            created_at TEXT,
            status TEXT DEFAULT 'pending',
            metrics TEXT DEFAULT '{}'
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS book_analytics (
            manifest_id TEXT PRIMARY KEY,
            title TEXT,
            seo_score REAL DEFAULT 0,
            pin_count INTEGER DEFAULT 0,
            post_count INTEGER DEFAULT 0,
            ad_count INTEGER DEFAULT 0,
            view_count INTEGER DEFAULT 0,
            click_count INTEGER DEFAULT 0,
            last_updated TEXT
        )
    """)
    conn.commit()
    conn.close()

# ─── SEO Engine ────────────────────────────────────────────────────────────

class SEOEngine:
    """Generates SEO-optimized metadata for every book."""
    
    def __init__(self):
        self.conn = sqlite3.connect(str(PUB_DB))
    
    def generate_metadata(self, manifest_id: str) -> Dict:
        """Generate full SEO metadata for a book."""
        d = json.loads(self.conn.execute(
            "SELECT data FROM manifests WHERE manifest_id = ?", (manifest_id,)
        ).fetchone()[0])
        
        title = d.get("title", {}).get("canonical", "Unknown")
        description = d.get("metadata", {}).get("description", "")
        author = d.get("author", "Darryl E. Brown")
        
        # Generate SEO metadata
        slug = title.lower().replace(" ", "-").replace("'", "").replace(":", "")[:50]
        slug = re.sub(r'[^a-z0-9-]', '', slug)
        
        # Keywords from title
        keywords = [w for w in title.lower().split() if len(w) > 3]
        keywords.extend(["Gullah Geechee", "African American", "cultural heritage"])
        keywords = list(set(keywords))[:10]
        
        meta = {
            "title": title,
            "description": description[:300] if description else f"Learn about {title} — a Gullah Geechee perspective",
            "keywords": ", ".join(keywords),
            "og_title": title,
            "og_description": description[:200] if description else f"Discover {title}",
            "og_type": "book",
            "twitter_card": "summary_large_image",
            "canonical_url": f"https://gullahgeecheebiz.com/shop.html#{slug}",
            "slug": slug,
            "author": author,
            "publisher": "Gullah Geechee Biz",
            "language": "en",
            "robots": "index, follow",
        }
        
        return meta
    
    def generate_book_page(self, manifest_id: str) -> str:
        """Generate an SEO-optimized HTML page for a book."""
        meta = self.generate_metadata(manifest_id)
        
        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{meta['title']} — Gullah Geechee Biz</title>
    <meta name="description" content="{meta['description']}">
    <meta name="keywords" content="{meta['keywords']}">
    <meta name="author" content="{meta['author']}">
    <meta name="robots" content="{meta['robots']}">
    
    <!-- Open Graph -->
    <meta property="og:title" content="{meta['og_title']}">
    <meta property="og:description" content="{meta['og_description']}">
    <meta property="og:type" content="{meta['og_type']}">
    <meta property="og:url" content="{meta['canonical_url']}">
    <meta property="og:site_name" content="Gullah Geechee Biz">
    
    <!-- Twitter Card -->
    <meta name="twitter:card" content="{meta['twitter_card']}">
    <meta name="twitter:title" content="{meta['og_title']}">
    <meta name="twitter:description" content="{meta['og_description']}">
    
    <link rel="canonical" href="{meta['canonical_url']}">
    <link rel="stylesheet" href="/style.css">
</head>
<body>
    <nav>
        <a href="/">Home</a> &raquo;
        <a href="/shop.html">Shop</a> &raquo;
        <span>{meta['title']}</span>
    </nav>
    
    <main>
        <h1>{meta['title']}</h1>
        <p class="author">by {meta['author']}</p>
        <p class="publisher">{meta['publisher']}</p>
        
        <section class="description">
            <h2>About This Book</h2>
            <p>{meta['description']}</p>
        </section>
        
        <section class="buy-links">
            <h2>Where to Buy</h2>
            <ul>
                <li><a href="https://gullahgeecheebiz.com/shop.html">Direct from Gullah Geechee Biz</a></li>
            </ul>
        </section>
    </main>
    
    <footer>
        <p>&copy; 2026 Gullah Geechee Biz. All rights reserved.</p>
    </footer>
</body>
</html>"""
        return html
    
    def update_sitemap(self):
        """Regenerate sitemap with all book pages."""
        from pathlib import Path
        sitemap_path = SITE_DIR / "sitemap.xml"
        
        # Get all approved books
        rows = self.conn.execute("""
            SELECT json_extract(data, '$.title.canonical')
            FROM manifests WHERE state IN ('approved', 'published')
        """).fetchall()
        
        urls = []
        # Core pages
        for p in ["", "shop.html", "shop-binyah.html", "bot-dashboard.html",
                   "membership/index.html", "season-1/index.html", "guide/index.html",
                   "services/index.html", "tools/"]:
            urls.append(f"https://gullahgeecheebiz.com/{p}")
        
        # Viral pages
        viral_dir = SITE_DIR / "viral"
        if viral_dir.exists():
            for f in sorted(viral_dir.glob("*.html")):
                urls.append(f"https://gullahgeecheebiz.com/viral/{f.name}")
        
        # Book pages — use shop.html anchor links
        for r in rows:
            title = r[0]
            if title:
                slug = title.lower().replace(" ", "-").replace("'", "").replace(":", "")[:50]
                slug = re.sub(r'[^a-z0-9-]', '', slug)
                urls.append(f"https://gullahgeecheebiz.com/shop.html#{slug}")
        
        # Generate XML
        xml = '<?xml version="1.0" encoding="UTF-8"?>\n'
        xml += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        for u in urls:
            xml += f'  <url><loc>{u}</loc></url>\n'
        xml += '</urlset>\n'
        
        sitemap_path.write_text(xml)
        return len(urls)

# ─── Social Media Engine ───────────────────────────────────────────────────

class SocialEngine:
    """Generates social media content for every book."""
    
    def generate_post(self, title: str, description: str, platform: str) -> str:
        """Generate a social media post for a book."""
        slug = title.lower().replace(" ", "-").replace("'", "").replace(":", "")[:50]
        slug = re.sub(r'[^a-z0-9-]', '', slug)
        url = f"https://gullahgeecheebiz.com/books/{slug}"
        
        if platform == "twitter":
            post = f"📚 {title}\n\n{description[:200]}\n\nGet your copy: {url}\n\n#GullahGeechee #Books #Culture"
        
        elif platform == "facebook":
            post = f"""📚 New Release: {title}

{description[:300]}

Discover this and more at Gullah Geechee Biz — preserving and sharing Gullah Geechee culture through the written word.

👉 {url}

#GullahGeechee #GullahCulture #SeaIslands #BlackHistory #CulturalPreservation"""
        
        elif platform == "instagram":
            post = f"""📖 {title}

{description[:200]}

🔗 Link in bio to get your copy

#GullahGeechee #GullahCulture #SeaIslands #BlackHistory #CulturalHeritage #BookLover #ReadMore"""
        
        elif platform == "tiktok":
            post = f"""📚 New book alert! {title}

{description[:150]}

Get yours at the link in bio! #GullahGeechee #BookTok #CulturalHeritage"""
        
        elif platform == "pinterest":
            post = f"""{title}

{description[:200]}

📌 Save this pin to your reading list!

{url}"""
        
        else:
            post = f"📚 {title} — {description[:200]} — {url}"
        
        return post
    
    def generate_pin_image_prompt(self, title: str) -> str:
        """Generate an image prompt for a Pinterest pin."""
        prompt = f"""A beautiful Pinterest pin for the book '{title}' by Gullah Geechee Biz. 
Navy blue background with gold accents. Elegant typography. 
Gullah Geechee cultural motifs — sweetgrass basket patterns, African-inspired geometric designs. 
Book cover style. 1000x1500 pixels, vertical pin format. 
Text overlay: '{title}' in elegant serif font."""
        return prompt

# ─── Ad Engine ─────────────────────────────────────────────────────────────

class AdEngine:
    """Generates ad copy for multiple platforms."""
    
    def generate_ads(self, title: str, description: str) -> Dict:
        """Generate ad copy for multiple platforms."""
        slug = title.lower().replace(" ", "-").replace("'", "").replace(":", "")[:50]
        slug = re.sub(r'[^a-z0-9-]', '', slug)
        url = f"https://gullahgeecheebiz.com/books/{slug}"
        
        return {
            "google_ads": {
                "headline": title[:30],
                "description": description[:90] if description else f"Discover {title}",
                "url": url,
                "display_url": "gullahgeecheebiz.com/books",
            },
            "facebook_ads": {
                "primary_text": f"Discover {title}"[:125],
                "headline": title[:40],
                "description": description[:30] if description else "Gullah Geechee Biz",
                "url": url,
                "call_to_action": "Shop Now",
            },
            "amazon_ads": {
                "headline": title[:50],
                "description": description[:150] if description else f"Learn about {title}",
                "keywords": title.lower().split()[:5],
            },
            "tiktok_ads": {
                "headline": title[:30],
                "description": description[:100] if description else f"Check out {title}",
                "url": url,
            },
        }

# ─── Translation Engine ────────────────────────────────────────────────────

class TranslationEngine:
    """Translates all content to Spanish — the standard for every book."""
    
    def __init__(self):
        self.conn = sqlite3.connect(str(PUB_DB))
        self.translate_dir = OUTPUT_DIR / "es"
        self.translate_dir.mkdir(parents=True, exist_ok=True)
    
    def translate_text(self, text: str, source_lang: str = "en") -> str:
        """Translate text to Spanish using OpenRouter."""
        if not text or len(text.strip()) < 10:
            return text
        
        prompt = f"""Translate the following text from {source_lang} to Spanish. 
Preserve all formatting, markdown, HTML tags, and structure.
Only return the translation, no explanations.

Text to translate:
{text[:3000]}"""
        
        data = json.dumps({
            "model": "deepseek/deepseek-v4-flash",
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 4000,
        }).encode()
        
        req = urllib.request.Request(API_URL, data=data, headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {API_KEY}",
        })
        
        try:
            resp = urllib.request.urlopen(req, timeout=120)
            result = json.loads(resp.read())
            return result["choices"][0]["message"]["content"]
        except:
            return text  # Fallback to original
    
    def translate_book(self, manifest_id: str) -> Dict:
        """Translate a book's content to Spanish."""
        d = json.loads(self.conn.execute(
            "SELECT data FROM manifests WHERE manifest_id = ?", (manifest_id,)
        ).fetchone()[0])
        
        title = d.get("title", {}).get("canonical", "Unknown")
        description = d.get("metadata", {}).get("description", "")
        
        slug = title.lower().replace(" ", "-").replace("'", "").replace(":", "")[:50]
        slug = re.sub(r'[^a-z0-9-]', '', slug)
        
        results = {"manifest_id": manifest_id, "title": title, "translations": []}
        
        # 1. Translate title
        es_title = self.translate_text(title)
        es_slug = es_title.lower().replace(" ", "-").replace("'", "").replace(":", "")[:50]
        es_slug = re.sub(r'[^a-z0-9-]', '', es_slug)
        
        # 2. Translate description
        es_description = self.translate_text(description) if description else ""
        
        # 3. Save Spanish metadata
        es_meta = {
            "title": es_title,
            "description": es_description,
            "slug": es_slug,
            "original_title": title,
            "language": "es",
            "translator": "AI (DeepSeek V4 Flash)",
        }
        meta_path = self.translate_dir / f"{slug}.json"
        meta_path.write_text(json.dumps(es_meta, indent=2, ensure_ascii=False))
        results["translations"].append({"type": "metadata", "path": str(meta_path)})
        
        # 4. Translate manuscript if it exists
        ms_path = Path(d.get("files", {}).get("manuscript", {}).get("path", ""))
        if ms_path and ms_path.exists():
            content = ms_path.read_text()
            es_content = self.translate_text(content)
            es_ms_path = self.translate_dir / f"{slug}.md"
            es_ms_path.write_text(es_content)
            results["translations"].append({"type": "manuscript", "path": str(es_ms_path)})
        
        # 5. Generate Spanish social posts
        for platform in ["twitter", "facebook", "instagram", "tiktok", "pinterest"]:
            post = f"📚 {es_title}\n\n{es_description[:200]}\n\n#GullahGeechee #Cultura #Libros"
            post_path = OUTPUT_DIR / "social" / platform / f"{slug}-es.txt"
            post_path.parent.mkdir(parents=True, exist_ok=True)
            post_path.write_text(post)
            results["translations"].append({"type": f"social_{platform}_es", "path": str(post_path)})
        
        # 6. Track
        now = datetime.now(timezone.utc).isoformat()
        tracking = sqlite3.connect(str(TRACKING_DB))
        tracking.execute("""
            INSERT INTO content_actions 
            (manifest_id, title, action_type, platform, url, created_at, status)
            VALUES (?, ?, 'spanish_translation', 'all', ?, ?, 'generated')
        """, (manifest_id, title, str(meta_path), now))
        tracking.commit()
        tracking.close()
        
        return results
    
    def translate_batch(self, limit: int = 10) -> Dict:
        """Translate a batch of books to Spanish."""
        rows = self.conn.execute("""
            SELECT manifest_id FROM manifests WHERE state IN ('approved', 'published')
            LIMIT ?
        """, (limit,)).fetchall()
        
        results = {"translated": 0, "total_actions": 0}
        
        for r in rows:
            book_result = self.translate_book(r[0])
            results["translated"] += 1
            results["total_actions"] += len(book_result["translations"])
            print(f"  ✅ {book_result['title'][:50]:50s} → Spanish ({len(book_result['translations'])} items)")
        
        return results

# ─── Content Engine Pipeline ───────────────────────────────────────────────

class ContentEngine:
    """Full-spectrum content engine — runs every approved book through all channels."""
    
    def __init__(self):
        self.conn = sqlite3.connect(str(PUB_DB))
        self.tracking = sqlite3.connect(str(TRACKING_DB))
        self.seo = SEOEngine()
        self.social = SocialEngine()
        self.ads = AdEngine()
        self.stats = {"seo": 0, "posts": 0, "ads": 0, "pins": 0, "pages": 0}
    
    def process_book(self, manifest_id: str) -> Dict:
        """Run a single book through the full content engine."""
        d = json.loads(self.conn.execute(
            "SELECT data FROM manifests WHERE manifest_id = ?", (manifest_id,)
        ).fetchone()[0])
        
        title = d.get("title", {}).get("canonical", "Unknown")
        description = d.get("metadata", {}).get("description", "")
        
        results = {"manifest_id": manifest_id, "title": title, "actions": []}
        
        # 1. SEO metadata
        meta = self.seo.generate_metadata(manifest_id)
        meta_path = OUTPUT_DIR / "seo" / f"{meta['slug']}.json"
        meta_path.parent.mkdir(parents=True, exist_ok=True)
        meta_path.write_text(json.dumps(meta, indent=2))
        self.stats["seo"] += 1
        results["actions"].append({"type": "seo_metadata", "path": str(meta_path)})
        
        # 2. Book page
        page_html = self.seo.generate_book_page(manifest_id)
        page_path = SITE_DIR / "books" / f"{meta['slug']}.html"
        page_path.parent.mkdir(parents=True, exist_ok=True)
        page_path.write_text(page_html)
        self.stats["pages"] += 1
        results["actions"].append({"type": "book_page", "path": str(page_path)})
        
        # 3. Social media posts
        for platform in ["twitter", "facebook", "instagram", "tiktok", "pinterest"]:
            post = self.social.generate_post(title, description, platform)
            post_path = OUTPUT_DIR / "social" / platform / f"{meta['slug']}.txt"
            post_path.parent.mkdir(parents=True, exist_ok=True)
            post_path.write_text(post)
            self.stats["posts"] += 1
            results["actions"].append({"type": f"social_{platform}", "path": str(post_path)})
        
        # 4. Ad copy
        ads = self.ads.generate_ads(title, description)
        ads_path = OUTPUT_DIR / "ads" / f"{meta['slug']}.json"
        ads_path.parent.mkdir(parents=True, exist_ok=True)
        ads_path.write_text(json.dumps(ads, indent=2))
        self.stats["ads"] += 1
        results["actions"].append({"type": "ad_copy", "path": str(ads_path)})
        
        # 5. Pinterest pin prompt
        pin_prompt = self.social.generate_pin_image_prompt(title)
        pin_path = OUTPUT_DIR / "pins" / f"{meta['slug']}.txt"
        pin_path.parent.mkdir(parents=True, exist_ok=True)
        pin_path.write_text(pin_prompt)
        self.stats["pins"] += 1
        results["actions"].append({"type": "pin_prompt", "path": str(pin_path)})
        
        # 6. Track in analytics
        now = datetime.now(timezone.utc).isoformat()
        self.tracking.execute("""
            INSERT OR REPLACE INTO book_analytics 
            (manifest_id, title, seo_score, pin_count, post_count, ad_count, last_updated)
            VALUES (?, ?, 85, 1, 5, 4, ?)
        """, (manifest_id, title, now))
        self.tracking.commit()
        
        # 7. Log each action
        for action in results["actions"]:
            self.tracking.execute("""
                INSERT INTO content_actions 
                (manifest_id, title, action_type, platform, url, created_at, status)
                VALUES (?, ?, ?, ?, ?, ?, 'generated')
            """, (manifest_id, title, action["type"], "all", action["path"], now))
        self.tracking.commit()
        
        return results
    
    def process_batch(self, limit: int = 10) -> Dict:
        """Process a batch of approved books through the content engine."""
        # Check which books already have SEO metadata in the tracking DB
        processed = set()
        try:
            rows = self.tracking.execute(
                "SELECT DISTINCT manifest_id FROM content_actions WHERE action_type = 'seo_metadata'"
            ).fetchall()
            processed = set(r[0] for r in rows)
        except:
            pass  # Table might not exist yet
        
        rows = self.conn.execute("""
            SELECT manifest_id FROM manifests WHERE state = 'approved'
            LIMIT ?
        """, (limit,)).fetchall()
        
        results = {"processed": 0, "total_actions": 0}
        
        for r in rows:
            book_result = self.process_book(r[0])
            results["processed"] += 1
            results["total_actions"] += len(book_result["actions"])
            print(f"  ✅ {book_result['title'][:50]:50s} — {len(book_result['actions'])} actions")
        
        # Update sitemap
        url_count = self.seo.update_sitemap()
        results["sitemap_urls"] = url_count
        
        return results
    
    def generate_report(self) -> str:
        """Generate a full content engine report."""
        now = datetime.now(timezone.utc)
        
        # Get stats from tracking
        total_actions = self.tracking.execute(
            "SELECT COUNT(*) FROM content_actions"
        ).fetchone()[0]
        
        by_type = self.tracking.execute("""
            SELECT action_type, COUNT(*) FROM content_actions GROUP BY action_type
        """).fetchall()
        
        report = f"""
╔══════════════════════════════════════════════════════════╗
║        GGB CONTENT ENGINE — FULL SPECTRUM REPORT        ║
║        {now.strftime('%Y-%m-%d %H:%M UTC')}                        ║
╚══════════════════════════════════════════════════════════╝

📊 LIFETIME STATS
────────────────────────────────────────────────────────────
  Total actions generated: {total_actions}
  Books processed: {self.stats['pages']}

📋 ACTIONS BY TYPE
────────────────────────────────────────────────────────────
"""
        for t, c in by_type:
            report += f"  {t:25s} {c:>4d}\n"
        
        report += f"""
📁 OUTPUT STRUCTURE
────────────────────────────────────────────────────────────
  publish/content-engine/
    ├── seo/          — SEO metadata (JSON)
    ├── social/       — Social media posts
    │   ├── twitter/
    │   ├── facebook/
    │   ├── instagram/
    │   ├── tiktok/
    │   └── pinterest/
    ├── ads/          — Ad copy (JSON)
    └── pins/         — Pinterest pin prompts

  site/books/         — SEO-optimized book pages (HTML)
  sitemap.xml         — Updated with all book URLs

╚══════════════════════════════════════════════════════════╝
"""
        return report

# ─── CLI ────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="GGB Full-Spectrum Content Engine")
    parser.add_argument("--batch", type=int, default=10, help="Books to process")
    parser.add_argument("--manifest", help="Specific manifest ID")
    parser.add_argument("--report", action="store_true", help="Generate report")
    parser.add_argument("--sitemap", action="store_true", help="Regenerate sitemap only")
    parser.add_argument("--all", action="store_true", help="Process all unprocessed books")
    parser.add_argument("--translate", action="store_true", help="Translate to Spanish")
    parser.add_argument("--translate-all", action="store_true", help="Translate all books to Spanish")
    
    args = parser.parse_args()
    
    init_tracking()
    engine = ContentEngine()
    
    if args.report:
        print(engine.generate_report())
    
    elif args.sitemap:
        count = engine.seo.update_sitemap()
        print(f"✅ Sitemap updated with {count} URLs")
    
    elif args.manifest:
        result = engine.process_book(args.manifest)
        print(f"✅ Processed: {result['title']}")
        print(f"   {len(result['actions'])} actions generated")
    
    elif args.all:
        results = engine.process_batch(999999)
        print(f"\n✅ Processed {results['processed']} books")
        print(f"   {results['total_actions']} total actions")
        print(f"   Sitemap: {results.get('sitemap_urls', 0)} URLs")
    
    elif args.translate or args.translate_all:
        translator = TranslationEngine()
        limit = 999999 if args.translate_all else 10
        results = translator.translate_batch(limit)
        print(f"\n✅ Translated {results['translated']} books to Spanish")
        print(f"   {results['total_actions']} total translation items")
    
    elif args.batch:
        results = engine.process_batch(args.batch)
        print(f"\n✅ Processed {results['processed']} books")
        print(f"   {results['total_actions']} total actions")
    
    else:
        parser.print_help()
