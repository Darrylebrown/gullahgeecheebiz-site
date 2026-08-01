#!/usr/bin/env python3
"""
GGB Agent B-2 — Draft2Digital Executor
Handles D2D upload, processing, preview, and distribution setup.
Never decides what to publish. Follows Agent A's orders.
"""
import json, sys, time
from pathlib import Path
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from publisher import PublishEngine, build_canonical_manifest_hash, REPO_ROOT

AGENT_NAME = "agent-b-d2d"
AGENT_VERSION = "1.0.0"
PLATFORM = "draft2digital"

class D2DExecutor:
    """Agent B-2: Draft2Digital platform executor."""

    def __init__(self, engine: PublishEngine = None):
        self.engine = engine or PublishEngine()
        self.name = AGENT_NAME
        self.version = AGENT_VERSION
        self.max_retries = 3

    def verify_approval(self, manifest_id: str) -> dict:
        manifest = self.engine.db.load_manifest(manifest_id)
        if not manifest:
            return {"verified": False, "error": "Manifest not found"}
        approval = manifest.get("approval", {})
        if approval.get("status") != "approved":
            return {"verified": False, "error": "Not approved by Agent A"}
        current_hash = build_canonical_manifest_hash(manifest)
        stored_hash = self.engine.db.get_approval_hash(manifest_id)
        if current_hash != stored_hash:
            return {"verified": False, "error": "Approval expired"}
        return {"verified": True}

    def upload(self, manifest_id: str) -> dict:
        approval = self.verify_approval(manifest_id)
        if not approval["verified"]:
            return {"error": approval["error"]}
        manifest = self.engine.db.load_manifest(manifest_id)
        auth = self.engine.adapter.check_auth()
        if not auth.get("authenticated"):
            return {"error": "D2D authentication failed"}
        draft_id = manifest.get("draft_id", "new-d2d")
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
            "status": "uploaded", "platform": PLATFORM, "draft_id": draft_id,
            "files_uploaded": len(uploads), "uploads": uploads,
            "_mock": self.engine.adapter.is_mock(),
        }

    def submit(self, manifest_id: str, owner_approved: bool = False) -> dict:
        if not owner_approved:
            return {"error": "Owner approval required"}
        manifest = self.engine.db.load_manifest(manifest_id)
        if not manifest:
            return {"error": "Manifest not found"}
        result = self.engine.adapter.submit(manifest.get("draft_id", "new-d2d"))
        return {
            "status": "submitted" if result.get("submitted") else "failed",
            "platform": PLATFORM, "confirmation_id": result.get("confirmation_id", ""),
            "_mock": self.engine.adapter.is_mock(),
        }


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description=f"{AGENT_NAME} v{AGENT_VERSION}")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("manifest_id")
    parser.add_argument("--platform", default="draft2digital")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("upload", help="Upload files")
    submit = sub.add_parser("submit", help="Submit")
    submit.add_argument("--owner-approved", action="store_true")

    args = parser.parse_args()
    executor = D2DExecutor()

    if args.command == "upload":
        result = executor.upload(args.manifest_id)
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
