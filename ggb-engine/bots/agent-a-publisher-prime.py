#!/usr/bin/env python3
"""
GGB Agent A — Publisher Prime (Extended)
Manages a fleet of platform executors. Decides what to publish, when, and on which platform.
Queue management, priority ordering, safety enforcement.
"""
import json, sys, uuid, subprocess
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional, Dict, List

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from publisher import (
    PublishEngine, StateStore, PublishState, build_canonical_manifest_hash,
    resolve_canonical_id, enforce_price, check_protected_draft,
    TITLE_REGISTRY, PROTECTED_DRAFTS, REPO_ROOT,
)

AGENT_NAME = "publisher-prime"
AGENT_VERSION = "2.0.0"

# ─── Platform Registry ─────────────────────────────────────────────────────

PLATFORMS = {
    "kdp": {
        "name": "Amazon KDP",
        "formats": ["ebook", "paperback"],
        "executor": "agent-b-kdp.py",
        "enabled": True,
        "max_concurrent": 1,
    },
    "draft2digital": {
        "name": "Draft2Digital",
        "formats": ["ebook", "paperback"],
        "executor": "agent-b-d2d.py",
        "enabled": True,
        "max_concurrent": 1,
    },
    "acx": {
        "name": "ACX (Audiobooks)",
        "formats": ["audiobook"],
        "executor": "agent-b-acx.py",
        "enabled": False,  # Future
        "max_concurrent": 1,
    },
    "ingramspark": {
        "name": "IngramSpark",
        "formats": ["paperback", "hardcover"],
        "executor": "agent-b-ingram.py",
        "enabled": False,  # Future
        "max_concurrent": 1,
    },
    "distrokid": {
        "name": "DistroKid",
        "formats": ["music"],
        "executor": "agent-b-distrokid.py",
        "enabled": False,  # Future
        "max_concurrent": 1,
    },
}

class PublisherPrime:
    """Agent A v2 — manages fleet of platform executors."""

    def __init__(self, engine: PublishEngine = None):
        self.engine = engine or PublishEngine()
        self.name = AGENT_NAME
        self.version = AGENT_VERSION
        self.bots_dir = Path(__file__).resolve().parent

    def scan_queue(self) -> List[Dict]:
        """Scan queue and return items needing attention."""
        queue = self.engine.db.get_queue()
        needs_review = []
        for item in queue:
            manifest = self.engine.db.load_manifest(item["manifest_id"])
            if not manifest:
                continue
            state = item["state"]
            if state in ("validated", "staged", "preview_clean", "awaiting_owner_approval", "approved"):
                needs_review.append({
                    "manifest_id": item["manifest_id"],
                    "title": manifest.get("title", {}).get("canonical", "Unknown"),
                    "state": state,
                    "priority": item.get("priority", 0),
                    "canonical_id": item.get("canonical_id", "unknown"),
                    "format": manifest.get("format", "ebook"),
                })
        return sorted(needs_review, key=lambda x: (-x["priority"], x["manifest_id"]))

    def review_package(self, manifest_id: str) -> Dict:
        """Review a package and determine readiness."""
        manifest = self.engine.db.load_manifest(manifest_id)
        if not manifest:
            return {"decision": "reject", "reason": "Manifest not found"}

        title = manifest.get("title", {}).get("canonical", "Unknown")
        cid = resolve_canonical_id(title)
        state = self.engine.db.get_state(manifest_id)

        # Check price policy
        price = manifest.get("publishing", {}).get("price", 0)
        allowed, price_msg = enforce_price(cid, price)
        if not allowed:
            return {"decision": "reject", "reason": price_msg, "title": title}

        # Check protected drafts
        if cid:
            draft_id = manifest.get("draft_id")
            platform = manifest.get("target_platform", "kdp")
            allowed, draft_msg = check_protected_draft(cid, platform, draft_id)
            if not allowed:
                return {"decision": "reject", "reason": draft_msg, "title": title}

        # Check metadata
        meta = manifest.get("metadata", {})
        if not meta.get("description") or len(meta.get("description", "")) < 20:
            return {"decision": "reject", "reason": "Description too short", "title": title}

        # Check DRM/Select
        pub = manifest.get("publishing", {})
        if pub.get("drm") not in ("no", "yes"):
            return {"decision": "reject", "reason": "DRM not set", "title": title}
        if pub.get("kdp_select") not in ("off", "on"):
            return {"decision": "reject", "reason": "KDP Select not set", "title": title}

        # Determine target platforms
        fmt = manifest.get("format", "ebook")
        eligible = [k for k, v in PLATFORMS.items() if v["enabled"] and fmt in v["formats"]]

        return {
            "decision": "approve",
            "reason": f"Ready for {', '.join(eligible)}",
            "title": title,
            "manifest_id": manifest_id,
            "state": state,
            "eligible_platforms": eligible,
        }

    def dispatch(self, manifest_id: str, platform: str = "kdp") -> Dict:
        """Dispatch a package to a platform executor."""
        manifest = self.engine.db.load_manifest(manifest_id)
        if not manifest:
            return {"error": "Manifest not found"}

        platform_info = PLATFORMS.get(platform)
        if not platform_info:
            return {"error": f"Unknown platform: {platform}"}
        if not platform_info["enabled"]:
            return {"error": f"Platform {platform} is not enabled"}

        executor = self.bots_dir / platform_info["executor"]
        if not executor.exists():
            return {"error": f"Executor not found: {executor}"}

        # Run the executor as a subprocess
        result = subprocess.run(
            [sys.executable, str(executor), manifest_id, "--platform", platform],
            capture_output=True, text=True, timeout=120
        )

        try:
            data = json.loads(result.stdout)
        except:
            data = {"error": result.stderr[:500] if result.stderr else "No JSON output"}

        data["exit_code"] = result.returncode
        return data

    def generate_report(self) -> Dict:
        """Full status report."""
        queue = self.engine.db.get_queue()
        pending = self.scan_queue()
        return {
            "agent": AGENT_NAME,
            "version": AGENT_VERSION,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "queue_total": len(queue),
            "pending_review": len(pending),
            "platforms": {k: v["name"] for k, v in PLATFORMS.items() if v["enabled"]},
            "items": pending,
        }


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description=f"{AGENT_NAME} v{AGENT_VERSION}")
    parser.add_argument("--json", action="store_true")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("scan", help="Scan queue")
    sub.add_parser("report", help="Full report")

    review = sub.add_parser("review", help="Review a package")
    review.add_argument("manifest_id")

    dispatch = sub.add_parser("dispatch", help="Dispatch to platform executor")
    dispatch.add_argument("manifest_id")
    dispatch.add_argument("--platform", default="kdp", choices=list(PLATFORMS.keys()))

    args = parser.parse_args()
    agent = PublisherPrime()

    if args.command == "scan":
        result = agent.scan_queue()
    elif args.command == "report":
        result = agent.generate_report()
    elif args.command == "review":
        result = agent.review_package(args.manifest_id)
    elif args.command == "dispatch":
        result = agent.dispatch(args.manifest_id, args.platform)

    if args.json:
        print(json.dumps(result, indent=2, default=str))
    else:
        if isinstance(result, list):
            print(f"Pending: {len(result)}")
            for item in result:
                print(f"  {item['state']:>20} | {item['title'][:50]}")
        elif isinstance(result, dict):
            for k, v in result.items():
                if isinstance(v, list) and len(v) > 5:
                    print(f"{k}: {len(v)} items")
                elif isinstance(v, dict):
                    print(f"{k}:")
                    for sk, sv in v.items():
                        print(f"  {sk}: {sv}")
                else:
                    print(f"{k}: {v}")
        else:
            print(result)
