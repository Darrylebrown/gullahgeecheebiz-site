#!/usr/bin/env python3
"""
GGB Publishing Bot 5/5 — READINESS CHECKER
Checks if a package is ready for owner approval.
Reports blockers. Never submits. Never publishes.
"""
import json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from publisher import PublishEngine

def run(manifest_id: str, dry_run: bool = False) -> dict:
    engine = PublishEngine()
    result = engine.get_status(manifest_id)
    if "error" in result:
        return {"bot": "readiness", "status": "error", "manifest_id": manifest_id, "error": result["error"]}
    return {
        "bot": "readiness",
        "status": "ready" if result.get("ready") else "blocked",
        "manifest_id": manifest_id,
        "title": result.get("title", "Unknown"),
        "state": result.get("status", "unknown"),
        "blockers": result.get("blockers", []),
        "report": result.get("report", ""),
    }

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="GGB Readiness Checker Bot")
    parser.add_argument("manifest_id", help="Manifest ID to check")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    result = run(args.manifest_id, args.dry_run)
    print(json.dumps(result, indent=2))
    sys.exit(0 if result.get("status") == "ready" else 1)
