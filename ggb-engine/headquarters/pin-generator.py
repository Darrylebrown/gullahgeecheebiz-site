#!/usr/bin/env python3
"""
GGB Pin Generator — generates actual Pinterest pin images for every
production item: books, magazines, encyclopedia volumes, and more.
Uses Agnes-Image-2.0 for free image generation.
"""
import json, os, sys, sqlite3, urllib.request, time, re
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Optional

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
PUB_DB = REPO_ROOT / "publish" / "publisher.db"
PINS_DIR = REPO_ROOT / "publish" / "pins"
LOGS_DIR = Path(__file__).resolve().parent / "logs"
MAGAZINES_DIR = REPO_ROOT / "publish" / "magazines"

PINS_DIR.mkdir(parents=True, exist_ok=True)
LOGS_DIR.mkdir(parents=True, exist_ok=True)

AGNES_KEY = os.environ.get("AGNES_API_KEY", "sk-qGBXic9m7VJcJ1vLJ6UPDdJLUbbunIWsNWs4Yl8RqFOfJPCj")
AGNES_IMAGE_URL = "https://apihub.agnes-ai.com/v1/images/generations"

PIN_DB = LOGS_DIR / "pins.db"

def init_db():
    conn = sqlite3.connect(str(PIN_DB))
    conn.execute("""CREATE TABLE IF NOT EXISTS pins (
        id TEXT PRIMARY KEY,
        source_type TEXT,
        source_id TEXT,
        title TEXT,
        lang TEXT,
        prompt TEXT,
        image_url TEXT,
        local_path TEXT,
        created_at TEXT
    )""")
    conn.commit()
    return conn

def call_agnes_image(prompt: str) -> Optional[str]:
    """Generate an image via Agnes-Image-2.0."""
    data = json.dumps({
        "model": "agnes-image-2.0-flash",
        "prompt": prompt,
        "n": 1,
        "size": "1024x1024",
    }).encode()
    req = urllib.request.Request(AGNES_IMAGE_URL, data=data, headers={
        "Content-Type": "application/json",
        "Authorization": f"Bearer {AGNES_KEY}",
    })
    try:
        resp = urllib.request.urlopen(req, timeout=60)
        result = json.loads(resp.read())
        return result["data"][0]["url"]
    except Exception as e:
        return None

def download_image(url: str, path: Path) -> bool:
    """Download an image from URL to local path."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "GGB-Pin-Generator/1.0"})
        resp = urllib.request.urlopen(req, timeout=30)
        path.write_bytes(resp.read())
        return True
    except Exception:
        return False

def generate_book_pins(pin_conn, limit: int = 10) -> Dict:
    """Generate Pinterest pins for approved books."""
    stats = {"books": 0, "pins": 0, "errors": 0}
    
    # Get already-pinned book IDs from pin DB
    already_pinned = set()
    for row in pin_conn.execute("SELECT source_id FROM pins WHERE source_type = 'book'"):
        already_pinned.add(row[0])
    
    pub_conn = sqlite3.connect(str(PUB_DB))
    placeholders = ",".join("?" for _ in (already_pinned or {None}))
    if already_pinned:
        rows = pub_conn.execute(f"""
            SELECT manifest_id, json_extract(data, '$.title.canonical'),
                   json_extract(data, '$.description.short')
            FROM manifests WHERE state = 'approved'
            AND manifest_id NOT IN ({placeholders})
            LIMIT ?
        """, list(already_pinned) + [limit]).fetchall()
    else:
        rows = pub_conn.execute("""
            SELECT manifest_id, json_extract(data, '$.title.canonical'),
                   json_extract(data, '$.description.short')
            FROM manifests WHERE state = 'approved'
            LIMIT ?
        """, (limit,)).fetchall()
    pub_conn.close()
    
    for r in rows:
        mid = r[0]
        title = r[1]
        desc = r[2] or "A Gullah Geechee Biz publication"
        
        if not title:
            continue
        
        stats["books"] += 1
        
        # Generate pin prompt
        prompt = f"""A beautiful Pinterest pin for the book '{title}' by Gullah Geechee Biz. 
Navy blue background with gold accents. Elegant serif typography. 
Gullah Geechee cultural motifs — sweetgrass basket patterns, African-inspired geometric designs. 
Book cover style. 1000x1500 pixels, vertical pin format. 
Text overlay: '{title}' in elegant serif font."""
        
        print(f"  📌 {title[:50]}...")
        
        # Try to generate image
        image_url = call_agnes_image(prompt)
        if not image_url:
            stats["errors"] += 1
            print(f"     ❌ Image gen failed")
            continue
        
        # Download
        pin_id = f"book-{mid[:8]}"
        local_path = PINS_DIR / f"{pin_id}.jpg"
        if download_image(image_url, local_path):
            pin_conn.execute("INSERT OR REPLACE INTO pins VALUES (?,?,?,?,?,?,?,?,?)",
                        (pin_id, "book", mid, title, "en", prompt, image_url, str(local_path),
                         datetime.now(timezone.utc).isoformat()))
            pin_conn.commit()
            stats["pins"] += 1
            print(f"     ✅ Pin saved")
        else:
            stats["errors"] += 1
            print(f"     ❌ Download failed")
        
        time.sleep(1)
    
    return stats

def generate_magazine_pins(conn) -> Dict:
    """Generate Pinterest pins for magazine issues."""
    stats = {"magazines": 0, "pins": 0, "errors": 0}
    
    for f in sorted(MAGAZINES_DIR.glob("*.md")):
        name = f.stem
        pin_id = f"mag-{name}"
        
        # Check if already generated
        existing = conn.execute("SELECT id FROM pins WHERE id = ?", (pin_id,)).fetchone()
        if existing:
            continue
        
        # Parse magazine info from filename
        parts = name.split("-weekly-")
        if len(parts) < 2:
            continue
        
        sport = parts[0].replace("-", " ").title()
        is_spanish = name.endswith("-es")
        lang = "es" if is_spanish else "en"
        lang_label = "Spanish" if is_spanish else "English"
        
        prompt = f"""A Pinterest pin for '{sport} Weekly' magazine by Gullah Geechee Biz. 
{sport} themed imagery. Navy blue background with gold accents. 
Modern magazine cover style. 1000x1500 pixels, vertical pin format. 
Text overlay: '{sport} Weekly' in bold serif font. {lang_label} edition."""
        
        print(f"  📌 {sport} Weekly ({lang_label})...")
        
        image_url = call_agnes_image(prompt)
        if not image_url:
            stats["errors"] += 1
            print(f"     ❌ Image gen failed")
            continue
        
        local_path = PINS_DIR / f"{pin_id}.jpg"
        if download_image(image_url, local_path):
            conn.execute("INSERT OR REPLACE INTO pins VALUES (?,?,?,?,?,?,?,?,?)",
                        (pin_id, "magazine", name, f"{sport} Weekly", lang, prompt, image_url, str(local_path),
                         datetime.now(timezone.utc).isoformat()))
            conn.commit()
            stats["pins"] += 1
            print(f"     ✅ Pin saved")
        else:
            stats["errors"] += 1
            print(f"     ❌ Download failed")
        
        time.sleep(1)
    
    return stats

def generate_encyclopedia_pins(conn) -> Dict:
    """Generate Pinterest pins for encyclopedia volumes."""
    stats = {"volumes": 0, "pins": 0, "errors": 0}
    
    for i in range(1, 51):
        pin_id = f"encyc-vol-{i:02d}"
        
        existing = conn.execute("SELECT id FROM pins WHERE id = ?", (pin_id,)).fetchone()
        if existing:
            continue
        
        prompt = f"""A Pinterest pin for 'Gullah Geechee Encyclopedia Volume {i:02d}' by Gullah Geechee Biz. 
Academic book cover style. Dark navy background with gold decorative borders. 
African-inspired geometric patterns and Adinkra symbols. 
1000x1500 pixels, vertical pin format. 
Text overlay: 'Encyclopedia Volume {i:02d}' in elegant serif font."""
        
        print(f"  📌 Encyclopedia Volume {i:02d}...")
        
        image_url = call_agnes_image(prompt)
        if not image_url:
            stats["errors"] += 1
            print(f"     ❌ Image gen failed")
            continue
        
        local_path = PINS_DIR / f"{pin_id}.jpg"
        if download_image(image_url, local_path):
            conn.execute("INSERT OR REPLACE INTO pins VALUES (?,?,?,?,?,?,?,?,?)",
                        (pin_id, "encyclopedia", f"vol-{i:02d}", f"Encyclopedia Volume {i:02d}", "en",
                         prompt, image_url, str(local_path),
                         datetime.now(timezone.utc).isoformat()))
            conn.commit()
            stats["pins"] += 1
            print(f"     ✅ Pin saved")
        else:
            stats["errors"] += 1
            print(f"     ❌ Download failed")
        
        time.sleep(1)
    
    return stats

def run_all(limit_books: int = 10):
    """Generate pins for all production items."""
    print(f"\n{'='*60}")
    print(f"📌 PIN GENERATOR")
    print(f"   {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}")
    print(f"{'='*60}")
    
    conn = init_db()
    
    # Books
    print(f"\n📚 Books")
    book_stats = generate_book_pins(conn, limit_books)
    
    # Magazines
    print(f"\n📰 Magazines")
    mag_stats = generate_magazine_pins(conn)
    
    # Encyclopedia
    print(f"\n📖 Encyclopedia")
    enc_stats = generate_encyclopedia_pins(conn)
    
    conn.close()
    
    # Summary
    total = book_stats["pins"] + mag_stats["pins"] + enc_stats["pins"]
    errors = book_stats["errors"] + mag_stats["errors"] + enc_stats["errors"]
    
    print(f"\n{'='*60}")
    print(f"📊 SUMMARY")
    print(f"{'='*60}")
    print(f"Books pins:       {book_stats['pins']}")
    print(f"Magazine pins:    {mag_stats['pins']}")
    print(f"Encyclopedia pins: {enc_stats['pins']}")
    print(f"Total pins:       {total}")
    print(f"Errors:           {errors}")
    
    return total

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--books", type=int, default=10, help="Number of book pins to generate")
    parser.add_argument("--magazines", action="store_true", help="Generate magazine pins")
    parser.add_argument("--encyclopedia", action="store_true", help="Generate encyclopedia pins")
    parser.add_argument("--all", action="store_true", help="Generate all pins")
    args = parser.parse_args()
    
    if args.all:
        run_all(limit_books=999999)
    elif args.magazines:
        conn = init_db()
        generate_magazine_pins(conn)
        conn.close()
    elif args.encyclopedia:
        conn = init_db()
        generate_encyclopedia_pins(conn)
        conn.close()
    else:
        run_all(limit_books=args.books)
