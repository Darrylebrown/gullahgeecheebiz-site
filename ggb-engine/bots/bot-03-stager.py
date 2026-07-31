#!/usr/bin/env python3
"""
GGB Publishing Bot 3/5 — STAGER
Copies validated, repaired files to staging directory.
Verifies hashes. Never submits. Hands off to Previewer Bot.
"""
import json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from publisher import PublishEngine

def run(manifest_id: str, dry_run: bool = False) -> dict:
    engine = PublishEngine()
    result = engine.stage(manifest_id, dry_run=dry_run)
    if dry_run:
        return {"bot": "stager", "status": "dry_run", "manifest_id": manifest_id}
    if "error" in result:
        return {"bot": "stager", "status": "blocked", "manifest_id": manifest_id, "error": result["error"]}
    return {"bot": "stager", "status": "staged", "manifest_id": manifest_id, "files": result.get("staged_files", [])}

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="GGB Stager Bot")
    parser.add_argument("manifest_id", help="Manifest ID to stage")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    result = run(args.manifest_id, args.dry_run)
    print(json.dumps(result, indent=2))
    sys.exit(0 if result.get("status") in ("staged", "dry_run") else 1)
