#!/usr/bin/env python3
"""
Gullah Geechee Biz — Page View Tracker
Runs alongside the redemption server on the M1.
Logs page views from the site and provides a simple dashboard.
No third-party services, no cookies, no cost.
"""

import json, os, sqlite3, datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

HOME = os.path.expanduser("~")
DB_PATH = os.path.join(HOME, ".hermes", "analytics", "pageviews.db")
PORT = 8766

os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS pageviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            page TEXT NOT NULL,
            referrer TEXT DEFAULT '',
            timestamp TEXT NOT NULL,
            ip TEXT DEFAULT '',
            user_agent TEXT DEFAULT ''
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS daily_stats (
            date TEXT PRIMARY KEY,
            total_views INTEGER DEFAULT 0,
            unique_pages INTEGER DEFAULT 0,
            top_page TEXT DEFAULT '',
            top_page_views INTEGER DEFAULT 0
        )
    """)
    conn.commit()
    conn.close()

def log_view(page, referrer, ip, user_agent):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    now = datetime.datetime.now().isoformat()
    c.execute(
        "INSERT INTO pageviews (page, referrer, timestamp, ip, user_agent) VALUES (?, ?, ?, ?, ?)",
        (page, referrer, now, ip, user_agent)
    )
    conn.commit()
    conn.close()

def get_stats(days=30):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Total views
    c.execute("SELECT COUNT(*) FROM pageviews")
    total = c.fetchone()[0]
    
    # Views in last N days
    cutoff = (datetime.datetime.now() - datetime.timedelta(days=days)).isoformat()
    c.execute("SELECT COUNT(*) FROM pageviews WHERE timestamp > ?", (cutoff,))
    recent = c.fetchone()[0]
    
    # Unique pages
    c.execute("SELECT COUNT(DISTINCT page) FROM pageviews")
    unique_pages = c.fetchone()[0]
    
    # Top pages
    c.execute("""
        SELECT page, COUNT(*) as cnt FROM pageviews 
        WHERE timestamp > ?
        GROUP BY page ORDER BY cnt DESC LIMIT 10
    """, (cutoff,))
    top_pages = c.fetchall()
    
    # Views by day (last 7)
    c.execute("""
        SELECT DATE(timestamp) as day, COUNT(*) as cnt
        FROM pageviews
        WHERE timestamp > ?
        GROUP BY day ORDER BY day DESC LIMIT 7
    """, (cutoff,))
    daily = c.fetchall()
    
    # Top referrers
    c.execute("""
        SELECT referrer, COUNT(*) as cnt
        FROM pageviews
        WHERE timestamp > ? AND referrer != ''
        GROUP BY referrer ORDER BY cnt DESC LIMIT 5
    """, (cutoff,))
    top_refs = c.fetchall()
    
    conn.close()
    
    return {
        "total": total,
        "recent": recent,
        "unique_pages": unique_pages,
        "top_pages": [{"page": p, "views": v} for p, v in top_pages],
        "daily": [{"day": d, "views": v} for d, v in daily],
        "top_referrers": [{"referrer": r, "views": v} for r, v in top_refs]
    }


class TrackerHandler(BaseHTTPRequestHandler):
    
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
    
    def do_GET(self):
        path = urlparse(self.path).path
        
        if path == "/track":
            # Tracking pixel (1x1 transparent GIF)
            params = parse_qs(urlparse(self.path).query)
            page = params.get("page", [""])[0]
            referrer = params.get("ref", [""])[0]
            ip = self.client_address[0]
            ua = self.headers.get("User-Agent", "")
            
            if page:
                log_view(page, referrer, ip, ua)
            
            # Return 1x1 transparent GIF
            self.send_response(200)
            self.send_header("Content-Type", "image/gif")
            self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            # 1x1 transparent GIF
            self.wfile.write(b'\x47\x49\x46\x38\x39\x61\x01\x00\x01\x00\x80\x00\x00\xff\xff\xff\x00\x00\x00\x21\xf9\x04\x00\x00\x00\x00\x00\x2c\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02\x44\x01\x00\x3b')
        
        elif path == "/dashboard":
            stats = get_stats()
            self._render_dashboard(stats)
        
        elif path == "/api/stats":
            stats = get_stats()
            self._json_response(200, stats)
        
        else:
            self.send_error(404)
    
    def _render_dashboard(self, stats):
        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Analytics — Gullah Geechee Biz</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;background:#0a0a14;color:#f0ede5;line-height:1.6;padding:40px 20px}}
.container{{max-width:800px;margin:0 auto}}
h1{{font-family:Georgia,serif;color:#d4af37;font-size:2em;margin-bottom:5px}}
.subtitle{{color:#888;margin-bottom:30px}}
.stats-grid{{display:grid;grid-template-columns:repeat(3,1fr);gap:15px;margin-bottom:30px}}
.stat-card{{background:#111122;border-radius:12px;padding:20px;text-align:center;border:1px solid #1a1a2e}}
.stat-card .num{{font-size:2em;font-weight:bold;color:#d4af37}}
.stat-card .label{{color:#888;font-size:0.85em;margin-top:4px}}
.section{{margin-bottom:30px}}
.section h2{{color:#d4af37;font-size:1.2em;margin-bottom:10px;border-bottom:1px solid #1a1a2e;padding-bottom:8px}}
table{{width:100%;border-collapse:collapse}}
th{{text-align:left;color:#888;font-size:0.85em;padding:8px 10px;border-bottom:1px solid #333}}
td{{padding:8px 10px;border-bottom:1px solid #1a1a2e;font-size:0.9em}}
td.num{{color:#d4af37;font-weight:bold;text-align:right}}
.bar{{display:inline-block;height:6px;background:#d4af37;border-radius:3px;margin-right:8px;vertical-align:middle}}
.footer{{margin-top:40px;color:#555;font-size:0.8em;text-align:center}}
</style>
</head>
<body>
<div class="container">
<h1>📊 Page Views</h1>
<p class="subtitle">Gullah Geechee Biz — Live analytics from the M1 tracker</p>

<div class="stats-grid">
<div class="stat-card">
<div class="num">{stats['total']}</div>
<div class="label">All Time Views</div>
</div>
<div class="stat-card">
<div class="num">{stats['recent']}</div>
<div class="label">Last 30 Days</div>
</div>
<div class="stat-card">
<div class="num">{stats['unique_pages']}</div>
<div class="label">Unique Pages</div>
</div>
</div>

<div class="section">
<h2>Top Pages (Last 30 Days)</h2>
<table>
<tr><th>Page</th><th style="text-align:right">Views</th></tr>
"""
        for p in stats['top_pages']:
            bar_width = max(20, min(200, p['views'] * 3))
            html += f'<tr><td>{p["page"]}</td><td class="num"><span class="bar" style="width:{bar_width}px"></span>{p["views"]}</td></tr>\n'
        
        html += """</table></div>

<div class="section">
<h2>Daily Views (Last 7 Days)</h2>
<table><tr><th>Date</th><th style="text-align:right">Views</th></tr>
"""
        for d in stats['daily']:
            bar_width = max(20, min(200, d['views'] * 3))
            html += f'<tr><td>{d["day"]}</td><td class="num"><span class="bar" style="width:{bar_width}px"></span>{d["views"]}</td></tr>\n'
        
        html += """</table></div>

<div class="section">
<h2>Top Referrers (Last 30 Days)</h2>
<table><tr><th>Source</th><th style="text-align:right">Views</th></tr>
"""
        for r in stats['top_referrers']:
            html += f'<tr><td>{r["referrer"]}</td><td class="num">{r["views"]}</td></tr>\n'
        
        if not stats['top_referrers']:
            html += '<tr><td colspan="2" style="color:#555">No referrer data yet</td></tr>\n'
        
        html += """</table></div>

<div class="footer">
<p>Gullah Geechee Biz · Local analytics · No third-party services</p>
</div>
</div>
</body>
</html>"""
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(html.encode("utf-8"))
    
    def _json_response(self, status, data):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode("utf-8"))
    
    def log_message(self, format, *args):
        msg = format % args
        if "track" in msg.lower():
            return  # Don't log tracking pixels
        print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] {msg}")


def main():
    init_db()
    print(f"📊 Gullah Geechee Biz — Page View Tracker")
    print(f"   Database: {DB_PATH}")
    print(f"   Listening on: http://localhost:{PORT}")
    print(f"")
    print(f"   Endpoints:")
    print(f"     GET /track?page=/recipes/&ref=google.com — Tracking pixel")
    print(f"     GET /dashboard — View analytics")
    print(f"     GET /api/stats — JSON stats")
    print(f"")
    print(f"   Press Ctrl+C to stop")
    
    server = HTTPServer(("0.0.0.0", PORT), TrackerHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down...")
        server.shutdown()


if __name__ == "__main__":
    main()
