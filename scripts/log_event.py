#!/usr/bin/env python3
"""
GGB Promotion Orchestrator — Event Stream Logger
Records promotion activities to the publisher database.
"""
import sqlite3
import json
from datetime import datetime
from pathlib import Path

HOME = Path.home()
DB_PATH = HOME / "gullahgeecheebiz-site" / "publish" / "publisher.db"

def log_event(manifest_id, title, author="Darryl Elliott Brown", **kwargs):
    """Log a promotion event to the publisher database."""
    data = {
        "id": manifest_id,
        "title": title,
        "author": author,
        **kwargs
    }
    
    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()
    
    # Check if already exists
    c.execute("SELECT 1 FROM manifests WHERE manifest_id = ?", (manifest_id,))
    if c.fetchone():
        print(f"Event {manifest_id} already exists, skipping")
        conn.close()
        return False
    
    c.execute(
        "INSERT INTO manifests (manifest_id, data, state, created_at) VALUES (?, ?, ?, ?)",
        (manifest_id, json.dumps(data), 'published', datetime.now().isoformat())
    )
    conn.commit()
    conn.close()
    print(f"✓ Logged: {manifest_id} - {title}")
    return True

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 3:
        print("Usage: python3 log_event.py <manifest_id> <title> [extra_json]")
        sys.exit(1)
    
    manifest_id = sys.argv[1]
    title = sys.argv[2]
    extra = {}
    if len(sys.argv) > 3:
        extra = json.loads(sys.argv[3])
    
    log_event(manifest_id, title, **extra)
