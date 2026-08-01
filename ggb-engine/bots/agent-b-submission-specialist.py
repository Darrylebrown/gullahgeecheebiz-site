#!/usr/bin/env python3
"""
GGB Autonomous Agent B — SUBMISSION SPECIALIST (The Executor)
Handles platform-specific upload, processing, previewer verification, and submission.
The button pusher. Never decides what to publish.
Requires Agent A's signed approval and owner's 'publish now' to submit.
"""

import json, sys, uuid, os, time
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional, Dict, List, Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from publisher import (
    PublishEngine, StateStore, PublishState, build_canonical_manifest_hash,
    MockKDPAdapter, REPO_ROOT, STAGING_DIR,
)

# ─── Agent Identity ─────────────────────────────────────────────────────────

AGENT_NAME = "submission-specialist"
AGENT_VERSION = "1.0.0"
AGENT_ROLE = "executor"

# ─── Agent B Core ───────────────────────────────────────────────────────────

class SubmissionSpecialist:
    """Agent B: The Executor — handles platform interaction and submission."""

    def __init__(self, engine: PublishEngine = None):
        self.engine = engine or PublishEngine()
        self.name = AGENT_NAME
        self.version = AGENT_VERSION
        self.max_retries = 3
        self.retry_delay = 5  # seconds

    def verify_approval(self, manifest_id: str) -> Dict:
        """Verify Agent A's approval is valid and unexpired."""
        manifest = self.engine.db.load_manifest(manifest_id)
        if not manifest:
            return {"verified": False, "error": "Manifest not found"}

        # Check engine-level approval
        approval = manifest.get("approval", {})
        if approval.get("status") != "approved":
            return {"verified": False, "error": "Not approved by Agent A"}

        # Verify hash still matches
        current_hash = build_canonical_manifest_hash(manifest)
        stored_hash = self.engine.db.get_approval_hash(manifest_id)
        if current_hash != stored_hash:
            return {"verified": False, "error": "Approval expired — manifest changed since approval"}

        return {"verified": True, "approval_hash": stored_hash}

    def verify_owner_approval(self, manifest_id: str) -> bool:
        """Check if owner has given 'publish now' for this title."""
        manifest = self.engine.db.load_manifest(manifest_id)
        if not manifest:
            return False
        # Owner approval is tracked in the manifest's approval field
        approval = manifest.get("approval", {})
        return approval.get("status") == "approved" and approval.get("approved_by") == "owner"

    def upload_to_platform(self, manifest_id: str, platform: str = "kdp") -> Dict:
        """Upload files to platform. Uses mock adapter in Phase 1."""
        manifest = self.engine.db.load_manifest(manifest_id)
        if not manifest:
            return {"error": "Manifest not found"}

        # Verify approval first
        approval = self.verify_approval(manifest_id)
        if not approval["verified"]:
            return {"error": approval["error"]}

        # Check staging directory
        stage_dir = STAGING_DIR / manifest_id
        if not stage_dir.exists():
            return {"error": "No staged files found. Run stager bot first."}

        # List staged files
        staged_files = list(stage_dir.iterdir())
        if not staged_files:
            return {"error": "Staging directory is empty"}

        # Authenticate
        auth = self.engine.adapter.check_auth()
        if not auth.get("authenticated"):
            return {"error": "Platform authentication failed"}

        draft_id = manifest.get("draft_id", "new")

        # Upload each file
        uploads = []
        for f in staged_files:
            key = "manuscript" if "manuscript" in f.name.lower() or f.suffix == ".docx" else "cover"
            for attempt in range(self.max_retries):
                result = self.engine.adapter.upload_artifact(draft_id, key, str(f))
                if result.get("success"):
                    uploads.append({"file": f.name, "key": key, "status": "uploaded"})
                    break
                elif attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay)
                else:
                    return {"error": f"Upload failed for {f.name} after {self.max_retries} attempts"}

        # Poll processing
        processing = self.engine.adapter.poll_processing(draft_id)
        if processing.get("errors"):
            return {"error": f"Processing errors: {processing['errors']}"}

        # Launch previewer
        preview = self.engine.adapter.launch_previewer(draft_id)
        evidence = self.engine.adapter.capture_preview_evidence(draft_id)

        return {
            "status": "uploaded",
            "draft_id": draft_id,
            "files_uploaded": len(uploads),
            "uploads": uploads,
            "processing": processing.get("status", "unknown"),
            "previewer_opened": preview.get("opened", False),
            "evidence_captured": len(evidence.get("screenshots", [])),
            "_mock": self.engine.adapter.is_mock(),
        }

    def submit_to_platform(self, manifest_id: str, platform: str = "kdp",
                          owner_approved: bool = False) -> Dict:
        """Submit to platform. Requires owner approval."""
        if not owner_approved:
            return {"error": "Owner approval required. Set owner_approved=True to confirm."}

        manifest = self.engine.db.load_manifest(manifest_id)
        if not manifest:
            return {"error": "Manifest not found"}

        # Double-check approval
        approval = self.verify_approval(manifest_id)
        if not approval["verified"]:
            return {"error": approval["error"]}

        # Verify owner has given explicit approval
        if not self.verify_owner_approval(manifest_id):
            return {"error": "Owner has not given 'publish now' for this title"}

        # Submit
        result = self.engine.adapter.submit(manifest.get("draft_id", "new"))

        return {
            "status": "submitted" if result.get("submitted") else "failed",
            "confirmation_id": result.get("confirmation_id", ""),
            "evidence": result.get("evidence", ""),
            "_mock": self.engine.adapter.is_mock(),
        }

    def check_status(self, manifest_id: str) -> Dict:
        """Check current submission status."""
        return self.engine.get_status(manifest_id)

    def generate_report(self) -> Dict:
        """Generate a report of all packages needing Agent B's attention."""
        queue = self.engine.db.get_queue()
        needs_execution = []
        for item in queue:
            if item["state"] in ("approved",):
                manifest = self.engine.db.load_manifest(item["manifest_id"])
                title = manifest.get("title", {}).get("canonical", "Unknown") if manifest else "Unknown"
                needs_execution.append({
                    "manifest_id": item["manifest_id"],
                    "title": title,
                    "state": item["state"],
                })
        return {
            "agent": AGENT_NAME,
            "version": AGENT_VERSION,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "pending_execution": len(needs_execution),
            "items": needs_execution,
        }


# ─── CLI ─────────────────────────────────────────────────────────────────────

def cli():
    import argparse
    parser = argparse.ArgumentParser(description=f"{AGENT_NAME} v{AGENT_VERSION} — {AGENT_ROLE}")
    parser.add_argument("--json", action="store_true", help="JSON output")
    parser.add_argument("--db", type=str, help="Path to shared publisher database")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("report", help="Show pending execution items")

    upload = sub.add_parser("upload", help="Upload files to platform")
    upload.add_argument("manifest_id", help="Manifest ID to upload")
    upload.add_argument("--platform", default="kdp", help="Target platform")

    submit = sub.add_parser("submit", help="Submit to platform (requires owner approval)")
    submit.add_argument("manifest_id", help="Manifest ID to submit")
    submit.add_argument("--platform", default="kdp", help="Target platform")
    submit.add_argument("--owner-approved", action="store_true", help="Confirm owner approval")

    status = sub.add_parser("status", help="Check submission status")
    status.add_argument("manifest_id", help="Manifest ID to check")

    args = parser.parse_args()
    if args.db:
        from publisher import StateStore
        store = StateStore(Path(args.db))
        engine = PublishEngine(db=store)
    else:
        # Default to the standard publisher DB
        from publisher import StateStore, DB_PATH
        store = StateStore(DB_PATH)
        engine = PublishEngine(db=store)
    agent = SubmissionSpecialist(engine=engine)

    if args.command == "report":
        result = agent.generate_report()
    elif args.command == "upload":
        result = agent.upload_to_platform(args.manifest_id, args.platform)
    elif args.command == "submit":
        result = agent.submit_to_platform(args.manifest_id, args.platform, args.owner_approved)
    elif args.command == "status":
        result = agent.check_status(args.manifest_id)

    if args.json:
        print(json.dumps(result, indent=2, default=str))
    else:
        if isinstance(result, dict):
            if "error" in result:
                print(f"ERROR: {result['error']}")
            elif "items" in result:
                print(f"Pending execution: {result['pending_execution']}")
                for item in result["items"]:
                    print(f"  {item['state']:>20} | {item['title'][:50]:50} | {item['manifest_id'][:20]}")
            else:
                for k, v in result.items():
                    print(f"{k}: {v}")
        else:
            print(result)

    return 0

if __name__ == "__main__":
    sys.exit(cli())
