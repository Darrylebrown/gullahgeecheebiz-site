#!/usr/bin/env python3
"""
Draft2Digital Book Submission Connector
Automates the process of uploading and submitting EPUB files to Draft2Digital
"""

import os
import sys
import time
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import asyncio
from datetime import datetime
import _env_creds

try:
    from playwright.async_api import async_playwright, Page, Browser, BrowserContext
except ImportError:
    print("ERROR: Playwright not installed. Run: pip install playwright")
    print("Then run: playwright install")
    sys.exit(1)

# Configuration
D2D_EMAIL = _env_creds.require("D2D_EMAIL")
D2D_PASSWORD = _env_creds.require("D2D_PASSWORD")
EPUB_DIRECTORY = "/Users/darrylsmac/gullahgeecheebiz-site/publish/for-distribution/google-play/"
LOG_FILE = "/Users/darrylsmac/gullahgeecheebiz-site/ggb-engine/headquarters/d2d_submission.log"

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class Draft2DigitalConnector:
    """Main connector class for Draft2Digital submissions"""
    
    def __init__(self):
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.is_logged_in = False
        
    async def __aenter__(self):
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.cleanup()
        
    async def initialize_browser(self) -> bool:
        """Initialize Playwright browser"""
        try:
            logger.info("Initializing browser...")
            playwright = await async_playwright().start()
            
            # Use Chromium with realistic settings
            self.browser = await playwright.chromium.launch(
                headless=False,  # Set to True for headless operation
                args=[
                    '--no-sandbox',
                    '--disable-blink-features=AutomationControlled',
                    '--disable-web-security',
                    '--allow-running-insecure-content'
                ]
            )
            
            # Create context with realistic user agent
            self.context = await self.browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            )
            
            self.page = await self.context.new_page()
            
            # Set longer timeout for file operations
            self.page.set_default_timeout(60000)  # 60 seconds
            
            logger.info("Browser initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize browser: {str(e)}")
            return False
    
    async def login(self) -> bool:
        """Login to Draft2Digital"""
        try:
            logger.info("Navigating to Draft2Digital login page...")
            await self.page.goto("https://www.draft2digital.com/login", wait_until="networkidle")
            
            # Wait for login form
            await self.page.wait_for_selector('input[name="email"]', timeout=10000)
            
            logger.info("Filling login credentials...")
            await self.page.fill('input[name="email"]', D2D_EMAIL)
            await self.page.fill('input[name="password"]', D2D_PASSWORD)
            
            # Click login button
            await self.page.click('button[type="submit"]')
            
            # Wait for login to complete - look for dashboard or profile elements
            try:
                await self.page.wait_for_selector('[data-test="dashboard"], .dashboard, #dashboard', timeout=15000)
                logger.info("Login successful - dashboard detected")
                self.is_logged_in = True
                return True
            except:
                # Alternative check - look for navigation elements that appear after login
                try:
                    await self.page.wait_for_selector('a[href*="books"], .nav-books, [data-nav="books"]', timeout=10000)
                    logger.info("Login successful - navigation detected")
                    self.is_logged_in = True
                    return True
                except:
                    # Check if we're redirected away from login page
                    current_url = self.page.url
                    if "login" not in current_url.lower():
                        logger.info("Login successful - redirected from login page")
                        self.is_logged_in = True
                        return True
                    else:
                        logger.error("Login failed - still on login page")
                        return False
                        
        except Exception as e:
            logger.error(f"Login failed: {str(e)}")
            return False
    
    async def navigate_to_upload(self) -> bool:
        """Navigate to book upload section"""
        try:
            logger.info("Navigating to book upload section...")
            
            # Try multiple possible URLs for book upload
            upload_urls = [
                "https://www.draft2digital.com/books/new",
                "https://www.draft2digital.com/books/upload",
                "https://www.draft2digital.com/dashboard/books/new",
                "https://www.draft2digital.com/add-book"
            ]
            
            for url in upload_urls:
                try:
                    await self.page.goto(url, wait_until="networkidle", timeout=15000)
                    
                    # Check if we found an upload form
                    upload_selectors = [
                        'input[type="file"]',
                        '[data-test="file-upload"]',
                        '.file-upload',
                        '#file-upload',
                        'input[accept*="epub"]'
                    ]
                    
                    for selector in upload_selectors:
                        try:
                            await self.page.wait_for_selector(selector, timeout=3000)
                            logger.info(f"Found upload form at {url}")
                            return True
                        except:
                            continue
                            
                except Exception as e:
                    logger.debug(f"Failed to access {url}: {str(e)}")
                    continue
            
            # If direct URLs don't work, try to find upload link in navigation
            logger.info("Trying to find upload link in navigation...")
            
            nav_selectors = [
                'a[href*="upload"]',
                'a[href*="new"]',
                'a[href*="add"]',
                '[data-test="add-book"]',
                '.add-book',
                'button:has-text("Add Book")',
                'a:has-text("Add Book")',
                'button:has-text("Upload")',
                'a:has-text("Upload")'
            ]
            
            for selector in nav_selectors:
                try:
                    element = await self.page.wait_for_selector(selector, timeout=2000)
                    if element:
                        await element.click()
                        await self.page.wait_for_load_state("networkidle")
                        
                        # Check if upload form appeared
                        try:
                            await self.page.wait_for_selector('input[type="file"]', timeout=5000)
                            logger.info("Successfully navigated to upload form")
                            return True
                        except:
                            continue
                except:
                    continue
            
            logger.error("Could not find book upload section")
            return False
            
        except Exception as e:
            logger.error(f"Failed to navigate to upload section: {str(e)}")
            return False
    
    async def upload_epub(self, epub_path: str, metadata: Dict[str, str]) -> bool:
        """Upload EPUB file with metadata"""
        try:
            logger.info(f"Uploading EPUB file: {epub_path}")
            
            if not os.path.exists(epub_path):
                logger.error(f"EPUB file not found: {epub_path}")
                return False
            
            # Find file input
            file_inputs = [
                'input[type="file"]',
                'input[accept*="epub"]',
                '[data-test="file-upload"] input',
                '.file-upload input'
            ]
            
            file_input = None
            for selector in file_inputs:
                try:
                    file_input = await self.page.wait_for_selector(selector, timeout=3000)
                    if file_input:
                        break
                except:
                    continue
            
            if not file_input:
                logger.error("Could not find file upload input")
                return False
            
            # Upload the file
            logger.info("Setting file for upload...")
            await file_input.set_input_files(epub_path)
            
            # Wait for file to process
            logger.info("Waiting for file to process...")
            await asyncio.sleep(3)
            
            # Wait for upload to complete - look for success indicators or metadata forms
            upload_complete = False
            wait_selectors = [
                '[data-test="upload-complete"]',
                '.upload-success',
                'input[name="title"]',
                'input[placeholder*="title"]',
                '.metadata-form',
                '[data-test="metadata"]'
            ]
            
            for selector in wait_selectors:
                try:
                    await self.page.wait_for_selector(selector, timeout=10000)
                    upload_complete = True
                    logger.info("File upload completed")
                    break
                except:
                    continue
            
            if not upload_complete:
                logger.warning("Upload completion status unclear, proceeding with metadata...")
            
            # Fill in metadata if forms are available
            await self.fill_metadata(metadata)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to upload EPUB: {str(e)}")
            return False
    
    async def fill_metadata(self, metadata: Dict[str, str]) -> bool:
        """Fill in book metadata"""
        try:
            logger.info("Filling metadata...")
            
            # Common metadata fields and their possible selectors
            field_mappings = {
                'title': [
                    'input[name="title"]',
                    'input[placeholder*="title"]',
                    '#title',
                    '[data-field="title"]'
                ],
                'author': [
                    'input[name="author"]',
                    'input[placeholder*="author"]',
                    '#author',
                    '[data-field="author"]'
                ],
                'description': [
                    'textarea[name="description"]',
                    'textarea[placeholder*="description"]',
                    '#description',
                    '[data-field="description"]'
                ],
                'price': [
                    'input[name="price"]',
                    'input[placeholder*="price"]',
                    '#price',
                    '[data-field="price"]'
                ]
            }
            
            for field_name, selectors in field_mappings.items():
                if field_name in metadata:
                    value = metadata[field_name]
                    logger.info(f"Setting {field_name}: {value}")
                    
                    for selector in selectors:
                        try:
                            element = await self.page.wait_for_selector(selector, timeout=2000)
                            if element:
                                await element.fill(value)
                                logger.info(f"Successfully set {field_name}")
                                break
                        except:
                            continue
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to fill metadata: {str(e)}")
            return False
    
    async def submit_book(self) -> Tuple[bool, str]:
        """Submit the book for distribution"""
        try:
            logger.info("Submitting book for distribution...")
            
            # Look for submit/publish buttons
            submit_selectors = [
                'button[type="submit"]',
                'button:has-text("Submit")',
                'button:has-text("Publish")',
                'button:has-text("Save")',
                '[data-test="submit"]',
                '.submit-btn',
                '#submit-book'
            ]
            
            for selector in submit_selectors:
                try:
                    element = await self.page.wait_for_selector(selector, timeout=3000)
                    if element:
                        await element.click()
                        logger.info("Clicked submit button")
                        
                        # Wait for submission to process
                        await asyncio.sleep(5)
                        
                        # Look for success indicators
                        success_selectors = [
                            '.success',
                            '[data-test="success"]',
                            ':has-text("successfully")',
                            ':has-text("submitted")',
                            ':has-text("published")'
                        ]
                        
                        for success_selector in success_selectors:
                            try:
                                await self.page.wait_for_selector(success_selector, timeout=5000)
                                return True, "Book submitted successfully"
                            except:
                                continue
                        
                        # Check URL change as success indicator
                        current_url = self.page.url
                        if "success" in current_url.lower() or "books" in current_url.lower():
                            return True, "Book submitted successfully (URL changed)"
                        
                        break
                except:
                    continue
            
            return False, "Could not find submit button or confirm submission"
            
        except Exception as e:
            error_msg = f"Failed to submit book: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
    
    async def cleanup(self):
        """Clean up browser resources"""
        try:
            if self.context:
                await self.context.close()
            if self.browser:
                await self.browser.close()
            logger.info("Browser cleanup completed")
        except Exception as e:
            logger.error(f"Error during cleanup: {str(e)}")

def get_epub_files(directory: str) -> List[str]:
    """Get list of EPUB files from directory"""
    try:
        epub_files = []
        path = Path(directory)
        
        if path.exists() and path.is_dir():
            for file in path.glob("*.epub"):
                epub_files.append(str(file))
            
        logger.info(f"Found {len(epub_files)} EPUB files in {directory}")
        return epub_files
        
    except Exception as e:
        logger.error(f"Error scanning directory {directory}: {str(e)}")
        return []

def extract_metadata_from_filename(epub_path: str) -> Dict[str, str]:
    """Extract basic metadata from filename"""
    filename = Path(epub_path).stem
    
    # Basic metadata - you can enhance this based on your naming convention
    metadata = {
        'title': filename.replace('_', ' ').replace('-', ' ').title(),
        'author': 'Darryle Brown',  # Default author
        'description': f'A compelling story: {filename}',
        'price': '2.99'  # Default price
    }
    
    return metadata

async def main():
    """Main execution function"""
    logger.info("=== Draft2Digital Book Submission Connector Started ===")
    
    # Check if EPUB directory exists
    if not os.path.exists(EPUB_DIRECTORY):
        logger.error(f"EPUB directory not found: {EPUB_DIRECTORY}")
        return
    
    # Get EPUB files
    epub_files = get_epub_files(EPUB_DIRECTORY)
    if not epub_files:
        logger.error("No EPUB files found to upload")
        return
    
    # Initialize connector
    async with Draft2DigitalConnector() as connector:
        
        # Initialize browser
        if not await connector.initialize_browser():
            logger.error("Failed to initialize browser")
            return
        
        # Login
        if not await connector.login():
            logger.error("Failed to login to Draft2Digital")
            return
        
        # Process each EPUB file
        for epub_file in epub_files:
            logger.info(f"\n=== Processing: {os.path.basename(epub_file)} ===")
            
            try:
                # Navigate to upload section
                if not await connector.navigate_to_upload():
                    logger.error(f"Failed to navigate to upload section for {epub_file}")
                    continue
                
                # Extract metadata
                metadata = extract_metadata_from_filename(epub_file)
                logger.info(f"Metadata: {metadata}")
                
                # Upload EPUB
                if not await connector.upload_epub(epub_file, metadata):
                    logger.error(f"Failed to upload {epub_file}")
                    continue
                
                # Submit book
                success, message = await connector.submit_book()
                
                if success:
                    logger.info(f"✅ SUCCESS: {os.path.basename(epub_file)} - {message}")
                else:
                    logger.error(f"❌ FAILED: {os.path.basename(epub_file)} - {message}")
                
                # Wait between submissions
                await asyncio.sleep(2)
                
            except Exception as e:
                logger.error(f"Error processing {epub_file}: {str(e)}")
                continue
    
    logger.info("=== Draft2Digital Book Submission Connector Completed ===")

def sync_main():
    """Synchronous wrapper for main function"""
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Process interrupted by user")
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")

if __name__ == "__main__":
    # Ensure log directory exists
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    
    # Run the connector
    sync_main()