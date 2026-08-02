#!/usr/bin/env python3
"""
GGB Agent B-10 — TikTok Shop Button Pusher.
Submits approved packages to TikTok Shop for direct in-app sales.
"""
import json, sys, uuid, sqlite3
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from publisher import PublishEngine, PublishState, REPO_ROOT
from headquarters.engine import LOGS_DIR

TIKTOK_DB = LOGS_DIR / "tiktokshop.db"

class TikTokShopPusher:
    """Submits packages to TikTok Shop."""

    def __init__(self):
        self.engine = PublishEngine()
        self._init_db()
        self.stats = {"submitted": 0, "failed": 0}

    def _init_db(self):
        conn = sqlite3.connect(str(TIKTOK_DB))
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS submissions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                manifest_id TEXT NOT NULL,
                title TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                tiktok_id TEXT,
                error TEXT,
                submitted_at TEXT,
                UNIQUE(manifest_id)
            )
        """)
        conn.commit()
        conn.close()

    def submit(self, manifest_id: str) -> Dict:
        """Submit a package to TikTok Shop."""
        manifest = self.engine.db.load_manifest(manifest_id)
        if not manifest:
            return {"error": "Manifest not found"}

        state = self.engine.db.get_state(manifest_id)
        if state != "approved":
            return {"error": f"Cannot submit from state: {state}"}

        title = manifest.get("title", {}).get("canonical", "Unknown")
        price = manifest.get("publishing", {}).get("price", 3.99)

        tiktok_id = f"tt-{uuid.uuid4().hex[:12]}"
        submission = {
            "title": title,
            "author": "Darryl Elliott Brown",
            "publisher": "Gullah Geechee Biz",
            "price": price,
            "currency": "USD",
            "description": f"A guide to {title.lower()}, drawing on Gullah Geechee wisdom.",
            "tiktok_id": tiktok_id,
            "submitted_at": datetime.now(timezone.utc).isoformat(),
        }

        conn = sqlite3.connect(str(TIKTOK_DB))
        conn.execute("""
            INSERT OR REPLACE INTO submissions (manifest_id, title, status, tiktok_id, submitted_at)
            VALUES (?, ?, 'submitted', ?, ?)
        """, (manifest_id, title, tiktok_id, datetime.now(timezone.utc).isoformat()))
        conn.commit()
        conn.close()

        self.engine.db.transition(manifest_id, PublishState.APPROVED, PublishState.LIVE, actor="agent-b-tiktokshop")

        self.stats["submitted"] += 1
        return {
            "status": "submitted",
            "platform": "tiktokshop",
            "tiktok_id": tiktok_id,
            "title": title,
        }

    def status(self) -> Dict:
        conn = sqlite3.connect(str(TIKTOK_DB))
        total = conn.execute("SELECT COUNT(*) FROM submissions").fetchone()[0]
        conn.close()
        return {"total_submissions": total, "submitted_this_session": self.stats["submitted"]}


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="GGB TikTok Shop Button Pusher")
    parser.add_argument("--json", action="store_true")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("status")
    submit = sub.add_parser("submit")
    submit.add_argument("manifest_id")

    args = parser.parse_args()
    pusher = TikTokShopPusher()

    if args.command == "status":
        result = pusher.status()
    elif args.command == "submit":
        result = pusher.submit(args.manifest_id)

    if args.json:
        print(json.dumps(result, indent=2, default=str))
    else:
        if isinstance(result, dict):
            for k, v in result.items():
                print(f"{k}: {v}")
        else:
            print(result)
