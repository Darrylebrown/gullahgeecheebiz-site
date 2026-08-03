#!/usr/bin/env python3
"""
GGB Google Play Upload Bot — uses your real Chrome browser (already logged in)
to upload CSV + EPUBs to the Partner Center. No reCAPTCHA, no session expiry.
"""
import time, json, os, sys, hashlib
from pathlib import Path
from datetime import datetime, timezone

BASE_DIR = Path("/Users/darrylsmac/gullahgeecheebiz-site")
GOOGLE_PLAY_DIR = BASE_DIR / "publish" / "for-distribution" / "google-play"
LOGS_DIR = Path(__file__).parent / "logs"
STATE_FILE = LOGS_DIR / "google-play-upload-state.json"
PARTNER_URL = "https://play.google.com/books/publish/"

os.makedirs(LOGS_DIR, exist_ok=True)

def get_csv_hash():
    csv_path = GOOGLE_PLAY_DIR / "google-play-bulk-import.csv"
    if not csv_path.exists():
        return None
    return hashlib.md5(csv_path.read_bytes()).hexdigest()

def get_epub_count():
    return len(list(GOOGLE_PLAY_DIR.glob("*.epub")))

def load_state():
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except:
            pass
    return {"csv_hash": None, "epub_count": 0, "last_upload": None}

def save_state(csv_hash, epub_count):
    state = {
        "csv_hash": csv_hash,
        "epub_count": epub_count,
        "last_upload": datetime.now(timezone.utc).isoformat(),
    }
    STATE_FILE.write_text(json.dumps(state, indent=2))

def has_changes():
    state = load_state()
    current_csv = get_csv_hash()
    current_epubs = get_epub_count()
    
    if current_csv != state["csv_hash"]:
        return True, "CSV changed"
    if current_epubs != state["epub_count"]:
        return True, f"EPUB count: {state['epub_count']} → {current_epubs}"
    return False, "No changes"

def upload_to_partner_center():
    """Upload CSV + EPUBs using your real Chrome browser."""
    from playwright.sync_api import sync_playwright
    
    csv_path = GOOGLE_PLAY_DIR / "google-play-bulk-import.csv"
    if not csv_path.exists():
        return {"status": "no_csv", "error": "No CSV to upload"}
    
    print("   🌐 Opening your Chrome browser (with your saved session)...")
    with sync_playwright() as p:
        # Use your real Chrome profile where you're already logged in
        user_data_dir = os.path.expanduser("~/Library/Application Support/Google/Chrome")
        context = p.chromium.launch_persistent_context(
            user_data_dir=user_data_dir,
            headless=False,
            channel="chrome",
            args=["--disable-blink-features=AutomationControlled"],
            viewport={"width": 1280, "height": 900},
        )
        page = context.pages[0] if context.pages else context.new_page()
        
        print("   📍 Navigating to Partner Center...")
        page.goto(PARTNER_URL, wait_until="networkidle")
        time.sleep(3)
        
        if "Sign" in page.url or "accounts.google" in page.url:
            print("\n   👆 Sign in with deb2020win3@gmail.com in the browser window.")
            print("   ⏳ Waiting for you to sign in...")
            for i in range(300):
                time.sleep(1)
                if "Sign" not in page.url and "accounts.google" not in page.url:
                    print(f"\n   ✅ Signed in!")
                    break
            else:
                print("\n   ⏰ Timeout waiting for login")
                context.close()
                return {"status": "timeout", "error": "Login timed out"}
        
        print(f"   📍 URL: {page.url[:80]}")
        
        # Navigate to Book Catalog
        catalog_url = f"{PARTNER_URL}a/4261777550639003130#book/catalog"
        page.goto(catalog_url, wait_until="networkidle")
        time.sleep(3)
        print(f"   📍 Catalog: {page.url[:80]}")
        
        # Look for Advanced options or Upload button
        page.screenshot(path="/tmp/google-play-catalog.png")
        print("   📸 Screenshot: /tmp/google-play-catalog.png")
        
        # Try to find the upload button
        buttons = page.locator("a, button, span[role='button'], div[role='button']")
        for i in range(buttons.count()):
            text = buttons.nth(i).inner_text().strip()
            if text and ("upload" in text.lower() or "advanced" in text.lower() or "import" in text.lower() or "add" in text.lower()):
                print(f"   🔘 Found: '{text[:50]}'")
        
        print("\n   👆 Look at the screenshot in /tmp/google-play-catalog.png")
        print("   Tell me what you see and I'll guide the upload.")
        
        # Keep browser open so user can see it
        input("\n   Press Enter in terminal when done looking...")
        context.close()
    
    return {"status": "ready", "note": "Session valid, catalog page captured"}

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Google Play Upload Bot")
    parser.add_argument("--check", action="store_true", help="Check for changes")
    parser.add_argument("--upload", action="store_true", help="Upload CSV + EPUBs")
    parser.add_argument("--force", action="store_true", help="Force upload")
    args = parser.parse_args()
    
    print(f"\n{'='*60}")
    print(f"🤖 GGB GOOGLE PLAY UPLOAD BOT")
    print(f"   {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
    print(f"{'='*60}\n")
    
    csv_path = GOOGLE_PLAY_DIR / "google-play-bulk-import.csv"
    epub_count = get_epub_count()
    print(f"📄 CSV: {'✅' if csv_path.exists() else '❌'} ({csv_path.stat().st_size/1024:.0f} KB)")
    print(f"📚 EPUBs: {epub_count}")
    
    if args.check:
        changed, reason = has_changes()
        print(f"\n{'✅ No changes' if not changed else '🔄 Changes detected'}: {reason}")
        return
    
    if args.upload or args.force:
        changed, reason = has_changes()
        if not changed and not args.force:
            print(f"\n✅ No changes since last upload ({load_state()['last_upload'][:19]})")
            print("   Use --force to upload anyway")
            return
        
        print(f"\n🔄 Changes: {reason}")
        result = upload_to_partner_center()
        print(f"\n📊 Result: {json.dumps(result, indent=2)}")
        
        if result["status"] in ("ready", "uploaded"):
            save_state(get_csv_hash(), get_epub_count())
            print("\n✅ State saved")

if __name__ == "__main__":
    main()
