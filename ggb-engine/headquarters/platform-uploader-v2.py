#!/usr/bin/env python3
"""
GGB Platform Uploader v2 — backup uploader using Browser Use library.
Alternative approach to v1 (raw Playwright). Same goal: free, open-source,
browser automation for publishing platforms.
"""
import json, os, sys, time, uuid, sqlite3, asyncio
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional, Dict, List

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
PUB_DB = REPO_ROOT / "publish" / "publisher.db"
COOKIES_DIR = Path(__file__).resolve().parent / "cookies-v2"
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

class PlatformUploaderV2:
    """
    Backup uploader using async Playwright with step-by-step logging,
    retry logic, and state persistence. Independent from v1.
    """
    
    def __init__(self, headless: bool = True):
        self.headless = headless
        self.browser = None
        self.context = None
        self.page = None
        self.conn = sqlite3.connect(str(PUB_DB))
        self.stats = {"uploads": 0, "retries": 0, "failures": 0}
    
    async def _start(self):
        """Start browser session."""
        from playwright.async_api import async_playwright
        self._pw = await async_playwright().start()
        self.browser = await self._pw.chromium.launch(
            headless=self.headless,
            args=["--disable-dev-shm-usage", "--no-sandbox"],
        )
        self.context = await self.browser.new_context(
            viewport={"width": 1280, "height": 900},
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        )
        self.page = await self.context.new_page()
    
    async def _stop(self):
        """Clean up browser session."""
        if self.browser:
            await self.browser.close()
        if hasattr(self, '_pw') and self._pw:
            await self._pw.stop()
        self.conn.close()
    
    async def _load_cookies(self, platform: str) -> bool:
        """Load saved cookies."""
        cookie_file = COOKIES_DIR / f"{platform}_cookies.json"
        if not cookie_file.exists():
            return False
        cookies = json.loads(cookie_file.read_text())
        await self.context.add_cookies(cookies)
        return True
    
    async def _save_cookies(self, platform: str):
        """Save cookies."""
        cookie_file = COOKIES_DIR / f"{platform}_cookies.json"
        cookies = await self.context.cookies()
        cookie_file.write_text(json.dumps(cookies, indent=2))
        print(f"  💾 Saved cookies for {platform}")
    
    async def _retry(self, fn, max_attempts: int = 3, delay: int = 2):
        """Retry a function with exponential backoff."""
        for attempt in range(max_attempts):
            try:
                return await fn()
            except Exception as e:
                self.stats["retries"] += 1
                if attempt < max_attempts - 1:
                    wait = delay * (2 ** attempt)
                    print(f"  ⚠️  Retry {attempt + 1}/{max_attempts} after {wait}s: {e}")
                    await asyncio.sleep(wait)
                else:
                    raise
    
    async def login(self, platform: str, email: str = None, password: str = None) -> bool:
        """Log into a publishing platform."""
        config = PLATFORMS.get(platform)
        if not config:
            print(f"  ❌ Unknown platform: {platform}")
            return False
        
        print(f"  🔑 Logging into {config['name']}...")
        
        if not self.browser:
            await self._start()
        
        # Try cookies first
        if await self._load_cookies(platform):
            await self.page.goto(config["dashboard_url"], wait_until="domcontentloaded")
            await asyncio.sleep(2)
            if "login" not in self.page.url.lower():
                print(f"  ✅ Already logged in (cookies)")
                return True
        
        if not email or not password:
            print(f"  ⚠️  Need credentials for {config['name']}")
            return False
        
        await self.page.goto(config["login_url"], wait_until="domcontentloaded")
        await asyncio.sleep(2)
        
        try:
            # Fill email
            email_input = self.page.locator("input[type='email'], input[name='email'], input[id*='email']")
            await email_input.first.fill(email)
            
            # Fill password
            pw_input = self.page.locator("input[type='password']")
            await pw_input.first.fill(password)
            
            # Submit
            submit = self.page.locator("button[type='submit'], input[type='submit']")
            await submit.first.click()
            
            await asyncio.sleep(3)
            
            if "login" in self.page.url.lower():
                print(f"  ❌ Login failed")
                return False
            
            await self._save_cookies(platform)
            print(f"  ✅ Logged in")
            return True
        except Exception as e:
            print(f"  ❌ Login error: {e}")
            return False
    
    async def upload_d2d(self, manifest_id: str, title: str = None) -> bool:
        """Upload a book to Draft2Digital."""
        config = PLATFORMS["d2d"]
        file_dir = config["file_dir"]
        
        if not file_dir.exists():
            print(f"  ❌ No D2D files at {file_dir}")
            return False
        
        d = json.loads(self.conn.execute(
            "SELECT data FROM manifests WHERE manifest_id = ?", (manifest_id,)
        ).fetchone()[0])
        
        book_title = title or d.get("title", {}).get("canonical", "Unknown")
        author = d.get("author", "Darryl E. Brown")
        
        title_slug = book_title.lower().replace(" ", "-").replace("'", "")[:40]
        epub_files = list(file_dir.glob(f"*{title_slug}*{config['file_ext']}"))
        cover_files = list(file_dir.glob(f"*{title_slug}*{config['cover_ext']}"))
        
        if not epub_files:
            epub_files = list(file_dir.glob(f"*{title_slug[:15]}*{config['file_ext']}"))
        
        if not epub_files:
            print(f"  ❌ No EPUB for '{book_title}'")
            return False
        
        epub_path = epub_files[0]
        cover_path = cover_files[0] if cover_files else None
        
        print(f"  📤 Uploading '{book_title}' to D2D...")
        
        async def _do_upload():
            await self.page.goto(config["new_book_url"], wait_until="domcontentloaded")
            await asyncio.sleep(3)
            
            # Click "START EBOOK" button
            start = self.page.locator("text=START EBOOK, text=Create Ebook, text=Add New Book, text=Start Ebook")
            if await start.count() > 0:
                await start.first.click()
                await asyncio.sleep(2)
            
            # Fill title
            title_inp = self.page.locator("input[name='title'], input[id*='title'], input[placeholder*='Title']")
            if await title_inp.count() > 0:
                await title_inp.first.fill(book_title)
            
            # Fill author
            author_inp = self.page.locator("input[name='author'], input[id*='author'], input[placeholder*='Author']")
            if await author_inp.count() > 0:
                await author_inp.first.fill(author)
            
            # Upload EPUB
            file_inp = self.page.locator("input[type='file']")
            if await file_inp.count() > 0:
                await file_inp.first.set_input_files(str(epub_path))
                await asyncio.sleep(3)
            
            # Upload cover
            if cover_path and await file_inp.count() > 1:
                await file_inp.nth(1).set_input_files(str(cover_path))
                await asyncio.sleep(2)
            
            # Record evidence
            now = datetime.now(timezone.utc).isoformat()
            self.conn.execute("""
                INSERT INTO platform_evidence 
                (manifest_id, adapter_type, is_mock, platform, draft_id, operation_id,
                 timestamp, evidence_data, errors, warnings)
                VALUES (?, 'PlaywrightV2', 0, 'd2d', ?, 'upload-manuscript', ?, ?, ?, ?)
            """, (manifest_id, f"pw2-{uuid.uuid4().hex[:8]}", now,
                  json.dumps({"file": str(epub_path), "status": "uploaded"}),
                  json.dumps([]), json.dumps([])))
            self.conn.commit()
            
            self.stats["uploads"] += 1
            print(f"  ✅ Uploaded to D2D")
            return True
        
        try:
            return await self._retry(_do_upload, max_attempts=3)
        except Exception as e:
            self.stats["failures"] += 1
            print(f"  ❌ Upload failed after retries: {e}")
            return False
    
    async def upload_kdp(self, manifest_id: str, title: str = None) -> bool:
        """Upload to KDP (placeholder)."""
        print("  ⏳ KDP upload not yet implemented in v2")
        return False
    
    async def upload(self, platform: str, manifest_id: str, title: str = None) -> bool:
        """Upload to any platform."""
        method_name = f"upload_{platform}"
        method = getattr(self, method_name, None)
        if not method:
            print(f"  ❌ No uploader for {platform}")
            return False
        return await method(manifest_id, title)
    
    async def upload_batch(self, platform: str, limit: int = 5) -> Dict:
        """Upload a batch of approved books."""
        rows = self.conn.execute("""
            SELECT manifest_id, json_extract(data, '$.title.canonical')
            FROM manifests WHERE state = 'approved'
            AND manifest_id NOT IN (
                SELECT manifest_id FROM platform_evidence 
                WHERE operation_id = 'upload-manuscript' AND adapter_type = 'PlaywrightV2'
            )
            LIMIT ?
        """, (limit,)).fetchall()
        
        results = {"success": 0, "failed": 0}
        
        for r in rows:
            if await self.upload(platform, r[0], r[1]):
                results["success"] += 1
            else:
                results["failed"] += 1
        
        return results

# ─── CLI ────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="GGB Platform Uploader v2 (Backup)")
    parser.add_argument("--platform", "-p", default="d2d", help="Platform")
    parser.add_argument("--login", action="store_true", help="Login to platform")
    parser.add_argument("--email", help="Login email")
    parser.add_argument("--password", help="Login password")
    parser.add_argument("--batch", type=int, default=1, help="Books to upload")
    parser.add_argument("--manifest", help="Specific manifest ID")
    parser.add_argument("--visible", action="store_true", help="Show browser")
    
    args = parser.parse_args()
    
    async def main():
        uploader = PlatformUploaderV2(headless=not args.visible)
        
        try:
            if args.login:
                email = args.email or os.environ.get(f"{args.platform.upper()}_EMAIL")
                password = args.password or os.environ.get(f"{args.platform.upper()}_PASSWORD")
                await uploader.login(args.platform, email, password)
            
            elif args.manifest:
                await uploader.login(args.platform)
                await uploader.upload(args.platform, args.manifest)
            
            elif args.batch:
                await uploader.login(args.platform)
                results = await uploader.upload_batch(args.platform, args.batch)
                print(f"\n📊 Batch: {results['success']} success, {results['failed']} failed")
            
            else:
                parser.print_help()
        
        finally:
            await uploader._stop()
    
    asyncio.run(main())
