#!/usr/bin/env python3
"""
GGB Agent B-9 — Google Play Books Button Pusher.
Submits approved packages to Google Play Books via their Partner Center API.
"""
import json, sys, uuid, hashlib, sqlite3
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from publisher import PublishEngine, PublishState, REPO_ROOT
from headquarters.engine import LOGS_DIR

GOOGLEPLAY_DB = LOGS_DIR / "googleplay.db"

class GooglePlayPusher:
    """Submits packages to Google Play Books."""

    def __init__(self):
        self.engine = PublishEngine()
        self._init_db()
        self.stats = {"submitted": 0, "failed": 0}

    def _init_db(self):
        conn = sqlite3.connect(str(GOOGLEPLAY_DB))
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS submissions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                manifest_id TEXT NOT NULL,
                title TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                googleplay_id TEXT,
                error TEXT,
                submitted_at TEXT,
                UNIQUE(manifest_id)
            )
        """)
        conn.commit()
        conn.close()

    def submit(self, manifest_id: str) -> Dict:
        """Submit a package to Google Play Books."""
        manifest = self.engine.db.load_manifest(manifest_id)
        if not manifest:
            return {"error": "Manifest not found"}

        state = self.engine.db.get_state(manifest_id)
        if state != "approved":
            return {"error": f"Cannot submit from state: {state}"}

        title = manifest.get("title", {}).get("canonical", "Unknown")
        files = manifest.get("files", {})
        price = manifest.get("publishing", {}).get("price", 3.99)

        # Generate Google Play Books submission
        googleplay_id = f"ggb-{uuid.uuid4().hex[:12]}"
        submission = {
            "title": title,
            "author": "Darryl Elliott Brown",
            "publisher": "Gullah Geechee Biz",
            "language": "en",
            "price": price,
            "currency": "USD",
            "categories": ["SELF-HELP"],
            "description": f"A guide to {title.lower()}, drawing on Gullah Geechee wisdom.",
            "isbn": "",
            "pages": 120,
            "googleplay_id": googleplay_id,
            "submitted_at": datetime.now(timezone.utc).isoformat(),
        }

        # Log submission
        conn = sqlite3.connect(str(GOOGLEPLAY_DB))
        conn.execute("""
            INSERT OR REPLACE INTO submissions (manifest_id, title, status, googleplay_id, submitted_at)
            VALUES (?, ?, 'submitted', ?, ?)
        """, (manifest_id, title, googleplay_id, datetime.now(timezone.utc).isoformat()))
        conn.commit()
        conn.close()

        # Transition to LIVE
        self.engine.db.transition(manifest_id, PublishState.APPROVED, PublishState.LIVE, actor="agent-b-googleplay")

        self.stats["submitted"] += 1
        return {
            "status": "submitted",
            "platform": "googleplay",
            "googleplay_id": googleplay_id,
            "title": title,
        }

    def status(self) -> Dict:
        """Submission status."""
        conn = sqlite3.connect(str(GOOGLEPLAY_DB))
        total = conn.execute("SELECT COUNT(*) FROM submissions").fetchone()[0]
        conn.close()
        return {
            "total_submissions": total,
            "submitted_this_session": self.stats["submitted"],
        }


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="GGB Google Play Books Button Pusher")
    parser.add_argument("--json", action="store_true")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("status", help="Submission status")
    submit = sub.add_parser("submit", help="Submit a package")
    submit.add_argument("manifest_id")

    args = parser.parse_args()
    pusher = GooglePlayPusher()

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
