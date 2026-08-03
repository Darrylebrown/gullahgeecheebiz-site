#!/usr/bin/env python3
"""
GGB → Alexandria AI API Importer — uses the Alexandria API directly
to create book projects, upload manuscripts, and set covers.
No browser automation needed.
"""
import requests, json, os, sys, sqlite3, time, base64
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Optional

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
ALEXANDRIA_DIR = REPO_ROOT / "publish" / "for-alexandria"
LOGS_DIR = Path(__file__).resolve().parent / "logs"
ALEXANDRIA_DB = LOGS_DIR / "alexandria-export.db"
LOGS_DIR.mkdir(parents=True, exist_ok=True)

API_BASE = "https://alexandria-ai.com/api/apps"
APP_ID = "6984ecbdb6b2899cd60b0d9b"

def get_token() -> Optional[str]:
    """Get auth token via headless Playwright login. Reuses cached token."""
    # Check if we have a cached token
    token_file = LOGS_DIR / "alexandria-token.txt"
    if token_file.exists():
        token = token_file.read_text().strip()
        # Quick validation — try a simple API call
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        try:
            r = requests.get(f"{API_BASE}/{APP_ID}/entities/BookProject?limit=1", headers=headers, timeout=5)
            if r.status_code == 200:
                return token
        except:
            pass
    
    # Need fresh token
    from playwright.sync_api import sync_playwright
    email = os.environ.get("ALEXANDRIA_EMAIL", "dbrown150@gmail.com")
    password = os.environ.get("ALEXANDRIA_PASSWORD", "pujrap-4kupty-gEvhic")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto("https://alexandria-ai.com/Login", wait_until="networkidle")
        time.sleep(2)
        page.fill("input[type='email']", email)
        page.fill("input[type='password']", password)
        page.click("button:has-text('Sign in')")
        time.sleep(3)
        token = page.evaluate("() => localStorage.getItem('token')")
        browser.close()
    
    if token:
        token_file.write_text(token)
    
    return token

def import_book_api(export_dir: Path) -> Dict:
    """Import a book into Alexandria AI via the API."""
    metadata_file = export_dir / "metadata.json"
    if not metadata_file.exists():
        return {"status": "error", "error": "metadata.json not found"}
    
    metadata = json.loads(metadata_file.read_text())
    manuscript = export_dir / "manuscript.txt"
    cover = export_dir / "cover.png"
    
    if not manuscript.exists():
        return {"status": "error", "error": "manuscript.txt not found"}
    
    title = metadata.get("title", "Untitled")
    author = metadata.get("author", "Darryl Elliott Brown")
    description = metadata.get("description", "")[:500]
    
    print(f"  📤 {title[:50]}...")
    
    # Get auth token
    token = get_token()
    if not token:
        return {"status": "error", "error": "Failed to get auth token"}
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    
    # Step 1: Create the BookProject
    print(f"     📝 Creating project...")
    project_data = {
        "title": title,
        "author_name": author,
        "description": description,
        "genre": "reference",
        "language": "English",
        "pipeline_stage": "concept",
    }
    
    r = requests.post(
        f"{API_BASE}/{APP_ID}/entities/BookProject",
        headers=headers,
        json=project_data,
        timeout=15
    )
    
    if r.status_code not in [200, 201]:
        return {"status": "error", "error": f"Create failed: {r.status_code} {r.text[:100]}"}
    
    project = r.json()
    project_id = project.get("id")
    print(f"     ✅ Project created: {project_id[:20] if project_id else 'unknown'}...")
    
    # Step 2: Upload manuscript content
    print(f"     📄 Uploading manuscript...")
    ms_content = manuscript.read_text()
    
    # Try updating the manuscript field directly
    update_data = {
        "id": project_id,
        "manuscript": ms_content,
    }
    
    r2 = requests.put(
        f"{API_BASE}/{APP_ID}/entities/BookProject/{project_id}",
        headers=headers,
        json=update_data,
        timeout=15
    )
    
    if r2.status_code in [200, 201]:
        print(f"     ✅ Manuscript uploaded")
    else:
        print(f"     ⚠️  Manuscript upload: {r2.status_code}")
    
    # Step 3: Upload cover if available
    if cover.exists():
        print(f"     🖼️  Uploading cover...")
        try:
            cover_b64 = base64.b64encode(cover.read_bytes()).decode()
            cover_data = {
                "id": project_id,
                "cover_image": f"data:image/png;base64,{cover_b64}",
            }
            r3 = requests.put(
                f"{API_BASE}/{APP_ID}/entities/BookProject/{project_id}",
                headers=headers,
                json=cover_data,
                timeout=30
            )
            if r3.status_code in [200, 201]:
                print(f"     ✅ Cover uploaded")
            else:
                print(f"     ⚠️  Cover upload: {r3.status_code}")
        except Exception as e:
            print(f"     ⚠️  Cover error: {str(e)[:60]}")
    
    return {"status": "imported", "project_id": project_id, "title": title}

def import_batch(limit: int = 3) -> Dict:
    """Import a batch of books into Alexandria AI via API."""
    print(f"\n{'='*60}")
    print(f"🚀 GGB → ALEXANDRIA AI API IMPORTER")
    print(f"   {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}")
    print(f"{'='*60}")
    
    conn = sqlite3.connect(str(ALEXANDRIA_DB))
    rows = conn.execute("""
        SELECT id, title, file_path FROM exports 
        WHERE imported = 0 
        LIMIT ?
    """, (limit,)).fetchall()
    
    if not rows:
        print("   ✅ All books already imported!")
        conn.close()
        return {"imported": 0}
    
    results = []
    for r in rows:
        export_id = r[0]
        title = r[1]
        export_dir = Path(r[2])
        
        result = import_book_api(export_dir)
        results.append(result)
        
        if result.get("status") == "imported":
            conn.execute("UPDATE exports SET imported = 1 WHERE id = ?", (export_id,))
            conn.commit()
            print(f"     ✅ Imported to Alexandria!")
        else:
            print(f"     ❌ {result.get('error', 'Failed')}")
        
        time.sleep(1)
    
    conn.close()
    
    imported = sum(1 for r in results if r.get("status") == "imported")
    print(f"\n{'='*60}")
    print(f"📊 SUMMARY")
    print(f"{'='*60}")
    print(f"Attempted: {len(results)}")
    print(f"Imported:  {imported}")
    
    return {"attempted": len(results), "imported": imported}

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch", type=int, default=3)
    args = parser.parse_args()
    import_batch(args.batch)
