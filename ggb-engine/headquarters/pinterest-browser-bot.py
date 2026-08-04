#!/usr/bin/env python3
"""
Pinterest Browser Bot - Automated Pin Creation
Uses Playwright to automate Pinterest web interface for pin creation.
"""

import asyncio
import csv
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from urllib.parse import urlparse

from dotenv import load_dotenv
from playwright.async_api import Browser, BrowserContext, Page, Playwright, async_playwright

# Load environment variables
load_dotenv()

# Configuration
CSV_FILE_PATH = "/Users/darrylsmac/gullahgeecheebiz-site/ggb-engine/headquarters/logs/universal-submitter/csv/pinterest-feed.csv"
PROGRESS_FILE = "/Users/darrylsmac/gullahgeecheebiz-site/ggb-engine/headquarters/logs/pinterest-progress.json"
LOG_FILE = "/Users/darrylsmac/gullahgeecheebiz-site/ggb-engine/headquarters/logs/pinterest-bot.log"

# Ensure log directory exists
os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
os.makedirs(os.path.dirname(PROGRESS_FILE), exist_ok=True)

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

class PinterestBrowserBot:
    def __init__(self):
        self.email = os.getenv('PINTEREST_EMAIL')
        self.password = os.getenv('PINTEREST_PASSWORD')
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.progress_data = self.load_progress()
        
        if not self.email or not self.password:
            raise ValueError("PINTEREST_EMAIL and PINTEREST_PASSWORD must be set in .env file")

    def load_progress(self) -> Dict:
        """Load progress data from file"""
        try:
            if os.path.exists(PROGRESS_FILE):
                with open(PROGRESS_FILE, 'r') as f:
                    return json.load(f)
        except Exception as e:
            logger.warning(f"Could not load progress file: {e}")
        
        return {
            'completed_pins': [],
            'failed_pins': [],
            'last_run': None,
            'total_processed': 0
        }

    def save_progress(self):
        """Save progress data to file"""
        try:
            self.progress_data['last_run'] = datetime.now().isoformat()
            with open(PROGRESS_FILE, 'w') as f:
                json.dump(self.progress_data, f, indent=2)
        except Exception as e:
            logger.error(f"Could not save progress: {e}")

    async def setup_browser(self, headless: bool = False):
        """Initialize browser and context"""
        playwright = await async_playwright().start()
        
        # Launch browser with realistic settings
        self.browser = await playwright.chromium.launch(
            headless=headless,
            args=[
                '--no-first-run',
                '--disable-blink-features=AutomationControlled',
                '--disable-web-security',
                '--disable-features=VizDisplayCompositor'
            ]
        )
        
        # Create context with realistic user agent
        self.context = await self.browser.new_context(
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            viewport={'width': 1920, 'height': 1080},
            locale='en-US',
            timezone_id='America/New_York'
        )
        
        # Create page
        self.page = await self.context.new_page()
        
        # Add stealth modifications
        await self.page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined,
            });
        """)

    async def login_to_pinterest(self) -> bool:
        """Login to Pinterest"""
        try:
            logger.info("Navigating to Pinterest login page...")
            await self.page.goto('https://www.pinterest.com/login/', wait_until='networkidle')
            
            # Wait for page to load
            await asyncio.sleep(2)
            
            # Check if already logged in
            if 'pinterest.com/login' not in self.page.url:
                logger.info("Already logged in to Pinterest")
                return True
            
            # Fill email
            email_selector = 'input[id="email"]'
            await self.page.wait_for_selector(email_selector, timeout=10000)
            await self.page.fill(email_selector, self.email)
            logger.info("Email filled")
            
            # Fill password
            password_selector = 'input[id="password"]'
            await self.page.fill(password_selector, self.password)
            logger.info("Password filled")
            
            # Click login button
            login_button = 'button[type="submit"]'
            await self.page.click(login_button)
            logger.info("Login button clicked")
            
            # Wait for navigation or error
            try:
                await self.page.wait_for_url('https://www.pinterest.com/', timeout=15000)
                logger.info("Successfully logged in to Pinterest")
                return True
            except:
                # Check for CAPTCHA or 2FA
                await asyncio.sleep(3)
                current_url = self.page.url
                
                if 'challenge' in current_url or 'captcha' in current_url:
                    logger.warning("CAPTCHA detected. Please solve manually...")
                    input("Press Enter after solving CAPTCHA...")
                    await self.page.wait_for_url('https://www.pinterest.com/', timeout=60000)
                    return True
                
                if 'verify' in current_url or 'two-factor' in current_url:
                    logger.warning("2FA detected. Please complete verification manually...")
                    input("Press Enter after completing 2FA...")
                    await self.page.wait_for_url('https://www.pinterest.com/', timeout=60000)
                    return True
                
                logger.error(f"Login failed. Current URL: {current_url}")
                return False
                
        except Exception as e:
            logger.error(f"Login error: {e}")
            return False

    async def navigate_to_pin_creator(self) -> bool:
        """Navigate to the pin creation page"""
        try:
            logger.info("Navigating to pin creator...")
            await self.page.goto('https://www.pinterest.com/pin-creation-tool/', wait_until='networkidle')
            
            # Wait for the pin creation interface to load
            await asyncio.sleep(3)
            
            # Check if we're on the right page
            if 'pin-creation-tool' in self.page.url or 'pin-builder' in self.page.url:
                logger.info("Successfully navigated to pin creator")
                return True
            else:
                logger.error(f"Failed to navigate to pin creator. Current URL: {self.page.url}")
                return False
                
        except Exception as e:
            logger.error(f"Navigation error: {e}")
            return False

    async def create_pin(self, pin_data: Dict) -> bool:
        """Create a single pin"""
        try:
            title = pin_data.get('Title', '').strip()
            description = pin_data.get('Description', '').strip()
            link = pin_data.get('Link', '').strip()
            image_url = pin_data.get('Image URL', '').strip()
            
            logger.info(f"Creating pin: {title}")
            
            # Navigate to pin creation tool if not already there
            if 'pin-creation-tool' not in self.page.url and 'pin-builder' not in self.page.url:
                if not await self.navigate_to_pin_creator():
                    return False
            
            # Wait for the image upload area
            try:
                # Try different selectors for image upload
                image_selectors = [
                    'input[type="file"][accept*="image"]',
                    'input[data-test-id="media-upload-input"]',
                    '[data-test-id="media-upload-input"]',
                    'input[accept*="image"]'
                ]
                
                image_input = None
                for selector in image_selectors:
                    try:
                        await self.page.wait_for_selector(selector, timeout=5000)
                        image_input = selector
                        break
                    except:
                        continue
                
                if not image_input:
                    # Try to click upload area first
                    upload_selectors = [
                        '[data-test-id="media-upload-section"]',
                        '[data-test-id="pin-draft-image-upload"]',
                        'button:has-text("Choose from computer")',
                        'div:has-text("Drag and drop")'
                    ]
                    
                    for selector in upload_selectors:
                        try:
                            await self.page.click(selector, timeout=3000)
                            await asyncio.sleep(1)
                            break
                        except:
                            continue
                    
                    # Try to find file input again
                    for selector in image_selectors:
                        try:
                            await self.page.wait_for_selector(selector, timeout=5000)
                            image_input = selector
                            break
                        except:
                            continue
                
                if not image_input:
                    logger.error("Could not find image upload input")
                    return False
                
                # Download image temporarily if it's a URL
                if image_url.startswith('http'):
                    logger.info(f"Using image URL: {image_url}")
                    # For now, we'll skip URL-based images and handle only local files
                    # In a production environment, you'd want to download the image first
                    logger.warning("URL-based images not implemented in this version")
                    return False
                else:
                    # Assume it's a local file path
                    if os.path.exists(image_url):
                        await self.page.set_input_files(image_input, image_url)
                        logger.info("Image uploaded successfully")
                    else:
                        logger.error(f"Image file not found: {image_url}")
                        return False
                
            except Exception as e:
                logger.error(f"Image upload failed: {e}")
                return False
            
            # Wait for image to process
            await asyncio.sleep(3)
            
            # Fill in title
            title_selectors = [
                'input[data-test-id="pin-draft-title"]',
                'input[placeholder*="title" i]',
                'input[aria-label*="title" i]',
                '#pin-draft-title'
            ]
            
            title_filled = False
            for selector in title_selectors:
                try:
                    await self.page.wait_for_selector(selector, timeout=5000)
                    await self.page.fill(selector, title)
                    title_filled = True
                    logger.info("Title filled")
                    break
                except:
                    continue
            
            if not title_filled:
                logger.warning("Could not fill title")
            
            # Fill in description
            description_selectors = [
                'textarea[data-test-id="pin-draft-description"]',
                'textarea[placeholder*="description" i]',
                'textarea[aria-label*="description" i]',
                '#pin-draft-description'
            ]
            
            description_filled = False
            for selector in description_selectors:
                try:
                    await self.page.wait_for_selector(selector, timeout=5000)
                    await self.page.fill(selector, description)
                    description_filled = True
                    logger.info("Description filled")
                    break
                except:
                    continue
            
            if not description_filled:
                logger.warning("Could not fill description")
            
            # Fill in link
            if link:
                link_selectors = [
                    'input[data-test-id="pin-draft-link"]',
                    'input[placeholder*="link" i]',
                    'input[placeholder*="website" i]',
                    'input[type="url"]'
                ]
                
                for selector in link_selectors:
                    try:
                        await self.page.wait_for_selector(selector, timeout=5000)
                        await self.page.fill(selector, link)
                        logger.info("Link filled")
                        break
                    except:
                        continue
            
            # Wait a moment for form to update
            await asyncio.sleep(2)
            
            # Click publish/save button
            publish_selectors = [
                'button[data-test-id="pin-draft-publish-button"]',
                'button:has-text("Publish")',
                'button:has-text("Save")',
                'button:has-text("Create Pin")'
            ]
            
            published = False
            for selector in publish_selectors:
                try:
                    await self.page.wait_for_selector(selector, timeout=5000)
                    await self.page.click(selector)
                    published = True
                    logger.info("Publish button clicked")
                    break
                except:
                    continue
            
            if not published:
                logger.error("Could not find publish button")
                return False
            
            # Wait for pin to be created
            await asyncio.sleep(5)
            
            # Check for success (URL change or success message)
            current_url = self.page.url
            if 'pin/' in current_url or 'created' in current_url.lower():
                logger.info(f"Pin created successfully: {title}")
                return True
            else:
                # Look for success indicators
                success_indicators = [
                    'text="Pin published"',
                    'text="Pin saved"',
                    'text="Pin created"',
                    '[data-test-id="pin-success"]'
                ]
                
                for indicator in success_indicators:
                    try:
                        await self.page.wait_for_selector(indicator, timeout=3000)
                        logger.info(f"Pin created successfully: {title}")
                        return True
                    except:
                        continue
                
                logger.warning(f"Pin creation status unclear for: {title}")
                return False
                
        except Exception as e:
            logger.error(f"Error creating pin '{pin_data.get('Title', 'Unknown')}': {e}")
            return False

    def read_csv_data(self) -> List[Dict]:
        """Read pin data from CSV file"""
        try:
            if not os.path.exists(CSV_FILE_PATH):
                logger.error(f"CSV file not found: {CSV_FILE_PATH}")
                return []
            
            pins_data = []
            with open(CSV_FILE_PATH, 'r', encoding='utf-8') as file:
                reader = csv.DictReader(file)
                for row in reader:
                    pins_data.append(row)
            
            logger.info(f"Loaded {len(pins_data)} pins from CSV")
            return pins_data
            
        except Exception as e:
            logger.error(f"Error reading CSV file: {e}")
            return []

    def is_pin_already_processed(self, pin_data: Dict) -> bool:
        """Check if pin was already processed"""
        title = pin_data.get('Title', '').strip()
        return title in self.progress_data.get('completed_pins', [])

    async def run(self, headless: bool = False):
        """Main execution method"""
        start_time = datetime.now()
        logger.info("Starting Pinterest Browser Bot")
        
        try:
            # Setup browser
            await self.setup_browser(headless=headless)
            
            # Login to Pinterest
            if not await self.login_to_pinterest():
                logger.error("Failed to login to Pinterest")
                return
            
            # Read CSV data
            pins_data = self.read_csv_data()
            if not pins_data:
                logger.error("No pin data to process")
                return
            
            # Process pins
            successful_pins = 0
            failed_pins = 0
            skipped_pins = 0
            
            for i, pin_data in enumerate(pins_data, 1):
                title = pin_data.get('Title', '').strip()
                logger.info(f"Processing pin {i}/{len(pins_data)}: {title}")
                
                # Check if already processed
                if self.is_pin_already_processed(pin_data):
                    logger.info(f"Skipping already processed pin: {title}")
                    skipped_pins += 1
                    continue
                
                # Create pin
                if await self.create_pin(pin_data):
                    successful_pins += 1
                    self.progress_data['completed_pins'].append(title)
                    logger.info(f"✅ Successfully created pin: {title}")
                else:
                    failed_pins += 1
                    if 'failed_pins' not in self.progress_data:
                        self.progress_data['failed_pins'] = []
                    self.progress_data['failed_pins'].append({
                        'title': title,
                        'timestamp': datetime.now().isoformat(),
                        'data': pin_data
                    })
                    logger.error(f"❌ Failed to create pin: {title}")
                
                # Update progress
                self.progress_data['total_processed'] = successful_pins + failed_pins
                self.save_progress()
                
                # Add delay between pins to avoid rate limiting
                await asyncio.sleep(3)
                
                # Report progress every 10 pins
                if i % 10 == 0:
                    logger.info(f"Progress: {i}/{len(pins_data)} processed, {successful_pins} successful, {failed_pins} failed, {skipped_pins} skipped")
            
            # Final report
            end_time = datetime.now()
            duration = end_time - start_time
            
            logger.info("🎉 Pinterest Bot Completed!")
            logger.info(f"📊 Final Results:")
            logger.info(f"   Total pins in CSV: {len(pins_data)}")
            logger.info(f"   Successful: {successful_pins}")
            logger.info(f"   Failed: {failed_pins}")
            logger.info(f"   Skipped (already processed): {skipped_pins}")
            logger.info(f"   Duration: {duration}")
            logger.info(f"   Success rate: {(successful_pins/(successful_pins+failed_pins)*100):.1f}%" if (successful_pins+failed_pins) > 0 else "N/A")
            
        except Exception as e:
            logger.error(f"Fatal error: {e}")
            raise
        finally:
            # Cleanup
            if self.browser:
                await self.browser.close()
            logger.info("Browser closed")

async def main():
    """Main entry point"""
    try:
        # Check if CSV file exists
        if not os.path.exists(CSV_FILE_PATH):
            print(f"❌ CSV file not found: {CSV_FILE_PATH}")
            print("Please ensure the CSV file exists with columns: Title, Description, Link, Image URL, Price, Availability")
            return
        
        # Create bot instance
        bot = PinterestBrowserBot()
        
        # Run the bot
        # Set headless=False to see the browser in action (useful for debugging)
        # Set headless=True for production runs
        await bot.run(headless=False)
        
    except KeyboardInterrupt:
        print("\n⏹️  Bot stopped by user")
    except Exception as e:
        print(f"❌ Error: {e}")
        logger.error(f"Main execution error: {e}")

if __name__ == "__main__":
    # Install required packages if not already installed
    try:
        import playwright
        from dotenv import load_dotenv
    except ImportError as e:
        print("❌ Missing required packages. Please install with:")
        print("pip install playwright python-dotenv")
        print("playwright install chromium")
        sys.exit(1)
    
    print("🤖 Pinterest Browser Bot Starting...")
    print("📁 CSV File:", CSV_FILE_PATH)
    print("📋 Progress File:", PROGRESS_FILE)
    print("📝 Log File:", LOG_FILE)
    print()
    
    # Run the async main function
    asyncio.run(main())
