#!/usr/bin/env python3
"""
GGB Agent B-3 — ACX (Audiobook) Executor
Handles ACX upload, narration assignment, proofing, and distribution.
Never decides what to publish. Follows Agent A's orders.
"""
import json, sys, time
from pathlib import Path
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from publisher import PublishEngine, build_canonical_manifest_hash, REPO_ROOT

AGENT_NAME = "agent-b-acx"
AGENT_VERSION = "1.0.0"
PLATFORM = "acx"

class ACXExecutor:
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

    def upload_audio(self, manifest_id: str) -> dict:
        approval = self.verify_approval(manifest_id)
        if not approval["verified"]:
            return {"error": approval["error"]}
        manifest = self.engine.db.load_manifest(manifest_id)
        auth = self.engine.adapter.check_auth()
        if not auth.get("authenticated"):
            return {"error": "ACX authentication failed"}
        draft_id = manifest.get("draft_id", "new-acx")
        audio_dir = REPO_ROOT / "publish" / "audio"
        uploads = []
        for f in sorted(audio_dir.glob("*.mp3")):
            if manifest_id[:8] in f.name:
                for attempt in range(self.max_retries):
                    result = self.engine.adapter.upload_artifact(draft_id, "audio", str(f))
                    if result.get("success"):
                        uploads.append({"file": f.name, "status": "uploaded"})
                        break
                    time.sleep(3)
        return {
            "status": "uploaded", "platform": PLATFORM, "draft_id": draft_id,
            "files_uploaded": len(uploads), "_mock": self.engine.adapter.is_mock(),
        }

    def submit(self, manifest_id: str, owner_approved: bool = False) -> dict:
        if not owner_approved:
            return {"error": "Owner approval required"}
        manifest = self.engine.db.load_manifest(manifest_id)
        if not manifest:
            return {"error": "Manifest not found"}
        result = self.engine.adapter.submit(manifest.get("draft_id", "new-acx"))
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
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("upload")
    submit = sub.add_parser("submit")
    submit.add_argument("--owner-approved", action="store_true")
    args = parser.parse_args()
    executor = ACXExecutor()
    if args.command == "upload":
        result = executor.upload_audio(args.manifest_id)
    elif args.command == "submit":
        result = executor.submit(args.manifest_id, args.owner_approved)
    if args.json:
        print(json.dumps(result, indent=2, default=str))
    else:
        for k, v in (result or {}).items():
            print(f"{k}: {v}")
