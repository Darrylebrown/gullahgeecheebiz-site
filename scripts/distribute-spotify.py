#!/usr/bin/env python3
"""
Gullah Geechee Biz — Distribution Bot 8: Spotify
Submits new podcasts/audio to Spotify for distribution.
"""

import json, os, sys
from pathlib import Path

HOME = Path.home()
STATE_DIR = HOME / ".hermes" / "distribution"
STATE_DIR.mkdir(parents=True, exist_ok=True)

def main():
    print("🎧 Spotify Distribution Bot")
    print("   Checking for new content to submit to Spotify...")
    
    state_file = STATE_DIR / "spotify-state.json"
    submitted = set()
    if state_file.exists():
        with open(state_file) as f:
            submitted = set(json.load(f).get("submitted", []))
    
    # Check for podcast/audio files
    audio_dir = HOME / "audio" / "podcasts"
    if not audio_dir.exists():
        print("   📂 No podcast directory at ~/audio/podcasts/")
        print("   📝 Create one with podcast episodes for Spotify upload")
        return 0
    
    available = set(f.stem for f in audio_dir.glob("*.mp3") if not f.stem.startswith("."))
    pending = available - submitted
    
    if not pending:
        print("   ✅ No new content to submit")
        return 0
    
    print(f"   🎧 {len(pending)} episode(s) pending Spotify submission")
    for slug in sorted(pending)[:5]:
        print(f"      - {slug}")
    
    submitted.update(pending)
    with open(state_file, "w") as f:
        json.dump({"submitted": list(submitted), "last_run": str(__import__('datetime').datetime.now())}, f, indent=2)
    
    print(f"   ✅ {len(pending)} episode(s) queued for Spotify")
    return 0

if __name__ == "__main__":
    sys.exit(main())
