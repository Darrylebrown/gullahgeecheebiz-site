#!/usr/bin/env python3
"""
Gumroad Publisher Bot
Automated publishing of Gullah Geechee Biz books to Gumroad
Author: Publishing Automation Engineer
Date: 2024
"""

import os
import sys
import sqlite3
import requests
import json
import time
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import hashlib
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

@dataclass
class Book:
    """Book data structure"""
    id: int
    title: str
    description: str
    author: str
    isbn: str
    genre: str
    tags: str
    epub_path: str
    gumroad_id: Optional[str] = None
    status: str = 'pending'

class GumroadPublisher:
    """Gumroad publishing automation bot"""
    
    def __init__(self):
        # Configuration
        self.BASE_URL = "https://api.gumroad.com/v2"
        self.ACCESS_TOKEN = os.getenv('GUMROAD_ACCESS_TOKEN')
        self.PRICE = 399  # $3.99 in cents
        self.AUTHOR = "Darryl Elliott Brown"
        self.PUBLISHER = "Gullah Geechee Biz"
        
        # Paths
        self.DB_PATH = "/Users/darrylsmac/gullahgeecheebiz-site/publish/publisher.db"
        self.EPUB_PATH = "/Users/darrylsmac/gullahgeecheebiz-site/publish/for-distribution/google-play/"
        self.PROGRESS_FILE = "/Users/darrylsmac/gullahgeecheebiz-site/ggb-engine/headquarters/gumroad_progress.json"
        
        # Rate limiting
        self.RATE_LIMIT_DELAY = 1.5  # seconds between API calls
        self.MAX_RETRIES = 3
        self.RETRY_DELAY = 5
        
        # Progress tracking
        self.progress = self.load_progress()
        self.session = requests.Session()
        
        # Setup logging
        self.setup_logging()
        
        # Validate configuration
        self.validate_config()
    
    def setup_logging(self):
        """Configure logging"""
        log_dir = Path("/Users/darrylsmac/gullahgeecheebiz-site/ggb-engine/headquarters/logs")
        log_dir.mkdir(exist_ok=True)
        
        log_file = log_dir / f"gumroad_publisher_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler(sys.stdout)
            ]
        )
        
        self.logger = logging.getLogger(__name__)
        self.logger.info("Gumroad Publisher Bot initialized")
    
    def validate_config(self):
        """Validate configuration and environment"""
        if not self.ACCESS_TOKEN:
            raise ValueError("GUMROAD_ACCESS_TOKEN not found in environment")
        
        if not Path(self.DB_PATH).exists():
            raise FileNotFoundError(f"Database not found: {self.DB_PATH}")
        
        if not Path(self.EPUB_PATH).exists():
            raise FileNotFoundError(f"EPUB directory not found: {self.EPUB_PATH}")
        
        self.logger.info("Configuration validated successfully")
    
    def load_progress(self) -> Dict:
        """Load progress from file"""
        if Path(self.PROGRESS_FILE).exists():
            try:
                with open(self.PROGRESS_FILE, 'r') as f:
                    return json.load(f)
            except Exception as e:
                self.logger.warning(f"Could not load progress file: {e}")
        
        return {
            'processed_books': {},
            'failed_books': {},
            'total_processed': 0,
            'total_successful': 0,
            'total_failed': 0,
            'start_time': None,
            'last_update': None
        }
    
    def save_progress(self):
        """Save progress to file"""
        self.progress['last_update'] = datetime.now().isoformat()
        
        try:
            with open(self.PROGRESS_FILE, 'w') as f:
                json.dump(self.progress, f, indent=2)
        except Exception as e:
            self.logger.error(f"Failed to save progress: {e}")
    
    def load_books_from_db(self) -> List[Book]:
        """Load books from SQLite database"""
        self.logger.info("Loading books from database...")
        
        books = []
        
        try:
            conn = sqlite3.connect(self.DB_PATH)
            cursor = conn.cursor()
            
            # Adjust query based on your database schema
            query = """
            SELECT id, title, description, author, isbn, genre, tags
            FROM books
            ORDER BY id
            """
            
            cursor.execute(query)
            rows = cursor.fetchall()
            
            for row in rows:
                book_id, title, description, author, isbn, genre, tags = row
                
                # Find corresponding EPUB file
                epub_filename = self.find_epub_file(title, isbn)
                
                if epub_filename:
                    book = Book(
                        id=book_id,
                        title=title,
                        description=description or f"A compelling book by {self.AUTHOR}",
                        author=author or self.AUTHOR,
                        isbn=isbn or "",
                        genre=genre or "",
                        tags=tags or "",
                        epub_path=os.path.join(self.EPUB_PATH, epub_filename)
                    )
                    books.append(book)
                else:
                    self.logger.warning(f"EPUB file not found for book: {title}")
            
            conn.close()
            self.logger.info(f"Loaded {len(books)} books from database")
            
        except Exception as e:
            self.logger.error(f"Error loading books from database: {e}")
            raise
        
        return books
    
    def find_epub_file(self, title: str, isbn: str) -> Optional[str]:
        """Find EPUB file for a book"""
        epub_dir = Path(self.EPUB_PATH)
        
        # Common patterns for EPUB files
        patterns = [
            f"{isbn}.epub",
            f"{self.sanitize_filename(title)}.epub",
            f"{isbn}_{self.sanitize_filename(title)}.epub"
        ]
        
        for pattern in patterns:
            epub_file = epub_dir / pattern
            if epub_file.exists():
                return pattern
        
        # Fallback: search for files containing title words
        title_words = self.sanitize_filename(title).lower().split('_')
        for epub_file in epub_dir.glob("*.epub"):
            filename_lower = epub_file.stem.lower()
            if any(word in filename_lower for word in title_words if len(word) > 3):
                return epub_file.name
        
        return None
    
    def sanitize_filename(self, filename: str) -> str:
        """Sanitize filename for safe file operations"""
        # Remove/replace problematic characters
        filename = filename.replace(' ', '_')
        filename = ''.join(c for c in filename if c.isalnum() or c in '_-.')
        return filename[:100]  # Limit length
    
    def make_api_request(self, method: str, endpoint: str, data: Dict = None, files: Dict = None) -> Tuple[bool, Dict]:
        """Make API request with error handling and retries"""
        url = f"{self.BASE_URL}{endpoint}"
        
        # Add access token to data
        if data is None:
            data = {}
        data['access_token'] = self.ACCESS_TOKEN
        
        for attempt in range(self.MAX_RETRIES):
            try:
                self.logger.debug(f"API request: {method} {url}")
                
                if method.upper() == 'GET':
                    response = self.session.get(url, params=data)
                elif method.upper() == 'POST':
                    if files:
                        response = self.session.post(url, data=data, files=files)
                    else:
                        response = self.session.post(url, data=data)
                elif method.upper() == 'PUT':
                    response = self.session.put(url, data=data)
                else:
                    raise ValueError(f"Unsupported HTTP method: {method}")
                
                if response.status_code == 200:
                    return True, response.json()
                elif response.status_code == 429:
                    # Rate limited
                    self.logger.warning("Rate limited, waiting longer...")
                    time.sleep(self.RETRY_DELAY * 2)
                    continue
                else:
                    self.logger.error(f"API error {response.status_code}: {response.text}")
                    
            except Exception as e:
                self.logger.error(f"API request failed (attempt {attempt + 1}): {e}")
            
            if attempt < self.MAX_RETRIES - 1:
                time.sleep(self.RETRY_DELAY)
        
        return False, {}
    
    def create_product(self, book: Book) -> Optional[str]:
        """Create a product on Gumroad"""
        self.logger.info(f"Creating product for: {book.title}")
        
        # Prepare product data
        product_data = {
            'name': book.title,
            'description': self.format_description(book),
            'price': self.PRICE,
            'type': 'digital',
            'tags': self.format_tags(book),
            'summary': book.description[:160] if book.description else f"Digital book by {self.AUTHOR}",
        }
        
        success, response = self.make_api_request('POST', '/products', product_data)
        
        if success and 'product' in response:
            product_id = response['product']['id']
            self.logger.info(f"Product created successfully: {product_id}")
            return product_id
        else:
            self.logger.error(f"Failed to create product for: {book.title}")
            return None
    
    def upload_file(self, product_id: str, book: Book) -> bool:
        """Upload EPUB file to Gumroad product"""
        self.logger.info(f"Uploading file for product: {product_id}")
        
        if not os.path.exists(book.epub_path):
            self.logger.error(f"EPUB file not found: {book.epub_path}")
            return False
        
        try:
            with open(book.epub_path, 'rb') as f:
                files = {'file': (f"{book.title}.epub", f, 'application/epub+zip')}
                
                success, response = self.make_api_request(
                    'POST',
                    f'/products/{product_id}/files',
                    files=files
                )
                
                if success:
                    self.logger.info(f"File uploaded successfully for product: {product_id}")
                    return True
                else:
                    self.logger.error(f"Failed to upload file for product: {product_id}")
                    return False
                    
        except Exception as e:
            self.logger.error(f"Error uploading file: {e}")
            return False
    
    def format_description(self, book: Book) -> str:
        """Format book description for Gumroad"""
        description = f"{book.description}\n\n"
        description += f"📚 Author: {book.author}\n"
        description += f"🏢 Publisher: {self.PUBLISHER}\n"
        
        if book.isbn:
            description += f"📖 ISBN: {book.isbn}\n"
        
        if book.genre:
            description += f"🎭 Genre: {book.genre}\n"
        
        description += "\n✨ Digital EPUB format - compatible with all major e-readers!"
        
        return description
    
    def format_tags(self, book: Book) -> str:
        """Format tags for Gumroad"""
        tags = ['ebook', 'digital-book', 'gullah-geechee-biz']
        
        if book.tags:
            # Split and clean tags
            book_tags = [tag.strip().lower().replace(' ', '-') 
                        for tag in book.tags.split(',') if tag.strip()]
            tags.extend(book_tags[:7])  # Limit tags
        
        if book.genre:
            tags.append(book.genre.lower().replace(' ', '-'))
        
        return ','.join(tags[:10])  # Gumroad tag limit
    
    def publish_book(self, book: Book) -> bool:
        """Publish a single book to Gumroad"""
        book_key = str(book.id)
        
        # Skip if already processed successfully
        if (book_key in self.progress['processed_books'] and 
            self.progress['processed_books'][book_key].get('status') == 'success'):
            self.logger.info(f"Book already published: {book.title}")
            return True
        
        self.logger.info(f"Publishing book: {book.title}")
        
        try:
            # Create product
            product_id = self.create_product(book)
            if not product_id:
                raise Exception("Failed to create product")
            
            # Rate limiting
            time.sleep(self.RATE_LIMIT_DELAY)
            
            # Upload file
            if not self.upload_file(product_id, book):
                raise Exception("Failed to upload file")
            
            # Record success
            self.progress['processed_books'][book_key] = {
                'title': book.title,
                'product_id': product_id,
                'status': 'success',
                'timestamp': datetime.now().isoformat()
            }
            
            self.progress['total_successful'] += 1
            self.logger.info(f"✅ Successfully published: {book.title}")
            
            return True
            
        except Exception as e:
            # Record failure
            self.progress['failed_books'][book_key] = {
                'title': book.title,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
            
            self.progress['total_failed'] += 1
            self.logger.error(f"❌ Failed to publish: {book.title} - {e}")
            
            return False
        
        finally:
            self.progress['total_processed'] += 1
            
            # Save progress every 10 books
            if self.progress['total_processed'] % 10 == 0:
                self.save_progress()
                self.print_progress_report()
    
    def print_progress_report(self):
        """Print progress report"""
        total = self.progress['total_processed']
        successful = self.progress['total_successful']
        failed = self.progress['total_failed']
        
        self.logger.info(f"\n📊 PROGRESS REPORT")
        self.logger.info(f"Total Processed: {total}")
        self.logger.info(f"✅ Successful: {successful}")
        self.logger.info(f"❌ Failed: {failed}")
        
        if total > 0:
            success_rate = (successful / total) * 100
            self.logger.info(f"Success Rate: {success_rate:.1f}%")
    
    def generate_final_report(self) -> str:
        """Generate final publishing report"""
        report = f"""
🎯 GUMROAD PUBLISHING REPORT
{'='*50}

📊 SUMMARY:
- Total Books Processed: {self.progress['total_processed']}
- ✅ Successfully Published: {self.progress['total_successful']}
- ❌ Failed: {self.progress['total_failed']}
- Success Rate: {(self.progress['total_successful']/max(1,self.progress['total_processed'])*100):.1f}%

⏱️ TIMING:
- Started: {self.progress.get('start_time', 'Unknown')}
- Completed: {datetime.now().isoformat()}

"""
        
        if self.progress['failed_books']:
            report += "\n❌ FAILED BOOKS:\n"
            for book_id, info in self.progress['failed_books'].items():
                report += f"- {info['title']}: {info['error']}\n"
        
        return report
    
    def run(self):
        """Main execution method"""
        self.logger.info("🚀 Starting Gumroad publishing process...")
        
        # Set start time if not already set
        if not self.progress.get('start_time'):
            self.progress['start_time'] = datetime.now().isoformat()
        
        try:
            # Load books from database
            books = self.load_books_from_db()
            
            if not books:
                self.logger.error("No books found to publish!")
                return
            
            self.logger.info(f"Found {len(books)} books to publish")
            
            # Filter out already processed books if resuming
            remaining_books = []
            for book in books:
                book_key = str(book.id)
                if (book_key not in self.progress['processed_books'] or 
                    self.progress['processed_books'][book_key].get('status') != 'success'):
                    remaining_books.append(book)
            
            self.logger.info(f"Publishing {len(remaining_books)} remaining books...")
            
            # Process each book
            for i, book in enumerate(remaining_books, 1):
                self.logger.info(f"\n📖 Processing book {i}/{len(remaining_books)}: {book.title}")
                
                # Publish book
                success = self.publish_book(book)
                
                # Rate limiting between books
                if i < len(remaining_books):
                    time.sleep(self.RATE_LIMIT_DELAY)
            
            # Final save and report
            self.save_progress()
            
            final_report = self.generate_final_report()
            self.logger.info(final_report)
            
            # Save report to file
            report_file = f"/Users/darrylsmac/gullahgeecheebiz-site/ggb-engine/headquarters/gumroad_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            with open(report_file, 'w') as f:
                f.write(final_report)
            
            self.logger.info(f"📋 Detailed report saved to: {report_file}")
            self.logger.info("🎉 Publishing process completed!")
            
        except Exception as e:
            self.logger.error(f"💥 Fatal error in publishing process: {e}")
            raise

def main():
    """Main entry point"""
    try:
        publisher = GumroadPublisher()
        publisher.run()
        
    except KeyboardInterrupt:
        print("\n⚠️ Publishing interrupted by user")
        sys.exit(1)
        
    except Exception as e:
        print(f"💥 Fatal error: {e}")
        sys.exit(1)

if __name__ == "__main__":