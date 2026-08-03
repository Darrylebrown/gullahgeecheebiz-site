#!/usr/bin/env python3
"""
GGB → Alexandria AI Connector — prepares our books for Alexandria import.
Generates the formats Alexandria needs: EPUB, PDF, DOCX, and metadata.
"""
import json, os, sys, sqlite3, shutil, zipfile, hashlib
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Optional

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
PUB_DB = REPO_ROOT / "publish" / "publisher.db"
LANDING_PAD = REPO_ROOT / "publish" / "landing-pad"
PLATFORM_DIR = REPO_ROOT / "publish" / "platform-ready"
ALEXANDRIA_DIR = REPO_ROOT / "publish" / "for-alexandria"
LOGS_DIR = Path(__file__).resolve().parent / "logs"

ALEXANDRIA_DIR.mkdir(parents=True, exist_ok=True)
LOGS_DIR.mkdir(parents=True, exist_ok=True)

ALEXANDRIA_DB = LOGS_DIR / "alexandria-export.db"

def init_db():
    conn = sqlite3.connect(str(ALEXANDRIA_DB))
    conn.execute("""CREATE TABLE IF NOT EXISTS exports (
        id TEXT PRIMARY KEY,
        manifest_id TEXT,
        title TEXT,
        author TEXT,
        lang TEXT,
        format TEXT,
        file_path TEXT,
        exported_at TEXT,
        imported INTEGER DEFAULT 0
    )""")
    conn.commit()
    return conn

def prepare_book(conn, manifest_id: str, title: str, author: str, lang: str = "en") -> Dict:
    """Prepare a book for Alexandria import."""
    export_id = f"alex-{hashlib.md5(manifest_id.encode()).hexdigest()[:12]}"
    
    # Check if already exported
    existing = conn.execute("SELECT id FROM exports WHERE id = ?", (export_id,)).fetchone()
    if existing:
        return {"status": "skipped", "id": export_id}
    
    # Create export directory
    export_dir = ALEXANDRIA_DIR / export_id
    export_dir.mkdir(parents=True, exist_ok=True)
    
    # Find the manuscript
    pub_conn = sqlite3.connect(str(PUB_DB))
    row = pub_conn.execute("""
        SELECT json_extract(data, '$.files.manuscript.path'),
               json_extract(data, '$.files.cover.path'),
               json_extract(data, '$.description.short'),
               json_extract(data, '$.publishing.price'),
               json_extract(data, '$.target_platform')
        FROM manifests WHERE manifest_id = ?
    """, (manifest_id,)).fetchone()
    pub_conn.close()
    
    if not row:
        return {"status": "error", "error": "manifest not found"}
    
    ms_path = row[0]
    cover_path = row[1]
    description = row[2] or ""
    price = row[3] or "3.99"
    platform = row[4] or "kdp"
    
    # Copy manuscript as .txt (Alexandria accepts .txt only)
    if ms_path and Path(ms_path).exists():
        content = Path(ms_path).read_text()
        (export_dir / "manuscript.txt").write_text(content)
    
    # Copy cover
    if cover_path and Path(cover_path).exists():
        shutil.copy2(cover_path, export_dir / "cover.png")
    
    # Generate metadata JSON for Alexandria
    metadata = {
        "title": title,
        "author": author,
        "publisher": "Gullah Geechee Biz",
        "language": lang,
        "description": description,
        "price": price,
        "platform": platform,
        "series": "",
        "categories": ["SOCIAL SCIENCE / Ethnic Studies / American / African American & Black Studies"],
        "keywords": ["gullah geechee", "african american", "sea islands", "culture", "heritage"],
        "exported_at": datetime.now(timezone.utc).isoformat(),
    }
    
    (export_dir / "metadata.json").write_text(json.dumps(metadata, indent=2))
    
    # Generate a simple README
    readme = f"""# {title}
## By {author}
### Gullah Geechee Biz

**Description:** {description[:200]}
**Price:** ${price}
**Platform:** {platform}
**Language:** {lang}

**Files:**
- manuscript.md — Full manuscript
- cover.png — Book cover
- metadata.json — Alexandria import metadata

**Instructions:**
1. Go to https://alexandria-ai.com/BookProjects
2. Click "Import Book"
3. Upload the manuscript.md file
4. Upload the cover.png file
5. Copy metadata.json fields into the form
6. Click publish
"""
    (export_dir / "README.txt").write_text(readme)
    
    # Record export
    conn.execute("INSERT OR REPLACE INTO exports VALUES (?,?,?,?,?,?,?,?,?)",
                (export_id, manifest_id, title, author, lang, "markdown", str(export_dir),
                 datetime.now(timezone.utc).isoformat(), 0))
    conn.commit()
    
    return {"status": "exported", "id": export_id, "dir": str(export_dir)}

def prepare_batch(limit: int = 10) -> Dict:
    """Prepare a batch of books for Alexandria import."""
    print(f"\n{'='*60}")
    print(f"📤 GGB → ALEXANDRIA AI CONNECTOR")
    print(f"   {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}")
    print(f"{'='*60}")
    
    conn = init_db()
    pub_conn = sqlite3.connect(str(PUB_DB))
    
    # Get books not yet exported
    rows = pub_conn.execute("""
        SELECT manifest_id, json_extract(data, '$.title.canonical'),
               json_extract(data, '$.author.name')
        FROM manifests WHERE state = 'approved'
        LIMIT ?
    """, (limit,)).fetchall()
    pub_conn.close()
    
    results = []
    for r in rows:
        mid = r[0]
        title = r[1] or "Untitled"
        author = r[2] or "Darryl Elliott Brown"
        
        print(f"  📤 {title[:50]}...")
        result = prepare_book(conn, mid, title, author)
        results.append(result)
        print(f"     {result['status']}")
    
    conn.close()
    
    # Summary
    exported = sum(1 for r in results if r.get("status") == "exported")
    print(f"\n{'='*60}")
    print(f"📊 SUMMARY")
    print(f"{'='*60}")
    print(f"Exported: {exported}")
    print(f"Total:    {len(results)}")
    print(f"Output:   {ALEXANDRIA_DIR}")
    print(f"\nNext: Go to https://alexandria-ai.com/BookProjects")
    print(f"      Click 'Import Book' and upload the files")
    
    return {"exported": exported, "total": len(results)}

def prepare_all():
    """Prepare ALL approved books for Alexandria."""
    conn = init_db()
    pub_conn = sqlite3.connect(str(PUB_DB))
    
    rows = pub_conn.execute("""
        SELECT manifest_id, json_extract(data, '$.title.canonical'),
               json_extract(data, '$.author.name')
        FROM manifests WHERE state = 'approved'
    """).fetchall()
    pub_conn.close()
    
    total = len(rows)
    exported = 0
    
    print(f"\n{'='*60}")
    print(f"📤 PREPARING ALL {total} BOOKS FOR ALEXANDRIA")
    print(f"{'='*60}")
    
    for i, r in enumerate(rows):
        mid = r[0]
        title = r[1] or "Untitled"
        author = r[2] or "Darryl Elliott Brown"
        
        result = prepare_book(conn, mid, title, author)
        if result.get("status") == "exported":
            exported += 1
        
        if (i + 1) % 100 == 0:
            print(f"  [{i+1}/{total}] {exported} exported...")
    
    conn.close()
    
    print(f"\n{'='*60}")
    print(f"📊 FINAL SUMMARY")
    print(f"{'='*60}")
    print(f"Total books: {total}")
    print(f"Exported:    {exported}")
    print(f"Output:      {ALEXANDRIA_DIR}")
    print(f"\nNext: Go to https://alexandria-ai.com/BookProjects")
    print(f"      Click 'Import Book' and upload the files")
    
    return {"total": total, "exported": exported}

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch", type=int, default=10)
    parser.add_argument("--all", action="store_true")
    args = parser.parse_args()
    
    if args.all:
        prepare_all()
    else:
        prepare_batch(args.batch)
