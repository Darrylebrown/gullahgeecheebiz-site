#!/usr/bin/env python3
"""
GGB Unified Publishing Connector — prepares and exports books for all
distribution platforms. Each connector is modular and independent.
"""
import csv, json, hashlib, os, sys, time, shutil
from pathlib import Path
from datetime import datetime, timedelta

BASE_DIR = Path("/Users/darrylsmac/gullahgeecheebiz-site")
PUB_DB = BASE_DIR / "publish" / "publisher.db"
PLATFORM_DIR = BASE_DIR / "publish" / "platform-ready"
OUTPUT_DIR = BASE_DIR / "publish" / "for-distribution"
LOGS_DIR = Path(__file__).parent / "logs"

os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(LOGS_DIR, exist_ok=True)

def get_books(limit=None, state="approved"):
    """Get books from publisher DB."""
    import sqlite3
    conn = sqlite3.connect(str(PUB_DB))
    query = f"SELECT manifest_id, data, state FROM manifests WHERE state = ? ORDER BY manifest_id"
    params = [state]
    if limit:
        query += f" LIMIT {limit}"
    rows = conn.execute(query, params).fetchall()
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

def get_epub(book_id, title):
    """Find EPUB file for a book by manifest_id or title."""
    short_id = get_short_id(book_id)
    safe = title.replace(" ", "-").replace(":", "").replace("'", "").replace('"', "").replace("/", "-")[:60].lower()
    for d2d_dir in (PLATFORM_DIR / "d2d").iterdir():
        if d2d_dir.is_dir():
            if book_id in d2d_dir.name or short_id in d2d_dir.name:
                for epub in d2d_dir.glob("*.epub"):
                    return epub
            for epub in d2d_dir.glob("*.epub"):
                stem = epub.stem.lower()
                if safe in stem or short_id in stem:
                    return epub
    return None

def get_cover(book_id, title):
    """Find cover image for a book."""
    for d2d_dir in (PLATFORM_DIR / "d2d").iterdir():
        if d2d_dir.is_dir():
            for img in d2d_dir.glob("cover.*"):
                return img
    return None

def ggkey(book_id):
    """Generate unique GGKEY."""
    return f"GGB{hashlib.md5(book_id.encode()).hexdigest()[:12]}"

def get_short_id(book_id):
    """Get a short unique identifier from the manifest_id."""
    parts = book_id.split("-")
    if len(parts) >= 3 and parts[0] == "ggb" and parts[1] == "manifest":
        return parts[2]
    return hashlib.md5(book_id.encode()).hexdigest()[:12]

def get_price(title):
    return "9.99" if "encyclopedia" in title.lower() else "3.99"

def get_categories(title):
    t = title.lower()
    if "encyclopedia" in t: return "REF000000,SOC002010,HIS036120"
    if any(w in t for w in ["cook","food","recipe"]): return "CKB000000,SOC002010,HIS036120"
    if any(w in t for w in ["magazine","travel"]): return "TRV000000,SOC002010,HIS036120"
    return "BUS000000,SEL000000,SOC002010"

# ─── CONNECTOR: Google Play Books ───────────────────────────────────────────

def connector_google_play(books, output_dir):
    """Generate Google Play Books bulk import CSV + copy EPUBs."""
    gp_dir = output_dir / "google-play"
    os.makedirs(gp_dir, exist_ok=True)
    
    csv_path = gp_dir / "google-play-bulk-import.csv"
    fieldnames = ["Title","Subtitle","Author","Description","Language","ISBN","GGKEY",
                  "Publisher","Publication Date","Categories","Keywords","Price",
                  "Currency","DRM","Distribution Territory","File Name"]
    
    with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for mid, title, author, state, data in books:
            key = ggkey(mid)
            epub = get_epub(mid, title)
            writer.writerow({
                "Title": title, "Subtitle": "", "Author": author,
                "Description": f"{title} — A Gullah Geechee Biz publication.",
                "Language": "en", "ISBN": "", "GGKEY": key,
                "Publisher": "Gullah Geechee Biz",
                "Publication Date": datetime.now().strftime("%Y-%m-%d"),
                "Categories": get_categories(title),
                "Keywords": "Gullah Geechee,African American,South Carolina,Lowcountry",
                "Price": get_price(title), "Currency": "USD",
                "DRM": "false", "Distribution Territory": "WORLD",
                "File Name": f"{key}.epub" if epub else "",
            })
            if epub:
                shutil.copy2(epub, gp_dir / f"{key}.epub")
    
    return {"csv": str(csv_path), "epubs": len(list(gp_dir.glob("*.epub")))}

# ─── CONNECTOR: Draft2Digital ──────────────────────────────────────────────

def connector_d2d(books, output_dir):
    """Generate D2D bulk import CSV + copy EPUBs."""
    d2d_dir = output_dir / "draft2digital"
    os.makedirs(d2d_dir, exist_ok=True)
    
    csv_path = d2d_dir / "d2d-bulk-import.csv"
    fieldnames = ["Title","Author","Description","ISBN","Categories","Price","File Name"]
    
    with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for mid, title, author, state, data in books:
            epub = get_epub(mid, title)
            writer.writerow({
                "Title": title, "Author": author,
                "Description": f"{title} — A Gullah Geechee Biz publication.",
                "ISBN": "", "Categories": get_categories(title),
                "Price": get_price(title),
                "File Name": f"{get_short_id(mid)}.epub" if epub else "",
            })
            if epub:
                shutil.copy2(epub, d2d_dir / f"{get_short_id(mid)}.epub")
    
    return {"csv": str(csv_path), "epubs": len(list(d2d_dir.glob("*.epub")))}

# ─── CONNECTOR: Apple Books ────────────────────────────────────────────────

def connector_apple(books, output_dir):
    """Generate Apple Books import files."""
    apple_dir = output_dir / "apple-books"
    os.makedirs(apple_dir, exist_ok=True)
    
    csv_path = apple_dir / "apple-books-import.csv"
    fieldnames = ["Title","Author","Description","ISBN","Categories","Price","File Name"]
    
    with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for mid, title, author, state, data in books:
            epub = get_epub(mid, title)
            writer.writerow({
                "Title": title, "Author": author,
                "Description": f"{title} — A Gullah Geechee Biz publication.",
                "ISBN": "", "Categories": get_categories(title),
                "Price": get_price(title),
                "File Name": f"{get_short_id(mid)}.epub" if epub else "",
            })
            if epub:
                shutil.copy2(epub, apple_dir / f"{get_short_id(mid)}.epub")
    
    return {"csv": str(csv_path), "epubs": len(list(apple_dir.glob("*.epub")))}

# ─── CONNECTOR: Kobo ───────────────────────────────────────────────────────

def connector_kobo(books, output_dir):
    """Generate Kobo import files."""
    kobo_dir = output_dir / "kobo"
    os.makedirs(kobo_dir, exist_ok=True)
    
    csv_path = kobo_dir / "kobo-import.csv"
    fieldnames = ["Title","Author","Description","ISBN","Categories","Price","File Name"]
    
    with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for mid, title, author, state, data in books:
            epub = get_epub(mid, title)
            writer.writerow({
                "Title": title, "Author": author,
                "Description": f"{title} — A Gullah Geechee Biz publication.",
                "ISBN": "", "Categories": get_categories(title),
                "Price": get_price(title),
                "File Name": f"{get_short_id(mid)}.epub" if epub else "",
            })
            if epub:
                shutil.copy2(epub, kobo_dir / f"{get_short_id(mid)}.epub")
    
    return {"csv": str(csv_path), "epubs": len(list(kobo_dir.glob("*.epub")))}

# ─── CONNECTOR: PublishDrive ───────────────────────────────────────────────

def connector_publishdrive(books, output_dir):
    """Generate PublishDrive import files."""
    pd_dir = output_dir / "publishdrive"
    os.makedirs(pd_dir, exist_ok=True)
    
    csv_path = pd_dir / "publishdrive-import.csv"
    fieldnames = ["Title","Author","Description","ISBN","Categories","Price","File Name"]
    
    with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for mid, title, author, state, data in books:
            epub = get_epub(mid, title)
            writer.writerow({
                "Title": title, "Author": author,
                "Description": f"{title} — A Gullah Geechee Biz publication.",
                "ISBN": "", "Categories": get_categories(title),
                "Price": get_price(title),
                "File Name": f"{get_short_id(mid)}.epub" if epub else "",
            })
            if epub:
                shutil.copy2(epub, pd_dir / f"{get_short_id(mid)}.epub")
    
    return {"csv": str(csv_path), "epubs": len(list(pd_dir.glob("*.epub")))}

# ─── MAIN ───────────────────────────────────────────────────────────────────

CONNECTORS = {
    "google_play": {"name": "Google Play Books", "fn": connector_google_play},
    "draft2digital": {"name": "Draft2Digital", "fn": connector_d2d},
    "apple_books": {"name": "Apple Books", "fn": connector_apple},
    "kobo": {"name": "Kobo", "fn": connector_kobo},
    "publishdrive": {"name": "PublishDrive", "fn": connector_publishdrive},
}

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Unified Publishing Connector")
    parser.add_argument("--batch", type=int, default=None, help="Books to process")
    parser.add_argument("--connectors", nargs="+", default=list(CONNECTORS.keys()),
                        help=f"Connectors to run: {list(CONNECTORS.keys())}")
    parser.add_argument("--list", action="store_true", help="List available connectors")
    args = parser.parse_args()
    
    if args.list:
        print("\nAvailable connectors:")
        for key, c in CONNECTORS.items():
            print(f"  {key:20s} → {c['name']}")
        return
    
    print(f"\n{'='*60}")
    print(f"📤 GGB UNIFIED PUBLISHING CONNECTOR")
    print(f"   {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
    print(f"{'='*60}\n")
    
    books = get_books(args.batch)
    print(f"📚 {len(books)} books to process\n")
    
    results = {}
    for key in args.connectors:
        if key not in CONNECTORS:
            print(f"  ⚠️  Unknown connector: {key}")
            continue
        c = CONNECTORS[key]
        print(f"  🔌 {c['name']}...")
        try:
            result = c["fn"](books, OUTPUT_DIR)
            results[key] = result
            print(f"     ✅ CSV: {result['csv']}")
            print(f"     ✅ Files: {result['epubs']} EPUBs")
        except Exception as e:
            print(f"     ❌ Error: {e}")
            results[key] = {"error": str(e)}
    
    print(f"\n{'='*60}")
    print(f"📊 SUMMARY")
    print(f"{'='*60}")
    for key, result in results.items():
        name = CONNECTORS[key]["name"]
        if "error" in result:
            print(f"  ❌ {name}: {result['error']}")
        else:
            print(f"  ✅ {name}: {result['epubs']} books ready")
    print(f"\n📂 Output: {OUTPUT_DIR}")
    print(f"{'='*60}\n")

if __name__ == "__main__":
    main()
