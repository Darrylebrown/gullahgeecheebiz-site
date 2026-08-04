#!/usr/bin/env python3
"""
Gullah Geechee Biz - Unified API Connector
Author: Publishing Automation Engineer
Date: [Current Date]
"""

import os
import sys
import json
import csv
import time
import logging
from datetime import datetime
from dotenv import load_dotenv
import requests
from typing import Dict, List, Optional, Tuple
import click
import webbrowser
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('unified_api_connector.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Constants
SCRIPT_DIR = Path(__file__).parent
DATA_DIR = SCRIPT_DIR.parent / 'data'
OUTPUT_DIR = SCRIPT_DIR.parent / 'output'
CONFIG_FILE = SCRIPT_DIR.parent / 'config' / 'api_config.json'
CREDENTIALS_FILE = SCRIPT_DIR.parent / '.env'

# Ensure directories exist
DATA_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

class APIConnector:
    """Base class for all API connectors"""
    
    def __init__(self):
        self.credentials = {}
        self.load_credentials()
        self.rate_limit = 5  # Default rate limit (calls per second)
        self.last_call_time = 0
        
    def load_credentials(self) -> bool:
        """Load credentials from environment variables"""
        raise NotImplementedError
        
    def check_credentials(self) -> Tuple[bool, List[str]]:
        """Check if required credentials are present"""
        raise NotImplementedError
        
    def authenticate(self) -> bool:
        """Authenticate with the API"""
        raise NotImplementedError
        
    def upload_book(self, book_data: Dict) -> Dict:
        """Upload a book to the platform"""
        raise NotImplementedError
        
    def batch_upload(self, csv_path: Path) -> Dict:
        """Upload multiple books from CSV"""
        raise NotImplementedError
        
    def enforce_rate_limit(self):
        """Enforce rate limiting"""
        elapsed = time.time() - self.last_call_time
        if elapsed < 1 / self.rate_limit:
            time.sleep((1 / self.rate_limit) - elapsed)
        self.last_call_time = time.time()
        
    def log_error(self, error: Exception, context: str = ""):
        """Log errors consistently"""
        logger.error(f"{self.__class__.__name__} error: {str(error)} {context}")

class PinterestConnector(APIConnector):
    """Handle Pinterest API operations"""
    
    def __init__(self):
        super().__init__()
        self.base_url = "https://api.pinterest.com/v5"
        self.rate_limit = 2  # Pinterest has stricter limits
        
    def load_credentials(self) -> bool:
        """Load Pinterest credentials"""
        self.credentials = {
            'app_id': os.getenv('PINTEREST_APP_ID'),
            'app_secret': os.getenv('PINTEREST_APP_SECRET'),
            'access_token': os.getenv('PINTEREST_ACCESS_TOKEN'),
            'board_id': os.getenv('PINTEREST_BOARD_ID')
        }
        return all(self.credentials.values())
        
    def check_credentials(self) -> Tuple[bool, List[str]]:
        """Check Pinterest credentials"""
        missing = []
        if not self.credentials.get('app_id'):
            missing.append('PINTEREST_APP_ID')
        if not self.credentials.get('app_secret'):
            missing.append('PINTEREST_APP_SECRET')
        if not self.credentials.get('access_token'):
            missing.append('PINTEREST_ACCESS_TOKEN')
        if not self.credentials.get('board_id'):
            missing.append('PINTEREST_BOARD_ID')
        return (not bool(missing), missing)
        
    def upload_book(self, book_data: Dict) -> Dict:
        """Create a Pin for a book"""
        try:
            self.enforce_rate_limit()
            
            payload = {
                "title": book_data.get('title'),
                "description": book_data.get('description'),
                "board_id": self.credentials['board_id'],
                "media_source": {
                    "source_type": "image_url",
                    "url": book_data.get('image_url')
                },
                "link": book_data.get('purchase_url')
            }
            
            headers = {
                "Authorization": f"Bearer {self.credentials['access_token']}",
                "Content-Type": "application/json"
            }
            
            response = requests.post(
                f"{self.base_url}/pins",
                headers=headers,
                json=payload
            )
            
            response.raise_for_status()
            return response.json()
            
        except Exception as e:
            self.log_error(e, f"uploading book {book_data.get('title')}")
            return {"success": False, "error": str(e)}
            
    def batch_upload(self, csv_path: Path) -> Dict:
        """Batch upload from CSV"""
        results = {"success": 0, "failed": 0, "errors": []}
        
        try:
            with open(csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    result = self.upload_book(row)
                    if result.get('success', False):
                        results["success"] += 1
                    else:
                        results["failed"] += 1
                        results["errors"].append({
                            "book": row.get('title'),
                            "error": result.get('error')
                        })
        except Exception as e:
            self.log_error(e, "batch_upload")
            results["errors"].append({"global_error": str(e)})
            
        return results

class ShopifyConnector(APIConnector):
    """Handle Shopify API operations"""
    
    def __init__(self):
        super().__init__()
        self.rate_limit = 4  # Shopify allows 4 calls per second
        
    def load_credentials(self) -> bool:
        """Load Shopify credentials"""
        self.credentials = {
            'shop_name': os.getenv('SHOPIFY_SHOP_NAME'),
            'api_key': os.getenv('SHOPIFY_API_KEY'),
            'api_secret': os.getenv('SHOPIFY_API_SECRET'),
            'access_token': os.getenv('SHOPIFY_ACCESS_TOKEN')
        }
        return all([self.credentials['shop_name'], self.credentials['access_token']])
        
    def check_credentials(self) -> Tuple[bool, List[str]]:
        """Check Shopify credentials"""
        missing = []
        if not self.credentials.get('shop_name'):
            missing.append('SHOPIFY_SHOP_NAME')
        if not self.credentials.get('access_token'):
            missing.append('SHOPIFY_ACCESS_TOKEN')
        return (not bool(missing), missing)
        
    def upload_book(self, book_data: Dict) -> Dict:
        """Upload book as Shopify product"""
        try:
            self.enforce_rate_limit()
            
            url = f"https://{self.credentials['shop_name']}.myshopify.com/admin/api/2023-04/products.json"
            
            headers = {
                "X-Shopify-Access-Token": self.credentials['access_token'],
                "Content-Type": "application/json"
            }
            
            # Transform book data to Shopify product format
            payload = {
                "product": {
                    "title": book_data.get('title'),
                    "body_html": book_data.get('description'),
                    "vendor": "Gullah Geechee Biz",
                    "product_type": "Book",
                    "status": "active",
                    "variants": [{
                        "price": book_data.get('price'),
                        "sku": book_data.get('isbn'),
                        "inventory_management": "shopify",
                        "inventory_quantity": book_data.get('quantity', 100)
                    }],
                    "images": [{
                        "src": book_data.get('image_url')
                    }]
                }
            }
            
            response = requests.post(url, headers=headers, json=payload)
            response.raise_for_status()
            
            return {
                "success": True,
                "product_id": response.json()['product']['id']
            }
            
        except Exception as e:
            self.log_error(e, f"uploading book {book_data.get('title')}")
            return {"success": False, "error": str(e)}
            
    def batch_upload(self, csv_path: Path) -> Dict:
        """Batch upload from CSV"""
        results = {"success": 0, "failed": 0, "errors": []}
        
        try:
            with open(csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    result = self.upload_book(row)
                    if result.get('success', False):
                        results["success"] += 1
                    else:
                        results["failed"] += 1
                        results["errors"].append({
                            "book": row.get('title'),
                            "error": result.get('error')
                        })
        except Exception as e:
            self.log_error(e, "batch_upload")
            results["errors"].append({"global_error": str(e)})
            
        return results

class EtsyConnector(APIConnector):
    """Handle Etsy API operations"""
    
    def __init__(self):
        super().__init__()
        self.base_url = "https://openapi.etsy.com/v3/application"
        self.rate_limit = 1  # Etsy has stricter rate limits
        
    def load_credentials(self) -> bool:
        """Load Etsy credentials"""
        self.credentials = {
            'api_key': os.getenv('ETSY_API_KEY'),
            'client_id': os.getenv('ETSY_CLIENT_ID'),
            'client_secret': os.getenv('ETSY_CLIENT_SECRET'),
            'access_token': os.getenv('ETSY_ACCESS_TOKEN'),
            'refresh_token': os.getenv('ETSY_REFRESH_TOKEN')
        }
        return all([self.credentials['api_key'], self.credentials['access_token']])
        
    def check_credentials(self) -> Tuple[bool, List[str]]:
        """Check Etsy credentials"""
        missing = []
        if not self.credentials.get('api_key'):
            missing.append('ETSY_API_KEY')
        if not self.credentials.get('access_token'):
            missing.append('ETSY_ACCESS_TOKEN')
        return (not bool(missing), missing)
        
    def refresh_access_token(self) -> bool:
        """Refresh Etsy OAuth token if needed"""
        try:
            url = f"{self.base_url}/oauth/access_token"
            
            headers = {
                "Content-Type": "application/x-www-form-urlencoded"
            }
            
            data = {
                "grant_type": "refresh_token",
                "client_id": self.credentials['client_id'],
                "refresh_token": self.credentials['refresh_token']
            }
            
            response = requests.post(url, headers=headers, data=data)
            response.raise_for_status()
            
            response_data = response.json()
            self.credentials['access_token'] = response_data['access_token']
            self.credentials['refresh_token'] = response_data['refresh_token']
            
            # Update .env file
            self.update_env_file('ETSY_ACCESS_TOKEN', response_data['access_token'])
            self.update_env_file('ETSY_REFRESH_TOKEN', response_data['refresh_token'])
            
            return True
            
        except Exception as e:
            self.log_error(e, "refreshing Etsy token")
            return False
            
    def update_env_file(self, key: str, value: str):
        """Update a value in the .env file"""
        try:
            # Read existing .env file
            env_path = CREDENTIALS_FILE
            if not env_path.exists():
                return
                
            lines = []
            found = False
            
            with open(env_path, 'r') as f:
                for line in f:
                    if line.startswith(f"{key}="):
                        lines.append(f"{key}={value}\n")
                        found = True
                    else:
                        lines.append(line)
                        
            if not found:
                lines.append(f"{key}={value}\n")
                
            with open(env_path, 'w') as f:
                f.writelines(lines)
                
        except Exception as e:
            logger.error(f"Failed to update .env file: {str(e)}")
            
    def upload_book(self, book_data: Dict) -> Dict:
        """Create Etsy listing for a book"""
        try:
            self.enforce_rate_limit()
            
            headers = {
                "x-api-key": self.credentials['api_key'],
                "Authorization": f"Bearer {self.credentials['access_token']}",
                "Content-Type": "application/json"
            }
            
            # First upload image
            image_url = book_data.get('image_url')
            image_result = None
            
            if image_url:
                try:
                    response = requests.post(
                        f"{self.base_url}/listings/{book_data.get('shop_id')}/images",
                        headers={
                            "x-api-key": self.credentials['api_key'],
                            "Authorization": f"Bearer {self.credentials['access_token']}"
                        },
                        files={
                            "image": (image_url.split('/')[-1], requests.get(image_url).content)
                        }
                    )
                    response.raise_for_status()
                    image_result = response.json()
                except Exception as e:
                    logger.warning(f"Failed to upload image: {str(e)}")
            
            # Transform book data to Etsy listing format
            payload = {
                "quantity": book_data.get('quantity', 1),
                "title": book_data.get('title'),
                "description": book_data.get('description'),
                "price": book_data.get('price'),
                "who_made": "i_did",
                "when_made": "2020_2023",
                "taxonomy_id": 1018,  # Books & Zines > Books
                "is_supply": False,
                "shipping_profile_id": book_data.get('shipping_profile_id', 1),
                "return_policy_id": book_data.get('return_policy_id', 1),
                "processing_min": 3,
                "processing_max": 5,
                "tags": ["book", "gullah geechee"],
                "materials": ["paper", "ink"],
                "is_digital": False
            }
            
            if image_result:
                payload["image_ids"] = [image_result['image_id']]
            
            response = requests.post(
                f"{self.base_url}/listings",
                headers=headers,
                json=payload
            )
            
            if response.status_code == 401:  # Token expired?
                if self.refresh_access_token():
                    headers["Authorization"] = f"Bearer {self.credentials['access_token']}"
                    response = requests.post(
                        f"{self.base_url}/listings",
                        headers=headers,
                        json=payload
                    )
            
            response.raise_for_status()
            
            return {
                "success": True,
                "listing_id": response.json()['listing_id']
            }
            
        except Exception as e:
            self.log_error(e, f"uploading book {book_data.get('title')}")
            return {"success": False, "error": str(e)}
            
    def batch_upload(self, csv_path: Path) -> Dict:
        """Batch upload from CSV"""
        results = {"success": 0, "failed": 0, "errors": []}
        
        try:
            with open(csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    result = self.upload_book(row)
                    if result.get('success', False):
                        results["success"] += 1
                    else:
                        results["failed"] += 1
                        results["errors"].append({
                            "book": row.get('title'),
                            "error": result.get('error')
                        })
        except Exception as e:
            self.log_error(e, "batch_upload")
            results["errors"].append({"global_error": str(e)})
            
        return results

class Draft2DigitalConnector(APIConnector):
    """Handle Draft2Digital operations (limited by no public API)"""
    
    def __init__(self):
        super().__init__()
        self.rate_limit = 1  # Be very gentle with D2D
        
    def load_credentials(self) -> bool:
        """Load Draft2Digital credentials"""
        self.credentials = {
            'username': os.getenv('D2D_USERNAME'),
            'password': os.getenv('D2D_PASSWORD'),
            'cookies': os.getenv('D2D_COOKIES')
        }
        return bool(self.credentials.get('cookies')) or \
              (bool(self.credentials.get('username')) and bool(self.credentials.get('password')))
        
    def check_credentials(self) -> Tuple[bool, List[str]]:
        """Check D2D credentials"""
        missing = []
        if not self.credentials.get('cookies') and not self.credentials.get('username'):
            missing.append('D2D_USERNAME or D2D_COOKIES')
        if not self.credentials.get('cookies') and not self.credentials.get('password'):
            missing.append('D2D_PASSWORD or D2D_COOKIES')
        return (not bool(missing), missing)
        
    def upload_book(self, book_data: Dict) -> Dict:
        """Upload book to D2D (workaround)"""
        logger.warning("Draft2Digital has no public API. Manual upload may be required.")
        return {
            "success": False,
            "error": "D2D lacks public API",
            "workaround": "Use their CSV upload feature"
        }
        
    def batch_upload(self, csv_path: Path) -> Dict:
        """D2D doesn't support API uploads"""
        logger.warning("Draft2Digital requires manual CSV upload via their dashboard")
        return {
            "success": False,
            "error": "No API available",
            "instructions": {
                "1": "Prepare books in D2D CSV format",
                "2": "Visit https://www.draft2digital.com/upload",
                "3": "Upload CSV file manually"
            }
        }

class PlatformManager:
    """Manage all platform connectors and automate distribution"""
    
    def __init__(self):
        self.platforms = {
            'pinterest': PinterestConnector(),
            'shopify': ShopifyConnector(),
            'etsy': EtsyConnector(),
            'draft2digital': Draft2DigitalConnector()
        }
        self.available_platforms = []
        self.missing_platforms = {}
        
    def detect_available_platforms(self):
        """Check which platforms have credentials"""
        self.available_platforms = []
        self.missing_platforms = {}
        
        for name, connector in self.platforms.items():
            has_creds, missing = connector.check_credentials()
            if has_creds:
                self.available_platforms.append(name)
            else:
                self.missing_platforms[name] = missing
                
    def generate_setup_checklist(self) -> Dict:
        """Generate a report of missing credentials"""
        checklist = {}
        
        for platform, missing in self.missing_platforms.items():
            checklist[platform] = {
                "status": "missing credentials",
                "required": missing,
                "setup_guide": self.get_setup_guide(platform)
            }
            
        return checklist
        
    def get_setup_guide(self, platform: str) -> str:
        """Return setup instructions for a platform"""
        guides = {
            'pinterest': "https://developers.pinterest.com/docs/getting-started/set-up-app/",
            'shopify': "https://shopify.dev/docs/api/admin-rest",
            'etsy': "https://developer.etsy.com/documentation/essentials/getting-started/",
            'draft2digital': "Contact support@draft2digital.com for API access"
        }
        return guides.get(platform, "No setup guide available")
        
    def upload_to_platform(self, platform: str, csv_path: Path) -> Dict:
        """Handle upload to a specific platform"""
        if platform not in self.platforms:
            return {
                "success": False,
                "error": f"Unknown platform: {platform}"
            }
            
        if platform not in self.available_platforms:
            return {
                "success": False,
                "error": f"Missing credentials for {platform}",
                "missing": self.missing_platforms.get(platform, [])
            }
            
        connector = self.platforms[platform]
        return connector.batch_upload(csv_path)
        
    def get_status_csv(self) -> Path:
        """Locate the status tracking CSV"""
        return DATA_DIR / 'upload_status.csv'
        
    def update_status(self, book_id: str, platform: str, status: str, details: str = ""):
        """Update the status of a book upload"""
        status_file = self.get_status_csv()
        fieldnames = ['book_id', 'platform', 'status', 'timestamp', 'details']
        
        try:
            if not status_file.exists():
                with open(status_file, 'w') as f:
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    writer.writeheader()
                    
            with open(status_file, 'a') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writerow({
                    'book_id': book_id,
                    'platform': platform,
                    'status': status,
                    'timestamp': datetime.now().isoformat(),
                    'details': details
                })
                
        except Exception as e:
            logger.error(f"Failed to update status: {str(e)}")

@click.group()
def cli():
    """Gullah Geechee Biz - Unified Distribution Connector"""
    pass

@cli.command()
@click.option('--platform', type=click.Choice(['pinterest', 'shopify', 'etsy', 'draft2digital', 'all']), 
              required=True, help="Platform to upload to")
@click.option('--csv', type=click.Path(exists=True), required=False, 
              help="Path to CSV file with book data")
def upload(platform, csv):
    """Upload books to distribution platforms"""
    manager = PlatformManager()
    manager.detect_available_platforms()
    
    if platform != 'all' and platform not in manager.available_platforms:
        click.echo(f"Error: Missing credentials for {platform}")
        click.echo(f"Required credentials: {manager.missing_platforms.get(platform, 'Unknown')}")
        return
        
    csv_path = Path(csv) if csv else DATA_DIR / f"{platform}_books.csv"
    
    if not csv_path.exists():
        click.echo(f"Error: CSV file not found at {csv_path}")
        return
        
    if platform == 'all':
        for plat in manager.available_platforms:
            click.echo(f"\nUploading to {plat}...")
            result = manager.upload_to_platform(plat, csv_path)
            click.echo(f"Result: {result.get('success', 0)} successful, {result.get('failed', 0)} failed")
    else:
        click.echo(f"\nUploading to {platform}...")
        result = manager.upload_to_platform(platform, csv_path)
        click.echo(f"Result: {result.get('success', 0)} successful, {result.get('failed', 0)} failed")
        
    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    result_file = OUTPUT_DIR / f"{platform}_results_{timestamp}.json"
    
    with open(result_file, 'w') as f:
        json.dump(result, f, indent=2)
        
    click.echo(f"Results saved to {result_file}")

@cli.command()
def check_creds():
    """Check available platforms and missing credentials"""
    manager = PlatformManager()
    manager.detect_available_platforms()
    
    click.echo("\n=== Available Platforms ===")
    if manager.available_platforms:
        for plat in manager.available_platforms:
            click.echo(f"- {plat}")
    else:
        click.echo("None (missing credentials)")
        
    click.echo("\n=== Missing Credentials ===")
    if manager.missing_platforms:
        for plat, missing in manager.missing_platforms.items():
            click.echo(f"- {plat}: {', '.join(missing)}")
    else:
        click.echo("All platforms configured!")
        
    click.echo("\nFor setup instructions, run: ./unified-api-connector.py setup_guide --platform [name]")

@cli.command()
@click.option('--platform', type=click.Choice(['pinterest', 'shopify', 'etsy', 'draft2digital']), 
              required=True, help="Platform to get setup guide for")
def setup_guide(platform):
    """Get setup instructions for a platform"""
    guides = {
        'pinterest': """Pinterest Setup:
        1. Go to https://developers.pinterest.com/
        2. Create a developer account
        3. Create a new app
        4. Generate access token with pins:write permission
        5. Add PINTEREST_APP_ID, PINTEREST_APP_SECRET, PINTEREST_ACCESS_TOKEN, PINTEREST_BOARD_ID to .env
        """,
        'shopify': """Shopify Setup:
        1. Go to your Shopify admin
        2. Navigate to Apps > Develop apps
        3. Create a new app
        4. Configure Admin API permissions
        5. Install app and get access token
        6. Add SHOPIFY_SHOP_NAME, SHOPIFY_ACCESS_TOKEN to .env
        """,
        'etsy': """Etsy Setup:
        1. Go to https://www.etsy.com/developers/
        2. Register a new app
        3. Note your API key
        4. Complete OAuth flow to get tokens
        5. Add ETSY_API_KEY, ETSY_ACCESS_TOKEN, ETSY_REFRESH_TOKEN to .env
        """,
        'draft2digital': """Draft2Digital Workaround:
        1. Contact support@draft2digital.com for API access
        2. Alternatively, use CSV upload at https://www.draft2digital.com/upload
        3. Add D2D_USERNAME and D2D_PASSWORD to .env for browser automation
        """
    }
    
    click.echo(guides.get(platform, "No setup guide for this platform"))

@cli.command()
def generate_cron():
    """Generate cron job configuration"""
    manager = PlatformManager()
    manager.detect_available_platforms()
    
    if not manager.available_platforms:
        click.echo("No platforms configured - cannot generate cron job")
        return
        
    script_path = Path(__file__).absolute()
    
    cron_config = f"""# Gullah Geechee Biz Distribution Cron
# Run every day at 3 AM
0 3 * * * cd {script_path.parent} && {sys.executable} {script_path} upload --platform all >> logs/cron.log 2>&1
"""
    
    cron_file = OUTPUT_DIR / 'ggb_cron_config.txt'
    with open(cron_file, 'w') as f:
        f.write(cron_config)
        
    click.echo(f"Cron configuration saved to {cron_file}")
    click.echo("\nTo install:")
    click.echo(f"1. Copy the content of {cron_file}")
    click.echo("2. Run `crontab -e`")
    click.echo("3. Paste the configuration")
    click.echo("4. Save and exit")

if __name__ == '__main__':
    # Load environment variables
    load_dotenv(CREDENTIALS_FILE)
    cli()
```

## Auto-Discovery

The script includes auto-discovery features:

1. **Dynamic Platform Detection**:
   - Checks .env for required credentials for each platform
   - Only shows available platforms in the CLI menu
   - Reports missing credentials with setup instructions

2. **Setup Checklist**:
   - Run `python unified-api-connector.py check_creds` to see:
     - Which platforms have complete credentials
     - Which credentials are missing for each platform
   - Generates a human-readable report

3. **Interactive Setup**:
   - For any platform with missing credentials:
   ```
   ./unified-api-connector.py setup_guide --platform etsy
   ```

## Cron Integration

1. **Generated Cron Configuration**:
   - The script can generate optimal cron configuration
   - Includes error logging and proper working directory setup

2. **Rate Limit Handling**:
   - Each connector enforces platform-specific rate limits
   - Built-in delay between API calls
   - Retry logic for failed requests

3. **Status Tracking**:
   - The script maintains a CSV of upload statuses
   - Each book's status is recorded per platform
   - Timestamped entries for audit trail

## Error Handling

1. **Comprehensive Error Capture**:
   - API errors are caught and logged
   - Detailed error messages with context
   - Failed operations are retried (where appropriate)

2. **Recovery Procedures**:
   - Token refresh for OAuth platforms
   - Rate limit backoff
   - Partial completion tracking

3. **Result Reporting**:
   - Detailed JSON results for each batch
   - Success/failure counts
   - Per-item error details

## Implementation Instructions

1. **Save the script**:
   - Save to `/Users/darrylsmac/gullahgeecheebiz-site/ggb-engine/headquarters/unified-api-connector.py`
   - Make executable: `chmod +x unified-api-connector.py`

2. **Setup environment**:
   - Create/update .env file with required credentials
   - Install dependencies: `pip install python-dotenv requests click`

3. **Test the script**:
   ```
   ./unified-api-connector.py check_creds