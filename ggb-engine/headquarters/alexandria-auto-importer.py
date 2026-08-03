#!/usr/bin/env python3
"""
GGB → Alexandria AI Auto-Importer — uses Playwright to automate
the Import Book flow on Alexandria AI. Logs in, uploads files,
fills metadata, and clicks publish.
"""
import json, os, sys, sqlite3, time, re
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Optional

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
ALEXANDRIA_DIR = REPO_ROOT / "publish" / "for-alexandria"
LOGS_DIR = Path(__file__).resolve().parent / "logs"
ALEXANDRIA_DB = LOGS_DIR / "alexandria-export.db"

LOGS_DIR.mkdir(parents=True, exist_ok=True)

# Try to import Playwright
try:
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False

ALEXANDRIA_URL = "https://alexandria-ai.com"

def get_credentials() -> tuple:
    """Get Alexandria AI credentials from env or .env file."""
    email = os.environ.get("ALEXANDRIA_EMAIL", "")
    password = os.environ.get("ALEXANDRIA_PASSWORD", "")
    
    if not email or not password:
        env_file = REPO_ROOT / ".env"
        if env_file.exists():
            for line in env_file.read_text().split("\n"):
                if line.startswith("ALEXANDRIA_EMAIL="):
                    email = line.split("=", 1)[1].strip().strip('"').strip("'")
                elif line.startswith("ALEXANDRIA_PASSWORD="):
                    password = line.split("=", 1)[1].strip().strip('"').strip("'")
    
    return email, password

def import_book_playwright(export_dir: Path, headless: bool = False) -> Dict:
    """Import a single book into Alexandria AI using Playwright."""
    if not PLAYWRIGHT_AVAILABLE:
        return {"status": "error", "error": "Playwright not installed"}
    
    email, password = get_credentials()
    if not email or not password:
        return {"status": "error", "error": "No credentials. Set ALEXANDRIA_EMAIL and ALEXANDRIA_PASSWORD in .env"}
    
    # Read metadata
    metadata_file = export_dir / "metadata.json"
    if not metadata_file.exists():
        return {"status": "error", "error": "metadata.json not found"}
    
    metadata = json.loads(metadata_file.read_text())
    manuscript = export_dir / "manuscript.txt"
    cover = export_dir / "cover.png"
    
    if not manuscript.exists():
        return {"status": "error", "error": "manuscript.md not found"}
    
    result = {"status": "unknown", "title": metadata.get("title", "")}
    
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=headless)
            context = browser.new_context(
                viewport={"width": 1280, "height": 800},
                storage_state=None
            )
            page = context.new_page()
            
            # Navigate to login
            print(f"     🔑 Logging in...")
            page.goto(f"{ALEXANDRIA_URL}/Login", wait_until="networkidle")
            time.sleep(2)
            
            # Fill login form
            page.fill("input[type='email']", email)
            page.fill("input[type='password']", password)
            page.click("button:has-text('Sign in')")
            time.sleep(3)
            
            # Navigate to Book Projects
            print(f"     📂 Opening Book Projects...")
            page.goto(f"{ALEXANDRIA_URL}/BookProjects", wait_until="networkidle")
            time.sleep(2)
            
            # Click Import Book
            print(f"     📥 Clicking Import Book...")
            import_btn = page.locator("button:has-text('Import Book'), a:has-text('Import Book')")
            if import_btn.is_visible():
                import_btn.click()
                time.sleep(2)
            else:
                # Try the New Project button instead
                new_btn = page.locator("button:has-text('New Project'), a:has-text('New Project')")
                if new_btn.is_visible():
                    new_btn.click()
                    time.sleep(2)
            
            # Upload manuscript via the hidden file input
            print(f"     📄 Uploading manuscript...")
            # Playwright's set_input_files works on hidden inputs
            page.set_input_files("input[type='file']#book-file", str(manuscript))
            time.sleep(2)
            
            # Upload cover if available
            if cover.exists():
                print(f"     🖼️  Uploading cover...")
                # The cover input might be the second file input
                page.set_input_files("input[type='file'] >> nth=1", str(cover))
                time.sleep(2)
            
            # Fill title (placeholder: "The Great Adventure")
            print(f"     ✏️  Filling title...")
            title_input = page.locator("input[placeholder='The Great Adventure']")
            if title_input.is_visible():
                title_input.fill(metadata.get("title", ""))
                time.sleep(1)
            
            # Fill subtitle (placeholder: "A Journey Through Time")
            subtitle_input = page.locator("input[placeholder='A Journey Through Time']")
            if subtitle_input.is_visible():
                subtitle_input.fill(metadata.get("description", "")[:100])
                time.sleep(1)
            
            # Fill author (placeholder: "Your Name")
            print(f"     ✏️  Filling author...")
            author_input = page.locator("input[placeholder='Your Name']")
            if author_input.is_visible():
                author_input.fill(metadata.get("author", "Darryl Elliott Brown"))
                time.sleep(1)
            
            # Click Import Book submit button
            print(f"     🚀 Clicking Import Book submit...")
            # Use the last visible "Import Book" button (the one in the modal, not the header)
            submit_btn = page.locator("button:has-text('Import Book')")
            count = submit_btn.count()
            if count >= 2:
                submit_btn.nth(count - 1).click()
                time.sleep(3)
                result["status"] = "submitted"
            elif count == 1:
                submit_btn.click()
                time.sleep(3)
                result["status"] = "submitted"
            else:
                result["status"] = "form_filled"
            
            # Take screenshot for proof
            screenshot_path = export_dir / "alexandria-import.png"
            page.screenshot(path=str(screenshot_path))
            result["screenshot"] = str(screenshot_path)
            
            browser.close()
            
    except Exception as e:
        result["status"] = "error"
        result["error"] = str(e)[:100]
    
    return result

def import_batch(limit: int = 3, headless: bool = False) -> Dict:
    """Import a batch of books into Alexandria AI."""
    print(f"\n{'='*60}")
    print(f"🚀 GGB → ALEXANDRIA AI AUTO-IMPORTER")
    print(f"   {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}")
    print(f"{'='*60}")
    
    if not PLAYWRIGHT_AVAILABLE:
        print("❌ Playwright not installed. Run: pip install playwright && playwright install chromium")
        return {"error": "Playwright not installed"}
    
    # Get unimported books
    conn = sqlite3.connect(str(ALEXANDRIA_DB))
    rows = conn.execute("""
        SELECT id, title, file_path FROM exports 
        WHERE imported = 0 
        LIMIT ?
    """, (limit,)).fetchall()
    
    if not rows:
        print("   ✅ All books already imported!")
        conn.close()
        return {"imported": 0}
    
    results = []
    for r in rows:
        export_id = r[0]
        title = r[1]
        export_dir = Path(r[2])
        
        print(f"\n  📤 {title[:50]}...")
        result = import_book_playwright(export_dir, headless)
        results.append(result)
        
        if result.get("status") == "published":
            conn.execute("UPDATE exports SET imported = 1 WHERE id = ?", (export_id,))
            conn.commit()
            print(f"     ✅ Published!")
        elif result.get("status") == "form_filled":
            print(f"     ⚠️  Form filled (may need manual submit)")
        else:
            print(f"     ❌ {result.get('error', 'Failed')}")
        
        time.sleep(2)
    
    conn.close()
    
    published = sum(1 for r in results if r.get("status") == "published")
    print(f"\n{'='*60}")
    print(f"📊 SUMMARY")
    print(f"{'='*60}")
    print(f"Attempted: {len(results)}")
    print(f"Published: {published}")
    
    return {"attempted": len(results), "published": published}

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch", type=int, default=3)
    parser.add_argument("--visible", action="store_true", help="Show browser window")
    args = parser.parse_args()
    
    import_batch(args.batch, headless=not args.visible)
