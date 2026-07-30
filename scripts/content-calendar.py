#!/usr/bin/env python3
"""
Gullah Geechee Biz — Content Calendar Scheduler
Schedules all content across all channels from the GGB Buffer Queue.
Pins, commercials, trailers, ads — everything on a timed rotation.
"""

import json, os, sys, sqlite3, subprocess, hashlib
from pathlib import Path
from datetime import datetime, timedelta
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

HOME = Path.home()
CALENDAR_DIR = HOME / ".hermes" / "calendar"
CALENDAR_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = CALENDAR_DIR / "calendar.db"
CALENDAR_PORT = 8772

# ─── Database ───────────────────────────────────────────────────────────────────

def init_db():
    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()
    
    # Content items
    c.execute("""
        CREATE TABLE IF NOT EXISTS content_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            content_type TEXT NOT NULL,
            source TEXT NOT NULL,
            file_path TEXT,
            duration_seconds INTEGER DEFAULT 0,
            created_at TEXT NOT NULL,
            scheduled_at TEXT,
            posted_at TEXT,
            status TEXT DEFAULT 'draft',
            channel TEXT DEFAULT '',
            notes TEXT DEFAULT ''
        )
    """)
    
    # Schedules
    c.execute("""
        CREATE TABLE IF NOT EXISTS schedules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            channel TEXT NOT NULL,
            content_type TEXT NOT NULL,
            interval_minutes INTEGER DEFAULT 1440,
            max_per_day INTEGER DEFAULT 1,
            last_posted TEXT,
            next_post TEXT,
            enabled INTEGER DEFAULT 1
        )
    """)
    
    # Posting log
    c.execute("""
        CREATE TABLE IF NOT EXISTS post_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            content_id INTEGER,
            channel TEXT NOT NULL,
            posted_at TEXT NOT NULL,
            status TEXT DEFAULT 'pending',
            url TEXT,
            notes TEXT
        )
    """)
    
    conn.commit()
    conn.close()

# ─── Content Registry ───────────────────────────────────────────────────────────

def register_content(title, content_type, source, file_path=None, duration=0, notes=""):
    """Register a content item in the calendar."""
    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()
    c.execute("""
        INSERT INTO content_items (title, content_type, source, file_path, duration_seconds, created_at, status, notes)
        VALUES (?, ?, ?, ?, ?, ?, 'ready', ?)
    """, (title, content_type, source, file_path, duration, datetime.now().isoformat(), notes))
    cid = c.lastrowid
    conn.commit()
    conn.close()
    return cid

def register_all_existing():
    """Register all existing content in the calendar."""
    count = 0
    
    # Trailers
    trailers = [
        ("Bundle Ad", "trailer", str(HOME / "gullahgeecheebiz-trailer.mp4"), 12),
        ("Seafood Cookbook", "trailer", str(HOME / "gullahgeecheebiz-seafood-trailer.mp4"), 12),
        ("Entrepreneur", "trailer", str(HOME / "gullahgeecheebiz-entrepreneur-trailer.mp4"), 12),
    ]
    
    # Commercials
    for d in sorted((HOME / "commercial-studio").glob("*/commercial-*.mp4")):
        name = d.parent.name
        trailers.append((f"Commercial: {name}", "commercial", str(d), 18))
    
    # Ad images
    for img in (HOME / "generated-ads" / "images").glob("*.png"):
        trailers.append((f"Ad Image: {img.stem}", "image", str(img), 0))
    
    # Copper concepts
    for img in (HOME / "copper-concepts").glob("*.png"):
        trailers.append((f"Copper: {img.stem}", "product", str(img), 0))
    
    for title, ctype, path, dur in trailers:
        if os.path.exists(path):
            register_content(title, ctype, "local", path, dur)
            count += 1
    
    return count

# ─── Schedule Definitions ──────────────────────────────────────────────────────

DEFAULT_SCHEDULES = [
    # Pinterest — 150 pins/day = 1 pin every 9.6 minutes during waking hours
    {"name": "Pinterest Pins", "channel": "pinterest", "content_type": "image", 
     "interval_minutes": 10, "max_per_day": 150, "enabled": 1},
    
    # TikTok — 3 posts/day
    {"name": "TikTok Posts", "channel": "tiktok", "content_type": "video", 
     "interval_minutes": 480, "max_per_day": 3, "enabled": 1},
    
    # Instagram — 2 posts/day
    {"name": "Instagram Posts", "channel": "instagram", "content_type": "video", 
     "interval_minutes": 720, "max_per_day": 2, "enabled": 1},
    
    # YouTube Shorts — 1/day
    {"name": "YouTube Shorts", "channel": "youtube", "content_type": "video", 
     "interval_minutes": 1440, "max_per_day": 1, "enabled": 1},
    
    # Commercial rotation — 1/day
    {"name": "Commercial Rotation", "channel": "all", "content_type": "commercial", 
     "interval_minutes": 1440, "max_per_day": 1, "enabled": 1},
]

def init_schedules():
    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()
    for sched in DEFAULT_SCHEDULES:
        c.execute("""
            INSERT OR IGNORE INTO schedules (name, channel, content_type, interval_minutes, max_per_day, enabled)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (sched["name"], sched["channel"], sched["content_type"], 
              sched["interval_minutes"], sched["max_per_day"], sched["enabled"]))
    conn.commit()
    conn.close()

def get_next_content(content_type):
    """Get the next unscheduled content item of a given type."""
    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()
    c.execute("""
        SELECT id, title, file_path FROM content_items 
        WHERE content_type=? AND status='ready' AND scheduled_at IS NULL
        ORDER BY created_at LIMIT 1
    """, (content_type,))
    row = c.fetchone()
    conn.close()
    return row

def get_content_rotation(content_type):
    """Get all ready content of a type for rotation."""
    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()
    c.execute("""
        SELECT id, title, file_path FROM content_items 
        WHERE content_type=? AND status='ready'
        ORDER BY created_at
    """, (content_type,))
    rows = c.fetchall()
    conn.close()
    return rows

def schedule_next():
    """Schedule the next batch of content based on schedules."""
    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()
    
    now = datetime.now()
    scheduled = []
    
    # Check each schedule
    c.execute("SELECT id, name, channel, content_type, interval_minutes, max_per_day, last_posted FROM schedules WHERE enabled=1")
    
    for row in c.fetchall():
        sched_id, name, channel, content_type, interval, max_per_day, last_posted = row
        
        # Check if it's time to post
        if last_posted:
            last = datetime.fromisoformat(last_posted)
            minutes_since = (now - last).total_seconds() / 60
            if minutes_since < interval:
                continue
        
        # Check daily limit
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
        c.execute("""
            SELECT COUNT(*) FROM post_log 
            WHERE channel=? AND posted_at > ? AND status='posted'
        """, (channel, today_start))
        posted_today = c.fetchone()[0]
        
        if posted_today >= max_per_day:
            continue
        
        # Get next content
        content = get_next_content(content_type)
        if not content:
            # Rotate: mark all as ready again
            c.execute("UPDATE content_items SET status='ready', scheduled_at=NULL WHERE content_type=?", (content_type,))
            content = get_next_content(content_type)
        
        if content:
            cid, title, filepath = content
            # Schedule it
            post_time = now + timedelta(minutes=5)
            c.execute("UPDATE content_items SET scheduled_at=?, status='scheduled' WHERE id=?", 
                     (post_time.isoformat(), cid))
            c.execute("UPDATE schedules SET last_posted=?, next_post=? WHERE id=?",
                     (now.isoformat(), post_time.isoformat(), sched_id))
            
            scheduled.append({
                "content_id": cid,
                "title": title,
                "channel": channel,
                "scheduled_at": post_time.isoformat(),
                "file_path": filepath
            })
    
    conn.commit()
    conn.close()
    return scheduled

# ─── Dashboard ─────────────────────────────────────────────────────────────────

class CalendarHandler(BaseHTTPRequestHandler):
    
    def do_GET(self):
        path = urlparse(self.path).path
        params = parse_qs(urlparse(self.path).query)
        
        if path == "/" or path == "/dashboard":
            self._render_dashboard()
        elif path == "/api/calendar":
            self._json(200, self._get_calendar())
        elif path == "/api/schedules":
            self._json(200, self._get_schedules())
        elif path == "/api/queue":
            scheduled = schedule_next()
            self._json(200, {"scheduled": scheduled})
        elif path == "/api/register":
            count = register_all_existing()
            self._json(200, {"registered": count})
        else:
            self._json(404, {"error": "Not found"})
    
    def _get_calendar(self):
        conn = sqlite3.connect(str(DB_PATH))
        c = conn.cursor()
        c.execute("""
            SELECT id, title, content_type, status, scheduled_at, posted_at, channel
            FROM content_items ORDER BY 
            CASE status 
                WHEN 'scheduled' THEN 0
                WHEN 'ready' THEN 1
                ELSE 2
            END, scheduled_at NULLS LAST, created_at DESC
            LIMIT 50
        """)
        items = [{"id": r[0], "title": r[1][:40], "type": r[2], "status": r[3], 
                  "scheduled": r[4], "posted": r[5], "channel": r[6]} for r in c.fetchall()]
        conn.close()
        return items
    
    def _get_schedules(self):
        conn = sqlite3.connect(str(DB_PATH))
        c = conn.cursor()
        c.execute("SELECT id, name, channel, content_type, interval_minutes, max_per_day, last_posted, next_post, enabled FROM schedules")
        scheds = [{"id": r[0], "name": r[1], "channel": r[2], "type": r[3], 
                   "interval": r[4], "max_per_day": r[5], "last_posted": r[6],
                   "next_post": r[7], "enabled": bool(r[8])} for r in c.fetchall()]
        conn.close()
        return scheds
    
    def _render_dashboard(self):
        items = self._get_calendar()
        scheds = self._get_schedules()
        
        ready = sum(1 for i in items if i['status'] == 'ready')
        scheduled = sum(1 for i in items if i['status'] == 'scheduled')
        posted = sum(1 for i in items if i['status'] == 'posted')
        
        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>GGB Content Calendar</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;background:#0a0a14;color:#f0ede5;line-height:1.6;padding:30px 20px}}
.container{{max-width:1000px;margin:0 auto}}
h1{{font-family:Georgia,serif;color:#d4af37;font-size:1.8em;margin-bottom:5px}}
.subtitle{{color:#888;margin-bottom:25px}}
.grid{{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-bottom:25px}}
.card{{background:#111122;border-radius:10px;padding:18px;text-align:center;border:1px solid #1a1a2e}}
.card .num{{font-size:1.8em;font-weight:bold;color:#d4af37}}
.card .label{{color:#888;font-size:0.8em;margin-top:3px}}
.controls{{display:flex;gap:8px;margin-bottom:20px;flex-wrap:wrap}}
.btn{{background:#d4af37;color:#0a0a14;padding:8px 16px;border-radius:20px;border:none;cursor:pointer;font-weight:bold;font-size:0.85em}}
.btn:hover{{background:#e8c84a}}
.btn-outline{{background:transparent;color:#d4af37;border:1px solid #d4af37}}
.section{{margin-bottom:25px}}
.section h2{{color:#d4af37;font-size:1.1em;margin-bottom:8px;border-bottom:1px solid #1a1a2e;padding-bottom:6px}}
table{{width:100%;border-collapse:collapse;font-size:0.85em}}
th{{text-align:left;color:#888;padding:6px 8px;border-bottom:1px solid #333;font-weight:normal}}
td{{padding:6px 8px;border-bottom:1px solid #1a1a2e}}
.status-ready{{color:#27ae60}}
.status-scheduled{{color:#f39c12}}
.status-posted{{color:#888}}
.footer{{margin-top:30px;color:#555;font-size:0.75em;text-align:center}}
</style>
</head>
<body>
<div class="container">
<h1>📅 GGB Content Calendar</h1>
<p class="subtitle">Schedule everything — pins, commercials, trailers, ads</p>

<div class="grid">
<div class="card"><div class="num">{ready}</div><div class="label">Ready</div></div>
<div class="card"><div class="num">{scheduled}</div><div class="label">Scheduled</div></div>
<div class="card"><div class="num">{posted}</div><div class="label">Posted</div></div>
<div class="card"><div class="num">{len(scheds)}</div><div class="label">Schedules</div></div>
</div>

<div class="controls">
<button class="btn" onclick="register()">Register Content</button>
<button class="btn" onclick="queue()">Schedule Next Batch</button>
<button class="btn btn-outline" onclick="window.location.reload()">Refresh</button>
</div>

<div class="section">
<h2>Schedules</h2>
<table><tr><th>Name</th><th>Channel</th><th>Type</th><th>Interval</th><th>Max/Day</th><th>Next Post</th><th>Status</th></tr>
"""
        for s in scheds:
            interval_str = f"every {s['interval']//60}h" if s['interval'] >= 60 else f"every {s['interval']}m"
            next_str = s['next_post'][:16] if s['next_post'] else 'now'
            html += f"""<tr>
<td>{s['name']}</td>
<td>{s['channel']}</td>
<td>{s['type']}</td>
<td>{interval_str}</td>
<td>{s['max_per_day']}</td>
<td style="font-size:0.8em">{next_str}</td>
<td>{'✅' if s['enabled'] else '❌'}</td>
</tr>"""
        
        html += """</table></div>

<div class="section">
<h2>Content Queue</h2>
<table><tr><th>Title</th><th>Type</th><th>Status</th><th>Scheduled</th><th>Channel</th></tr>
"""
        for item in items[:20]:
            status_class = f"status-{item['status']}"
            sched_str = item['scheduled'][:16] if item['scheduled'] else '-'
            html += f"""<tr>
<td>{item['title']}</td>
<td style="color:#888">{item['type']}</td>
<td class="{status_class}">{item['status']}</td>
<td style="font-size:0.8em">{sched_str}</td>
<td style="color:#555">{item['channel']}</td>
</tr>"""
        
        html += """</table></div>

<div class="footer">
GGB Content Calendar · Port 8772 · SQLite backend
</div>
</div>

<script>
async function register() {
    const resp = await fetch('/api/register');
    const data = await resp.json();
    alert('Registered ' + data.registered + ' content items');
    window.location.reload();
}
async function queue() {
    const resp = await fetch('/api/queue');
    const data = await resp.json();
    alert('Scheduled ' + data.scheduled.length + ' items');
    window.location.reload();
}
</script>
</body>
</html>"""
        
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(html.encode("utf-8"))
    
    def _json(self, status, data):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode("utf-8"))
    
    def log_message(self, format, *args):
        pass

# ─── Main ──────────────────────────────────────────────────────────────────────

def main():
    init_db()
    init_schedules()
    
    # Auto-register existing content
    count = register_all_existing()
    
    # Start dashboard
    server = HTTPServer(("0.0.0.0", CALENDAR_PORT), CalendarHandler)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    
    print(f"\n{'='*50}")
    print(f"📅 GGB Content Calendar")
    print(f"{'='*50}")
    print(f"   Dashboard: http://localhost:{CALENDAR_PORT}")
    print(f"   Content registered: {count} items")
    print(f"   Schedules: {len(DEFAULT_SCHEDULES)}")
    print(f"{'='*50}")
    print()
    print(f"   Pinterest: 150 pins/day (every 10 min)")
    print(f"   TikTok: 3 posts/day")
    print(f"   Instagram: 2 posts/day")
    print(f"   YouTube Shorts: 1/day")
    print(f"   Commercial Rotation: 1/day")
    print()
    
    # Schedule loop
    try:
        while True:
            scheduled = schedule_next()
            if scheduled:
                for s in scheduled:
                    print(f"   📅 Scheduled: {s['title']} → {s['channel']} at {s['scheduled_at'][:16]}")
            time.sleep(60)
    except KeyboardInterrupt:
        print("\nShutting down...")

if __name__ == "__main__":
    import threading, time
    main()
