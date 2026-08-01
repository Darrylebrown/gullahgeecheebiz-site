#!/usr/bin/env python3
"""
GGB Analytics & Reporting Bot — tracks sales, traffic, conversions.
Feeds back into the system to prioritize what to publish next.
"""
import json, sys, sqlite3
from pathlib import Path
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from publisher import REPO_ROOT
from headquarters.engine import LOGS_DIR

ANALYTICS_DB = LOGS_DIR / "analytics.db"

class AnalyticsBot:
    def __init__(self):
        self._init_db()
        self.stats = {"reports": 0}

    def _init_db(self):
        conn = sqlite3.connect(str(ANALYTICS_DB))
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                report_type TEXT NOT NULL,
                data TEXT,
                generated_at TEXT NOT NULL
            )
        """)
        conn.commit()
        conn.close()

    def generate_report(self) -> dict:
        """Generate a pipeline analytics report."""
        # Pull from scoreboard
        scoreboard_db = LOGS_DIR / "scoreboard.db"
        pipeline_stats = {"total": 0, "by_status": {}}
        if scoreboard_db.exists():
            conn = sqlite3.connect(str(scoreboard_db))
            pipeline_stats["total"] = conn.execute("SELECT COUNT(*) FROM packages").fetchone()[0]
            rows = conn.execute("SELECT status, COUNT(*) FROM packages GROUP BY status").fetchall()
            pipeline_stats["by_status"] = {r[0]: r[1] for r in rows}
            conn.close()

        # Pull from neural monitor
        neural_db = LOGS_DIR / "neural-monitor.db"
        neural_stats = {"checks": 0, "fixes": 0, "incidents": 0}
        if neural_db.exists():
            conn = sqlite3.connect(str(neural_db))
            neural_stats["checks"] = conn.execute("SELECT COUNT(*) FROM checks").fetchone()[0]
            neural_stats["fixes"] = conn.execute("SELECT COUNT(*) FROM fixes").fetchone()[0]
            neural_stats["incidents"] = conn.execute("SELECT COUNT(*) FROM incidents WHERE resolved_at IS NULL").fetchone()[0]
            conn.close()

        # Pull from self-heal
        heal_db = LOGS_DIR / "self-heal.db"
        heal_stats = {"heals": 0}
        if heal_db.exists():
            conn = sqlite3.connect(str(heal_db))
            heal_stats["heals"] = conn.execute("SELECT COUNT(*) FROM heal_log WHERE fixed=1").fetchone()[0]
            conn.close()

        report = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "pipeline": pipeline_stats,
            "neural_monitor": neural_stats,
            "self_healing": heal_stats,
        }

        conn = sqlite3.connect(str(ANALYTICS_DB))
        conn.execute("INSERT INTO reports (report_type, data, generated_at) VALUES (?, ?, ?)",
                     ("pipeline", json.dumps(report), datetime.now(timezone.utc).isoformat()))
        conn.commit()
        conn.close()

        self.stats["reports"] += 1
        return report


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    bot = AnalyticsBot()
    result = bot.generate_report()
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"Pipeline: {result['pipeline']['total']} packages")
        for s, c in result['pipeline'].get('by_status', {}).items():
            print(f"  {s}: {c}")
        print(f"Neural: {result['neural_monitor']['checks']} checks, {result['neural_monitor']['fixes']} fixes")
        print(f"Heals: {result['self_healing']['heals']}")
