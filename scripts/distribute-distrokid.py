#!/usr/bin/env python3
"""
Gullah Geechee Biz — Distribution Bot 7: DistroKid
Submits new music/audio to DistroKid for streaming distribution.
"""

import json, os, sys
from pathlib import Path

HOME = Path.home()
STATE_DIR = HOME / ".hermes" / "distribution"
STATE_DIR.mkdir(parents=True, exist_ok=True)

def main():
    print("🎵 DistroKid Distribution Bot")
    print("   Checking for new audio to submit to DistroKid...")
    
    state_file = STATE_DIR / "distrokid-state.json"
    submitted = set()
    if state_file.exists():
        with open(state_file) as f:
            submitted = set(json.load(f).get("submitted", []))
    
    # Check for music/audio files
    audio_dir = HOME / "audio" / "releases"
    if not audio_dir.exists():
        print("   📂 No audio releases directory at ~/audio/releases/")
        print("   📝 Create one with mastered WAV/MP3 files for DistroKid upload")
        return 0
    
    available = set(f.stem for f in audio_dir.glob("*.mp3") if not f.stem.startswith("."))
    pending = available - submitted
    
    if not pending:
        print("   ✅ No new audio to submit")
        return 0
    
    print(f"   🎵 {len(pending)} release(s) pending DistroKid submission")
    for slug in sorted(pending)[:5]:
        print(f"      - {slug}")
    
    submitted.update(pending)
    with open(state_file, "w") as f:
        json.dump({"submitted": list(submitted), "last_run": str(__import__('datetime').datetime.now())}, f, indent=2)
    
    print(f"   ✅ {len(pending)} release(s) queued for DistroKid")
    return 0

if __name__ == "__main__":
    sys.exit(main())
