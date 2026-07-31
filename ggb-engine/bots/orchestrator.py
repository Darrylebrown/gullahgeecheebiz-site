#!/usr/bin/env python3
"""
GGB Publishing Bot Orchestrator — chains 5 bots in sequence.
1. Validator → 2. Repairer → 3. Stager → 4. Previewer → 5. Readiness
Never submits. Never publishes. Reports results.
"""
import json, sys, subprocess, uuid
from pathlib import Path
from datetime import datetime, timezone

BOTS_DIR = Path(__file__).resolve().parent
ENGINE_DIR = BOTS_DIR.parent / "ggb-engine"
PYTHON = sys.executable

def run_bot(name: str, script: str, manifest_id: str, dry_run: bool = False) -> dict:
    cmd = [PYTHON, script, manifest_id]
    if dry_run:
        cmd.append("--dry-run")
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError:
        data = {"error": result.stderr[:500] if result.stderr else "No JSON output"}
    data["bot"] = name
    data["exit_code"] = result.returncode
    return data

def run(manifest_id: str, dry_run: bool = False) -> dict:
    workflow_id = f"ggb-bot-{uuid.uuid4().hex[:8]}"
    print(f"Workflow: {workflow_id}")
    print(f"Package: {manifest_id}")
    print(f"Started: {datetime.now(timezone.utc).isoformat()}")
    print()

    bots = [
        ("01-validator", BOTS_DIR / "bot-01-validator.py"),
        ("02-repairer", BOTS_DIR / "bot-02-repairer.py"),
        ("03-stager", BOTS_DIR / "bot-03-stager.py"),
        ("04-previewer", BOTS_DIR / "bot-04-previewer.py"),
        ("05-readiness", BOTS_DIR / "bot-05-readiness.py"),
    ]

    results = []
    for name, script in bots:
        if not script.exists():
            results.append({"bot": name, "status": "error", "error": f"Script not found: {script}"})
            break
        result = run_bot(name, str(script), manifest_id, dry_run)
        results.append(result)
        status = result.get("status", "error")
        print(f"  [{status.upper():>8}] {name}: {result.get('error', result.get('evidence', result.get('report', '')))[:80]}")
        if status in ("blocked", "error"):
            print(f"  → Pipeline stopped at {name}")
            break

    print(f"\nCompleted: {datetime.now(timezone.utc).isoformat()}")
    return {"workflow_id": workflow_id, "manifest_id": manifest_id, "results": results}

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="GGB Publishing Bot Orchestrator")
    parser.add_argument("manifest_id", help="Manifest ID to process")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    result = run(args.manifest_id, args.dry_run)
    print(json.dumps(result, indent=2))
    sys.exit(0)
