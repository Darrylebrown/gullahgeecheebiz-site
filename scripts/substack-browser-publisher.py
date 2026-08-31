#!/usr/bin/env python3
"""
GGB Substack Publisher — Browser Automation Mode
Uses Playwright to authenticate and publish Substack posts.
"""
import json
import os
import sys
import time
from pathlib import Path
from datetime import datetime, timezone

try:
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False

# Configuration
SITE_DIR = Path("/Users/darrylsmac/gullahgeecheebiz-site")
DRAFTS_DIR = SITE_DIR / "publish" / "substack-drafts"
OUTPUT_DIR = SITE_DIR / "publish" / "substack-published"
EVENT_STREAM = SITE_DIR / "publish" / "event_stream.jsonl"
SUBSTACK_URL = "https://kofigullahgeecheebiz.substack.com"
DASHBOARD_URL = f"{SUBSTACK_URL}/dashboard"

def htmlify_body(text):
    """Convert markdown-style text to HTML."""
    lines = text.split("\n")
    html_lines = []
    in_list = False
    
    for line in lines:
        line = line.strip()
        if not line:
            if in_list:
                html_lines.append("</ul>")
                in_list = False
            continue
        
        line = line.replace("**", "")
        
        if line.startswith("### "):
            html_lines.append(f"<h3>{line[4:]}</h3>")
        elif line.startswith("## "):
            html_lines.append(f"<h2>{line[3:]}</h2>")
        elif line.startswith("# "):
            html_lines.append(f"<h1>{line[2:]}</h1>")
        elif line.startswith("- ") or line.startswith("* "):
            if not in_list:
                html_lines.append("<ul>")
                in_list = True
            html_lines.append(f"<li>{line[2:]}</li>")
        elif line == "---":
            html_lines.append("<hr>")
        else:
            if in_list:
                html_lines.append("</ul>")
                in_list = False
            html_lines.append(f"<p>{line}</p>")
    
    if in_list:
        html_lines.append("</ul>")
    
    return "\n".join(html_lines)

def record_event(event_type, payload):
    """Record to event stream."""
    try:
        event = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "source_bot": "SUBSTACK_GOAL",
            "action": event_type,
            "detail": json.dumps(payload) if isinstance(payload, dict) else str(payload)
        }
        with open(EVENT_STREAM, "a") as f:
            f.write(json.dumps(event) + "\n")
    except Exception as e:
        print(f"  Event record failed: {e}")

def find_drafts():
    """Find pending draft JSON files."""
    drafts = []
    for f in sorted(DRAFTS_DIR.glob("*.json")):
        if f.stem.startswith("202"):
            with open(f) as fp:
                draft = json.load(fp)
                draft["_file"] = str(f)
                drafts.append(draft)
    return drafts

def publish_via_browser(draft):
    """Publish a single draft via browser automation."""
    if not PLAYWRIGHT_AVAILABLE:
        return False, "Playwright not available"
    
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context()
            page = context.new_page()
            
            # Navigate to dashboard
            print(f"    Navigating to Substack dashboard...")
            page.goto(DASHBOARD_URL, wait_until="networkidle", timeout=60000)
            time.sleep(3)
            
            # Check if logged in
            current_url = page.url
            if "login" in current_url.lower() or "sign" in current_url.lower():
                print(f"    ❌ Not logged in. Need authentication.")
                browser.close()
                return False, "Not authenticated - need manual login or cookie"
            
            # Click New Post
            print(f"    Looking for 'New Post' button...")
            try:
                page.click('text=New Post', timeout=10000)
            except:
                try:
                    page.click('button:has-text("New")', timeout=10000)
                except:
                    print(f"    Could not find New Post button")
                    browser.close()
                    return False, "Cannot find New Post button"
            
            time.sleep(2)
            
            # Fill in title
            title = draft.get("title", "Untitled")
            print(f"    Filling title: {title[:40]}...")
            try:
                page.fill('input[placeholder*="Title"]', title)
            except:
                try:
                    page.fill('input[type="text"]', title)
                except:
                    print(f"    Could not fill title field")
            
            # Fill in subtitle
            subtitle = draft.get("subtitle", "")
            if subtitle:
                print(f"    Filling subtitle...")
                try:
                    page.fill('input[placeholder*="Subtitle"]', subtitle)
                except:
                    pass
            
            # Fill in body content
            body_html = htmlify_body(draft.get("body", ""))
            print(f"    Filling content ({len(body_html)} chars)...")
            
            # Try to find the editor
            try:
                # Wait for editor to load
                page.wait_for_selector('.ProseMirror, [contenteditable="true"], .editor-container', timeout=15000)
                time.sleep(1)
                
                # Click in editor and paste content
                page.click('.ProseMirror, [contenteditable="true"]', timeout=5000)
                time.sleep(0.5)
                
                # Use JavaScript to set content
                escaped_html = body_html.replace('`', '\\`')
                page.evaluate(f"""
                    const editor = document.querySelector('.ProseMirror, [contenteditable="true"]');
                    if (editor) {{
                        editor.innerHTML = `{escaped_html}`;
                        editor.dispatchEvent(new Event('input', {{ bubbles: true }}));
                        editor.dispatchEvent(new Event('change', {{ bubbles: true }}));
                    }}
                """)
                print(f"    ✓ Content filled")
            except Exception as e:
                print(f"    ⚠ Editor interaction failed: {e}")
            
            # Set to paid/free
            is_premium = draft.get("is_premium", False)
            if is_premium:
                print(f"    Setting as paid post...")
                try:
                    page.click('text=Paid', timeout=5000)
                except:
                    try:
                        page.click('label:has-text("Paid")', timeout=5000)
                    except:
                        pass
            
            # Publish
            print(f"    Publishing...")
            try:
                page.click('button:has-text("Publish")', timeout=10000)
                time.sleep(3)
                
                # Check for success
                success_url = page.url
                if "/p/" in success_url or "published" in success_url.lower():
                    print(f"    ✓ Published successfully!")
                    print(f"    URL: {success_url}")
                    browser.close()
                    return True, success_url
                else:
                    # Maybe it's a draft
                    print(f"    ⚠ Published as draft: {success_url}")
                    browser.close()
                    return True, success_url
                    
            except Exception as e:
                print(f"    ❌ Publish failed: {e}")
                browser.close()
                return False, str(e)
            
    except Exception as e:
        print(f"    ❌ Browser error: {e}")
        return False, str(e)

def main():
    print("=" * 60)
    print("  GGB SUBSTACK PUBLISHER — Browser Mode")
    print("=" * 60)
    print(f"  Time: {datetime.now().isoformat()}")
    print()
    
    # Find drafts
    drafts = find_drafts()
    print(f"  Found {len(drafts)} drafts to publish")
    for d in drafts:
        print(f"    • {d.get('title', 'Untitled')[:50]}... (premium={d.get('is_premium', False)})")
    print()
    
    if not drafts:
        print("  No drafts found.")
        return
    
    if not PLAYWRIGHT_AVAILABLE:
        print("  ❌ Playwright not installed. Run: npm install @playwright/test && npx playwright install")
        return
    
    # Publish each draft
    published = []
    failed = []
    
    for i, draft in enumerate(drafts):
        print(f"  [{i+1}/{len(drafts)}] Publishing: {draft.get('title', 'Untitled')[:40]}...")
        
        success, msg = publish_via_browser(draft)
        
        if success:
            print(f"    ✓ Success: {msg}")
            published.append({
                "slug": draft.get("slug"),
                "title": draft.get("title"),
                "url": msg,
                "is_premium": draft.get("is_premium", False)
            })
            
            # Move draft file
            output_dir = OUTPUT_DIR / datetime.now().strftime("%Y%m%d")
            output_dir.mkdir(parents=True, exist_ok=True)
            src = Path(draft["_file"])
            dst = output_dir / src.name
            if src.exists():
                src.rename(dst)
        else:
            print(f"    ❌ Failed: {msg}")
            failed.append(draft.get("slug"))
        
        # Break between posts
        if i < len(drafts) - 1:
            print(f"    Waiting 5 seconds before next post...")
            time.sleep(5)
    
    # Summary
    print()
    print("=" * 60)
    print(f"  RESULTS: {len(published)} published, {len(failed)} failed")
    print("=" * 60)
    
    for p in published:
        print(f"  ✓ {p['title'][:50]}...")
        print(f"    {p['url']}")
        print(f"    Type: {'Premium' if p['is_premium'] else 'Free'}")
        print()
    
    for f in failed:
        print(f"  ❌ {f}")
    
    # Record to event stream
    record_event("substack_publish", {
        "timestamp": datetime.now().isoformat(),
        "published": len(published),
        "failed": len(failed),
        "posts": published
    })
    
    print()
    print("  Done!")

if __name__ == "__main__":
    main()
