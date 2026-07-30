#!/usr/bin/env python3
"""
Gullah Geechee Biz — Distribution Bot 4: Own Site
Actually deploys content: regenerates sitemap, runs tests, reports status.
"""

import json, os, subprocess, sys
from pathlib import Path
from datetime import datetime

HOME = Path.home()
SITE_DIR = HOME / "gullahgeecheebiz-site"
STATE_DIR = HOME / ".hermes" / "distribution"

def main():
    print("🌐 Site Distribution Bot")
    print("   Deploying new content to gullahgeecheebiz.com...")
    
    results = {}
    
    # 1. Regenerate sitemap
    sitemap_script = SITE_DIR / "scripts" / "regenerate-sitemap.py"
    if sitemap_script.exists():
        result = subprocess.run(["python3", str(sitemap_script)], capture_output=True, text=True, timeout=30)
        results["sitemap"] = "ok" if result.returncode == 0 else "failed"
        print(f"   {'✅' if result.returncode == 0 else '❌'} Sitemap: {result.stdout.strip()}")
    
    # 2. Run smoke tests
    result = subprocess.run(["npm", "test"], cwd=str(SITE_DIR), capture_output=True, text=True, timeout=60)
    results["smoke_tests"] = "ok" if result.returncode == 0 else "failed"
    passed = result.stdout.count("✅")
    failed = result.stdout.count("❌")
    print(f"   {'✅' if result.returncode == 0 else '❌'} Smoke tests: {passed} passed, {failed} failed")
    
    # 3. Check git status
    result = subprocess.run(["git", "status", "--short"], cwd=str(SITE_DIR), capture_output=True, text=True, timeout=10)
    changes = result.stdout.strip()
    if changes:
        lines = changes.split("\n")
        print(f"   📝 {len(lines)} uncommitted change(s)")
        for line in lines[:5]:
            print(f"      {line}")
    else:
        print(f"   ✅ Working tree clean")
    
    # 4. Check site is live
    result = subprocess.run(["curl", "-s", "--max-time", "5", "-o", "/dev/null", "-w", "%{http_code}", 
                           "https://gullahgeecheebiz.com/"], capture_output=True, text=True, timeout=10)
    status = result.stdout.strip()
    print(f"   {'✅' if status == '200' else '❌'} Site: HTTP {status}")
    
    # 5. Check key pages
    pages = ["/ebooks/", "/recipes/", "/membership/", "/shop/"]
    for page in pages:
        result = subprocess.run(["curl", "-s", "--max-time", "5", "-o", "/dev/null", "-w", "%{http_code}",
                               f"https://gullahgeecheebiz.com{page}"], capture_output=True, text=True, timeout=10)
        s = result.stdout.strip()
        if s != "200":
            print(f"   ⚠️  {page}: HTTP {s}")
    
    # Save state
    state_file = STATE_DIR / "site-state.json"
    with open(state_file, "w") as f:
        json.dump({"last_run": str(datetime.now()), "results": results}, f, indent=2)
    
    print(f"\n   ✅ Site distribution check complete")
    return 0 if results.get("smoke_tests") == "ok" else 1

if __name__ == "__main__":
    sys.exit(main())
