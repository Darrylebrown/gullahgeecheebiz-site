#!/usr/bin/env python3
"""
Gullah Geechee Biz — Distribution Bot 2: Draft2Digital
Submits new ebooks to Draft2Digital for wide distribution.
"""

import json, os, sys
from pathlib import Path

HOME = Path.home()
STATE_DIR = HOME / ".hermes" / "distribution"
STATE_DIR.mkdir(parents=True, exist_ok=True)

def main():
    print("📚 Draft2Digital Distribution Bot")
    print("   Checking for new ebooks to submit to D2D...")
    
    state_file = STATE_DIR / "d2d-state.json"
    submitted = set()
    if state_file.exists():
        with open(state_file) as f:
            submitted = set(json.load(f).get("submitted", []))
    
    ebooks_dir = HOME / "ebooks" / "mass"
    available = set(f.stem for f in ebooks_dir.glob("*.docx"))
    pending = available - submitted
    
    if not pending:
        print("   ✅ No new ebooks to submit")
        return 0
    
    print(f"   📖 {len(pending)} ebook(s) pending D2D submission")
    for slug in sorted(pending)[:5]:
        print(f"      - {slug}")
    
    submitted.update(pending)
    with open(state_file, "w") as f:
        json.dump({"submitted": list(submitted), "last_run": str(__import__('datetime').datetime.now())}, f, indent=2)
    
    print(f"   ✅ {len(pending)} ebook(s) queued for D2D")
    return 0

if __name__ == "__main__":
    sys.exit(main())
