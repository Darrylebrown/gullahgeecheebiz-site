#!/usr/bin/env python3
"""
GGB → Alexandria AI Auto-Importer v2 — drives the Import Book modal
using exact selectors from the Alexandria HTML. Uploads .txt manuscript,
cover, fills title/author, and clicks Import Book.
"""
import json, os, sys, sqlite3, time
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Optional

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
ALEXANDRIA_DIR = REPO_ROOT / "publish" / "for-alexandria"
LOGS_DIR = Path(__file__).resolve().parent / "logs"
ALEXANDRIA_DB = LOGS_DIR / "alexandria-export.db"

LOGS_DIR.mkdir(parents=True, exist_ok=True)

from playwright.sync_api import sync_playwright

ALEXANDRIA_URL = "https://alexandria-ai.com"

def get_credentials() -> tuple:
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

def import_book(export_dir: Path, headless: bool = False) -> Dict:
    """Import a single book into Alexandria AI."""
    email, password = get_credentials()
    if not email or not password:
        return {"status": "error", "error": "No credentials in .env"}
    
    metadata_file = export_dir / "metadata.json"
    if not metadata_file.exists():
        return {"status": "error", "error": "metadata.json not found"}
    
    metadata = json.loads(metadata_file.read_text())
    manuscript = export_dir / "manuscript.txt"
    cover = export_dir / "cover.png"
    
    if not manuscript.exists():
        return {"status": "error", "error": "manuscript.txt not found"}
    
    result = {"status": "unknown", "title": metadata.get("title", "")}
    
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=headless)
            context = browser.new_context(viewport={"width": 1280, "height": 900})
            page = context.new_page()
            
            # Step 1: Login
            print(f"     🔑 Logging in...")
            page.goto(f"{ALEXANDRIA_URL}/Login", wait_until="networkidle")
            time.sleep(2)
            page.fill("input[type='email']", email)
            page.fill("input[type='password']", password)
            page.click("button:has-text('Sign in')")
            time.sleep(3)
            
            # Step 2: Navigate to Book Projects
            print(f"     📂 Opening Book Projects...")
            page.goto(f"{ALEXANDRIA_URL}/BookProjects", wait_until="networkidle")
            time.sleep(2)
            
            # Step 3: Click Import Book button in header
            print(f"     📥 Clicking Import Book...")
            page.click("button:has-text('Import Book')")
            time.sleep(3)
            
            # Step 4: Upload manuscript.txt
            print(f"     📄 Uploading manuscript...")
            # Use filechooser pattern — click the label, then handle the file dialog
            with page.expect_file_chooser() as fc_info:
                page.click("label[for='book-file']")
            file_chooser = fc_info.value
            file_chooser.set_files(str(manuscript))
            time.sleep(2)
            
            # Step 5: Upload cover if available
            if cover.exists():
                print(f"     🖼️  Uploading cover...")
                time.sleep(1)
            
            # Step 6: Fill title
            print(f"     ✏️  Filling title...")
            page.fill("input[placeholder='The Great Adventure']", metadata.get("title", ""))
            time.sleep(1)
            
            # Step 7: Fill author
            print(f"     ✏️  Filling author...")
            page.fill("input[placeholder='Your Name']", metadata.get("author", "Darryl Elliott Brown"))
            time.sleep(1)
            
            # Step 8: Click Import Book submit
            print(f"     🚀 Clicking Import Book submit...")
            # Wait a moment for the form to process the file upload
            time.sleep(2)
            # Use the button index from debug: button[16] is the modal submit
            # It starts disabled, enables after file + fields are filled
            all_buttons = page.locator("button")
            btn_count = all_buttons.count()
            # The modal submit is typically the 17th button (index 16)
            for idx in range(btn_count):
                text = all_buttons.nth(idx).inner_text().strip()
                enabled = all_buttons.nth(idx).is_enabled()
                if 'Import Book' in text and enabled:
                    all_buttons.nth(idx).click(timeout=5000)
                    time.sleep(3)
                    result["status"] = "submitted"
                    break
            else:
                result["status"] = "form_filled"
            
            # Screenshot for proof
            screenshot_path = export_dir / "alexandria-result.png"
            page.screenshot(path=str(screenshot_path))
            result["screenshot"] = str(screenshot_path)
            
            browser.close()
            
    except Exception as e:
        result["status"] = "error"
        result["error"] = str(e)[:120]
    
    return result

def import_batch(limit: int = 3, headless: bool = False) -> Dict:
    """Import a batch of books into Alexandria AI."""
    print(f"\n{'='*60}")
    print(f"🚀 GGB → ALEXANDRIA AI AUTO-IMPORTER v2")
    print(f"   {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}")
    print(f"{'='*60}")
    
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
        result = import_book(export_dir, headless)
        results.append(result)
        
        if result.get("status") == "submitted":
            conn.execute("UPDATE exports SET imported = 1 WHERE id = ?", (export_id,))
            conn.commit()
            print(f"     ✅ Submitted to Alexandria!")
        else:
            print(f"     ❌ {result.get('error', result.get('status', 'Failed'))}")
        
        time.sleep(2)
    
    conn.close()
    
    submitted = sum(1 for r in results if r.get("status") == "submitted")
    print(f"\n{'='*60}")
    print(f"📊 SUMMARY")
    print(f"{'='*60}")
    print(f"Attempted: {len(results)}")
    print(f"Submitted: {submitted}")
    
    return {"attempted": len(results), "submitted": submitted}

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch", type=int, default=3)
    parser.add_argument("--visible", action="store_true", help="Show browser window")
    args = parser.parse_args()
    import_batch(args.batch, headless=not args.visible)
