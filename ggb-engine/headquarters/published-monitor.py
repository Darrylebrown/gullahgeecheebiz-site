#!/usr/bin/env python3
"""
GGB Published Production Monitor — real-time view of published packages.
Shows what's been published, when, and on which platforms.
Wires into the dashboard and can send alerts.
"""
import json, sys, sqlite3
from pathlib import Path
from datetime import datetime, timezone, timedelta

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from publisher import REPO_ROOT
from headquarters.engine import LOGS_DIR

SCOREBOARD_DB = LOGS_DIR / "scoreboard.db"
PUBLISHER_DB = Path.home() / ".hermes" / "ggb-publish-default" / "publisher.db"

class PublishedMonitor:
    def __init__(self):
        self.stats = {"published_today": 0, "published_this_week": 0, "total_published": 0}

    def get_published(self, days: int = 7) -> list:
        """Get all published packages within the last N days."""
        if not SCOREBOARD_DB.exists():
            return []
        conn = sqlite3.connect(str(SCOREBOARD_DB))
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        rows = conn.execute(
            "SELECT title, slug, status, published_at, manifest_id FROM packages "
            "WHERE status='published' AND published_at > ? "
            "ORDER BY published_at DESC LIMIT 100",
            (cutoff,)
        ).fetchall()
        conn.close()
        return [{"title": r[0], "slug": r[1], "status": r[2], "published_at": r[3], "manifest_id": r[4]} for r in rows]

    def get_published_today(self) -> list:
        """Get packages published today."""
        return self.get_published(days=1)

    def get_published_this_week(self) -> list:
        """Get packages published this week."""
        return self.get_published(days=7)

    def get_published_by_platform(self) -> dict:
        """Get published packages grouped by platform/content type."""
        published = self.get_published(days=30)
        by_platform = {}
        for pkg in published:
            slug = pkg["slug"]
            # Infer platform from slug prefix
            platform = "unknown"
            for prefix in ["book", "audiobook", "ad", "commercial", "movie", "pin", "music", "magazine"]:
                if slug.startswith(prefix):
                    platform = prefix
                    break
            if platform == "unknown" and "encyclopedia" in slug:
                platform = "book"
            by_platform.setdefault(platform, []).append(pkg)
        return {k: len(v) for k, v in by_platform.items()}

    def get_production_history(self, days: int = 30) -> dict:
        """Get cumulative production history for a chart.
        Returns daily cumulative counts for the last N days."""
        if not SCOREBOARD_DB.exists():
            return {"labels": [], "cumulative": [], "daily": []}

        conn = sqlite3.connect(str(SCOREBOARD_DB))
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        rows = conn.execute(
            "SELECT published_at FROM packages WHERE status='published' AND published_at > ? ORDER BY published_at ASC",
            (cutoff,)
        ).fetchall()
        conn.close()

        # Build daily buckets
        today = datetime.now(timezone.utc).date()
        start = today - timedelta(days=days)
        daily_counts = {}
        for d in range(days + 1):
            day = start + timedelta(days=d)
            daily_counts[day.isoformat()] = 0

        for (published_at,) in rows:
            if published_at:
                pub_date = published_at[:10]
                if pub_date in daily_counts:
                    daily_counts[pub_date] += 1

        labels = sorted(daily_counts.keys())
        daily = [daily_counts[d] for d in labels]
        cumulative = []
        running = 0
        for c in daily:
            running += c
            cumulative.append(running)

        return {"labels": labels, "cumulative": cumulative, "daily": daily}

    def report(self) -> dict:
        """Full published production report."""
        today = self.get_published_today()
        week = self.get_published_this_week()
        by_platform = self.get_published_by_platform()
        return {
            "published_today": len(today),
            "published_this_week": len(week),
            "total_published": len(self.get_published(days=365)),
            "by_platform": by_platform,
            "recent": today[:10],
        }


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="GGB Published Production Monitor")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--days", type=int, default=7, help="Days to look back")
    sub = parser.add_subparsers(dest="command")
    sub.add_parser("report", help="Full published production report")
    sub.add_parser("today", help="Published today")
    sub.add_parser("week", help="Published this week")
    sub.add_parser("platforms", help="Published by platform")
    sub.add_parser("history", help="Production history (30-day chart data)")

    args = parser.parse_args()
    monitor = PublishedMonitor()

    if args.command == "report" or not args.command:
        result = monitor.report()
    elif args.command == "today":
        result = {"published_today": monitor.get_published_today()}
    elif args.command == "week":
        result = {"published_this_week": monitor.get_published_this_week()}
    elif args.command == "platforms":
        result = {"by_platform": monitor.get_published_by_platform()}
    elif args.command == "history":
        result = monitor.get_production_history(days=args.days)

    if args.json:
        print(json.dumps(result, indent=2, default=str))
    else:
        if isinstance(result, dict):
            if "published_today" in result:
                print(f"📊 GGB Published Production")
                print(f"   Today: {result['published_today']}")
                print(f"   This week: {result['published_this_week']}")
                print(f"   Total: {result['total_published']}")
                print(f"\n   By platform:")
                for p, c in sorted(result.get("by_platform", {}).items()):
                    print(f"     {p:>15}: {c}")
                print(f"\n   Recent:")
                for pkg in result.get("recent", [])[:5]:
                    print(f"     {pkg['title'][:50]:50} | {pkg['published_at'][:19]}")
            elif "published_today" in result:
                print(f"📅 Published Today: {len(result['published_today'])}")
                for pkg in result["published_today"][:10]:
                    print(f"  {pkg['title'][:50]:50} | {pkg['published_at'][:19]}")
            elif "published_this_week" in result:
                print(f"📅 Published This Week: {len(result['published_this_week'])}")
                for pkg in result["published_this_week"][:10]:
                    print(f"  {pkg['title'][:50]:50} | {pkg['published_at'][:19]}")
            elif "by_platform" in result:
                print(f"📊 Published by Platform")
                for p, c in sorted(result["by_platform"].items()):
                    print(f"  {p:>15}: {c}")
        else:
            print(result)
