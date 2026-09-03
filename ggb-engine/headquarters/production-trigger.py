#!/usr/bin/env python3
"""GGB Production Trigger — checks real pipeline capacity and fires the real
publishing pipeline (workflow engine master-orchestrator) when conditions are met.

Previously a simulation stub (hardcoded capacity + hardcoded OK). Rewritten
2026-09-01 to query live state and run the actual engine. Requires Python 3.10+
(repo venv)."""
import argparse
import sqlite3
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]           # ~/gullahgeecheebiz-site
DB_PATH = REPO / "publish" / "publisher.db"
ENGINE_DIR = REPO / "ggb-engine"
ENGINE = ENGINE_DIR / "engine.py"


def pipeline_capacity():
    """Fraction of manifests in terminal (published) state. Returns (ready, capacity, errors)."""
    if not DB_PATH.exists():
        return False, 0.0, f"DB missing: {DB_PATH}"
    if not ENGINE.exists():
        return False, 0.0, f"engine.py missing: {ENGINE}"
    try:
        conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
        row = conn.execute("SELECT state, COUNT(*) FROM manifests GROUP BY state").fetchall()
        conn.close()
        total = sum(c for _, c in row)
        if total == 0:
            return False, 0.0, "No manifests in DB"
        published = dict(row).get("published", 0)
        return True, published / total, 0
    except Exception as e:  # pragma: no cover
        return False, 0.0, str(e)


def fire_production():
    """Run the real pipeline via the workflow engine. Returns dict stage -> status."""
    cmd = [sys.executable, str(ENGINE), "run", "master-orchestrator"]
    try:
        proc = subprocess.run(cmd, cwd=str(ENGINE_DIR), capture_output=True,
                              text=True, timeout=600)
        out = proc.stdout + proc.stderr
    except subprocess.TimeoutExpired:
        return {"master-orchestrator": "TIMEOUT (>600s)"}

    # Parse per-phase results from engine output: "▶ phase-1-content... ✅ (0.1s)"
    results = {}
    for line in out.splitlines():
        if "▶" in line and ("✅" in line or "❌" in line or "⚠" in line):
            stage = line.split("▶")[1].split("...")[0].strip()
            results[stage] = "OK" if "✅" in line else ("WARN" if "⚠" in line else "FAIL")
    if not results:
        # Fallback: engine produced no parseable lines
        rc = proc.returncode if "proc" in dir() else -1
        return {"master-orchestrator": f"OK" if rc == 0 else f"FAIL (rc={rc})"}
    return results


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--fire", action="store_true")
    args = parser.parse_args()

    ready, capacity, errors = pipeline_capacity()
    min_capacity = 0.25

    if args.check:
        if ready and capacity >= min_capacity:
            print(f"Would trigger — capacity {capacity:.0%} (>= {min_capacity:.0%})")
        elif errors:
            print(f"Cannot check — {errors}")
        else:
            print(f"Not ready — capacity {capacity:.0%}")
    elif args.fire:
        if ready and capacity >= min_capacity:
            results = fire_production()
            print("Triggered full-spectrum production:")
            for stage, status in results.items():
                print(f"- {stage}: {status}")
            failed = [s for s, st in results.items() if st != "OK"]
            if failed:
                print(f"ERROR: {len(failed)} stage(s) failed: {', '.join(failed)}")
                sys.exit(1)
        else:
            print(f"Cannot fire — capacity {capacity:.0%} (need >= {min_capacity:.0%})" if not errors
                  else f"Cannot fire — {errors}")


if __name__ == "__main__":
    main()
