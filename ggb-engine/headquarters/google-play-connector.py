#!/usr/bin/env python3
"""
GGB → Google Play Books Connector — generates bulk upload CSV + prepares files
for Google Play Books Partner Center. Free, no API key needed.
"""
import csv, json, hashlib, os, sys, time
from pathlib import Path
from datetime import datetime, timedelta

BASE_DIR = Path("/Users/darrylsmac/gullahgeecheebiz-site")
PUBLISHER_DB = BASE_DIR / "publish" / "publisher.db"
PLATFORM_DIR = BASE_DIR / "publish" / "platform-ready"
OUTPUT_DIR = BASE_DIR / "publish" / "for-google-play"
LOGS_DIR = Path(__file__).parent / "logs"

os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(LOGS_DIR, exist_ok=True)

def get_books(limit=None):
    """Get approved books from publisher DB."""
    import sqlite3
    conn = sqlite3.connect(str(PUBLISHER_DB))
    query = "SELECT manifest_id, data, state FROM manifests WHERE state = 'approved' ORDER BY manifest_id"
    if limit:
        query += f" LIMIT {limit}"
    rows = conn.execute(query).fetchall()
    conn.close()
    
    books = []
    for manifest_id, data_json, state in rows:
        try:
            data = json.loads(data_json) if data_json else {}
        except:
            data = {}
        title = data.get("title", data.get("name", manifest_id))
        if isinstance(title, dict):
            title = title.get("canonical", title.get("subtitle", manifest_id))
        author = data.get("author", "Gullah Geechee Biz")
        if isinstance(author, dict):
            author = author.get("name", str(author))
        books.append((manifest_id, title, author, state, data))
    return books

def get_epub_path(book_id, title):
    """Find the EPUB file for a book."""
    safe_title = title.replace(" ", "-").replace(":", "").replace("'", "").replace('"', "").replace("/", "-")[:60]
    for d2d_dir in (PLATFORM_DIR / "d2d").iterdir():
        if d2d_dir.is_dir():
            for epub in d2d_dir.glob("*.epub"):
                if safe_title.lower() in epub.stem.lower() or book_id in d2d_dir.name:
                    return epub
    return None

def get_cover_path(book_id, title):
    """Find the cover image for a book."""
    safe_title = title.replace(" ", "-").replace(":", "").replace("'", "").replace('"', "").replace("/", "-")[:60]
    for d2d_dir in (PLATFORM_DIR / "d2d").iterdir():
        if d2d_dir.is_dir():
            for img in d2d_dir.glob("cover.*"):
                return img
    return None

def generate_ggkey(book_id):
    """Generate a unique GGKEY-like identifier."""
    h = hashlib.md5(f"ggb-{book_id}".encode()).hexdigest()[:12]
    return f"GGB{h}"

def build_csv(limit=None):
    """Build the Google Play Books bulk upload CSV."""
    books = get_books(limit)
    
    csv_path = OUTPUT_DIR / "google-play-bulk-import.csv"
    
    # Google Play Books CSV columns (from their template)
    fieldnames = [
        "Title", "Subtitle", "Author", "Description", "Language",
        "ISBN", "GGKEY", "Publisher", "Publication Date",
        "Categories", "Keywords", "Price", "Currency",
        "DRM", "Distribution Territory", "File Name"
    ]
    
    with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        
        for book_id, title, author, state, manifest_data in books:
            ggkey = generate_ggkey(book_id)
            epub = get_epub_path(book_id, title)
            
            # Determine price
            price = "9.99" if "encyclopedia" in title.lower() else "3.99"
            
            # Determine categories
            if "encyclopedia" in title.lower():
                categories = "REF000000,SOC002010,HIS036120"
            elif "cook" in title.lower() or "food" in title.lower() or "recipe" in title.lower():
                categories = "CKB000000,SOC002010,HIS036120"
            elif "magazine" in title.lower() or "travel" in title.lower():
                categories = "TRV000000,SOC002010,HIS036120"
            else:
                categories = "BUS000000,SEL000000,SOC002010"
            
            keywords = "Gullah Geechee,African American,South Carolina,Lowcountry"
            
            filename = f"{ggkey}.epub" if epub else ""
            
            writer.writerow({
                "Title": title,
                "Subtitle": "",
                "Author": author or "Gullah Geechee Biz",
                "Description": f"{title} — A Gullah Geechee Biz publication.",
                "Language": "en",
                "ISBN": "",
                "GGKEY": ggkey,
                "Publisher": "Gullah Geechee Biz",
                "Publication Date": datetime.now().strftime("%Y-%m-%d"),
                "Categories": categories,
                "Keywords": "Gullah Geechee, African American, South Carolina, Lowcountry",
                "Price": price,
                "Currency": "USD",
                "DRM": "false",
                "Distribution Territory": "WORLD",
                "File Name": filename,
            })
    
    print(f"✅ CSV generated: {csv_path}")
    print(f"   {len(books)} books in catalog")
    return csv_path

def copy_files(limit=None):
    """Copy EPUB and cover files with GGKEY filenames."""
    books = get_books(limit)
    copied = 0
    
    for book_id, title, author, state, manifest_data in books:
        ggkey = generate_ggkey(book_id)
        epub = get_epub_path(book_id, title)
        cover = get_cover_path(book_id, title)
        
        if epub:
            dest = OUTPUT_DIR / f"{ggkey}.epub"
            import shutil
            shutil.copy2(epub, dest)
            copied += 1
        
        if cover:
            ext = Path(cover).suffix
            dest = OUTPUT_DIR / f"{ggkey}{ext}"
            import shutil
            shutil.copy2(cover, dest)
    
    print(f"✅ Copied {copied} EPUB files to {OUTPUT_DIR}")
    return copied

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Google Play Books Connector")
    parser.add_argument("--batch", type=int, default=None, help="Number of books to process")
    parser.add_argument("--csv-only", action="store_true", help="Only generate CSV, skip file copy")
    args = parser.parse_args()
    
    print(f"\n{'='*60}")
    print(f"📤 GGB → GOOGLE PLAY BOOKS CONNECTOR")
    print(f"   {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
    print(f"{'='*60}\n")
    
    # Generate CSV
    csv_path = build_csv(args.batch)
    
    # Copy files
    if not args.csv_only:
        copy_files(args.batch)
    
    # Summary
    print(f"\n{'='*60}")
    print(f"📊 SUMMARY")
    print(f"{'='*60}")
    print(f"CSV:    {csv_path}")
    print(f"Files:  {OUTPUT_DIR}")
    print(f"\nNext steps:")
    print(f"1. Go to https://play.google.com/books/publish/")
    print(f"2. Sign in with your Google account")
    print(f"3. Click Advanced options → Upload book list")
    print(f"4. Upload the CSV file")
    print(f"5. Click Advanced options → Upload content files")
    print(f"6. Upload the EPUB files")
    print(f"7. Review and publish")
    print(f"{'='*60}\n")

if __name__ == "__main__":
    main()
