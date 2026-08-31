#!/usr/bin/env python3
"""
GGB Revenue Orchestrator — Sales Goal Runner (v3)
Uses proper Gumroad API flow: presign → S3 upload → PUT product with file_url
Handles rate limiting with exponential backoff.
"""
import json, os, sys, time, sqlite3, requests, zipfile, re
from pathlib import Path

BASE = Path("/Users/darrylsmac/gullahgeecheebiz-site")
DB = BASE / "publish" / "publisher.db"
EPUB_DIR = BASE / "publish" / "for-distribution" / "google-play"
ENV = BASE / ".env"
LOG_FILE = BASE / "ggb-engine" / "headquarters" / "logs" / "sales_goal.log"
STATUS_FILE = BASE / "ggb-engine" / "headquarters" / "gauntlet-output" / "sales-goal" / "status.json"

API = "https://api.gumroad.com/v2"
TOKEN = None
PRICE_CENTS = 999  # $9.99

def log(msg):
    ts = time.strftime("%H:%M:%S")
    print(f"[{ts}] {msg}")
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG_FILE, "a") as f:
        f.write(f"[{ts}] {msg}\n")

def load_token():
    global TOKEN
    if ENV.exists():
        for line in ENV.read_text().splitlines():
            if "GUMROAD_ACCESS_TOKEN" in line:
                TOKEN = line.split("=", 1)[1].strip().strip('"').strip("'")
                return TOKEN
    return None

def api_call(method, endpoint, data=None, files=None, max_retries=5):
    url = f"{API}/{endpoint}"
    params = {"access_token": TOKEN}
    for attempt in range(max_retries):
        try:
            if method == "GET":
                r = requests.get(url, params=params, timeout=30)
            elif method == "PUT":
                r = requests.put(url, params=params, data=data, timeout=30)
            elif method == "POST":
                r = requests.post(url, params=params, data=data, files=files, timeout=60)
            if r.status_code == 200:
                return r.json()
            if r.status_code == 429:
                wait = min(300, (attempt + 1) * 30)
                log(f"  Rate limited ({attempt+1}/{max_retries}), waiting {wait}s...")
                time.sleep(wait)
                continue
            return {"success": False, "error": f"HTTP {r.status_code}: {r.text[:200]}"}
        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(5)
                continue
            return {"success": False, "error": str(e)}
    return {"success": False, "error": "Max retries exceeded"}

def presign_upload(filename, file_size):
    """Get presigned URL for file upload."""
    result = api_call("POST", "files/presign", data={
        "filename": filename,
        "file_size": file_size
    })
    return result

def upload_to_s3(file_url, file_path):
    """Upload file to S3 using presigned URL."""
    with open(file_path, "rb") as f:
        r = requests.put(file_url, data=f.read(), timeout=60)
    return r.status_code == 200

def update_product_with_file(pid, name, description, file_url):
    """Update existing product with file."""
    data = {
        "name": name,
        "price": str(PRICE_CENTS),
        "description": description,
        "customizable_price": False,
        "files[][url]": file_url,
    }
    result = api_call("PUT", f"products/{pid}", data=data)
    return result

def create_product(name, description, file_url):
    """Create a new product with file."""
    data = {
        "name": name,
        "price": str(PRICE_CENTS),
        "description": description,
        "customizable_price": False,
        "preview_url": "https://gullahgeecheebiz.com/books.html",
        "files[][url]": file_url,
    }
    result = api_call("POST", "products", data=data)
    return result

def get_existing_products():
    result = api_call("GET", "products")
    if result.get("success"):
        return {p["id"]: p for p in result.get("products", [])}
    log(f"  Error fetching products: {result.get('error')}")
    return {}

def get_manifest_map():
    conn = sqlite3.connect(str(DB))
    rows = conn.execute("SELECT manifest_id, data FROM manifests WHERE state='published'").fetchall()
    conn.close()
    mapping = {}
    for mid, data_json in rows:
        try:
            data = json.loads(data_json) if data_json else {}
            title = data.get("title", mid)
            if isinstance(title, dict):
                title = title.get("canonical", str(title))
            mapping[mid] = str(title).strip()
        except:
            pass
    return mapping

def get_epub_titles():
    titles = {}
    for epub_path in EPUB_DIR.glob("*.epub"):
        try:
            with zipfile.ZipFile(epub_path) as z:
                for name in z.namelist():
                    if 'content.opf' in name.lower():
                        content = z.read(name).decode('utf-8', errors='ignore')
                        m = re.search(r'<dc:title[^>]*>([^<]+)</dc:title>', content)
                        if m:
                            titles[epub_path.stem] = m.group(1)
                        break
        except:
            pass
    return titles

def match_manifests_to_epubs(manifest_map, epub_titles):
    matches = {}
    for mid, mtitle in manifest_map.items():
        for epub_name, etitle in epub_titles.items():
            if mtitle.lower() == etitle.lower() or mtitle in etitle or etitle in mtitle:
                matches[mid] = (mtitle, epub_name)
                break
    return matches

def update_status(**kwargs):
    if not STATUS_FILE.exists():
        status = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S-04:00"),
            "source_bot": "SALES_10K_GOAL",
            "status": "IN_PROGRESS",
            "current_sales": 0.00,
            "goal": 10000.00,
            "progress_percent": 0.0,
            "sales_count": 0,
            "actions_taken": [],
            "remaining_work": []
        }
    else:
        with open(STATUS_FILE) as f:
            status = json.load(f)
    for k, v in kwargs.items():
        status[k] = v
    status["timestamp"] = time.strftime("%Y-%m-%dT%H:%M:%S-04:00")
    with open(STATUS_FILE, "w") as f:
        json.dump(status, f, indent=2)

def main():
    global TOKEN
    if not load_token():
        log("ERROR: GUMROAD_ACCESS_TOKEN not found")
        return
    
    log("=" * 60)
    log("GGB Revenue Orchestrator — Sales Goal Run (v3)")
    log("=" * 60)
    
    # Step 1: Check current sales
    sales_result = api_call("GET", "sales")
    sales = sales_result.get("sales", [])
    total_sales = sum(s.get("price_cents", 0) for s in sales) / 100
    sales_count = len(sales)
    
    log(f"Current sales: ${total_sales:.2f} ({sales_count} sales)")
    log(f"Goal: $10,000.00")
    progress_pct = (total_sales / 10000) * 100
    log(f"Progress: {progress_pct:.2f}%")
    
    if total_sales >= 10000:
        log("✅ GOAL REACHED! $10,000 in sales!")
        update_status(current_sales=total_sales, sales_count=sales_count, status="COMPLETE")
        return
    
    # Step 2: Get existing products
    existing = get_existing_products()
    log(f"Existing Gumroad products: {len(existing)}")
    
    # Step 3: Get manifest-EPUB matches
    manifest_map = get_manifest_map()
    epub_titles = get_epub_titles()
    matches = match_manifests_to_epubs(manifest_map, epub_titles)
    log(f"Found {len(matches)} manifest-EPUB matches")
    
    # Step 4: Upload EPUBs to existing products using presign flow
    uploaded_count = 0
    for pname, pid in existing.items():
        # Find matching EPUB
        matching_epub = None
        for mid, (mtitle, epub_stem) in matches.items():
            if mtitle == pname:
                matching_epub = (epub_stem, pname)
                break
        
        if not matching_epub:
            log(f"SKIP {pname}: No matching EPUB found")
            continue
        
        epub_stem, _ = matching_epub
        epub_path = EPUB_DIR / f"{epub_stem}.epub"
        if not epub_path.exists():
            log(f"SKIP {pname}: No EPUB file found ({epub_stem}.epub)")
            continue
        
        log(f"Processing: {pname}")
        
        # Step 4a: Presign upload
        file_size = epub_path.stat().st_size
        log(f"  Presigning {epub_path.name} ({file_size} bytes)...")
        presign_result = presign_upload(epub_path.name, file_size)
        
        if not presign_result.get("success"):
            log(f"  ✗ Presign failed: {presign_result.get('error')}")
            time.sleep(5)
            continue
        
        file_url = presign_result.get("parts", [{}])[0].get("presigned_url")
        if not file_url:
            log(f"  ✗ No presigned URL in response")
            time.sleep(5)
            continue
        
        # Step 4b: Upload to S3
        log(f"  Uploading to S3...")
        upload_ok = upload_to_s3(file_url, epub_path)
        if not upload_ok:
            log(f"  ✗ S3 upload failed")
            time.sleep(5)
            continue
        
        # Step 4c: Update product with file
        log(f"  Updating product with file...")
        time.sleep(2)
        description = f"{pname} - A comprehensive guide to Gullah Geechee culture, history, and traditions by Darryl Elliott Brown. Part of the Encyclopedia series."
        result = update_product_with_file(pid, pname, description, file_url)
        
        if result.get("success"):
            log(f"  ✓ Updated: {pname} with {epub_path.name}")
            uploaded_count += 1
        else:
            log(f"  ✗ Failed: {result.get('error', 'unknown')}")
        
        time.sleep(2)  # Rate limit respect
    
    # Step 5: Create new products for unmatched manifests
    created_count = 0
    existing_names = set(existing.keys())
    
    pending_creates = []
    for mid, (mtitle, epub_stem) in matches.items():
        if mtitle not in existing_names:
            pending_creates.append((mtitle, epub_stem))
    
    log(f"Products to create: {len(pending_creates)} (limiting to 20 per run)")
    
    for i, (mtitle, epub_stem) in enumerate(pending_creates[:20]):
        log(f"Creating: {mtitle} ({i+1}/20)")
        
        description = f"{mtitle} - A comprehensive guide to Gullah Geechee culture, history, and traditions by Darryl Elliott Brown. Part of the Encyclopedia series."
        
        epub_path = EPUB_DIR / f"{epub_stem}.epub"
        if not epub_path.exists():
            log(f"  ⚠ No EPUB found: {epub_stem}.epub")
            # Try without EPUB first
            result = create_product(mtitle, description, "")
            if result.get("success"):
                log(f"  ✓ Created product (no file): {result.get('product', {}).get('id')}")
                created_count += 1
            time.sleep(3)
            continue
        
        # Step 5a: Presign upload
        file_size = epub_path.stat().st_size
        log(f"  Presigning {epub_path.name}...")
        presign_result = presign_upload(epub_path.name, file_size)
        
        if not presign_result.get("success"):
            log(f"  ✗ Presign failed: {presign_result.get('error')}")
            time.sleep(10)
            continue
        
        file_url = presign_result.get("parts", [{}])[0].get("presigned_url")
        if not file_url:
            log(f"  ✗ No presigned URL")
            time.sleep(10)
            continue
        
        # Step 5b: Upload to S3
        log(f"  Uploading to S3...")
        upload_ok = upload_to_s3(file_url, epub_path)
        if not upload_ok:
            log(f"  ✗ S3 upload failed")
            time.sleep(10)
            continue
        
        # Step 5c: Create product with file
        log(f"  Creating product...")
        time.sleep(2)
        result = create_product(mtitle, description, file_url)
        
        if result.get("success"):
            new_pid = result.get("product", {}).get("id")
            log(f"  ✓ Created: {new_pid}")
            created_count += 1
        else:
            log(f"  ✗ Create failed: {result.get('error', str(result)[:100])}")
        
        time.sleep(3)  # Rate limit respect
    
    log("")
    log("=" * 60)
    log(f"Run complete: {uploaded_count} EPUBs uploaded, {created_count} products created")
    log(f"Total products on Gumroad: {len(existing) + created_count}")
    log(f"Current sales: ${total_sales:.2f}")
    log("=" * 60)
    
    # Update status
    actions = list(status.get("actions_taken", [])) if 'status' in dir() else []
    actions.append(f"Uploaded {uploaded_count} EPUBs, created {created_count} products")
    
    update_status(
        current_sales=total_sales,
        sales_count=sales_count,
        progress_percent=round(progress_pct, 2),
        actions_taken=actions,
        remaining_work=[
            "Continue creating products for remaining manifests (use multiple runs)",
            "Generate traffic content (TikTok, Pinterest, Substack)",
            "Monitor sales performance",
            "Create box set ($39.99) and Heritage Vault ($97) products",
            "Ensure all products have working purchase links"
        ]
    )

if __name__ == "__main__":
    # Load status for actions tracking
    try:
        with open(STATUS_FILE) as f:
            status = json.load(f)
    except:
        status = {}
    main()
