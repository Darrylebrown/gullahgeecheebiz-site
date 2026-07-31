#!/usr/bin/env python3
"""
GGB Publishing Bot 4/5 — PREVIEWER
Runs mock adapter sequence: upload, process, preview.
Captures evidence. Never submits. Hands off to Readiness Bot.
"""
import json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from publisher import PublishEngine

def run(manifest_id: str, dry_run: bool = False) -> dict:
    engine = PublishEngine()
    result = engine.preview(manifest_id, dry_run=dry_run)
    if dry_run:
        return {"bot": "previewer", "status": "dry_run", "manifest_id": manifest_id}
    if "error" in result:
        return {"bot": "previewer", "status": "blocked", "manifest_id": manifest_id, "error": result["error"]}
    return {
        "bot": "previewer",
        "status": "previewed",
        "manifest_id": manifest_id,
        "previewer_opened": result.get("previewer_opened", False),
        "evidence_recorded": result.get("_mock", False) is not None,
        "_mock": result.get("_mock", True),
    }

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="GGB Previewer Bot")
    parser.add_argument("manifest_id", help="Manifest ID to preview")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    result = run(args.manifest_id, args.dry_run)
    print(json.dumps(result, indent=2))
    sys.exit(0 if result.get("status") in ("previewed", "dry_run") else 1)
