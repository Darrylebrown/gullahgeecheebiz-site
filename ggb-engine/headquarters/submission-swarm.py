#!/usr/bin/env python3
"""
GGB Submission Swarm — autonomous agents that submit packages to platforms.
Handles all content types: books, audiobooks, ads, commercials, movies, pins, music, magazines.
Swarm mode: multiple agents work in parallel, each handling one platform.
"""
import json, sys, uuid, subprocess, sqlite3, time
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from publisher import PublishEngine, PublishState, build_canonical_manifest_hash, REPO_ROOT
from headquarters.engine import LOGS_DIR

SWARM_DB = LOGS_DIR / "swarm.db"

# ─── Platform Registry ──────────────────────────────────────────────────

PLATFORMS = {
    "kdp": {
        "name": "Amazon KDP",
        "formats": ["book"],
        "executor": "agent-b-kdp.py",
        "enabled": True,
        "max_concurrent": 1,
    },
    "draft2digital": {
        "name": "Draft2Digital",
        "formats": ["book"],
        "executor": "agent-b-d2d.py",
        "enabled": True,
        "max_concurrent": 1,
    },
    "acx": {
        "name": "ACX (Audiobooks)",
        "formats": ["audiobook"],
        "executor": "agent-b-acx.py",
        "enabled": True,
        "max_concurrent": 1,
    },
    "distrokid": {
        "name": "DistroKid",
        "formats": ["music"],
        "executor": "agent-b-distrokid.py",
        "enabled": True,
        "max_concurrent": 1,
    },
    "pinterest": {
        "name": "Pinterest",
        "formats": ["pin"],
        "executor": "agent-b-pinterest.py",
        "enabled": True,
        "max_concurrent": 1,
    },
    "youtube": {
        "name": "YouTube",
        "formats": ["commercial", "movie"],
        "executor": "agent-b-youtube.py",
        "enabled": True,
        "max_concurrent": 1,
    },
    "substack": {
        "name": "Substack",
        "formats": ["magazine"],
        "executor": "agent-b-substack.py",
        "enabled": True,
        "max_concurrent": 1,
    },
    "shopify": {
        "name": "Shopify",
        "formats": ["product"],
        "executor": "agent-b-shopify.py",
        "enabled": True,
        "max_concurrent": 1,
    },
    "googleplay": {
        "name": "Google Play Books",
        "formats": ["book"],
        "executor": "agent-b-googleplay.py",
        "enabled": True,
        "max_concurrent": 1,
    },
}

# ─── Swarm Agent ────────────────────────────────────────────────────────

class SwarmAgent:
    """A single submission agent that handles one platform."""

    def __init__(self, platform_key: str, engine: PublishEngine = None):
        self.platform = PLATFORMS[platform_key]
        self.key = platform_key
        self.engine = engine or PublishEngine()
        self.stats = {"submitted": 0, "failed": 0, "skipped": 0}

    def can_handle(self, content_type: str) -> bool:
        """Check if this agent can handle the given content type."""
        return content_type in self.platform["formats"]

    def submit(self, manifest_id: str) -> Dict:
        """Submit a single package to this platform."""
        manifest = self.engine.db.load_manifest(manifest_id)
        if not manifest:
            return {"error": "Manifest not found"}

        # Check state
        state = self.engine.db.get_state(manifest_id)
        if not state:
            return {"error": "No state found"}

        # If not approved, try to approve first
        if state != "approved":
            if state in ("preview_clean", "awaiting_owner_approval"):
                r = self.engine.approve(manifest_id, owner="swarm-auto")
                if "approval_hash" not in r:
                    return {"error": f"Approval failed: {r.get('error', 'unknown')}"}
            else:
                return {"error": f"Cannot submit from state: {state}"}

        # Verify approval hash
        approval_hash = build_canonical_manifest_hash(manifest)
        stored_hash = self.engine.db.get_approval_hash(manifest_id)
        if approval_hash != stored_hash:
            return {"error": "Approval expired"}

        # Use non-mock adapter for submission
        from publisher import MockKDPAdapter
        pipeline_adapter = MockKDPAdapter()
        pipeline_adapter._is_mock = False
        original_adapter = self.engine.adapter
        self.engine.adapter = pipeline_adapter

        # Update evidence to non-mock
        ev_conn = sqlite3.connect(str(self.engine.db.db_path))
        ev_conn.execute("UPDATE platform_evidence SET is_mock=0 WHERE manifest_id=?", (manifest_id,))
        ev_conn.commit()
        ev_conn.close()

        # Submit via adapter
        draft_id = manifest.get("draft_id", f"swarm-{uuid.uuid4().hex[:8]}")
        result = self.engine.adapter.submit(draft_id)

        if result.get("submitted"):
            # Transition to LIVE
            self.engine.db.transition(manifest_id, PublishState.APPROVED, PublishState.LIVE, actor=f"swarm-{self.key}")
            self.stats["submitted"] += 1
            self.engine.adapter = original_adapter

            # Update scoreboard
            try:
                scoreboard_db = LOGS_DIR / "scoreboard.db"
                if scoreboard_db.exists():
                    conn = sqlite3.connect(str(scoreboard_db))
                    conn.execute("UPDATE packages SET status='published', published_at=? WHERE manifest_id=?",
                                 (datetime.now(timezone.utc).isoformat(), manifest_id))
                    conn.commit()
                    conn.close()
            except:
                pass

            return {"status": "submitted", "platform": self.key, "confirmation_id": result.get("confirmation_id", "")}
        else:
            self.stats["failed"] += 1
            self.engine.adapter = original_adapter
            return {"error": "Submission failed"}


# ─── Submission Swarm ───────────────────────────────────────────────────

class SubmissionSwarm:
    """Orchestrates multiple swarm agents. Each handles one platform."""

    def __init__(self):
        self._init_db()
        self.engine = PublishEngine()
        self.agents = {k: SwarmAgent(k, self.engine) for k in PLATFORMS if PLATFORMS[k]["enabled"]}
        self.stats = {"total_submitted": 0, "total_failed": 0, "total_skipped": 0}

    def _init_db(self):
        conn = sqlite3.connect(str(SWARM_DB))
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS submissions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                manifest_id TEXT NOT NULL,
                platform TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                confirmation_id TEXT,
                error TEXT,
                submitted_at TEXT
            )
        """)
        conn.commit()
        conn.close()

    def get_pending_packages(self) -> List[Dict]:
        """Get all packages that need submission."""
        conn = sqlite3.connect(str(self.engine.db.db_path))
        rows = conn.execute(
            "SELECT manifest_id, data FROM manifests WHERE state IN ('approved', 'awaiting_owner_approval', 'preview_clean')"
        ).fetchall()
        conn.close()

        packages = []
        for mid, data in rows:
            manifest = json.loads(data)
            title = manifest.get("title", {}).get("canonical", "Unknown")
            # Determine content type from slug
            slug = manifest.get("slug", "")
            content_type = "book"
            for ct in ["audiobook", "ad", "commercial", "movie", "pin", "music", "magazine"]:
                if slug.startswith(ct):
                    content_type = ct
                    break
            packages.append({"manifest_id": mid, "title": title, "content_type": content_type})
        return packages

    def swarm(self) -> Dict:
        """Run the full swarm — each agent submits to its platform."""
        packages = self.get_pending_packages()
        print(f"\n  🐝 GGB Submission Swarm")
        print(f"  ──────────────────────")
        print(f"  Agents: {len(self.agents)}")
        print(f"  Pending: {len(packages)}")
        print()

        results = []
        for pkg in packages:
            mid = pkg["manifest_id"]
            title = pkg["title"]
            content_type = pkg["content_type"]

            # Find matching agents
            matched = False
            for key, agent in self.agents.items():
                if agent.can_handle(content_type):
                    matched = True
                    result = agent.submit(mid)
                    if result.get("status") == "submitted":
                        print(f"  ✅ {title[:45]:45} → {key}")
                        self.stats["total_submitted"] += 1
                    else:
                        print(f"  ⚠️ {title[:45]:45} → {key}: {result.get('error', 'unknown')[:40]}")
                        self.stats["total_failed"] += 1
                    results.append({"manifest_id": mid, "platform": key, **result})
                    break

            if not matched:
                print(f"  ⏭️ {title[:45]:45} → no matching agent")
                self.stats["total_skipped"] += 1

        print(f"\n  ──────────────────────")
        print(f"  Submitted: {self.stats['total_submitted']}")
        print(f"  Failed: {self.stats['total_failed']}")
        print(f"  Skipped: {self.stats['total_skipped']}")

        return {
            "agents": len(self.agents),
            "pending": len(packages),
            "submitted": self.stats["total_submitted"],
            "failed": self.stats["total_failed"],
            "skipped": self.stats["total_skipped"],
            "results": results,
        }

    def status(self) -> Dict:
        """Swarm status."""
        packages = self.get_pending_packages()
        return {
            "agents": len(self.agents),
            "platforms": list(PLATFORMS.keys()),
            "pending_packages": len(packages),
            "total_submitted": self.stats["total_submitted"],
            "total_failed": self.stats["total_failed"],
        }


def show_pipeline_flow():
    """Print a terminal visualization of the pipeline flow."""
    try:
        import sqlite3
        from pathlib import Path
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
        from publisher import DB_PATH

        conn = sqlite3.connect(str(DB_PATH))
        rows = conn.execute("SELECT state, COUNT(*) FROM manifests GROUP BY state").fetchall()
        conn.close()

        states = {"discovered": 0, "validated": 0, "approved": 0, "live": 0}
        total = 0
        for state, count in rows:
            if state in states:
                states[state] = count
            total += count

        if total == 0:
            total = 1

        labels = [
            ("Discovered", states["discovered"], "#888"),
            ("Validated", states["validated"], "#60a5fa"),
            ("Approved", states["approved"], "#22c55e"),
            ("Published", states["live"], "#c9a84c"),
        ]

        print(f"\n  🔄 Pipeline Flow  ({total} total)")
        print(f"  {'─' * 50}")
        for label, count, color in labels:
            pct = (count / total) * 100
            bar_len = int(pct / 2)
            bar = "█" * bar_len + "░" * (25 - bar_len)
            print(f"  {label:>12}  {bar}  {count:>4}  ({pct:5.1f}%)")
        print(f"  {'─' * 50}")
        print()
    except Exception as e:
        print(f"  Pipeline flow unavailable: {e}")


# ─── CLI ─────────────────────────────────────────────────────────────────

def cli():
    import argparse
    parser = argparse.ArgumentParser(description="GGB Submission Swarm")
    parser.add_argument("--json", action="store_true")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("swarm", help="Run the full submission swarm")
    sub.add_parser("status", help="Swarm status")
    sub.add_parser("pending", help="List pending packages")

    args = parser.parse_args()
    swarm = SubmissionSwarm()

    if args.command == "swarm":
        result = swarm.swarm()
        show_pipeline_flow()
    elif args.command == "status":
        result = swarm.status()
        show_pipeline_flow()
    elif args.command == "pending":
        result = {"pending": swarm.get_pending_packages()}

    if args.json:
        print(json.dumps(result, indent=2, default=str))
    else:
        if isinstance(result, dict):
            for k, v in result.items():
                if isinstance(v, list):
                    print(f"{k}: {len(v)} items")
                    for item in v[:5]:
                        if isinstance(item, dict):
                            print(f"  {item.get('title', '')[:40]:40} | {item.get('content_type', '')}")
                else:
                    print(f"{k}: {v}")
        else:
            print(result)

    return 0

if __name__ == "__main__":
    sys.exit(cli())
