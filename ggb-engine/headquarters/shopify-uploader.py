
#!/usr/bin/env python3
"""
Shopify Product Uploader
Uploads products from CSV to Shopify store via Admin REST API
"""

import csv
import json
import os
import sys
import time
import logging
from datetime import datetime
from pathlib import Path
import requests
from dotenv import load_dotenv

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('shopify_upload.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class ShopifyUploader:
    def __init__(self):
        """Initialize the Shopify uploader with API credentials"""
        # Load environment variables
        env_path = Path('/Users/darrylsmac/gullahgeecheebiz-site/.env')
        if env_path.exists():
            load_dotenv(env_path)
        else:
            logger.error(f"Environment file not found at {env_path}")
            sys.exit(1)
        
        # Get Shopify credentials
        self.shop_name = os.getenv('SHOPIFY_SHOP_NAME') or 'gullahgeecheebiz'
        self.api_key = os.getenv('SHOPIFY_API_KEY')
        self.access_token = os.getenv('SHOPIFY_ACCESS_TOKEN')
        self.api_secret = os.getenv('SHOPIFY_API_SECRET')
        
        if not self.access_token and not (self.api_key and self.api_secret):
            logger.error("Missing Shopify API credentials. Need either SHOPIFY_ACCESS_TOKEN or SHOPIFY_API_KEY + SHOPIFY_API_SECRET")
            sys.exit(1)
        
        # Setup API endpoint
        if not self.shop_name.endswith('.myshopify.com'):
            self.shop_url = f"https://{self.shop_name}.myshopify.com"
        else:
            self.shop_url = f"https://{self.shop_name}"
        
        self.api_base = f"{self.shop_url}/admin/api/2023-10/products.json"
        
        # Setup headers
        self.headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
        
        if self.access_token:
            self.headers['X-Shopify-Access-Token'] = self.access_token
        
        # Rate limiting (2 requests per second max)
        self.rate_limit_delay = 0.5  # 500ms between requests
        
        # Statistics
        self.stats = {
            'total': 0,
            'successful': 0,
            'failed': 0,
            'skipped': 0,
            'errors': []
        }
        
    def read_csv(self, csv_path):
        """Read products from CSV file"""
        csv_file = Path(csv_path)
        if not csv_file.exists():
            logger.error(f"CSV file not found at {csv_path}")
            return []
        
        products = []
        try:
            with open(csv_file, 'r', encoding='utf-8') as file:
                reader = csv.DictReader(file)
                products = list(reader)
                logger.info(f"Loaded {len(products)} products from CSV")
        except Exception as e:
            logger.error(f"Error reading CSV: {e}")
            
        return products
    
    def format_product_data(self, row):
        """Convert CSV row to Shopify product format"""
        try:
            # Basic product data
            product_data = {
                "product": {
                    "title": row.get('title', '').strip(),
                    "body_html": row.get('description', '').strip(),
                    "vendor": row.get('vendor', '').strip(),
                    "product_type": row.get('product_type', '').strip(),
                    "status": row.get('status', 'active').lower(),
                    "published": True if row.get('status', 'active').lower() == 'active' else False,
                    "tags": row.get('tags', '').strip(),
                    "variants": [],
                    "images": []
                }
            }
            
            # Handle price and inventory
            price = self.clean_price(row.get('price', '0'))
            compare_price = self.clean_price(row.get('compare_at_price', ''))
            inventory_qty = self.clean_number(row.get('inventory_quantity', '0'))
            weight = self.clean_number(row.get('weight', '0'))
            
            # Create variant
            variant = {
                "price": str(price),
                "inventory_management": "shopify",
                "inventory_quantity": int(inventory_qty),
                "fulfillment_service": "manual",
                "inventory_policy": "deny"
            }
            
            if compare_price and compare_price > price:
                variant["compare_at_price"] = str(compare_price)
            
            if weight:
                variant["weight"] = float(weight)
                variant["weight_unit"] = "lb"
            
            # Handle SKU
            if row.get('sku'):
                variant["sku"] = row.get('sku').strip()
            
            # Handle barcode
            if row.get('barcode'):
                variant["barcode"] = row.get('barcode').strip()
            
            product_data["product"]["variants"].append(variant)
            
            # Handle images
            if row.get('image_src'):
                images = [img.strip() for img in row.get('image_src').split(',') if img.strip()]
                for img_url in images:
                    if img_url:
                        product_data["product"]["images"].append({"src": img_url})
            
            # Handle SEO
            if row.get('seo_title') or row.get('seo_description'):
                product_data["product"]["metafields_global_title_tag"] = row.get('seo_title', '')
                product_data["product"]["metafields_global_description_tag"] = row.get('seo_description', '')
            
            return product_data
            
        except Exception as e:
            logger.error(f"Error formatting product data: {e}")
            return None
    
    def clean_price(self, price_str):
        """Clean and convert price string to float"""
        if not price_str:
            return 0.0
        try:
            # Remove currency symbols and spaces
            clean_price = str(price_str).replace('$', '').replace(',', '').strip()
            return float(clean_price) if clean_price else 0.0
        except:
            return 0.0
    
    def clean_number(self, num_str):
        """Clean and convert number string"""
        if not num_str:
            return 0
        try:
            return int(float(str(num_str).replace(',', '').strip()))
        except:
            return 0
    
    def create_product(self, product_data):
        """Create a single product via Shopify API"""
        try:
            # Rate limiting
            time.sleep(self.rate_limit_delay)
            
            # Make API request
            if self.access_token:
                response = requests.post(
                    self.api_base,
                    headers=self.headers,
                    json=product_data,
                    timeout=30
                )
            else:
                # Use basic auth if no access token
                response = requests.post(
                    self.api_base,
                    headers=self.headers,
                    json=product_data,
                    auth=(self.api_key, self.api_secret),
                    timeout=30
                )
            
            if response.status_code == 201:
                result = response.json()
                product_id = result['product']['id']
                logger.info(f"✅ Created product: {product_data['product']['title']} (ID: {product_id})")
                return True, product_id
            
            elif response.status_code == 429:
                # Rate limited - wait longer and retry
                logger.warning("Rate limited. Waiting 2 seconds...")
                time.sleep(2)
                return self.create_product(product_data)
            
            else:
                error_msg = f"HTTP {response.status_code}: {response.text}"
                logger.error(f"❌ Failed to create product '{product_data['product']['title']}': {error_msg}")
                return False, error_msg
                
        except requests.exceptions.RequestException as e:
            error_msg = f"Request error: {e}"
            logger.error(f"❌ Network error creating product '{product_data['product']['title']}': {error_msg}")
            return False, error_msg
        
        except Exception as e:
            error_msg = f"Unexpected error: {e}"
            logger.error(f"❌ Unexpected error creating product '{product_data['product']['title']}': {error_msg}")
            return False, error_msg
    
    def test_connection(self):
        """Test connection to Shopify API"""
        try:
            test_url = f"{self.shop_url}/admin/api/2023-10/shop.json"
            
            if self.access_token:
                response = requests.get(test_url, headers=self.headers, timeout=10)
            else:
                response = requests.get(test_url, headers=self.headers, 
                                     auth=(self.api_key, self.api_secret), timeout=10)
            
            if response.status_code == 200:
                shop_info = response.json()
                shop_name = shop_info['shop']['name']
                logger.info(f"✅ Connected to Shopify store: {shop_name}")
                return True
            else:
                logger.error(f"❌ Connection failed: HTTP {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Connection test failed: {e}")
            return False
    
    def upload_products(self, csv_path):
        """Main method to upload all products"""
        logger.info("🚀 Starting Shopify product upload...")
        logger.info(f"Shop URL: {self.shop_url}")
        
        # Test connection first
        if not self.test_connection():
            logger.error("Cannot connect to Shopify. Check your credentials.")
            return False
        
        # Read products from CSV
        products = self.read_csv(csv_path)
        if not products:
            logger.error("No products to upload")
            return False
        
        self.stats['total'] = len(products)
        logger.info(f"📦 Uploading {len(products)} products...")
        
        # Upload each product
        for i, row in enumerate(products, 1):
            try:
                # Skip empty rows
                if not row.get('title', '').strip():
                    logger.warning(f"⚠️  Skipping row {i}: No title")
                    self.stats['skipped'] += 1
                    continue
                
                logger.info(f"📤 [{i}/{len(products)}] Processing: {row.get('title', 'Unknown')}")
                
                # Format product data
                product_data = self.format_product_data(row)
                if not product_data:
                    logger.error(f"❌ Failed to format product data for row {i}")
                    self.stats['failed'] += 1
                    continue
                
                # Create product
                success, result = self.create_product(product_data)
                
                if success:
                    self.stats['successful'] += 1
                else:
                    self.stats['failed'] += 1
                    self.stats['errors'].append({
                        'row': i,
                        'title': row.get('title', 'Unknown'),
                        'error': result
                    })
                
                # Progress update every 50 products
                if i % 50 == 0:
                    logger.info(f"📊 Progress: {i}/{len(products)} processed "
                              f"({self.stats['successful']} successful, {self.stats['failed']} failed)")
                
            except KeyboardInterrupt:
                logger.warning("Upload interrupted by user")
                break
            except Exception as e:
                logger.error(f"❌ Unexpected error processing row {i}: {e}")
                self.stats['failed'] += 1
        
        # Final report
        self.print_final_report()
        return self.stats['failed'] == 0
    
    def print_final_report(self):
        """Print final upload statistics"""
        logger.info("\n" + "="*60)
        logger.info("📊 UPLOAD COMPLETE - FINAL REPORT")
        logger.info("="*60)
        logger.info(f"Total products processed: {self.stats['total']}")
        logger.info(f"✅ Successful uploads: {self.stats['successful']}")
        logger.info(f"❌ Failed uploads: {self.stats['failed']}")
        logger.info(f"⚠️  Skipped: {self.stats['skipped']}")
        logger.info(f"Success rate: {(self.stats['successful']/max(1,self.stats['total']))*100:.1f}%")
        
        if self.stats['errors']:
            logger.info(f"\n❌ ERRORS ({len(self.stats['errors'])}):")
            for error in self.stats['errors'][:10]:  # Show first 10 errors
                logger.info(f"  Row {error['row']}: {error['title']} - {error['error']}")
            if len(self.stats['errors']) > 10:
                logger.info(f"  ... and {len(self.stats['errors']) - 10} more errors")
        
        logger.info("="*60)

def main():
    """Main execution function"""
    # File paths
    csv_path = "/Users/darrylsmac/gullahgeecheebiz-site/ggb-engine/headquarters/logs/universal-submitter/csv/shopify-products.csv"
    
    logger.info("🏪 Shopify Product Uploader Starting...")
    logger.info(f"CSV Path: {csv_path}")
    
    try:
        # Create uploader instance
        uploader = ShopifyUploader()
        
        # Upload products
        success = uploader.upload_products(csv_path)
        
        if success:
            logger.info("🎉 All products uploaded successfully!")
            return 0
        else:
            logger.warning("⚠️  Upload completed with some errors. Check the log above.")
            return 1
            
    except KeyboardInterrupt:
        logger.warning("Upload interrupted by user")
        return 1
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)