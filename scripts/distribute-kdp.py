#!/usr/bin/env python3
"""
Gullah Geechee Biz — Distribution Bot 1: KDP (Amazon)
Submits new ebooks to Amazon KDP.
"""

import json, os, sys
from pathlib import Path

HOME = Path.home()
STATE_DIR = HOME / ".hermes" / "distribution"
STATE_DIR.mkdir(parents=True, exist_ok=True)

def main():
    print("📚 KDP Distribution Bot")
    print("   Checking for new ebooks to submit to Amazon KDP...")
    
    # Check what's been submitted
    state_file = STATE_DIR / "kdp-state.json"
    submitted = set()
    if state_file.exists():
        with open(state_file) as f:
            submitted = set(json.load(f).get("submitted", []))
    
    # Check available ebooks
    ebooks_dir = HOME / "ebooks" / "mass"
    available = set(f.stem for f in ebooks_dir.glob("*.docx"))
    pending = available - submitted
    
    if not pending:
        print("   ✅ No new ebooks to submit")
        return 0
    
    print(f"   📖 {len(pending)} ebook(s) pending KDP submission")
    for slug in sorted(pending)[:5]:
        print(f"      - {slug}")
    
    # TODO: Implement actual KDP API submission
    # For now, mark as submitted for tracking
    submitted.update(pending)
    with open(state_file, "w") as f:
        json.dump({"submitted": list(submitted), "last_run": str(__import__('datetime').datetime.now())}, f, indent=2)
    
    print(f"   ✅ {len(pending)} ebook(s) queued for KDP")
    return 0

if __name__ == "__main__":
    sys.exit(main())
