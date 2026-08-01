#!/usr/bin/env python3
"""
GGB Autonomous Agent A — PUBLISHER PRIME (The Strategist)
Decides what to publish, when, and on which terms.
Reviews readiness, makes judgment calls, manages queue.
Never touches a platform directly. Delegates to Agent B.
"""

import json, sys, uuid, os
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional, Dict, List, Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from publisher import (
    PublishEngine, StateStore, PublishState, build_canonical_manifest_hash,
    resolve_canonical_id, enforce_price, check_protected_draft,
    TITLE_REGISTRY, PROTECTED_DRAFTS, REPO_ROOT,
)

# ─── Agent Identity ─────────────────────────────────────────────────────────

AGENT_NAME = "publisher-prime"
AGENT_VERSION = "1.0.0"
AGENT_ROLE = "strategist"

# ─── Agent State ────────────────────────────────────────────────────────────

class AgentState:
    """Persistent state for Agent A: queue, decisions, approvals."""

    def __init__(self, db_path: Path = None):
        if db_path is None:
            db_path = REPO_ROOT / "publish" / "agent-a.db"
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        import sqlite3
        conn = sqlite3.connect(str(self.db_path))
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS decisions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                manifest_id TEXT NOT NULL,
                decision TEXT NOT NULL,
                reason TEXT,
                approved_at TEXT,
                expires_at TEXT,
                approval_hash TEXT,
                created_at TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS queue_review (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                manifest_id TEXT NOT NULL,
                priority INTEGER DEFAULT 0,
                reviewed_at TEXT,
                decision TEXT,
                notes TEXT
            )
        """)
        conn.commit()
        conn.close()

    def record_decision(self, manifest_id: str, decision: str, reason: str = "",
                        approval_hash: str = "", expires_hours: int = 24):
        import sqlite3, uuid
        now = datetime.now(timezone.utc).isoformat()
        expires = datetime.fromtimestamp(
            datetime.now(timezone.utc).timestamp() + expires_hours * 3600,
            tz=timezone.utc
        ).isoformat()
        conn = sqlite3.connect(str(self.db_path))
        conn.execute("""
            INSERT INTO decisions (manifest_id, decision, reason, approved_at, expires_at, approval_hash, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (manifest_id, decision, reason, now, expires, approval_hash, now))
        conn.commit()
        conn.close()

    def get_decisions(self, manifest_id: str) -> List[dict]:
        import sqlite3
        conn = sqlite3.connect(str(self.db_path))
        rows = conn.execute(
            "SELECT decision, reason, approved_at, expires_at, approval_hash FROM decisions WHERE manifest_id=? ORDER BY id DESC",
            (manifest_id,)
        ).fetchall()
        conn.close()
        return [{"decision": r[0], "reason": r[1], "approved_at": r[2],
                 "expires_at": r[3], "approval_hash": r[4]} for r in rows]

    def is_approved(self, manifest_id: str, approval_hash: str = "") -> bool:
        import sqlite3
        now = datetime.now(timezone.utc).isoformat()
        conn = sqlite3.connect(str(self.db_path))
        row = conn.execute(
            "SELECT COUNT(*) FROM decisions WHERE manifest_id=? AND decision='approve' AND expires_at > ?",
            (manifest_id, now)
        ).fetchone()
        conn.close()
        return row[0] > 0 if row else False


# ─── Agent A Core ───────────────────────────────────────────────────────────

class PublisherPrime:
    """Agent A: The Strategist — decides what to publish."""

    def __init__(self, engine: PublishEngine = None, state: AgentState = None):
        self.engine = engine or PublishEngine()
        self.state = state or AgentState()
        self.name = AGENT_NAME
        self.version = AGENT_VERSION

    # ── Queue Management ──────────────────────────────────────────────────

    def scan_queue(self) -> List[dict]:
        """Scan the publishing queue and return items needing review."""
        queue = self.engine.db.get_queue()
        needs_review = []
        for item in queue:
            manifest = self.engine.db.load_manifest(item["manifest_id"])
            if not manifest:
                continue
            state = item["state"]
            # Items that need Agent A's attention
            if state in ("validated", "staged", "preview_clean", "awaiting_owner_approval"):
                needs_review.append({
                    "manifest_id": item["manifest_id"],
                    "title": manifest.get("title", {}).get("canonical", "Unknown"),
                    "state": state,
                    "priority": item.get("priority", 0),
                    "canonical_id": item.get("canonical_id", "unknown"),
                })
        return sorted(needs_review, key=lambda x: (-x["priority"], x["manifest_id"]))

    def review_package(self, manifest_id: str) -> Dict:
        """Review a package and make a decision. Returns the decision."""
        manifest = self.engine.db.load_manifest(manifest_id)
        if not manifest:
            return {"decision": "reject", "reason": "Manifest not found"}

        title = manifest.get("title", {}).get("canonical", "Unknown")
        cid = resolve_canonical_id(title)
        state = self.engine.db.get_state(manifest_id)

        # Check readiness
        status = self.engine.get_status(manifest_id)
        blockers = status.get("blockers", [])

        # Check price policy
        price = manifest.get("publishing", {}).get("price", 0)
        allowed, price_msg = enforce_price(cid, price)
        if not allowed:
            return {"decision": "reject", "reason": price_msg, "title": title}

        # Check protected drafts
        if cid:
            draft_id = manifest.get("draft_id")
            allowed, draft_msg = check_protected_draft(cid, manifest.get("target_platform", "kdp"), draft_id)
            if not allowed:
                return {"decision": "reject", "reason": draft_msg, "title": title}

        # Check metadata completeness
        meta = manifest.get("metadata", {})
        if not meta.get("description") or len(meta.get("description", "")) < 20:
            return {"decision": "reject", "reason": "Description too short or missing", "title": title}

        # Check AI disclosure
        ai = meta.get("ai_disclosure", {})
        if not isinstance(ai.get("text"), bool):
            return {"decision": "reject", "reason": "AI disclosure incomplete", "title": title}

        # Check DRM and Select are explicitly set
        pub = manifest.get("publishing", {})
        if pub.get("drm") not in ("no", "yes"):
            return {"decision": "reject", "reason": "DRM not explicitly set", "title": title}
        if pub.get("kdp_select") not in ("off", "on"):
            return {"decision": "reject", "reason": "KDP Select not explicitly set", "title": title}

        # If all checks pass, approve
        approval_hash = build_canonical_manifest_hash(manifest)
        self.state.record_decision(manifest_id, "approve",
                                   reason=f"All checks passed for '{title}'",
                                   approval_hash=approval_hash)

        return {
            "decision": "approve",
            "reason": f"All checks passed for '{title}'",
            "title": title,
            "manifest_id": manifest_id,
            "approval_hash": approval_hash,
            "state": state,
            "blockers": blockers,
        }

    def approve_for_submission(self, manifest_id: str, owner: str = "agent-a") -> Dict:
        """Approve a package for submission. Records decision, transitions state."""
        manifest = self.engine.db.load_manifest(manifest_id)
        if not manifest:
            return {"error": "Manifest not found"}

        # Review first
        review = self.review_package(manifest_id)
        if review.get("decision") != "approve":
            return {"error": review.get("reason", "Review failed")}

        # Use engine's approve method
        result = self.engine.approve(manifest_id, owner=owner)
        if "error" in result:
            return result

        return {
            "status": "approved",
            "manifest_id": manifest_id,
            "title": review.get("title", "Unknown"),
            "approval_hash": result.get("approval_hash", ""),
            "next": "Ready for Agent B (Submission Specialist)",
        }

    def generate_report(self) -> Dict:
        """Generate a full status report of the queue and decisions."""
        queue = self.engine.db.get_queue()
        pending = self.scan_queue()

        report = {
            "agent": AGENT_NAME,
            "version": AGENT_VERSION,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "queue_total": len(queue),
            "pending_review": len(pending),
            "items": [],
        }

        for item in queue:
            manifest = self.engine.db.load_manifest(item["manifest_id"])
            title = manifest.get("title", {}).get("canonical", "Unknown") if manifest else "Unknown"
            decisions = self.state.get_decisions(item["manifest_id"])
            report["items"].append({
                "manifest_id": item["manifest_id"],
                "title": title,
                "state": item["state"],
                "priority": item.get("priority", 0),
                "canonical_id": item.get("canonical_id", "unknown"),
                "decisions": decisions[-1] if decisions else None,
            })

        return report


# ─── CLI ─────────────────────────────────────────────────────────────────────

def cli():
    import argparse
    parser = argparse.ArgumentParser(description=f"{AGENT_NAME} v{AGENT_VERSION} — {AGENT_ROLE}")
    parser.add_argument("--json", action="store_true", help="JSON output")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("scan", help="Scan queue for items needing review")
    sub.add_parser("report", help="Generate full status report")

    review = sub.add_parser("review", help="Review a package")
    review.add_argument("manifest_id", help="Manifest ID to review")

    approve = sub.add_parser("approve", help="Approve a package for submission")
    approve.add_argument("manifest_id", help="Manifest ID to approve")

    args = parser.parse_args()
    agent = PublisherPrime()

    if args.command == "scan":
        result = agent.scan_queue()
    elif args.command == "report":
        result = agent.generate_report()
    elif args.command == "review":
        result = agent.review_package(args.manifest_id)
    elif args.command == "approve":
        result = agent.approve_for_submission(args.manifest_id)

    if args.json:
        print(json.dumps(result, indent=2, default=str))
    else:
        if isinstance(result, list):
            print(f"Items needing review: {len(result)}")
            for item in result:
                print(f"  {item['state']:>20} | {item['title'][:50]:50} | {item['manifest_id'][:20]}")
        elif isinstance(result, dict):
            if "error" in result:
                print(f"ERROR: {result['error']}")
            elif "items" in result:
                print(f"Queue: {result['queue_total']} total, {result['pending_review']} pending review")
                for item in result["items"]:
                    d = item.get("decisions", {})
                    decision = d.get("decision", "pending") if d else "pending"
                    print(f"  {item['state']:>20} | {decision:>8} | {item['title'][:40]:40} | {item['manifest_id'][:20]}")
            else:
                for k, v in result.items():
                    print(f"{k}: {v}")
        else:
            print(result)

    return 0

if __name__ == "__main__":
    sys.exit(cli())
