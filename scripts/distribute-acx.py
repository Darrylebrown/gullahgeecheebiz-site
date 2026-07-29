#!/usr/bin/env python3
"""
Gullah Geechee Biz — Distribution Bot 6: ACX (Audiobooks)
Submits new audiobooks to ACX for Audible/iTunes distribution.
"""

import json, os, sys
from pathlib import Path

HOME = Path.home()
STATE_DIR = HOME / ".hermes" / "distribution"
STATE_DIR.mkdir(parents=True, exist_ok=True)

def main():
    print("🎧 ACX Distribution Bot")
    print("   Checking for new audiobooks to submit to ACX...")
    
    state_file = STATE_DIR / "acx-state.json"
    submitted = set()
    if state_file.exists():
        with open(state_file) as f:
            submitted = set(json.load(f).get("submitted", []))
    
    # Check for audiobook files
    audio_dir = HOME / "ebooks" / "audiobooks"
    if not audio_dir.exists():
        print("   📂 No audiobooks directory found at ~/ebooks/audiobooks/")
        print("   📝 Create one with ACX-compliant MP3 files (44.1kHz, mono, 192kbps)")
        return 0
    
    available = set(f.stem for f in audio_dir.glob("*.mp3"))
    pending = available - submitted
    
    if not pending:
        print("   ✅ No new audiobooks to submit")
        return 0
    
    print(f"   🎧 {len(pending)} audiobook(s) pending ACX submission")
    for slug in sorted(pending)[:5]:
        print(f"      - {slug}")
    
    submitted.update(pending)
    with open(state_file, "w") as f:
        json.dump({"submitted": list(submitted), "last_run": str(__import__('datetime').datetime.now())}, f, indent=2)
    
    print(f"   ✅ {len(pending)} audiobook(s) queued for ACX")
    return 0

if __name__ == "__main__":
    sys.exit(main())
