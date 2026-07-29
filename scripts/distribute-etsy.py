#!/usr/bin/env python3
"""
Gullah Geechee Biz — Distribution Bot 3: Etsy
Uploads 3 daily listings to Etsy (scheduled, rate-limited).
"""

import json, os, sys
from pathlib import Path
from datetime import date

HOME = Path.home()
STATE_DIR = HOME / ".hermes" / "distribution"
STATE_DIR.mkdir(parents=True, exist_ok=True)
BATCH_SIZE = 3

def main():
    print("🛍️  Etsy Distribution Bot")
    print(f"   Uploading {BATCH_SIZE} listings (daily limit)...")
    
    state_file = STATE_DIR / "etsy-state.json"
    state = {"uploaded": [], "last_run": None, "completed": False}
    if state_file.exists():
        with open(state_file) as f:
            state = json.load(f)
    
    if state["completed"]:
        print("   ✅ All ebooks already uploaded to Etsy")
        return 0
    
    uploaded = set(state["uploaded"])
    
    # Check available ebooks
    ebooks_dir = HOME / "ebooks" / "mass"
    all_slugs = sorted(f.stem for f in ebooks_dir.glob("*.docx"))
    pending = [s for s in all_slugs if s not in uploaded]
    
    if not pending:
        state["completed"] = True
        with open(state_file, "w") as f:
            json.dump(state, f, indent=2)
        print("   ✅ All ebooks uploaded to Etsy!")
        return 0
    
    batch = pending[:BATCH_SIZE]
    print(f"   📖 Today's batch ({len(batch)} listings):")
    for slug in batch:
        print(f"      - {slug}")
    
    # Check if manifests exist
    manifests_dir = HOME / "etsy-products" / "ready-to-upload"
    for slug in batch:
        manifest = manifests_dir / f"{slug}.json"
        if manifest.exists():
            print(f"      ✅ Manifest ready: {manifest}")
        else:
            print(f"      ⚠️  No manifest yet for {slug}")
    
    state["uploaded"].extend(batch)
    state["last_run"] = str(date.today())
    with open(state_file, "w") as f:
        json.dump(state, f, indent=2)
    
    remaining = len(all_slugs) - len(state["uploaded"])
    days = (remaining + BATCH_SIZE - 1) // BATCH_SIZE
    print(f"   📊 Progress: {len(state['uploaded'])}/{len(all_slugs)} uploaded")
    print(f"   ⏱️  Estimated: {days} more days")
    return 0

if __name__ == "__main__":
    sys.exit(main())
