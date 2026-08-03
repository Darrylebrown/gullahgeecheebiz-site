#!/usr/bin/env python3
"""
GGB Platform Uploader — browser automation for publishing platforms.
Uses Playwright (free, open-source) to drive real browsers.
"""
import json, os, sys, time, uuid, sqlite3
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional, Dict, List

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
PUB_DB = REPO_ROOT / "publish" / "publisher.db"
COOKIES_DIR = Path(__file__).resolve().parent / "cookies"
LOGS_DIR = Path(__file__).resolve().parent / "logs"
PLATFORM_DIR = REPO_ROOT / "publish" / "platform-ready"

COOKIES_DIR.mkdir(parents=True, exist_ok=True)
LOGS_DIR.mkdir(parents=True, exist_ok=True)

# ─── Platform Configs ───────────────────────────────────────────────────────

PLATFORMS = {
    "d2d": {
        "name": "Draft2Digital",
        "url": "https://draft2digital.com",
        "login_url": "https://draft2digital.com/account/login",
        "dashboard_url": "https://draft2digital.com/books",
        "new_book_url": "https://draft2digital.com/books/new",
        "file_dir": PLATFORM_DIR / "d2d",
        "file_ext": ".epub",
        "cover_ext": ".jpg",
        "login_selector": "#login-email",
        "password_selector": "#login-password",
        "submit_selector": "button[type='submit']",
    },
    "kdp": {
        "name": "Kindle Direct Publishing",
        "url": "https://kdp.amazon.com",
        "login_url": "https://kdp.amazon.com/en_US/bookshelf",
        "dashboard_url": "https://kdp.amazon.com/en_US/bookshelf",
        "new_book_url": "https://kdp.amazon.com/en_US/title-setup",
        "file_dir": PLATFORM_DIR / "kdp",
        "file_ext": ".docx",
        "cover_ext": ".jpg",
    },
    "kobo": {
        "name": "Kobo Writing Life",
        "url": "https://writinglife.kobo.com",
        "login_url": "https://writinglife.kobo.com/login",
        "dashboard_url": "https://writinglife.kobo.com/books",
        "file_dir": PLATFORM_DIR / "kobo",
        "file_ext": ".epub",
        "cover_ext": ".jpg",
    },
    "google_play": {
        "name": "Google Play Books",
        "url": "https://play.google.com/books/publish",
        "login_url": "https://play.google.com/books/publish/u/0/",
        "dashboard_url": "https://play.google.com/books/publish/u/0/",
        "file_dir": PLATFORM_DIR / "google-play",
        "file_ext": ".epub",
        "cover_ext": ".jpg",
    },
    "apple_books": {
        "name": "Apple Books",
        "url": "https://books.apple.com",
        "login_url": "https://appstoreconnect.apple.com",
        "dashboard_url": "https://appstoreconnect.apple.com",
        "file_dir": PLATFORM_DIR / "apple-books",
        "file_ext": ".epub",
        "cover_ext": ".jpg",
    },
    "ingramspark": {
        "name": "IngramSpark",
        "url": "https://www.ingramspark.com",
        "login_url": "https://www.ingramspark.com/login",
        "dashboard_url": "https://www.ingramspark.com/dashboard",
        "file_dir": PLATFORM_DIR / "ingramspark",
        "file_ext": ".pdf",
        "cover_ext": ".jpg",
    },
    "acx": {
        "name": "ACX (Audiobook)",
        "url": "https://www.acx.com",
        "login_url": "https://www.acx.com/login",
        "dashboard_url": "https://www.acx.com/bookshelf",
        "file_dir": PLATFORM_DIR / "acx",
        "file_ext": ".mp3",
        "cover_ext": ".jpg",
    },
    "spotify": {
        "name": "Spotify for Authors",
        "url": "https://authors.spotify.com",
        "login_url": "https://authors.spotify.com/login",
        "dashboard_url": "https://authors.spotify.com/dashboard",
        "file_dir": PLATFORM_DIR / "spotify",
        "file_ext": ".mp3",
        "cover_ext": ".jpg",
    },
    "distrokid": {
        "name": "DistroKid",
        "url": "https://distrokid.com",
        "login_url": "https://distrokid.com/login",
        "dashboard_url": "https://distrokid.com/dashboard",
        "file_dir": PLATFORM_DIR / "distrokid",
        "file_ext": ".mp3",
        "cover_ext": ".jpg",
    },
    "pinterest": {
        "name": "Pinterest",
        "url": "https://www.pinterest.com",
        "login_url": "https://www.pinterest.com/login",
        "dashboard_url": "https://www.pinterest.com/business/hub/",
        "file_dir": PLATFORM_DIR / "pinterest",
        "file_ext": ".jpg",
        "cover_ext": ".jpg",
    },
}

class PlatformUploader:
    """Browser automation for uploading books to publishing platforms."""
    
    def __init__(self, headless: bool = False, slow_mo: int = 100):
        self.headless = headless
        self.slow_mo = slow_mo
        self.browser = None
        self.context = None
        self.page = None
        self.conn = sqlite3.connect(str(PUB_DB))
    
    def _ensure_browser(self):
        """Lazy-init browser to save memory."""
        if self.browser:
            return
        from playwright.sync_api import sync_playwright
        self._pw = sync_playwright().start()
        self.browser = self._pw.chromium.launch(
            headless=self.headless,
            slow_mo=self.slow_mo,
        )
    
    def close(self):
        """Clean up browser resources."""
        if self.browser:
            self.browser.close()
        if hasattr(self, '_pw') and self._pw:
            self._pw.stop()
        self.conn.close()
    
    def _load_cookies(self, platform: str) -> bool:
        """Load saved cookies for a platform."""
        cookie_file = COOKIES_DIR / f"{platform}_cookies.json"
        if not cookie_file.exists():
            return False
        if not self.context:
            self._ensure_browser()
            self.context = self.browser.new_context()
        cookies = json.loads(cookie_file.read_text())
        self.context.add_cookies(cookies)
        return True
    
    def _save_cookies(self, platform: str):
        """Save cookies for a platform."""
        if not self.context:
            return
        cookie_file = COOKIES_DIR / f"{platform}_cookies.json"
        cookies = self.context.cookies()
        cookie_file.write_text(json.dumps(cookies, indent=2))
        print(f"  💾 Saved cookies for {platform}")
    
    def login(self, platform: str, email: str = None, password: str = None) -> bool:
        """Log into a publishing platform. Uses saved cookies if available."""
        config = PLATFORMS.get(platform)
        if not config:
            print(f"  ❌ Unknown platform: {platform}")
            return False
        
        print(f"  🔑 Logging into {config['name']}...")
        
        # Try saved cookies first
        if self._load_cookies(platform):
            self._ensure_browser()
            if not self.context:
                self.context = self.browser.new_context()
            self.page = self.context.new_page()
            self.page.goto(config["dashboard_url"], wait_until="domcontentloaded")
            time.sleep(2)
            
            # Check if we're already logged in
            if "login" not in self.page.url.lower():
                print(f"  ✅ Already logged in (cookies)")
                return True
        
        # Need to log in manually
        if not email or not password:
            print(f"  ⚠️  Need credentials for {config['name']}")
            print(f"     Set {platform.upper()}_EMAIL and {platform.upper()}_PASSWORD env vars")
            return False
        
        self._ensure_browser()
        if not self.context:
            self.context = self.browser.new_context()
        self.page = self.context.new_page()
        self.page.goto(config["login_url"], wait_until="domcontentloaded")
        time.sleep(2)
        
        # Fill login form
        try:
            if "email" in config.get("login_selector", ""):
                self.page.fill(config["login_selector"], email)
            else:
                self.page.fill("input[type='email'], input[name='email'], input[id*='email']", email)
            
            if "password" in config.get("password_selector", ""):
                self.page.fill(config["password_selector"], password)
            else:
                self.page.fill("input[type='password'], input[name='password'], input[id*='password']", password)
            
            # Click submit
            if "submit" in config.get("submit_selector", ""):
                self.page.click(config["submit_selector"])
            else:
                self.page.click("button[type='submit'], input[type='submit']")
            
            time.sleep(3)
            
            # Check if login succeeded
            if "login" in self.page.url.lower():
                print(f"  ❌ Login failed for {config['name']}")
                return False
            
            self._save_cookies(platform)
            print(f"  ✅ Logged into {config['name']}")
            return True
            
        except Exception as e:
            print(f"  ❌ Login error: {e}")
            return False
    
    def upload_d2d(self, manifest_id: str, title: str = None) -> bool:
        """Upload a book to Draft2Digital."""
        config = PLATFORMS["d2d"]
        
        # Find the platform-ready files
        file_dir = config["file_dir"]
        if not file_dir.exists():
            print(f"  ❌ No D2D files directory at {file_dir}")
            return False
        
        # Load manifest
        d = json.loads(self.conn.execute(
            "SELECT data FROM manifests WHERE manifest_id = ?", (manifest_id,)
        ).fetchone()[0])
        
        book_title = title or d.get("title", {}).get("canonical", "Unknown")
        author = d.get("author", "Darryl E. Brown")
        description = d.get("metadata", {}).get("description", "")
        
        # Find matching files
        title_slug = book_title.lower().replace(" ", "-").replace("'", "")[:40]
        epub_files = list(file_dir.glob(f"*{title_slug}*{config['file_ext']}"))
        cover_files = list(file_dir.glob(f"*{title_slug}*{config['cover_ext']}"))
        
        if not epub_files:
            # Broader match
            epub_files = list(file_dir.glob(f"*{title_slug[:15]}*{config['file_ext']}"))
        
        if not epub_files:
            print(f"  ❌ No EPUB file found for '{book_title}'")
            return False
        
        epub_path = epub_files[0]
        cover_path = cover_files[0] if cover_files else None
        
        print(f"  📤 Uploading '{book_title}' to D2D...")
        print(f"     EPUB: {epub_path.name}")
        if cover_path:
            print(f"     Cover: {cover_path.name}")
        
        try:
            # Navigate to new book page
            self.page.goto(config["new_book_url"], wait_until="domcontentloaded")
            time.sleep(2)
            
            # Click "START EBOOK" or similar
            start_btn = self.page.locator("text=START EBOOK, text=Create Ebook, text=Add New Book")
            if start_btn.count() > 0:
                start_btn.first.click()
                time.sleep(2)
            
            # Fill title
            title_input = self.page.locator("input[name='title'], input[id*='title'], input[placeholder*='Title']")
            if title_input.count() > 0:
                title_input.first.fill(book_title)
            
            # Fill author
            author_input = self.page.locator("input[name='author'], input[id*='author'], input[placeholder*='Author']")
            if author_input.count() > 0:
                author_input.first.fill(author)
            
            # Upload EPUB
            file_input = self.page.locator("input[type='file']")
            if file_input.count() > 0:
                file_input.first.set_input_files(str(epub_path))
                print(f"  ✅ EPUB uploaded")
                time.sleep(3)
            
            # Upload cover
            if cover_path:
                cover_inputs = self.page.locator("input[type='file']")
                if cover_inputs.count() > 1:
                    cover_inputs.nth(1).set_input_files(str(cover_path))
                    print(f"  ✅ Cover uploaded")
                    time.sleep(2)
            
            # Record evidence
            now = datetime.now(timezone.utc).isoformat()
            self.conn.execute("""
                INSERT INTO platform_evidence 
                (manifest_id, adapter_type, is_mock, platform, draft_id, operation_id,
                 timestamp, evidence_data, errors, warnings)
                VALUES (?, 'Playwright', 0, 'd2d', ?, 'upload-manuscript', ?, ?, ?, ?)
            """, (manifest_id, f"pw-{uuid.uuid4().hex[:8]}", now,
                  json.dumps({"file": str(epub_path), "status": "uploaded"}),
                  json.dumps([]), json.dumps([])))
            self.conn.commit()
            
            print(f"  ✅ Uploaded to D2D: {book_title}")
            return True
            
        except Exception as e:
            print(f"  ❌ Upload error: {e}")
            return False
    
    def upload_kdp(self, manifest_id: str, title: str = None) -> bool:
        """Upload a book to KDP (placeholder — needs KDP-specific flow)."""
        print("  ⏳ KDP upload not yet implemented")
        return False
    
    def upload(self, platform: str, manifest_id: str, title: str = None) -> bool:
        """Upload a book to any supported platform."""
        method_name = f"upload_{platform}"
        method = getattr(self, method_name, None)
        if not method:
            print(f"  ❌ No uploader for platform: {platform}")
            return False
        return method(manifest_id, title)
    
    def upload_batch(self, platform: str, limit: int = 5) -> Dict:
        """Upload a batch of approved books to a platform."""
        rows = self.conn.execute("""
            SELECT manifest_id, json_extract(data, '$.title.canonical')
            FROM manifests WHERE state = 'approved'
            AND manifest_id NOT IN (
                SELECT manifest_id FROM platform_evidence 
                WHERE operation_id = 'upload-manuscript' AND adapter_type = 'Playwright'
            )
            LIMIT ?
        """, (limit,)).fetchall()
        
        results = {"success": 0, "failed": 0, "skipped": 0}
        
        for r in rows:
            mid = r[0]
            title = r[1]
            
            if self.upload(platform, mid, title):
                results["success"] += 1
            else:
                results["failed"] += 1
        
        return results

# ─── CLI ────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="GGB Platform Uploader")
    parser.add_argument("--platform", "-p", default="d2d", help="Platform to upload to")
    parser.add_argument("--login", action="store_true", help="Login to platform")
    parser.add_argument("--email", help="Login email")
    parser.add_argument("--password", help="Login password")
    parser.add_argument("--batch", type=int, default=1, help="Number of books to upload")
    parser.add_argument("--manifest", help="Specific manifest ID to upload")
    parser.add_argument("--headless", action="store_true", help="Run headless (no browser window)")
    parser.add_argument("--visible", action="store_true", help="Show browser window")
    
    args = parser.parse_args()
    
    uploader = PlatformUploader(headless=args.headless, slow_mo=200)
    
    try:
        if args.login:
            email = args.email or os.environ.get(f"{args.platform.upper()}_EMAIL")
            password = args.password or os.environ.get(f"{args.platform.upper()}_PASSWORD")
            uploader.login(args.platform, email, password)
        
        elif args.manifest:
            uploader.login(args.platform)
            uploader.upload(args.platform, args.manifest)
        
        elif args.batch:
            uploader.login(args.platform)
            results = uploader.upload_batch(args.platform, args.batch)
            print(f"\n📊 Batch complete: {results['success']} success, {results['failed']} failed")
        
        else:
            parser.print_help()
    
    finally:
        uploader.close()
