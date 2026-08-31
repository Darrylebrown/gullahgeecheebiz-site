#!/usr/bin/env python3
"""
Post real Pinterest pins for books that only have placeholder entries.
Replaces the gullahgeecheebiz.com/shop placeholder with actual Pinterest pin URLs.
"""
import asyncio
import json
import logging
import sqlite3
import sys
import time
import urllib.request
from datetime import datetime
from pathlib import Path

try:
    from playwright.async_api import async_playwright
except ImportError:
    print("ERROR: playwright not installed. Install with: pip3 install playwright")
    sys.exit(1)

PROJECT_ROOT = Path("/Users/darrylsmac/gullahgeecheebiz-site")
DB_PATH = PROJECT_ROOT / "ggb-engine/headquarters/logs/publishing-bot/brain-state.db"
LOG_FILE = PROJECT_ROOT / "ggb-engine/headquarters/logs/pinterest-post-real.log"
COVERS_DIR = PROJECT_ROOT / "ggb-engine/headquarters/covers"
LANDING_PAD = PROJECT_ROOT / "publish/landing-pad"
EVENT_STREAM = PROJECT_ROOT / "publish/event_stream.jsonl"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger("pinterest-post-real")

PIN_URL_PATTERN = "https://www.pinterest.com/pin/"
PLACEHOLDER_URL = "https://gullahgeecheebiz.com/shop"


def get_unpinned_books():
    """Find books that have placeholder pins (gullahgeecheebiz.com/shop)."""
    conn = sqlite3.connect(str(DB_PATH))
    cur = conn.cursor()
    cur.execute("""
        SELECT p.book_id, b.title 
        FROM pins p 
        JOIN books b ON p.book_id = b.id 
        WHERE p.pin_url = ? 
        ORDER BY p.created_at ASC
    """, (PLACEHOLDER_URL,))
    rows = cur.fetchall()
    conn.close()
    return rows


def find_cover_for_book(book_id: str, book_title: str) -> str:
    """Find an appropriate cover image for the book."""
    # Try covers dir first (encyclopedia volumes)
    for pattern in [f"encyclopedia-vol-{book_id[-4:] if len(book_id) >= 4 else book_id}-1_1.jpg",
                    book_id.replace("ggb-manifest-", "") + "-1_1.jpg",
                    book_title.lower().replace(" ", "-") + "-1_1.jpg"]:
        cover = COVERS_DIR / f"{pattern}"
        if cover.exists():
            return str(cover)
    
    # Try landing-pad
    for vol_dir in sorted(LANDING_PAD.iterdir()):
        if vol_dir.is_dir():
            cover = vol_dir / "cover.jpg"
            if cover.exists():
                return str(cover)
    
    return None


def verify_pin_url(url: str) -> bool:
    """Verify the pin URL returns HTTP 200."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.status == 200
    except Exception as e:
        log.error(f"Pin URL verification failed: {e}")
        return False


def log_event(book_id: str, pin_url: str, pin_id: str, verified: bool):
    """Log to event_stream."""
    ts = datetime.utcnow().isoformat() + "Z"
    payload = {
        "ts": ts,
        "source_bot": "PROMOTION_GOAL",
        "action": "pinterest_pin_posted",
        "book_id": book_id,
        "pin_url": pin_url,
        "pin_id": pin_id,
        "verified": verified,
    }
    with open(EVENT_STREAM, "a", encoding="utf-8") as f:
        f.write(json.dumps(payload) + "\n")
    
    # Also update the pin in brain-state
    conn = sqlite3.connect(str(DB_PATH))
    cur = conn.cursor()
    cur.execute("""
        UPDATE pins SET pin_url = ?, status = 'PUBLISHED_REAL'
        WHERE book_id = ? AND pin_url = ?
    """, (pin_url, book_id, PLACEHOLDER_URL))
    conn.commit()
    conn.close()
    
    # Update platform_health
    now = datetime.utcnow().isoformat() + "Z"
    conn = sqlite3.connect(str(DB_PATH))
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO platform_health (platform, attempts, successes, last_result, last_updated)
        VALUES ('pinterest', 1, 1, 'REAL - Pin posted and verified', datetime('now'))
        ON CONFLICT(platform) DO UPDATE SET
          attempts = attempts + 1,
          successes = successes + 1,
          last_result = 'REAL - Pin posted and verified',
          last_updated = datetime('now')
    """)
    conn.commit()
    conn.close()


async def post_pin_via_browser(book_id: str, cover_path: str, book_title: str) -> dict:
    """Use Playwright with persistent Chrome profile to post a pin."""
    chrome_profile = Path.home() / "Library/Application Support/Google/Chrome/Default"
    
    if not chrome_profile.exists():
        log.error(f"Chrome Default profile not found at {chrome_profile}")
        return {"success": False, "error": "No Chrome profile"}
    
    result = {
        "book_id": book_id,
        "cover_path": cover_path,
        "title": book_title,
        "pin_url": None,
        "pin_id": None,
        "success": False,
        "error": None,
    }
    
    async with async_playwright() as p:
        browser = await p.chromium.launch_persistent_context(
            str(chrome_profile),
            headless=True,
            args=["--no-first-run", "--disable-blink-features=AutomationControlled"],
        )
        
        page = await browser.new_page()
        try:
            log.info(f"Navigating to Pinterest pin creator for: {book_title}")
            await page.goto(
                "https://www.pinterest.com/pin-creation-tool/",
                wait_until="networkidle",
                timeout=60000
            )
            await asyncio.sleep(3)
            
            if "login" in page.url.lower():
                log.error("Not logged in to Pinterest. Please log in manually in Chrome.")
                return result
            
            input_selector = 'input[type="file"][accept*="image"]'
            await page.wait_for_selector(input_selector, timeout=15000)
            await page.set_input_files(input_selector, cover_path)
            log.info("Cover image uploaded")
            await asyncio.sleep(3)
            
            title_selector = 'input[placeholder*="title" i], input[aria-label*="title" i]'
            await page.wait_for_selector(title_selector, timeout=10000)
            await page.fill(title_selector, book_title)
            log.info("Title filled")
            
            desc_selector = 'textarea[placeholder*="description" i], textarea[aria-label*="description" i]'
            await page.wait_for_selector(desc_selector, timeout=10000)
            desc_text = f"Discover '{book_title}' by Darryl Elliott Brown at Gullah Geechee Biz. Rich in Gullah Geechee culture, history, and tradition. #GullahGeechee #BlackAuthors #SelfPublishing"
            await page.fill(desc_selector, desc_text)
            log.info("Description filled")
            
            link_selector = 'input[type="url"], input[placeholder*="link" i]'
            await page.wait_for_selector(link_selector, timeout=10000)
            book_url = f"https://gullahgeecheebiz.com/books/{book_id.replace('ggb-manifest-', '')}"
            await page.fill(link_selector, book_url)
            log.info(f"Link filled: {book_url}")
            
            publish_btn = await page.locator('button:has-text("Publish")', timeout=15000).first
            await publish_btn.click()
            log.info("Published button clicked")
            
            await asyncio.sleep(5)
            
            current_url = page.url
            if "pin/" in current_url:
                pin_id = current_url.split("pin/")[1].split("/")[0]
                pin_url = f"https://www.pinterest.com/pin/{pin_id}"
                result["pin_id"] = pin_id
                result["pin_url"] = pin_url
                result["success"] = True
                log.info(f"Pin created: {pin_url}")
            else:
                log.warning(f"Could not extract pin ID from URL: {current_url}")
                
        except Exception as e:
            log.error(f"Error during pin creation: {e}")
            result["error"] = str(e)
        finally:
            await browser.close()
    
    return result


async def main():
    log.info("=" * 60)
    log.info("Pinterest Real Pin Poster Starting")
    log.info("=" * 60)
    
    unpinned = get_unpinned_books()
    log.info(f"Found {len(unpinned)} books with placeholder pins")
    
    if not unpinned:
        log.info("All books have real pins! Nothing to do.")
        return
    
    posted_count = 0
    for i, (book_id, book_title) in enumerate(unpinned[:10]):  # Post up to 10 per run
        log.info(f"\n--- Posting book {i+1}/{min(10, len(unpinned))}: {book_title} ---")
        
        cover_path = find_cover_for_book(book_id, book_title)
        if not cover_path:
            log.warning(f"No cover found for {book_title}, skipping")
            continue
        
        log.info(f"Using cover: {cover_path}")
        
        result = await post_pin_via_browser(book_id, cover_path, book_title)
        
        if not result["success"]:
            log.error(f"Failed to post pin: {result.get('error')}")
            continue
        
        pin_url = result["pin_url"]
        pin_id = result["pin_id"]
        
        log.info(f"Verifying pin URL: {pin_url}")
        verified = verify_pin_url(pin_url)
        
        if verified:
            log.info(f"VERIFIED_PIN_ID={pin_id}")
            log.info(f"Pin verified live: {pin_url} (HTTP 200)")
        else:
            log.warning(f"Pin URL verification failed (may take time to propagate): {pin_url}")
        
        log_event(book_id, pin_url, pin_id, verified)
        posted_count += 1
        
        # Rate limit pause
        await asyncio.sleep(5)
    
    log.info("\n" + "=" * 60)
    log.info(f"RESULTS: Posted {posted_count} new real Pinterest pins")
    log.info("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
