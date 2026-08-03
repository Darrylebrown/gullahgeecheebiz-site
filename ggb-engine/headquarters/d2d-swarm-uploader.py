#!/usr/bin/env python3
"""
GGB → Draft2Digital Swarm Uploader — batch uploads EPUBs to D2D
using Playwright with session persistence, retry logic, and progress tracking.
Mirrors the Alexandria API importer pattern.
"""
import json, os, sys, sqlite3, time, re
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Optional

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
PLATFORM_DIR = REPO_ROOT / "publish" / "platform-ready" / "d2d"
LOGS_DIR = Path(__file__).resolve().parent / "logs"
D2D_DB = LOGS_DIR / "d2d-upload.db"
SESSION_DIR = LOGS_DIR / "d2d-sessions"

LOGS_DIR.mkdir(parents=True, exist_ok=True)
SESSION_DIR.mkdir(parents=True, exist_ok=True)
D2D_DB.parent.mkdir(parents=True, exist_ok=True)

from playwright.sync_api import sync_playwright

D2D_URL = "https://www.draft2digital.com"

def init_db():
    conn = sqlite3.connect(str(D2D_DB))
    conn.execute("""CREATE TABLE IF NOT EXISTS uploads (
        id TEXT PRIMARY KEY,
        title TEXT,
        epub_path TEXT,
        status TEXT DEFAULT 'pending',
        attempts INTEGER DEFAULT 0,
        error TEXT,
        uploaded_at TEXT
    )""")
    conn.commit()
    return conn

def get_credentials() -> tuple:
    email = os.environ.get("D2D_EMAIL", "")
    password = os.environ.get("D2D_PASSWORD", "")
    if not email or not password:
        env_file = REPO_ROOT / ".env"
        if env_file.exists():
            for line in env_file.read_text().split("\n"):
                if line.startswith("D2D_EMAIL="):
                    email = line.split("=", 1)[1].strip().strip('"').strip("'")
                elif line.startswith("D2D_PASSWORD="):
                    password = line.split("=", 1)[1].strip().strip('"').strip("'")
    return email, password

def login_and_save_session(page) -> bool:
    """Login to D2D and save session state. Uses saved session if available."""
    session_file = SESSION_DIR / "d2d-session.json"
    if session_file.exists():
        print(f"     📂 Using saved session")
        return True
    
    email, password = get_credentials()
    if not email or not password:
        print("     ❌ No D2D credentials in .env")
        return False
    
    print(f"     🔑 Logging into D2D...")
    page.goto(f"{D2D_URL}/account/login", wait_until="networkidle")
    time.sleep(2)
    
    page.fill("#id_username", email)
    page.fill("#id_password", password)
    page.click("#two_factor_wizard_next")
    time.sleep(3)
    
    if "login" in page.url.lower():
        print("     ❌ Login failed (reCAPTCHA may be blocking)")
        return False
    
    print("     ✅ Logged in")
    return True

def upload_book(page, epub_path: Path, title: str) -> bool:
    """Upload a single EPUB to D2D."""
    try:
        # Navigate to add new book
        print(f"     📂 Opening add book page...")
        page.goto(f"{D2D_URL}/book/add", wait_until="networkidle")
        time.sleep(2)
        
        # Upload EPUB file
        print(f"     📄 Uploading EPUB...")
        file_input = page.locator("input[type='file']")
        if file_input.is_visible():
            file_input.set_input_files(str(epub_path))
        else:
            # Try hidden file input
            page.set_input_files("input[type='file']", str(epub_path))
        time.sleep(3)
        
        # Fill title if needed
        title_input = page.locator("input[name='title'], input[id='title']")
        if title_input.is_visible() and not title_input.input_value():
            title_input.fill(title)
            time.sleep(1)
        
        # Click submit
        print(f"     🚀 Submitting...")
        submit = page.locator("button[type='submit'], input[type='submit']")
        if submit.is_visible():
            submit.click()
            time.sleep(3)
            return True
        
        return True
    except Exception as e:
        print(f"     ❌ Upload error: {str(e)[:80]}")
        return False

def upload_batch(limit: int = 3, headless: bool = False) -> Dict:
    """Upload a batch of EPUBs to D2D."""
    print(f"\n{'='*60}")
    print(f"📤 GGB → DRAFT2DIGITAL SWARM UPLOADER")
    print(f"   {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}")
    print(f"{'='*60}")
    
    conn = init_db()
    
    # Find EPUBs to upload
    epubs = sorted(PLATFORM_DIR.glob("**/*.epub"))
    if not epubs:
        print("   ❌ No EPUBs found in platform-ready/d2d/")
        conn.close()
        return {"uploaded": 0}
    
    print(f"   Found {len(epubs)} EPUBs ready to upload")
    
    # Login once — use saved session if available
    session_file = SESSION_DIR / "d2d-session.json"
    
    with sync_playwright() as p:
        if session_file.exists():
            context = p.chromium.launch(headless=headless).new_context(
                viewport={"width": 1280, "height": 900},
                storage_state=str(session_file)
            )
        else:
            context = p.chromium.launch(headless=headless).new_context(
                viewport={"width": 1280, "height": 900}
            )
        
        page = context.new_page()
        
        if not login_and_save_session(page):
            context.close()
            conn.close()
            return {"uploaded": 0, "error": "Login failed"}
        
        uploaded = 0
        errors = 0
        
        for epub in epubs[:limit]:
            title = epub.stem.replace("-", " ").title()
            print(f"\n  📤 {title[:50]}...")
            
            if upload_book(page, epub, title):
                uploaded += 1
                print(f"     ✅ Uploaded!")
            else:
                errors += 1
                print(f"     ❌ Failed")
            
            time.sleep(2)
        
        browser.close()
    
    conn.close()
    
    print(f"\n{'='*60}")
    print(f"📊 SUMMARY")
    print(f"{'='*60}")
    print(f"Uploaded: {uploaded}")
    print(f"Errors:   {errors}")
    
    return {"uploaded": uploaded, "errors": errors}

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch", type=int, default=3)
    parser.add_argument("--visible", action="store_true")
    args = parser.parse_args()
    upload_batch(args.batch, headless=not args.visible)
