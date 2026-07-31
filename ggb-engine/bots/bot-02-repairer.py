#!/usr/bin/env python3
"""
GGB Publishing Bot 2/5 — REPAIRER
Applies deterministic fixes: CMYK→RGB, size upscale, metadata sync.
Never submits. Never publishes. Hands off to Stager Bot.
"""
import json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from publisher import PublishEngine

def run(manifest_id: str, dry_run: bool = False) -> dict:
    engine = PublishEngine()
    result = engine.repair(manifest_id, dry_run=dry_run)
    if dry_run:
        return {"bot": "repairer", "status": "dry_run", "manifest_id": manifest_id}
    return {"bot": "repairer", "status": "repaired" if result.get("count", 0) > 0 else "clean", "manifest_id": manifest_id, "repairs": result.get("repairs", [])}

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="GGB Repairer Bot")
    parser.add_argument("manifest_id", help="Manifest ID to repair")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    result = run(args.manifest_id, args.dry_run)
    print(json.dumps(result, indent=2))
    sys.exit(0)
