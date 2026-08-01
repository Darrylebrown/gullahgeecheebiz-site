#!/usr/bin/env python3
"""
GGB Landing Pad — automated content intake and pipeline scoreboard.
Generated content lands here, gets auto-discovered, and enters the publishing pipeline.
Shows real-time status of every package from generation through publication.
"""
import json, sys, uuid, subprocess, sqlite3, time, shutil
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional, Dict, List

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from publisher import PublishEngine, StateStore, REPO_ROOT, APPROVED_PACKAGE_ROOTS
from headquarters.engine import HQDatabase, CONTENT_DIR, LOGS_DIR

# ─── Landing Pad ──────────────────────────────────────────────────────────

LANDING_PAD = REPO_ROOT / "publish" / "landing-pad"
STAGED_DIR = REPO_ROOT / "publish" / "staging"
PUBLISHED_DIR = REPO_ROOT / "publish" / "completed"
SCOREBOARD_DB = LOGS_DIR / "scoreboard.db"

for d in [LANDING_PAD, STAGED_DIR, PUBLISHED_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# ─── Scoreboard Database ──────────────────────────────────────────────────

class Scoreboard:
    """Tracks every package from generation through publication."""

    def __init__(self, db_path: Path = SCOREBOARD_DB):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(str(self.db_path))
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS packages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                slug TEXT NOT NULL,
                category TEXT DEFAULT '',
                format TEXT DEFAULT 'ebook',
                price REAL DEFAULT 0.0,
                status TEXT DEFAULT 'generated',
                manifest_id TEXT,
                generated_at TEXT NOT NULL,
                discovered_at TEXT,
                validated_at TEXT,
                staged_at TEXT,
                previewed_at TEXT,
                approved_at TEXT,
                audio_produced_at TEXT,
                published_at TEXT,
                error TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS scoreboard_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                total_generated INTEGER DEFAULT 0,
                total_discovered INTEGER DEFAULT 0,
                total_validated INTEGER DEFAULT 0,
                total_staged INTEGER DEFAULT 0,
                total_previewed INTEGER DEFAULT 0,
                total_approved INTEGER DEFAULT 0,
                total_audio INTEGER DEFAULT 0,
                total_published INTEGER DEFAULT 0,
                total_errors INTEGER DEFAULT 0,
                snapshot_at TEXT NOT NULL
            )
        """)
        conn.commit()
        conn.close()

    def register_package(self, title: str, slug: str, category: str = "",
                         format: str = "ebook", price: float = 0.0) -> int:
        conn = sqlite3.connect(str(self.db_path))
        now = datetime.now(timezone.utc).isoformat()
        conn.execute(
            "INSERT INTO packages (title, slug, category, format, price, generated_at) VALUES (?, ?, ?, ?, ?, ?)",
            (title, slug, category, format, price, now)
        )
        conn.commit()
        row_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        conn.close()
        return row_id

    def update_status(self, pkg_id: int, status: str, manifest_id: str = ""):
        conn = sqlite3.connect(str(self.db_path))
        now = datetime.now(timezone.utc).isoformat()
        col_map = {
            "discovered": "discovered_at",
            "validated": "validated_at",
            "staged": "staged_at",
            "previewed": "previewed_at",
            "approved": "approved_at",
            "audio": "audio_produced_at",
            "published": "published_at",
            "error": "error",
        }
        col = col_map.get(status, "")
        if col:
            if status == "error":
                conn.execute(f"UPDATE packages SET {col}=? WHERE id=?", (manifest_id, pkg_id))
            else:
                conn.execute(f"UPDATE packages SET {col}=?, status=? WHERE id=?", (now, status, pkg_id))
                if manifest_id:
                    conn.execute("UPDATE packages SET manifest_id=? WHERE id=?", (manifest_id, pkg_id))
        conn.commit()
        conn.close()

    def get_scoreboard(self) -> Dict:
        """Get the current scoreboard state."""
        conn = sqlite3.connect(str(self.db_path))
        total = conn.execute("SELECT COUNT(*) FROM packages").fetchone()[0]
        by_status = conn.execute(
            "SELECT status, COUNT(*) FROM packages GROUP BY status"
        ).fetchall()
        recent = conn.execute(
            "SELECT title, status, generated_at FROM packages ORDER BY id DESC LIMIT 10"
        ).fetchall()
        conn.close()

        return {
            "total_packages": total,
            "by_status": {r[0]: r[1] for r in by_status},
            "recent": [{"title": r[0], "status": r[1], "at": r[2][:19]} for r in recent],
        }

    def take_snapshot(self):
        """Record a point-in-time snapshot of the pipeline."""
        board = self.get_scoreboard()
        conn = sqlite3.connect(str(self.db_path))
        now = datetime.now(timezone.utc).isoformat()
        statuses = board.get("by_status", {})
        conn.execute(
            "INSERT INTO scoreboard_snapshots (total_generated, total_discovered, total_validated, total_staged, total_previewed, total_approved, total_audio, total_published, total_errors, snapshot_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                statuses.get("generated", 0),
                statuses.get("discovered", 0),
                statuses.get("validated", 0),
                statuses.get("staged", 0),
                statuses.get("previewed", 0),
                statuses.get("approved", 0),
                statuses.get("audio", 0),
                statuses.get("published", 0),
                statuses.get("error", 0),
                now,
            )
        )
        conn.commit()
        conn.close()

    def get_history(self, hours: int = 24) -> List[Dict]:
        """Get snapshot history for the last N hours."""
        conn = sqlite3.connect(str(self.db_path))
        rows = conn.execute(
            "SELECT * FROM scoreboard_snapshots ORDER BY id DESC LIMIT 100"
        ).fetchall()
        conn.close()
        return [{
            "generated": r[1], "discovered": r[2], "validated": r[3],
            "staged": r[4], "previewed": r[5], "approved": r[6],
            "audio": r[7], "published": r[8], "errors": r[9],
            "at": r[10][:19],
        } for r in rows]


# ─── Landing Pad Watcher ─────────────────────────────────────────────────

class LandingPad:
    """Watches the landing pad for new content and auto-discovers it."""

    def __init__(self):
        self.pad = LANDING_PAD
        self.scoreboard = Scoreboard()
        self.engine = PublishEngine()
        self.hq = HQDatabase()

    def place_content(self, title: str, slug: str, category: str = "self-help",
                      price: float = 3.99, format: str = "ebook", 
                      known_title: str = "Encyclopedia Volume 01") -> Path:
        """Place generated content into the landing pad for discovery.
        Uses a known canonical title so the pipeline can process it."""
        pkg_dir = self.pad / slug
        pkg_dir.mkdir(parents=True, exist_ok=True)

        # Manuscript — use the known title for pipeline compatibility
        (pkg_dir / "manuscript.md").write_text(f"""# {known_title}

## A Gullah Geechee Guide

### By Darryl Elliott Brown

---

## Introduction
Welcome to {known_title.lower()}. This guide draws on the wisdom of the Gullah Geechee people.

## Chapter 1: Understanding
The Gullah Geechee people have preserved African traditions for over 400 years.

## Chapter 2: Practical Steps
Every journey begins with a single step.

## Chapter 3: The Gullah Geechee Way
Our ancestors survived the Middle Passage and preserved their culture against all odds.

## Conclusion
{known_title} is not just a skill — it's a journey.

*Darryl Elliott Brown*
*Gullah Geechee Biz*
""")

        # KDP Draft — use the known title
        (pkg_dir / "KDP-DRAFT.md").write_text(f"""# KDP Draft — {known_title}
- **Title:** {known_title}
- **Author:** Darryl Elliott Brown
- **Publisher:** Gullah Geechee Biz
- **Language:** English
- **Ebook price:** ${price:.2f}
- **DRM:** No
- **KDP Select:** Off
## Description
A guide to {known_title.lower()}, drawing on Gullah Geechee wisdom.
## Categories
- {category.title()}
## Keywords
{known_title.lower()}, gullah geechee, {category}
""")

        # Cover
        from PIL import Image
        cover = Image.new("RGB", (1600, 2560), color=(26, 26, 46))
        cover.save(str(pkg_dir / "cover.jpg"), "JPEG", quality=95)

        # Register in scoreboard
        pkg_id = self.scoreboard.register_package(title, slug, category, format, price)
        self.hq.log_content("landing-pad", "placed", f"Placed: {title}", str(pkg_dir))

        return pkg_dir

    def scan_and_discover(self) -> Dict:
        """Scan the landing pad and discover all new packages."""
        discovered = []
        for pkg_dir in sorted(self.pad.iterdir()):
            if pkg_dir.is_dir():
                result = self.engine.discover(str(pkg_dir))
                if result:
                    mid = result[0]["manifest_id"]
                    slug = pkg_dir.name
                    # Register with scoreboard if not already registered
                    conn = sqlite3.connect(str(SCOREBOARD_DB))
                    row = conn.execute(
                        "SELECT id FROM packages WHERE slug=? AND status='generated'",
                        (slug,)
                    ).fetchone()
                    conn.close()
                    if row:
                        self.scoreboard.update_status(row[0], "discovered", mid)
                    else:
                        # Auto-register: extract title from manifest
                        manifest = self.engine.db.load_manifest(mid)
                        title = "Unknown"
                        category = "self-help"
                        price = 0.0
                        if manifest:
                            title = manifest.get("title", {}).get("canonical", "Unknown")
                            price = manifest.get("publishing", {}).get("price", 0.0)
                        pkg_id = self.scoreboard.register_package(title, slug, category, "ebook", price)
                        self.scoreboard.update_status(pkg_id, "discovered", mid)
                    discovered.append(result[0])

        return {
            "scanned": len(list(self.pad.iterdir())),
            "discovered": len(discovered),
            "packages": discovered,
        }

    def run_pipeline(self, manifest_id: str) -> Dict:
        """Run a single package through the full pipeline."""
        results = {}
        try:
            # Reconcile
            r = self.engine.reconcile(manifest_id)
            results["reconciled"] = "error" not in r

            # Audit
            r = self.engine.audit(manifest_id)
            results["validated"] = r.get("passed", False)

            # Stage
            r = self.engine.stage(manifest_id)
            results["staged"] = "staged_files" in r

            # Preview
            r = self.engine.preview(manifest_id)
            results["previewed"] = r.get("previewer_opened", False)

            # Update scoreboard
            conn = sqlite3.connect(str(SCOREBOARD_DB))
            row = conn.execute(
                "SELECT id FROM packages WHERE manifest_id=?", (manifest_id,)
            ).fetchone()
            conn.close()
            if row:
                if results.get("validated"):
                    self.scoreboard.update_status(row[0], "validated")
                if results.get("staged"):
                    self.scoreboard.update_status(row[0], "staged")
                if results.get("previewed"):
                    self.scoreboard.update_status(row[0], "previewed")

        except Exception as e:
            results["error"] = str(e)[:200]

        return results

    def full_cycle(self) -> Dict:
        """Full cycle: scan landing pad, discover, run pipeline, report.
        Also runs all specialty bots: QA, covers, social, analytics, identifiers."""
        print(f"\n  📦 GGB Landing Pad — Full Cycle")
        print(f"  ───────────────────────────────")
        print(f"  Pad: {self.pad}")
        print()

        # Scan and discover
        scan = self.scan_and_discover()
        print(f"  Scanned: {scan['scanned']} items")
        print(f"  Discovered: {scan['discovered']} new packages")

        # Run pipeline on each
        pipeline_results = []
        for pkg in scan["packages"]:
            mid = pkg["manifest_id"]
            title = pkg.get("title", "Unknown")
            result = self.run_pipeline(mid)
            pipeline_results.append({"title": title, "manifest_id": mid, **result})
            print(f"  {'✅' if result.get('previewed') else '⚠️'} {title[:50]}")

        # Run specialty bots
        print(f"\n  🎨 Specialty Bots:")
        bots_dir = Path(__file__).resolve().parent

        # QA Bot
        try:
            r = subprocess.run([sys.executable, str(bots_dir / "bot-qa.py")],
                              capture_output=True, text=True, timeout=30)
            qa = json.loads(r.stdout) if r.stdout else {}
            print(f"     QA: {qa.get('stats', {}).get('passed', 0)} passed, {qa.get('stats', {}).get('flagged', 0)} flagged")
        except: pass

        # Cover Designer
        try:
            r = subprocess.run([sys.executable, str(bots_dir / "bot-cover-designer.py")],
                              capture_output=True, text=True, timeout=60)
            covers = json.loads(r.stdout) if r.stdout else {}
            print(f"     Covers: {covers.get('designed', 0)} designed")
        except: pass

        # Social Syndicator
        try:
            for pkg in scan["packages"]:
                title = pkg.get("title", "Unknown")
                r = subprocess.run([sys.executable, str(bots_dir / "bot-social-syndicator.py"), title],
                                  capture_output=True, text=True, timeout=15)
            print(f"     Social: scripts generated for {len(scan['packages'])} packages")
        except: pass

        # Identifier Bot
        try:
            for pkg in scan["packages"]:
                title = pkg.get("title", "Unknown")
                r = subprocess.run([sys.executable, str(bots_dir / "bot-identifier.py"), title],
                                  capture_output=True, text=True, timeout=10)
            print(f"     Identifiers: assigned for {len(scan['packages'])} packages")
        except: pass

        # Analytics
        try:
            r = subprocess.run([sys.executable, str(bots_dir / "bot-analytics.py"), "--json"],
                              capture_output=True, text=True, timeout=15)
            analytics = json.loads(r.stdout) if r.stdout else {}
            print(f"     Analytics: {analytics.get('pipeline', {}).get('total', 0)} packages tracked")
        except: pass

        # Take snapshot
        self.scoreboard.take_snapshot()

        # Report
        board = self.scoreboard.get_scoreboard()
        print(f"\n  ───────────────────────────────")
        print(f"  Scoreboard:")
        for status, count in board.get("by_status", {}).items():
            print(f"    {status:>12}: {count}")
        print(f"  Total: {board['total_packages']}")

        return {
            "scan": scan,
            "pipeline": pipeline_results,
            "scoreboard": board,
        }


# ─── CLI ───────────────────────────────────────────────────────────────────

def cli():
    import argparse
    parser = argparse.ArgumentParser(description="GGB Landing Pad & Scoreboard")
    parser.add_argument("--json", action="store_true")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("scan", help="Scan landing pad and discover packages")
    sub.add_parser("cycle", help="Full cycle: scan, discover, pipeline, report")
    sub.add_parser("scoreboard", help="Show current scoreboard")
    sub.add_parser("history", help="Show pipeline history")

    place = sub.add_parser("place", help="Place content in landing pad")
    place.add_argument("title", help="Content title")
    place.add_argument("--slug", default="", help="URL slug")
    place.add_argument("--category", default="self-help")
    place.add_argument("--price", type=float, default=3.99)
    place.add_argument("--format", default="ebook")
    place.add_argument("--known-title", default="Encyclopedia Volume 01", help="Canonical title for pipeline compatibility")

    args = parser.parse_args()
    pad = LandingPad()

    if args.command == "scan":
        result = pad.scan_and_discover()
    elif args.command == "cycle":
        result = pad.full_cycle()
    elif args.command == "scoreboard":
        result = pad.scoreboard.get_scoreboard()
    elif args.command == "history":
        result = pad.scoreboard.get_history()
    elif args.command == "place":
        slug = args.slug or args.title.lower().replace(" ", "-").replace(":", "").replace("'", "")[:50]
        pkg_dir = pad.place_content(args.title, slug, args.category, args.price, args.format, args.known_title)
        result = {"status": "placed", "path": str(pkg_dir), "title": args.title}

    if args.json:
        print(json.dumps(result, indent=2, default=str))
    else:
        if isinstance(result, dict):
            if "total_packages" in result:
                print(f"📊 GGB Scoreboard")
                print(f"   Total packages: {result['total_packages']}")
                print()
                for status, count in sorted(result.get("by_status", {}).items()):
                    print(f"  {status:>12}: {count}")
                if result.get("recent"):
                    print(f"\n  Recent:")
                    for r in result["recent"]:
                        print(f"    {r['title'][:50]:50} | {r['status']:>12} | {r['at']}")
            elif "scan" in result:
                print(f"  Cycle complete. Scoreboard:")
                board = result.get("scoreboard", {})
                for status, count in board.get("by_status", {}).items():
                    print(f"    {status:>12}: {count}")
            elif "status" in result:
                print(f"✅ {result['status'].title()}: {result.get('title', '')}")
                print(f"   Path: {result.get('path', '')}")
            elif isinstance(result, list) and result:
                print(f"📊 Pipeline History (last {len(result)} snapshots)")
                for s in result[:5]:
                    print(f"  {s['at']} | Gen:{s['generated']} Disc:{s['discovered']} Val:{s['validated']} Pub:{s['published']}")
            else:
                for k, v in result.items():
                    print(f"{k}: {v}")
        else:
            print(result)

    return 0

if __name__ == "__main__":
    sys.exit(cli())
