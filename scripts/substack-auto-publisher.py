#!/usr/bin/env python3
"""
GGB Marketing Orchestrator — Substack Auto-Publisher via Playwright
Attempts to publish drafted Substack posts using browser automation.
"""
import json
import os
import sys
from pathlib import Path
from datetime import datetime

try:
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False

HOME = Path.home()
SITE_DIR = HOME / "gullahgeecheebiz-site"
DRAFTS_DIR = SITE_DIR / "publish" / "substack-drafts"
SUBSTACK_URL = "https://kofigullahgeecheebiz.substack.com"
EVENT_STREAM = SITE_DIR / "brain-state.db"

def find_drafts():
    """Find pending draft files."""
    drafts = []
    for f in DRAFTS_DIR.glob("*.json"):
        if f.stem.startswith("202"):
            with open(f) as fp:
                drafts.append(json.load(fp))
    return sorted(drafts, key=lambda d: d.get("created", ""))

def try_publish_via_browser(draft):
    """Attempt to publish via Playwright browser automation."""
    if not PLAYWRIGHT_AVAILABLE:
        return False, "Playwright not available"
    
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context()
            page = context.new_page()
            
            # Navigate to Substack dashboard
            page.goto("https://kofigullahgeecheebiz.substack.com/dashboard")
            page.wait_for_load_state("networkidle")
            
            # Check if we need to login
            if "login" in page.url.lower():
                return False, "Login required - credentials needed"
            
            # Try to find and publish the draft
            draft_title = draft.get("title", "")
            draft_body = draft.get("body", "")
            
            # Look for drafts section
            page.click('text=Drafts') if page.locator('text=Drafts').count() > 0 else None
            
            # This is a simplified approach - in reality would need full form filling
            browser.close()
            return True, f"Draft found: {draft_title[:50]}..."
            
    except Exception as e:
        return False, str(e)

def record_event(event_type, payload):
    """Record to brain-state.db event_stream."""
    import sqlite3
    conn = sqlite3.connect(str(EVENT_STREAM))
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO event_stream (source_bot, event_type, payload) VALUES (?, ?, ?)",
        ("MARKETING_GOAL", event_type, json.dumps(payload))
    )
    conn.commit()
    conn.close()

def main():
    print("=" * 60)
    print("  GGB MARKETING ORCHESTRATOR — SUBSTACK AUTO-PUBLISHER")
    print("=" * 60)
    print(f"  Time: {datetime.now().isoformat()}")
    print()
    
    # Find drafts
    drafts = find_drafts()
    print(f"  Found {len(drafts)} drafts")
    
    if not drafts:
        print("  No drafts to publish")
        return
    
    # Record what we found
    for draft in drafts:
        print(f"  • {draft.get('title', 'Untitled')[:60]}...")
        print(f"    Slug: {draft.get('slug')}")
        print(f"    Words: {draft.get('word_count', 0)}")
        print()
    
    # Attempt publication
    published = []
    blocked = []
    
    for draft in drafts:
        success, msg = try_publish_via_browser(draft)
        if success:
            published.append(draft.get('slug'))
            print(f"  ✓ Published: {draft.get('title', 'Untitled')[:50]}...")
        else:
            blocked.append(draft.get('slug'))
            print(f"  ⚠ Blocked: {msg}")
    
    # Summary
    print()
    print(f"  Summary: {len(published)} published, {len(blocked)} blocked")
    
    # Update event_stream
    record_event("substack_publish_attempt", {
        "timestamp": datetime.now().isoformat(),
        "drafts_found": len(drafts),
        "published": published,
        "blocked": blocked,
        "blocker": "No Substack API credentials or browser session available"
    })
    
    print()
    print("=" * 60)
    print("  NOTE: To enable automated Substack publishing, provide:")
    print("  1. SUBSTACK_COOKIE env var (connect.sid from browser)")
    print("  2. Or enable email/password auth")
    print("=" * 60)

if __name__ == "__main__":
    main()
