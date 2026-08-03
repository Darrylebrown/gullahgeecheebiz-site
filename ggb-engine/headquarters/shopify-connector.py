#!/usr/bin/env python3
"""
GGB Shopify Connector — prepares all published books as Shopify products.
Generates CSV for bulk import via Shopify's admin interface.
"""
import json, os, sys, sqlite3, csv, hashlib
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Optional

BASE_DIR = Path("/Users/darrylsmac/gullahgeecheebiz-site")
PUB_DB = BASE_DIR / "publish" / "publisher.db"
SHOPIFY_DIR = BASE_DIR / "publish" / "for-shopify"
LOGS_DIR = Path(__file__).parent / "logs"

SHOPIFY_DIR.mkdir(parents=True, exist_ok=True)
LOGS_DIR.mkdir(parents=True, exist_ok=True)

def get_books() -> List[Dict]:
    """Get all published books from the pipeline."""
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
        
        # Extract price
        price = data.get("price", 3.99)
        if isinstance(price, dict):
            price = price.get("amount", 3.99)
        
        # Extract description
        description = data.get("description", f"{title} — A Gullah Geechee publication by Darryl E. Brown")
        if isinstance(description, dict):
            description = description.get("en", str(description))
        
        # Extract categories
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

def generate_shopify_csv(books: List[Dict], limit: int = None):
    """Generate Shopify bulk import CSV."""
    if limit:
        books = books[:limit]
    
    csv_path = SHOPIFY_DIR / "shopify-products.csv"
    
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "Handle", "Title", "Body (HTML)", "Vendor", "Type",
            "Tags", "Published", "Option1 Name", "Option1 Value",
            "Variant SKU", "Variant Price", "Variant Inventory Qty",
            "Variant Inventory Policy", "Variant Fulfillment Service",
            "Image Src", "Status"
        ])
        
        for book in books:
            handle = book["title"].lower().replace(" ", "-").replace(":", "").replace("'", "")[:60]
            sku = book["manifest_id"][:20]
            tags = "Gullah Geechee, Book, " + ", ".join(book["categories"][:3])
            
            writer.writerow([
                handle,
                book["title"],
                f"<p>{book['description']}</p>",
                "Gullah Geechee Biz",
                "Book",
                tags,
                "TRUE",
                "Format",
                "eBook",
                sku,
                f"{book['price']:.2f}",
                "1",
                "deny",
                "manual",
                "",  # Image URL — add later
                "active",
            ])
    
    print(f"📄 Shopify CSV: {csv_path} ({len(books)} products)")
    return csv_path

def generate_shopify_json(books: List[Dict], limit: int = None):
    """Generate Shopify REST API JSON for programmatic upload."""
    if limit:
        books = books[:limit]
    
    products = []
    for book in books:
        products.append({
            "product": {
                "title": book["title"],
                "body_html": f"<p>{book['description']}</p>",
                "vendor": "Gullah Geechee Biz",
                "product_type": "Book",
                "tags": ", ".join(book["categories"][:3]),
                "published": True,
                "variants": [{
                    "sku": book["manifest_id"][:20],
                    "price": f"{book['price']:.2f}",
                    "inventory_quantity": 1,
                    "inventory_management": "shopify",
                    "fulfillment_service": "manual",
                    "requires_shipping": False,
                }],
                "status": "active",
            }
        })
    
    json_path = SHOPIFY_DIR / "shopify-products.json"
    json_path.write_text(json.dumps(products, indent=2))
    print(f"📄 Shopify JSON: {json_path} ({len(products)} products)")
    return json_path

def generate_shopify_meta(books: List[Dict], limit: int = None):
    """Generate SEO metadata for Shopify products."""
    if limit:
        books = books[:limit]
    
    meta_path = SHOPIFY_DIR / "shopify-meta.json"
    meta = []
    for book in books:
        meta.append({
            "handle": book["title"].lower().replace(" ", "-")[:60],
            "title": book["title"],
            "meta_title": f"{book['title'][:60]} | Gullah Geechee Biz",
            "meta_description": book["description"][:160],
            "price": book["price"],
        })
    
    meta_path.write_text(json.dumps(meta, indent=2))
    print(f"📄 Shopify Meta: {meta_path} ({len(meta)} products)")
    return meta_path

def main():
    import argparse
    parser = argparse.ArgumentParser(description="GGB Shopify Connector")
    parser.add_argument("--limit", type=int, help="Limit number of products")
    parser.add_argument("--check", action="store_true", help="Check what would be exported")
    args = parser.parse_args()
    
    print(f"\n{'='*60}")
    print(f"🛍️  GGB SHOPIFY CONNECTOR")
    print(f"   {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
    print(f"{'='*60}\n")
    
    books = get_books()
    print(f"📚 {len(books)} published books\n")
    
    if args.check:
        print("Sample products:")
        for b in books[:3]:
            print(f"  📖 {b['title'][:50]} — ${b['price']:.2f}")
        return
    
    if args.limit:
        books = books[:args.limit]
    
    generate_shopify_csv(books)
    generate_shopify_json(books)
    generate_shopify_meta(books)
    
    print(f"\n✅ Shopify files ready in: {SHOPIFY_DIR}")
    print(f"   Upload shopify-products.csv to Shopify admin → Products → Import")

if __name__ == "__main__":
    main()
