#!/usr/bin/env python3
"""
GGB Agent B-1 — KDP Executor
Handles Amazon KDP upload, processing, preview, and submission.
Never decides what to publish. Follows Agent A's orders.
"""
import json, sys, uuid, time
from pathlib import Path
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from publisher import PublishEngine, StateStore, PublishState, build_canonical_manifest_hash, REPO_ROOT

AGENT_NAME = "agent-b-kdp"
AGENT_VERSION = "1.0.0"
PLATFORM = "kdp"

class KDPExecutor:
    """Agent B-1: KDP platform executor."""

    def __init__(self, engine: PublishEngine = None):
        self.engine = engine or PublishEngine()
        self.name = AGENT_NAME
        self.version = AGENT_VERSION
        self.max_retries = 3

    def verify_approval(self, manifest_id: str) -> Dict:
        """Verify Agent A's approval is valid."""
        manifest = self.engine.db.load_manifest(manifest_id)
        if not manifest:
            return {"verified": False, "error": "Manifest not found"}
        approval = manifest.get("approval", {})
        if approval.get("status") != "approved":
            return {"verified": False, "error": "Not approved by Agent A"}
        current_hash = build_canonical_manifest_hash(manifest)
        stored_hash = self.engine.db.get_approval_hash(manifest_id)
        if current_hash != stored_hash:
            return {"verified": False, "error": "Approval expired — manifest changed"}
        return {"verified": True, "approval_hash": stored_hash}

    def upload(self, manifest_id: str) -> Dict:
        """Upload files to KDP."""
        approval = self.verify_approval(manifest_id)
        if not approval["verified"]:
            return {"error": approval["error"]}

        manifest = self.engine.db.load_manifest(manifest_id)
        auth = self.engine.adapter.check_auth()
        if not auth.get("authenticated"):
            return {"error": "KDP authentication failed"}

        draft_id = manifest.get("draft_id", "new")
        stage_dir = REPO_ROOT / "publish" / "staging" / manifest_id

        uploads = []
        for key in ["manuscript", "cover"]:
            finfo = manifest.get("files", {}).get(key)
            if finfo:
                path = Path(finfo["path"])
                if not path.exists() and stage_dir.exists():
                    staged = stage_dir / path.name
                    if staged.exists():
                        path = staged
                for attempt in range(self.max_retries):
                    result = self.engine.adapter.upload_artifact(draft_id, key, str(path))
                    if result.get("success"):
                        uploads.append({"file": path.name, "key": key, "status": "uploaded"})
                        break
                    time.sleep(3)

        return {
            "status": "uploaded",
            "platform": PLATFORM,
            "draft_id": draft_id,
            "files_uploaded": len(uploads),
            "uploads": uploads,
            "_mock": self.engine.adapter.is_mock(),
        }

    def process(self, manifest_id: str) -> Dict:
        """Poll KDP processing status."""
        manifest = self.engine.db.load_manifest(manifest_id)
        draft_id = manifest.get("draft_id", "new") if manifest else "new"
        processing = self.engine.adapter.poll_processing(draft_id)
        return {
            "status": processing.get("status", "unknown"),
            "platform": PLATFORM,
            "draft_id": draft_id,
            "errors": processing.get("errors", []),
            "_mock": self.engine.adapter.is_mock(),
        }

    def preview(self, manifest_id: str) -> Dict:
        """Launch KDP previewer and capture evidence."""
        manifest = self.engine.db.load_manifest(manifest_id)
        draft_id = manifest.get("draft_id", "new") if manifest else "new"
        preview = self.engine.adapter.launch_previewer(draft_id)
        evidence = self.engine.adapter.capture_preview_evidence(draft_id)
        return {
            "status": "previewed",
            "platform": PLATFORM,
            "draft_id": draft_id,
            "previewer_opened": preview.get("opened", False),
            "screenshots": len(evidence.get("screenshots", [])),
            "_mock": self.engine.adapter.is_mock(),
        }

    def submit(self, manifest_id: str, owner_approved: bool = False) -> Dict:
        """Submit to KDP. Requires owner approval."""
        if not owner_approved:
            return {"error": "Owner approval required. Set owner_approved=True."}
        manifest = self.engine.db.load_manifest(manifest_id)
        if not manifest:
            return {"error": "Manifest not found"}
        result = self.engine.adapter.submit(manifest.get("draft_id", "new"))
        return {
            "status": "submitted" if result.get("submitted") else "failed",
            "platform": PLATFORM,
            "confirmation_id": result.get("confirmation_id", ""),
            "_mock": self.engine.adapter.is_mock(),
        }


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description=f"{AGENT_NAME} v{AGENT_VERSION}")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("manifest_id", help="Manifest ID")
    parser.add_argument("--platform", default="kdp")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("upload", help="Upload files")
    sub.add_parser("process", help="Check processing")
    sub.add_parser("preview", help="Launch previewer")
    submit = sub.add_parser("submit", help="Submit (requires owner approval)")
    submit.add_argument("--owner-approved", action="store_true")

    args = parser.parse_args()
    executor = KDPExecutor()

    if args.command == "upload":
        result = executor.upload(args.manifest_id)
    elif args.command == "process":
        result = executor.process(args.manifest_id)
    elif args.command == "preview":
        result = executor.preview(args.manifest_id)
    elif args.command == "submit":
        result = executor.submit(args.manifest_id, args.owner_approved)

    if args.json:
        print(json.dumps(result, indent=2, default=str))
    else:
        if isinstance(result, dict):
            for k, v in result.items():
                print(f"{k}: {v}")
        else:
            print(result)
