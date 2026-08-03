#!/usr/bin/env python3
"""
GGB Google Play Publishing Bot — automates the Partner Center upload flow.
Logs in, uploads CSV, uploads EPUBs, monitors review status, and publishes.
"""
import time, json, os, sys
from pathlib import Path
from datetime import datetime

BASE_DIR = Path("/Users/darrylsmac/gullahgeecheebiz-site")
GOOGLE_PLAY_DIR = BASE_DIR / "publish" / "for-distribution" / "google-play"
LOGS_DIR = Path(__file__).parent / "logs"
SESSION_DIR = LOGS_DIR / "google-play-sessions"

os.makedirs(SESSION_DIR, exist_ok=True)
os.makedirs(LOGS_DIR, exist_ok=True)

SESSION_FILE = SESSION_DIR / "google-play-session.json"
PARTNER_URL = "https://play.google.com/books/publish/"

def get_google_credentials():
    """Get Google account credentials from .env."""
    env_file = BASE_DIR / ".env"
    if not env_file.exists():
        return None, None
    for line in env_file.read_text().split("\n"):
        if line.startswith("GOOGLE_EMAIL="):
            email = line.split("=", 1)[1].strip().strip('"').strip("'")
        if line.startswith("GOOGLE_PASSWORD="):
            password = line.split("=", 1)[1].strip().strip('"').strip("'")
    return email, password

def login_and_save_session():
    """Open browser, user logs in, save session."""
    from playwright.sync_api import sync_playwright
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(viewport={"width": 1280, "height": 900})
        page = context.new_page()
        
        print("🌐 Opening Google Play Books Partner Center...")
        page.goto(PARTNER_URL, wait_until="networkidle")
        time.sleep(2)
        
        print("\n👆 Sign in with your Google account in this browser window.")
        print("   ⏳ Waiting for login...")
        
        for i in range(300):
            time.sleep(1)
            current = page.url
            if "publish" in current and "Sign" not in current:
                print(f"\n✅ Signed in! URL: {current}")
                context.storage_state(path=str(SESSION_FILE))
                print(f"✅ Session saved to {SESSION_FILE}")
                browser.close()
                return True
        
        print("\n⏰ Timeout waiting for login")
        browser.close()
        return False

def upload_csv():
    """Upload the bulk import CSV to Partner Center."""
    from playwright.sync_api import sync_playwright
    
    csv_path = GOOGLE_PLAY_DIR / "google-play-bulk-import.csv"
    if not csv_path.exists():
        print(f"❌ CSV not found: {csv_path}")
        return False
    
    with sync_playwright() as p:
        context = p.chromium.launch(headless=False).new_context(
            viewport={"width": 1280, "height": 900},
            storage_state=str(SESSION_FILE) if SESSION_FILE.exists() else None
        )
        page = context.new_page()
        
        print(f"📍 Navigating to Partner Center...")
        page.goto(PARTNER_URL, wait_until="networkidle")
        time.sleep(3)
        
        # Check if logged in
        if "Sign" in page.url:
            print("❌ Session expired. Need to log in again.")
            context.close()
            return False
        
        print("✅ Logged in!")
        
        # Navigate to Book Catalog
        page.goto(f"{PARTNER_URL}a/4261777550639003130#book/catalog", wait_until="networkidle")
        time.sleep(3)
        print(f"📍 Book Catalog: {page.url}")
        
        # Look for Advanced options
        page.screenshot(path="/tmp/google-play-catalog.png")
        print("📸 Screenshot saved to /tmp/google-play-catalog.png")
        
        context.close()
        return True

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Google Play Publishing Bot")
    parser.add_argument("--login", action="store_true", help="Log in and save session")
    parser.add_argument("--upload-csv", action="store_true", help="Upload bulk import CSV")
    parser.add_argument("--upload-epubs", action="store_true", help="Upload EPUB files")
    parser.add_argument("--monitor", action="store_true", help="Monitor review status")
    parser.add_argument("--publish", action="store_true", help="Publish approved books")
    parser.add_argument("--all", action="store_true", help="Run full pipeline")
    args = parser.parse_args()
    
    print(f"\n{'='*60}")
    print(f"🤖 GGB GOOGLE PLAY PUBLISHING BOT")
    print(f"   {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
    print(f"{'='*60}\n")
    
    if args.login or args.all:
        print("🔑 Step 1: Login")
        if login_and_save_session():
            print("   ✅ Ready for next steps\n")
    
    if args.upload_csv or args.all:
        print("📄 Step 2: Upload CSV")
        upload_csv()
    
    if args.upload_epubs or args.all:
        print("📚 Step 3: Upload EPUBs")
        print("   (Coming next)")
    
    if args.monitor or args.all:
        print("👁️  Step 4: Monitor review status")
        print("   (Coming next)")
    
    if args.publish or args.all:
        print("🚀 Step 5: Publish approved books")
        print("   (Coming next)")
    
    print(f"\n{'='*60}")
    print(f"✅ Done")
    print(f"{'='*60}\n")

if __name__ == "__main__":
    main()
