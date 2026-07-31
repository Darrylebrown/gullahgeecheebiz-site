#!/usr/bin/env python3
"""
GGB Publishing Bot 1/5 — VALIDATOR
Audits packages: metadata, prices, rights, AI disclosures, cover, hashes.
Never submits. Never publishes. Hands off to Repair Bot.
"""
import json, sys, uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "ggb-engine"))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from publisher import PublishEngine, StateStore, PublishState, resolve_canonical_id, enforce_price, check_protected_draft

def run(manifest_id: str, dry_run: bool = False) -> dict:
    engine = PublishEngine()
    result = engine.audit(manifest_id, dry_run=dry_run)
    if dry_run:
        return {"bot": "validator", "status": "dry_run", "manifest_id": manifest_id}
    if result.get("passed"):
        return {"bot": "validator", "status": "passed", "manifest_id": manifest_id, "evidence": result}
    return {"bot": "validator", "status": "blocked", "manifest_id": manifest_id, "errors": result.get("errors", [])}

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="GGB Validator Bot")
    parser.add_argument("manifest_id", help="Manifest ID to validate")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    result = run(args.manifest_id, args.dry_run)
    print(json.dumps(result, indent=2))
    sys.exit(0 if result.get("status") in ("passed", "dry_run") else 1)
