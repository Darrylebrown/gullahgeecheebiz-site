import asyncio
import os
import re
import json
from pathlib import Path
from playwright.async_api import async_playwright, Page, expect, BrowserContext, TimeoutError as PlaywrightTimeoutError

# --- Configuration ---
# Your Google account credentials (use environment variables for security!)
GOOGLE_EMAIL = os.environ.get("GOOGLE_EMAIL")
GOOGLE_PASSWORD = os.environ.get("GOOGLE_PASSWORD")

# URL for Google Play Books Publisher Portal
PLATFORM_URL = "https://play.google.com/books/publish/"

# Directory containing your book files
BOOKS_DIR = Path("/Users/darrylsmac/gullahgeecheebiz-site/publish/for-distribution/google-play")

# Output directory for logs, cookies, etc.
OUTPUT_DIR = Path("playwright_output")
OUTPUT_DIR.mkdir(exist_ok=True)

# Path for storing session cookies (for persistence)
STORAGE_STATE_PATH = OUTPUT_DIR / "storage_state.json"

# Number of files to upload in a single batch (adjust based on UI performance)
BATCH_SIZE = 5

# Set to True to run in headless mode (no browser UI), False to see the browser
HEADLESS = True

# Playwright timeout for actions (milliseconds)
PLAYWRIGHT_TIMEOUT = 30000 # 30 seconds

# --- Helper Functions ---

async def save_storage_state(context: BrowserContext):
    """Saves the browser context's state (cookies, local storage) to a file."""
    await context.storage_state(path=STORAGE_STATE_PATH)
    print(f"Session state saved to {STORAGE_STATE_PATH}")

async def load_storage_state_or_none():
    """Loads the browser context's state from a file, returns None if not found."""
    if STORAGE_STATE_PATH.exists():
        print(f"Loading session state from {STORAGE_STATE_PATH}")
        return STORAGE_STATE_PATH
    print("No existing session state found.")
    return None

def get_book_files(directory: Path) -> list[Path]:
    """
    Retrieves all PDF and EPUB files from the specified directory.
    You might need to adjust this if you have other file types or specific naming.
    """
    book_files = []
    for file_path in directory.iterdir():
        if file_path.is_file() and file_path.suffix.lower() in [".pdf", ".epub"]:
            book_files.append(file_path)
    return sorted(book_files) # Ensure consistent order

async def handle_google_login(page: Page):
    """
    Handles the Google login process.
    This is a generic approach and might need adjustments based on 2FA, new prompts, etc.
    """
    if not GOOGLE_EMAIL or not GOOGLE_PASSWORD:
        raise ValueError("Google email and password must be set as environment variables.")

    print("Attempting Google login...")

    # Wait for email input and enter email
    try:
        await page.wait_for_selector('input[type="email"]', timeout=PLAYWRIGHT_TIMEOUT)
        await page.fill('input[type="email"]', GOOGLE_EMAIL)
        await page.click('button:has-text("Next")')
        print("Email entered.")
    except PlaywrightTimeoutError:
        print("Email input not found, might already be logged in or a different prompt.")
        return # Assume logged in or a different flow is active

    # Wait for password input and enter password
    try:
        await page.wait_for_selector('input[type="password"]', timeout=PLAYWRIGHT_TIMEOUT)
        await page.fill('input[type="password"]', GOOGLE_PASSWORD)
        await page.click('button:has-text("Next")')
        print("Password entered.")
    except PlaywrightTimeoutError:
        print("Password input not found, might have skipped due to SSO or previous login.")

    # Wait for navigation to complete or for a common element on the publisher portal
    print("Waiting for login to complete...")
    try:
        await page.wait_for_url(re.compile(r"play\.google\.com/books/publish/home"), timeout=PLAYWRIGHT_TIMEOUT * 2)
        print("Successfully navigated to publisher home after login.")
    except PlaywrightTimeoutError:
        print("Could not confirm navigation to publisher home. Please check manually.")
        # Attempt to navigate directly to the dashboard just in case
        await page.goto(PLATFORM_URL, wait_until="networkidle")


# --- Main Script ---

async def main():
    if not BOOKS_DIR.exists():
        print(f"Error: Books directory '{BOOKS_DIR}' does not exist.")
        return

    book_files = get_book_files(BOOKS_DIR)
    if not book_files:
        print(f"No PDF or EPUB files found in '{BOOKS_DIR}'. Exiting.")
        return

    print(f"Found {len(book_files)} book files to upload.")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=HEADLESS)
        context = await browser.new_context(storage_state=await load_storage_state_or_none())
        page = await context.new_page()

        try:
            print(f"Navigating to {PLATFORM_URL}")
            await page.goto(PLATFORM_URL, wait_until="networkidle")

            # Check if login is required (e.g., if storage_state was old or missing)
            if "accounts.google.com" in page.url:
                await handle_google_login(page)
                # After login, save the state for next time
                await save_storage_state(context)
                # Navigate again to the main page after login, just in case
                await page.goto(PLATFORM_URL, wait_until="networkidle")
            else:
                print("Appears to be logged in, skipping explicit login.")

            # --- Start Upload Process ---
            uploaded_count = 0
            failed_uploads = []
            
            # Navigate to the "Upload new books" section if not already there
            # This selector might need adjustment based on the actual UI.
            try:
                await page.wait_for_selector('a[href="/books/publish/books"]', timeout=PLAYWRIGHT_TIMEOUT)
                await page.click('a[href="/books/publish/books"]')
                print("Navigated to 'Your books' section.")

                # Look for an "Upload new books" button or link
                # This is a common pattern, but it might vary.
                # Example: a button with specific text or an icon
                await page.wait_for_selector('button:has-text("Upload new books"), a:has-text