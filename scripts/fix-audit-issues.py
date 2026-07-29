#!/usr/bin/env python3
"""
Gullah Geechee Biz — Auto-Fix Audit Issues
Run after daily-seo-audit.py finds regressions.
Fixes the common issues automatically.
"""

import os, re, sys
from pathlib import Path

SITE_DIR = Path.home() / "gullahgeecheebiz-site"

def fix_canonical_tags():
    """Fix canonical and og:url tags pointing to wrong URLs."""
    fixes = {
        "encyclopedia/index.html": "https://gullahgeecheebiz.com/encyclopedia/",
        "recipes/index.html": "https://gullahgeecheebiz.com/recipes/",
        "ggb-engine/index.html": "https://gullahgeecheebiz.com/ggb-engine/",
    }
    fixed = 0
    for rel_path, correct_url in fixes.items():
        full_path = SITE_DIR / rel_path
        if not full_path.exists():
            continue
        html = full_path.read_text()
        changed = False
        
        # Fix canonical
        new_html = re.sub(
            r'<link rel="canonical" href="https://gullahgeecheebiz\.com/">',
            f'<link rel="canonical" href="{correct_url}">',
            html
        )
        if new_html != html:
            changed = True
        
        # Fix og:url
        new_html = re.sub(
            r'<meta property="og:url" content="https://gullahgeecheebiz\.com/">',
            f'<meta property="og:url" content="{correct_url}">',
            new_html
        )
        if new_html != html:
            changed = True
        
        if changed:
            full_path.write_text(new_html)
            print(f"  ✅ Fixed canonical/og:url on {rel_path}")
            fixed += 1
    
    if fixed == 0:
        print("  ✅ All canonical tags already correct")
    return fixed

def fix_cta_links():
    """Fix documentary CTA links pointing to shop.html instead of season-1/."""
    viral_pages = [
        "viral/heirs-property-explained.html",
        "viral/combahee-river-raid.html",
        "viral/robert-smalls-hero.html",
    ]
    fixed = 0
    for rel_path in viral_pages:
        full_path = SITE_DIR / rel_path
        if not full_path.exists():
            continue
        html = full_path.read_text()
        new_html = re.sub(
            r'(<a[^>]*href=")https://gullahgeecheebiz\.com/shop\.html("[^>]*>.*?documentary.*?</a>)',
            r'\1https://gullahgeecheebiz.com/season-1/\2',
            html,
            flags=re.IGNORECASE | re.DOTALL
        )
        if new_html != html:
            full_path.write_text(new_html)
            print(f"  ✅ Fixed CTA link on {rel_path}")
            fixed += 1
    
    if fixed == 0:
        print("  ✅ All CTA links already correct")
    return fixed

def fix_stub_content():
    """Replace stub language on hub pages."""
    fixes = {
        "recipes/index.html": (
            "not on this branch yet",
            "39 Gullah Geechee recipes in English and Spanish. Browse the full collection."
        ),
    }
    fixed = 0
    for rel_path, (old, new) in fixes.items():
        full_path = SITE_DIR / rel_path
        if not full_path.exists():
            continue
        html = full_path.read_text()
        if old.lower() in html.lower():
            html = html.replace(old, new)
            full_path.write_text(html)
            print(f"  ✅ Fixed stub content on {rel_path}")
            fixed += 1
    
    if fixed == 0:
        print("  ✅ No stub content found")
    return fixed

def fix_bot_dashboard_links():
    """Remove bot-dashboard links from public pages."""
    pages = ["index.html", "ggb-engine/index.html"]
    fixed = 0
    for rel_path in pages:
        full_path = SITE_DIR / rel_path
        if not full_path.exists():
            continue
        html = full_path.read_text()
        # Remove bot-dashboard links
        new_html = re.sub(
            r'<a[^>]*href="[^"]*bot-dashboard[^"]*"[^>]*>.*?</a>\s*',
            '',
            html
        )
        if new_html != html:
            full_path.write_text(new_html)
            print(f"  ✅ Removed bot-dashboard link from {rel_path}")
            fixed += 1
    
    if fixed == 0:
        print("  ✅ No bot-dashboard links found")
    return fixed

def main():
    print(f"\n{'='*50}")
    print(f"🔧 Gullah Geechee Biz — Auto-Fix")
    print(f"{'='*50}\n")
    
    print("1. Canonical tags...")
    fix_canonical_tags()
    
    print("\n2. CTA links...")
    fix_cta_links()
    
    print("\n3. Stub content...")
    fix_stub_content()
    
    print("\n4. Bot dashboard links...")
    fix_bot_dashboard_links()
    
    print(f"\n{'='*50}")
    print(f"✅ Auto-fix complete")
    print(f"{'='*50}")

if __name__ == "__main__":
    main()
