#!/usr/bin/env python3
"""
GGB Book Pipeline Trigger — Keeps books flowing through the pipeline.
Runs every 4 hours via cron. Creates new books, validates, packages, submits.
"""
import json, os, sys, time, sqlite3, requests, subprocess
from pathlib import Path
from datetime import datetime

BASE = Path("/Users/darrylsmac/gullahgeecheebiz-site")
DB = BASE / "publish" / "publisher.db"
HQ = BASE / "ggb-engine" / "headquarters"
LOG_DIR = HQ / "logs" / "book-pipeline"
LOG_DIR.mkdir(parents=True, exist_ok=True)

def log(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] {msg}")
    with open(LOG_DIR / "pipeline.log", "a") as f:
        f.write(f"[{ts}] {msg}\n")

def get_book_count():
    conn = sqlite3.connect(str(DB))
    count = conn.execute("SELECT COUNT(*) FROM manifests WHERE state='published'").fetchone()[0]
    conn.close()
    return count

def get_controller_token():
    """Read the publishing-controller Bearer token (env first, then .agent_tokens.env)."""
    token = os.environ.get("AGENT_TOKEN_PUBLISHING_CONTROLLER", "")
    if not token:
        try:
            for line in (HQ / ".agent_tokens.env").read_text().splitlines():
                if line.startswith("AGENT_TOKEN_PUBLISHING_CONTROLLER="):
                    token = line.split("=", 1)[1].strip()
                    break
        except Exception:
            pass
    return token

def trigger_controller(task_type, book_id):
    """Send a task to the Publishing Controller."""
    token = get_controller_token()
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    try:
        r = requests.post(
            "http://127.0.0.1:8090/api/assign",
            json={"task_type": task_type, "book_id": book_id},
            headers=headers,
            timeout=10
        )
        if r.status_code == 200:
            return r.json().get("status") == "queued"
        return False
    except:
        return False

def get_controller_status():
    try:
        r = requests.get("http://127.0.0.1:8090/api/status", timeout=5)
        if r.status_code == 200:
            return r.json()
    except:
        pass
    return None

def main():
    log("=" * 50)
    log("BOOK PIPELINE TRIGGER STARTING")
    
    # Step 1: Check current state
    before = get_book_count()
    log(f"Current published books: {before}")
    
    # Step 2: Check controller status
    status = get_controller_status()
    if status:
        idle = status.get("agents", {}).get("by_status", {}).get("IDLE", 0)
        queue = status.get("queue", {}).get("size", 0)
        log(f"Controller: {idle} agents idle, {queue} in queue")
    
    # Step 3: Get a book to work on
    conn = sqlite3.connect(str(DB))
    rows = conn.execute("SELECT manifest_id FROM manifests WHERE state='published' LIMIT 5").fetchall()
    conn.close()
    
    if rows:
        for row in rows:
            book_id = row[0]
            # Assign content creation task
            if trigger_controller("CONTENT_CREATION", book_id):
                log(f"  ✅ Assigned CONTENT_CREATION for {book_id[:40]}...")
            time.sleep(1)
            
            # Assign validation
            if trigger_controller("VALIDATION", book_id):
                log(f"  ✅ Assigned VALIDATION for {book_id[:40]}...")
            time.sleep(1)
            
            # Assign packaging
            if trigger_controller("PACKAGING", book_id):
                log(f"  ✅ Assigned PACKAGING for {book_id[:40]}...")
            time.sleep(1)
    
    # Step 4: Run Gumroad publisher (if daily limit reset)
    gumroad_script = HQ / "gumroad-publisher-v3.py"
    if gumroad_script.exists():
        log("Running Gumroad publisher...")
        result = subprocess.run(
            [sys.executable, str(gumroad_script)],
            capture_output=True, text=True, timeout=300
        )
        for line in result.stdout.split("\n"):
            if "✅" in line or "❌" in line or "📊" in line or "Progress" in line:
                log(f"  Gumroad: {line.strip()}")
    
    # Step 5: Report
    after = get_book_count()
    diff = after - before
    log(f"Books before: {before}, after: {after}, change: {diff}")
    
    print(f"\n📊 Pipeline complete: {before} → {after} ({diff:+d})")
    log("=" * 50)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        log(f"💥 Error: {e}")
