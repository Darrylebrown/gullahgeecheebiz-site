#!/usr/bin/env python3
"""
GGB Substack Publisher — Authenticated API Publisher
Uses Substack internal API with session cookie for automated publishing.
"""
import json
import os
import sys
import time
import requests
from pathlib import Path
from datetime import datetime, timezone

# Configuration
SITE_DIR = Path("/Users/darrylsmac/gullahgeecheebiz-site")
DRAFTS_DIR = SITE_DIR / "publish" / "substack-drafts"
OUTPUT_DIR = SITE_DIR / "publish" / "substack-published"
COOKIE_FILE = SITE_DIR / ".substack_cookie"
EVENT_STREAM = SITE_DIR / "publish" / "event_stream.jsonl"
SUBSTACK_HOST = "kofigullahgeecheebiz.substack.com"

def load_cookie():
    """Load Substack session cookie from file or env."""
    # Check env first
    cookie = os.environ.get("SUBSTACK_COOKIE")
    if cookie:
        return cookie
    
    # Check file
    if COOKIE_FILE.exists():
        return COOKIE_FILE.read_text().strip()
    
    return None

def api_get(path, cookie):
    """Make authenticated GET request."""
    headers = {
        "Cookie": f"connect.sid={cookie}; substack.sid={cookie}",
        "Accept": "application/json",
    }
    url = f"https://{SUBSTACK_HOST}{path}"
    try:
        r = requests.get(url, headers=headers, timeout=30)
        return r.json() if r.status_code == 200 else None
    except Exception as e:
        print(f"  GET {path} failed: {e}")
        return None

def api_post(path, cookie, data):
    """Make authenticated POST request."""
    headers = {
        "Cookie": f"connect.sid={cookie}; substack.sid={cookie}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    url = f"https://{SUBSTACK_HOST}{path}"
    try:
        r = requests.post(url, headers=headers, json=data, timeout=30)
        if r.status_code in [200, 201]:
            return r.json()
        print(f"  POST {path} failed: {r.status_code} - {r.text[:200]}")
        return None
    except Exception as e:
        print(f"  POST {path} failed: {e}")
        return None

def get_profile(cookie):
    """Get user profile and publications."""
    return api_get("/api/v1/user/profile/self", cookie)

def list_drafts(cookie):
    """List drafts for the publication."""
    return api_get("/api/v1/drafts", cookie)

def create_draft(cookie, title, subtitle, body, is_premium=False, tags=None):
    """Create a draft post."""
    data = {
        "draft_title": title,
        "draft_subtitle": subtitle,
        "draft_body": body,
        "type": "newsletter",
    }
    if tags:
        data["tags"] = tags
    if is_premium:
        data["is_paid"] = True
    
    result = api_post("/api/v1/drafts", cookie, data)
    return result

def publish_draft(cookie, draft_id):
    """Publish a draft by ID."""
    result = api_post(f"/api/v1/drafts/{draft_id}/publish", cookie, {})
    return result

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

def htmlify_body(text):
    """Convert markdown-style text to HTML for Substack."""
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
        
        # Bold text **text**
        line = line.replace("**", "")
        
        # Headers
        if line.startswith("### "):
            html_lines.append(f"<h3>{line[4:]}</h3>")
        elif line.startswith("## "):
            html_lines.append(f"<h2>{line[3:]}</h2>")
        elif line.startswith("# "):
            html_lines.append(f"<h1>{line[2:]}</h1>")
        # Lists
        elif line.startswith("- ") or line.startswith("* "):
            if not in_list:
                html_lines.append("<ul>")
                in_list = True
            html_lines.append(f"<li>{line[2:]}</li>")
        # Horizontal rule
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

def main():
    print("=" * 60)
    print("  GGB SUBSTACK PUBLISHER — API Mode")
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
        print("  No drafts found. Generating new content...")
        return
    
    # Try to authenticate
    cookie = load_cookie()
    if not cookie:
        print("  ❌ No Substack cookie found.")
        print("  To get one:")
        print("    1. Log into https://kofigullahgeecheebiz.substack.com in Chrome")
        print("    2. Open DevTools → Application → Cookies → substack.com")
        print("    3. Copy 'connect.sid' value")
        print("    4. Save to .substack_cookie file")
        print()
        
        # Try to get cookie via browser automation
        print("  Attempting browser automation to obtain session...")
        return
    
    print(f"  ✓ Cookie loaded ({len(cookie)} chars)")
    
    # Test auth
    profile = get_profile(cookie)
    if not profile:
        print("  ❌ Authentication failed. Cookie may be expired.")
        return
    
    print(f"  ✓ Authenticated as: {profile.get('name', 'Unknown')}")
    
    # Get publications
    pubs = profile.get("publicationUsers", [])
    if not pubs:
        print("  ❌ No publications found for this account.")
        return
    
    # Find our publication
    target_pub = None
    for pub in pubs:
        if pub.get("slug") == "kofigullahgeecheebiz":
            target_pub = pub
            break
    if not target_pub:
        target_pub = pubs[0]
    
    print(f"  ✓ Publication: {target_pub.get('name', 'Unknown')}")
    print()
    
    # Publish each draft
    published = []
    failed = []
    
    for draft in drafts:
        print(f"  Publishing: {draft.get('title', 'Untitled')[:60]}...")
        
        # Convert body to HTML
        body_html = htmlify_body(draft.get("body", ""))
        
        # Create draft via API
        result = create_draft(
            cookie,
            title=draft.get("title", "Untitled"),
            subtitle=draft.get("subtitle", ""),
            body=body_html,
            is_premium=draft.get("is_premium", False),
            tags=draft.get("tags", [])
        )
        
        if not result:
            print(f"    ❌ Failed to create draft")
            failed.append(draft.get("slug"))
            continue
        
        draft_id = result.get("id") or result.get("draft_id")
        if not draft_id:
            print(f"    ❌ No draft ID returned")
            failed.append(draft.get("slug"))
            continue
        
        print(f"    ✓ Draft created: {draft_id}")
        
        # Publish it
        time.sleep(1)  # Be nice to the API
        pub_result = publish_draft(cookie, draft_id)
        
        if pub_result:
            post_url = pub_result.get("url") or f"https://{SUBSTACK_HOST}/p/{draft.get('slug')}"
            print(f"    ✓ Published: {post_url}")
            published.append({
                "slug": draft.get("slug"),
                "title": draft.get("title"),
                "url": post_url,
                "is_premium": draft.get("is_premium", False)
            })
            
            # Move draft file to published
            output_dir = OUTPUT_DIR / datetime.now().strftime("%Y%m%d")
            output_dir.mkdir(parents=True, exist_ok=True)
            src = Path(draft["_file"])
            dst = output_dir / src.name
            if src.exists():
                src.rename(dst)
        else:
            print(f"    ❌ Failed to publish")
            failed.append(draft.get("slug"))
        
        time.sleep(2)  # Rate limit breathing
    
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
