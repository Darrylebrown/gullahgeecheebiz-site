#!/usr/bin/env python3
"""
GGB Etsy Connector — prepares all published books as Etsy listings.
Generates CSV for bulk import via Etsy's CSV import tool.
"""
import json, os, sys, sqlite3, csv
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Optional

BASE_DIR = Path("/Users/darrylsmac/gullahgeecheebiz-site")
PUB_DB = BASE_DIR / "publish" / "publisher.db"
ETSY_DIR = BASE_DIR / "publish" / "for-etsy"
LOGS_DIR = Path(__file__).parent / "logs"

ETSY_DIR.mkdir(parents=True, exist_ok=True)
LOGS_DIR.mkdir(parents=True, exist_ok=True)

def get_books() -> List[Dict]:
    conn = sqlite3.connect(str(PUB_DB))
    rows = conn.execute("SELECT manifest_id, data FROM manifests WHERE state = 'published'").fetchall()
    conn.close()
    
    books = []
    for mid, data_json in rows:
        try:
            data = json.loads(data_json) if data_json else {}
        except:
            data = {}
        title = data.get("title", mid)
        if isinstance(title, dict):
            title = title.get("canonical", str(title))
        
        price = data.get("price", 3.99)
        if isinstance(price, dict):
            price = price.get("amount", 3.99)
        
        description = data.get("description", f"{title} — A Gullah Geechee publication by Darryl E. Brown")
        if isinstance(description, dict):
            description = description.get("en", str(description))
        
        categories = data.get("categories", ["Books"])
        if isinstance(categories, str):
            categories = [categories]
        
        books.append({
            "manifest_id": mid,
            "title": title,
            "price": float(price),
            "description": str(description)[:500],
            "categories": categories,
        })
    
    return books

def generate_etsy_csv(books: List[Dict], limit: int = None):
    """Generate Etsy bulk import CSV."""
    if limit:
        books = books[:limit]
    
    csv_path = ETSY_DIR / "etsy-listings.csv"
    
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "Title", "Description", "Price", "Quantity",
            "SKU", "Category", "Tags", "Materials",
            "Item Weight", "Item Length", "Item Width", "Item Height",
            "Is Digital", "Digital File Type", "Status"
        ])
        
        for book in books:
            tags = ", ".join(book["categories"][:3] + ["Gullah Geechee", "eBook", "Digital"])
            
            writer.writerow([
                book["title"][:100],  # Etsy max 100 chars
                book["description"],
                f"{book['price']:.2f}",
                "1",  # Quantity
                book["manifest_id"][:20],
                "Books & Magazines > Books > eBooks",
                tags,
                "Digital",
                "", "", "", "",  # Dimensions (not needed for digital)
                "Yes",  # Is Digital
                "PDF, EPUB",  # Digital file type
                "Active",
            ])
    
    print(f"📄 Etsy CSV: {csv_path} ({len(books)} listings)")
    return csv_path

def generate_etsy_json(books: List[Dict], limit: int = None):
    """Generate Etsy API JSON for programmatic upload."""
    if limit:
        books = books[:limit]
    
    listings = []
    for book in books:
        listings.append({
            "title": book["title"][:100],
            "description": book["description"],
            "price": book["price"],
            "quantity": 1,
            "sku": book["manifest_id"][:20],
            "taxonomy_id": 2,  # eBooks
            "tags": book["categories"][:3] + ["Gullah Geechee", "eBook"],
            "is_digital": True,
            "digital_file_type": "PDF, EPUB",
            "who_made": "someone_else",
            "when_made": "2020_2026",
            "is_supply": False,
            "state": "active",
        })
    
    json_path = ETSY_DIR / "etsy-listings.json"
    json_path.write_text(json.dumps(listings, indent=2))
    print(f"📄 Etsy JSON: {json_path} ({len(listings)} listings)")
    return json_path

def main():
    import argparse
    parser = argparse.ArgumentParser(description="GGB Etsy Connector")
    parser.add_argument("--limit", type=int, help="Limit number of listings")
    parser.add_argument("--check", action="store_true", help="Check what would be exported")
    args = parser.parse_args()
    
    print(f"\n{'='*60}")
    print(f"🧶 GGB ETSY CONNECTOR")
    print(f"   {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
    print(f"{'='*60}\n")
    
    books = get_books()
    print(f"📚 {len(books)} published books\n")
    
    if args.check:
        print("Sample listings:")
        for b in books[:3]:
            print(f"  📖 {b['title'][:50]} — ${b['price']:.2f}")
        return
    
    if args.limit:
        books = books[:args.limit]
    
    generate_etsy_csv(books)
    generate_etsy_json(books)
    
    print(f"\n✅ Etsy files ready in: {ETSY_DIR}")
    print(f"   Upload etsy-listings.csv to Etsy → Shop Manager → CSV Import")

if __name__ == "__main__":
    main()
