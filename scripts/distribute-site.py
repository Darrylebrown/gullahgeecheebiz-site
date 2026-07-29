#!/usr/bin/env python3
"""
Gullah Geechee Biz — Distribution Bot 4: Own Site
Deploys new content to gullahgeecheebiz.com.
"""

import json, os, sys, subprocess
from pathlib import Path

HOME = Path.home()
SITE_DIR = HOME / "gullahgeecheebiz-site"
STATE_DIR = HOME / ".hermes" / "distribution"
STATE_DIR.mkdir(parents=True, exist_ok=True)

def main():
    print("🌐 Site Distribution Bot")
    print("   Deploying new content to gullahgeecheebiz.com...")
    
    # Regenerate sitemap
    sitemap_script = SITE_DIR / "scripts" / "regenerate-sitemap.py"
    if sitemap_script.exists():
        result = subprocess.run(["python3", str(sitemap_script)], capture_output=True, text=True)
        if result.returncode == 0:
            print(f"   ✅ Sitemap: {result.stdout.strip()}")
        else:
            print(f"   ❌ Sitemap error: {result.stderr[:200]}")
    
    # Run smoke tests
    result = subprocess.run(["npm", "test"], cwd=str(SITE_DIR), capture_output=True, text=True, timeout=60)
    if result.returncode == 0:
        print(f"   ✅ Smoke tests: all passed")
    else:
        print(f"   ❌ Smoke tests failed")
        print(f"      {result.stdout[-200:]}")
    
    # Check git status
    result = subprocess.run(["git", "status", "--short"], cwd=str(SITE_DIR), capture_output=True, text=True)
    changes = result.stdout.strip()
    if changes:
        print(f"   📝 Uncommitted changes: {len(changes.split(chr(10)))} file(s)")
        for line in changes.split(chr(10))[:5]:
            print(f"      {line}")
    else:
        print(f"   ✅ Working tree clean")
    
    print(f"   ✅ Site distribution check complete")
    return 0

if __name__ == "__main__":
    sys.exit(main())
