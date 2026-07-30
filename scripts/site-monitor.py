#!/usr/bin/env python3
"""
Gullah Geechee Biz — Site Monitor + Auto-SEO Engine
Runs on M1. Tracks page views, checks SEO health, and directs bots
to maintain visibility. All local, no third-party services.
"""

import json, os, sys, subprocess, sqlite3, time
from pathlib import Path
from datetime import datetime, timedelta
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

HOME = Path.home()
SITE_DIR = HOME / "gullahgeecheebiz-site"
DB_PATH = HOME / ".hermes" / "monitor" / "site-monitor.db"
MONITOR_PORT = 8767
TRACKER_PORT = 8766

os.makedirs(DB_PATH.parent, exist_ok=True)

def init_db():
    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS page_views (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            page TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            referrer TEXT DEFAULT '',
            ip TEXT DEFAULT ''
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS seo_checks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            check_date TEXT NOT NULL,
            page TEXT NOT NULL,
            check_type TEXT NOT NULL,
            status TEXT NOT NULL,
            detail TEXT DEFAULT ''
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS bot_actions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            bot_name TEXT NOT NULL,
            action TEXT NOT NULL,
            result TEXT DEFAULT ''
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS page_content (
            page TEXT PRIMARY KEY,
            title TEXT DEFAULT '',
            description TEXT DEFAULT '',
            last_updated TEXT DEFAULT '',
            word_count INTEGER DEFAULT 0,
            has_canonical INTEGER DEFAULT 0,
            has_og INTEGER DEFAULT 0,
            has_schema INTEGER DEFAULT 0
        )
    """)
    conn.commit()
    conn.close()

def log_view(page, referrer, ip):
    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()
    c.execute(
        "INSERT INTO page_views (page, timestamp, referrer, ip) VALUES (?, ?, ?, ?)",
        (page, datetime.now().isoformat(), referrer, ip)
    )
    conn.commit()
    conn.close()

def log_seo_check(page, check_type, status, detail=""):
    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()
    c.execute(
        "INSERT INTO seo_checks (check_date, page, check_type, status, detail) VALUES (?, ?, ?, ?, ?)",
        (datetime.now().isoformat(), page, check_type, status, detail)
    )
    conn.commit()
    conn.close()

def log_bot_action(bot_name, action, result=""):
    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()
    c.execute(
        "INSERT INTO bot_actions (timestamp, bot_name, action, result) VALUES (?, ?, ?, ?)",
        (datetime.now().isoformat(), bot_name, action, result)
    )
    conn.commit()
    conn.close()

def get_stats(days=7):
    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()
    
    cutoff = (datetime.now() - timedelta(days=days)).isoformat()
    
    # Total views
    c.execute("SELECT COUNT(*) FROM page_views WHERE timestamp > ?", (cutoff,))
    total = c.fetchone()[0]
    
    # Top pages
    c.execute("""
        SELECT page, COUNT(*) as cnt FROM page_views
        WHERE timestamp > ?
        GROUP BY page ORDER BY cnt DESC LIMIT 10
    """, (cutoff,))
    top_pages = c.fetchall()
    
    # Views by day
    c.execute("""
        SELECT DATE(timestamp) as day, COUNT(*) as cnt
        FROM page_views WHERE timestamp > ?
        GROUP BY day ORDER BY day DESC
    """, (cutoff,))
    daily = c.fetchall()
    
    # SEO check stats
    c.execute("SELECT COUNT(*) FROM seo_checks WHERE check_date > ?", (cutoff,))
    seo_total = c.fetchone()[0]
    
    c.execute("""
        SELECT status, COUNT(*) as cnt FROM seo_checks
        WHERE check_date > ?
        GROUP BY status
    """, (cutoff,))
    seo_status = c.fetchall()
    
    # Bot actions
    c.execute("SELECT COUNT(*) FROM bot_actions WHERE timestamp > ?", (cutoff,))
    bot_total = c.fetchone()[0]
    
    conn.close()
    
    return {
        "total_views": total,
        "top_pages": [{"page": p, "views": v} for p, v in top_pages],
        "daily_views": [{"day": d, "views": v} for d, v in daily],
        "seo_checks": seo_total,
        "seo_status": [{"status": s, "count": c} for s, c in seo_status],
        "bot_actions": bot_total
    }

def run_seo_audit():
    """Run the daily SEO audit and return results."""
    script = SITE_DIR / "scripts" / "daily-seo-audit.py"
    if not script.exists():
        return {"status": "error", "detail": "SEO audit script not found"}
    
    result = subprocess.run(["python3", str(script)], capture_output=True, text=True, timeout=60)
    
    # Log each check
    for line in result.stdout.split("\n"):
        if "❌" in line:
            log_seo_check("site-wide", "audit", "fail", line.strip())
        elif "✅" in line:
            log_seo_check("site-wide", "audit", "pass", line.strip())
    
    return {
        "status": "ok" if result.returncode == 0 else "issues_found",
        "output": result.stdout,
        "exit_code": result.returncode
    }

def run_auto_fix():
    """Run the auto-fix script if issues were found."""
    script = SITE_DIR / "scripts" / "fix-audit-issues.py"
    if not script.exists():
        return {"status": "error", "detail": "Fix script not found"}
    
    result = subprocess.run(["python3", str(script)], capture_output=True, text=True, timeout=60)
    log_bot_action("seo-fixer", "auto-fix", result.stdout[:200])
    return {"status": "ok", "output": result.stdout}

def check_page_health(url):
    """Check if a page is returning 200 and has proper SEO tags."""
    try:
        result = subprocess.run(
            ["curl", "-sL", "--max-time", "10", url],
            capture_output=True, text=True
        )
        content = result.stdout
        
        checks = {
            "status": result.returncode == 0,
            "has_title": "<title>" in content,
            "has_meta_desc": 'name="description"' in content,
            "has_canonical": 'rel="canonical"' in content,
            "has_og": 'property="og:' in content,
            "content_length": len(content)
        }
        
        return checks
    except:
        return {"status": False, "error": "timeout"}

def promote_new_content():
    """Check for new content and trigger promotion bots."""
    ebook_count = 0
    recipe_count = 0
    
    # Check for new ebooks
    ebooks_dir = HOME / "ebooks" / "mass"
    if ebooks_dir.exists():
        ebook_count = len(list(ebooks_dir.glob("*.docx")))
        log_bot_action("content-check", f"ebook-count: {ebook_count}")
    
    # Check for new recipes
    recipes_dir = SITE_DIR / "recipes"
    if recipes_dir.exists():
        recipe_count = len(list(recipes_dir.glob("*.html")))
        log_bot_action("content-check", f"recipe-count: {recipe_count}")
    
    return {"ebooks": ebook_count, "recipes": recipe_count}

def check_traffic_and_escalate():
    """
    Check traffic levels. If below threshold, trigger promotion bots
    to push more visibility across all channels.
    """
    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()
    
    # Views in last 24 hours
    cutoff_24h = (datetime.now() - timedelta(hours=24)).isoformat()
    c.execute("SELECT COUNT(*) FROM page_views WHERE timestamp > ?", (cutoff_24h,))
    views_24h = c.fetchone()[0]
    
    # Views in last 7 days
    cutoff_7d = (datetime.now() - timedelta(days=7)).isoformat()
    c.execute("SELECT COUNT(*) FROM page_views WHERE timestamp > ?", (cutoff_7d,))
    views_7d = c.fetchone()[0]
    
    conn.close()
    
    # Thresholds (adjustable)
    LOW_TRAFFIC_24H = 5      # Less than 5 views in 24h = low
    LOW_TRAFFIC_7D = 20      # Less than 20 views in 7d = low
    
    status = "normal"
    actions = []
    
    if views_24h < LOW_TRAFFIC_24H:
        status = "low_traffic"
        actions.append("Traffic below 24h threshold — escalating promotion")
        log_bot_action("traffic-monitor", "escalate-24h", f"views={views_24h}, threshold={LOW_TRAFFIC_24H}")
        
        # Generate fresh ads
        _generate_ads()
        
        # Trigger promotion bots
        _run_promotion_bot("promoter-1", "traffic-escalation")
        _run_promotion_bot("promoter-2", "traffic-escalation")
        _run_seo_bot()
        
    if views_7d < LOW_TRAFFIC_7D:
        status = "low_traffic"
        actions.append("Traffic below 7d threshold — escalating SEO and distribution")
        log_bot_action("traffic-monitor", "escalate-7d", f"views={views_7d}, threshold={LOW_TRAFFIC_7D}")
        
        # Generate more ads
        _generate_ads(count=10)
        
        # Run SEO audit + fix
        run_seo_audit()
        run_auto_fix()
        
        # Trigger viral page generation
        _run_viral_bot()
    
    if status == "normal":
        log_bot_action("traffic-monitor", "normal", f"24h={views_24h}, 7d={views_7d}")
    
    return {
        "status": status,
        "views_24h": views_24h,
        "views_7d": views_7d,
        "actions_taken": actions
    }

def _generate_ads(count=5):
    """Run the ad generator."""
    script = SITE_DIR / "scripts" / "ad-generator.py"
    if script.exists():
        try:
            result = subprocess.run(["python3", str(script)], capture_output=True, text=True, timeout=30)
            log_bot_action("ad-generator", "traffic-escalation", f"generated {count} ads")
        except:
            pass

def _run_promotion_bot(bot_name, reason):
    """Run a promotion bot script."""
    script = SITE_DIR / "scripts" / f"{bot_name}.sh"
    if script.exists():
        try:
            result = subprocess.run(["bash", str(script), "traffic", reason],
                                  capture_output=True, text=True, timeout=120)
            log_bot_action(bot_name, f"triggered-{reason}", result.stdout[:200])
        except subprocess.TimeoutExpired:
            log_bot_action(bot_name, f"triggered-{reason}", "timeout")
        except Exception as e:
            log_bot_action(bot_name, f"triggered-{reason}", str(e))

def _run_seo_bot():
    """Run the SEO optimization bot."""
    script = SITE_DIR / "scripts" / "seo-bot.sh"
    if script.exists():
        try:
            result = subprocess.run(["bash", str(script), "optimize", "all-pages"],
                                  capture_output=True, text=True, timeout=120)
            log_bot_action("seo-bot", "traffic-escalation", result.stdout[:200])
        except:
            pass

def _run_viral_bot():
    """Run the viral page generator."""
    script = SITE_DIR / "scripts" / "viral-seller-1.sh"
    if script.exists():
        try:
            result = subprocess.run(["bash", str(script), "gullah-geechee", "culture"],
                                  capture_output=True, text=True, timeout=120)
            log_bot_action("viral-bot", "traffic-escalation", result.stdout[:200])
        except:
            pass

class MonitorHandler(BaseHTTPRequestHandler):
    
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
    
    def do_GET(self):
        path = urlparse(self.path).path
        
        if path == "/track":
            params = parse_qs(urlparse(self.path).query)
            page = params.get("page", [""])[0]
            ref = params.get("ref", [""])[0]
            ip = self.client_address[0]
            
            if page:
                log_view(page, ref, ip)
            
            # Return 1x1 transparent GIF
            self.send_response(200)
            self.send_header("Content-Type", "image/gif")
            self.send_header("Cache-Control", "no-cache, no-store")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(b'\x47\x49\x46\x38\x39\x61\x01\x00\x01\x00\x80\x00\x00\xff\xff\xff\x00\x00\x00\x21\xf9\x04\x00\x00\x00\x00\x00\x2c\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02\x44\x01\x00\x3b')
        
        elif path == "/dashboard":
            stats = get_stats()
            self._render_dashboard(stats)
        
        elif path == "/api/stats":
            stats = get_stats()
            self._json_response(200, stats)
        
        elif path == "/api/run-audit":
            result = run_seo_audit()
            self._json_response(200, result)
        
        elif path == "/api/run-fix":
            result = run_auto_fix()
            self._json_response(200, result)
        
        elif path == "/api/check-pages":
            pages = [
                "https://gullahgeecheebiz.com/",
                "https://gullahgeecheebiz.com/ebooks/",
                "https://gullahgeecheebiz.com/recipes/",
                "https://gullahgeecheebiz.com/membership/",
                "https://gullahgeecheebiz.com/shop/",
                "https://gullahgeecheebiz.com/wholesale/",
            ]
            results = {}
            for p in pages:
                results[p] = check_page_health(p)
            self._json_response(200, results)
        
        elif path == "/api/traffic-check":
            result = check_traffic_and_escalate()
            self._json_response(200, result)
        
        else:
            self.send_error(404)
    
    def _render_dashboard(self, stats):
        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Site Monitor — Gullah Geechee Biz</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;background:#0a0a14;color:#f0ede5;line-height:1.6;padding:40px 20px}}
.container{{max-width:900px;margin:0 auto}}
h1{{font-family:Georgia,serif;color:#d4af37;font-size:2em;margin-bottom:5px}}
.subtitle{{color:#888;margin-bottom:30px}}
.grid{{display:grid;grid-template-columns:repeat(3,1fr);gap:15px;margin-bottom:30px}}
.card{{background:#111122;border-radius:12px;padding:20px;text-align:center;border:1px solid #1a1a2e}}
.card .num{{font-size:2em;font-weight:bold;color:#d4af37}}
.card .label{{color:#888;font-size:0.85em;margin-top:4px}}
.section{{margin-bottom:30px}}
.section h2{{color:#d4af37;font-size:1.2em;margin-bottom:10px;border-bottom:1px solid #1a1a2e;padding-bottom:8px}}
table{{width:100%;border-collapse:collapse}}
th{{text-align:left;color:#888;font-size:0.85em;padding:8px 10px;border-bottom:1px solid #333}}
td{{padding:8px 10px;border-bottom:1px solid #1a1a2e;font-size:0.9em}}
td.num{{color:#d4af37;font-weight:bold;text-align:right}}
.actions{{display:flex;gap:10px;margin:20px 0;flex-wrap:wrap}}
.btn{{display:inline-block;background:#d4af37;color:#0a0a14;padding:10px 20px;border-radius:25px;text-decoration:none;font-weight:bold;font-size:0.9em;cursor:pointer;border:none}}
.btn:hover{{background:#e8c84a}}
.btn-outline{{background:transparent;color:#d4af37;border:1px solid #d4af37}}
.footer{{margin-top:40px;color:#555;font-size:0.8em;text-align:center}}
</style>
</head>
<body>
<div class="container">
<h1>📊 Site Monitor</h1>
<p class="subtitle">Gullah Geechee Biz — Live traffic, SEO health, and bot oversight</p>

<div class="grid">
<div class="card"><div class="num">{stats['total_views']}</div><div class="label">Page Views (7d)</div></div>
<div class="card"><div class="num">{stats['seo_checks']}</div><div class="label">SEO Checks (7d)</div></div>
<div class="card"><div class="num">{stats['bot_actions']}</div><div class="label">Bot Actions (7d)</div></div>
</div>

<div class="actions">
<button class="btn" onclick="runAudit()">Run SEO Audit</button>
<button class="btn" onclick="checkPages()">Check Page Health</button>
<button class="btn btn-outline" onclick="window.location.reload()">Refresh</button>
</div>
<div id="action-result" style="margin:10px 0;padding:10px;background:#111122;border-radius:8px;display:none"></div>

<div class="section">
<h2>Top Pages (7 Days)</h2>
<table><tr><th>Page</th><th style="text-align:right">Views</th></tr>
"""
        for p in stats['top_pages']:
            html += f'<tr><td>{p["page"]}</td><td class="num">{p["views"]}</td></tr>\n'
        
        if not stats['top_pages']:
            html += '<tr><td colspan="2" style="color:#555">No page views recorded yet</td></tr>\n'
        
        html += """</table></div>

<div class="section">
<h2>Daily Views (7 Days)</h2>
<table><tr><th>Date</th><th style="text-align:right">Views</th></tr>
"""
        for d in stats['daily_views']:
            html += f'<tr><td>{d["day"]}</td><td class="num">{d["views"]}</td></tr>\n'
        
        html += """</table></div>

<div class="section">
<h2>SEO Check Status</h2>
<table><tr><th>Status</th><th style="text-align:right">Count</th></tr>
"""
        for s in stats['seo_status']:
            icon = "✅" if s["status"] == "pass" else "❌"
            html += f'<tr><td>{icon} {s["status"]}</td><td class="num">{s["count"]}</td></tr>\n'
        
        html += """</table></div>

<div class="footer">
<p>Gullah Geechee Biz · Local monitor · No third-party services</p>
<p>Tracker: localhost:8766 · Monitor: localhost:8767</p>
</div>
</div>

<script>
async function runAudit() {{
    const div = document.getElementById('action-result');
    div.style.display = 'block';
    div.innerHTML = 'Running SEO audit...';
    const resp = await fetch('/api/run-audit');
    const data = await resp.json();
    div.innerHTML = '<pre style="font-size:0.85em;color:#ccc;white-space:pre-wrap">' + (data.output || 'Done') + '</pre>';
}}
async function checkPages() {{
    const div = document.getElementById('action-result');
    div.style.display = 'block';
    div.innerHTML = 'Checking page health...';
    const resp = await fetch('/api/check-pages');
    const data = await resp.json();
    let html = '<table><tr><th>Page</th><th>Status</th><th>SEO</th></tr>';
    for (const [url, checks] of Object.entries(data)) {{
        const status = checks.status ? '✅' : '❌';
        const seo = (checks.has_title && checks.has_meta_desc) ? '✅' : '⚠️';
        html += '<tr><td style="font-size:0.8em">' + url.split('/').slice(2).join('/') + '</td><td>' + status + '</td><td>' + seo + '</td></tr>';
    }}
    html += '</table>';
    div.innerHTML = html;
}}
</script>
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
            return
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")


def main():
    init_db()
    
    print(f"📊 Gullah Geechee Biz — Site Monitor + Auto-SEO Engine")
    print(f"   Database: {DB_PATH}")
    print(f"   Listening on: http://localhost:{MONITOR_PORT}")
    print()
    print(f"   Endpoints:")
    print(f"     GET /track?page=/&ref=... — Tracking pixel")
    print(f"     GET /dashboard — Full monitor dashboard")
    print(f"     GET /api/stats — JSON stats")
    print(f"     GET /api/run-audit — Run SEO audit now")
    print(f"     GET /api/run-fix — Run auto-fix")
    print(f"     GET /api/check-pages — Check all page health")
    print()
    print(f"   Press Ctrl+C to stop")
    
    server = HTTPServer(("0.0.0.0", MONITOR_PORT), MonitorHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down...")
        server.shutdown()


if __name__ == "__main__":
    main()
