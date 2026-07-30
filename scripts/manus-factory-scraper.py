#!/usr/bin/env python3
"""
Gullah Geechee Biz — Manus Factory Scraper
Visits all Manus share links weekly and pulls production data.
Saves whatever is accessible from each session replay.
"""

import json, os, sys, subprocess, time
from pathlib import Path
from datetime import datetime

HOME = Path.home()
DATA_DIR = HOME / ".hermes" / "manus-factories"
DATA_DIR.mkdir(parents=True, exist_ok=True)

MANUS_LINKS = [
    "https://manus.im/share/5MitUnfiqChLw9yfUEwYVM",
    "https://manus.im/share/mKtSRrjZL6h3CTDAvtxTp5",
    "https://manus.im/share/jmVUaxycud6TSfwPiCe5Jq",
    "https://manus.im/share/xsvp8hjDGwPTcCkEkq6MJS",
    "https://manus.im/share/u4qMxnRtrj8UxPRr9QyAqS",
    "https://manus.im/share/ZTitawt3NNu34X7gyiXbH8",
    "https://manus.im/share/ArgjBakzJn8mRC56y4j5VQ",
    "https://manus.im/share/dzzBkc5dPFuNoEMNLi3uNV",
    "https://manus.im/share/5xz4NS9sZUTsYuFRcKXoZC",
    "https://manus.im/share/rZiP3PrBtC2a1jJuDG2DpV",
    "https://manus.im/share/m7JtZejLPRwaa3Y8oNZt53",
    "https://manus.im/share/hr7B7tdFXLveWsAiCbAmJ8",
    "https://manus.im/share/LahUi9KM54zvoSvwdvzMaJ",
    "https://manus.im/share/LLuawnEF7LLoJYeJyvRK2s",
    "https://manus.im/share/S5d7AbeKYkDaGavhB47p6G",
]

def fetch_link(url):
    """Fetch a Manus share link and extract content."""
    try:
        result = subprocess.run(
            ["curl", "-sL", "--max-time", "15", url],
            capture_output=True, text=True
        )
        return {"url": url, "status": result.returncode, "content": result.stdout[:2000]}
    except Exception as e:
        return {"url": url, "status": -1, "error": str(e)}

def main():
    today = datetime.now().strftime("%Y-%m-%d")
    print(f"🏭 Gullah Geechee Biz — Manus Factory Scraper")
    print(f"   Date: {today}")
    print(f"   Factories: {len(MANUS_LINKS)}")
    print()
    
    results = []
    for i, url in enumerate(MANUS_LINKS, 1):
        print(f"  [{i}/{len(MANUS_LINKS)}] Fetching {url.split('/')[-1][:12]}...", end=" ", flush=True)
        data = fetch_link(url)
        results.append(data)
        
        if data.get("content"):
            # Extract title or key info
            lines = data["content"].strip().split("\n")
            title = lines[0][:80] if lines else "no content"
            print(f"✅ {title}")
        else:
            print(f"⚠️  no content")
        
        time.sleep(1)  # Be polite
    
    # Save results
    output_file = DATA_DIR / f"factory-snapshot-{today}.json"
    with open(output_file, "w") as f:
        json.dump({"date": today, "factories": results}, f, indent=2)
    
    # Summary
    accessible = sum(1 for r in results if r.get("content") and len(r["content"]) > 100)
    print(f"\n📊 Summary: {accessible}/{len(MANUS_LINKS)} factories accessible")
    print(f"   Saved to: {output_file}")
    
    return 0 if accessible > 0 else 1

if __name__ == "__main__":
    sys.exit(main())
