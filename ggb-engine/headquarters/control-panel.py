#!/usr/bin/env python3
"""
GGB Control Panel — designed by the AI Think Tank. A single dashboard
that shows every system, agent, cron job, and metric in real-time.
"""
import json, os, sys, time, sqlite3, subprocess, threading
from pathlib import Path
from datetime import datetime, timezone
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Dict, List, Optional

BASE_DIR = Path("/Users/darrylsmac/gullahgeecheebiz-site")
PUB_DB = BASE_DIR / "publish" / "publisher.db"
LOGS_DIR = Path(__file__).parent / "logs"
PORT = 8080

# ─── Data Collectors ──────────────────────────────────────────────────────

def get_pipeline():
    try:
        conn = sqlite3.connect(str(PUB_DB))
        states = conn.execute("SELECT state, COUNT(*) FROM manifests GROUP BY state ORDER BY state").fetchall()
        conn.close()
        return {s[0]: s[1] for s in states}
    except:
        return {"error": "Cannot read pipeline"}

def get_cron_count():
    try:
        r = subprocess.run(["crontab", "-l"], capture_output=True, text=True, timeout=5)
        lines = [l for l in r.stdout.strip().split("\n") if l and not l.startswith("#")]
        return len(lines)
    except:
        return 0

def get_security():
    p = LOGS_DIR / "security-network" / "security-state.json"
    if p.exists():
        try:
            return json.loads(p.read_text())
        except:
            pass
    return {}

def get_soe():
    p = LOGS_DIR / "soe" / "soe-state.json"
    if p.exists():
        try:
            return json.loads(p.read_text())
        except:
            pass
    return {}

def get_brain():
    p = LOGS_DIR / "system-brain" / "brain-state.json"
    if p.exists():
        try:
            return json.loads(p.read_text())
        except:
            pass
    return {}

def get_sales():
    p = LOGS_DIR / "sales-activation" / "sales-state.json"
    if p.exists():
        try:
            return json.loads(p.read_text())
        except:
            pass
    return {}

def get_agents():
    p = LOGS_DIR / "agent-evolution-state.json"
    if p.exists():
        try:
            return json.loads(p.read_text())
        except:
            pass
    return {}

def get_rating_army():
    p = LOGS_DIR / "rating-army" / "rating-state.json"
    if p.exists():
        try:
            return json.loads(p.read_text())
        except:
            pass
    return {}

def get_chatbots():
    p = LOGS_DIR / "chatbot-army" / "army-state.json"
    if p.exists():
        try:
            return json.loads(p.read_text())
        except:
            pass
    return {}

def get_bible():
    p = LOGS_DIR / "bible-bots" / "bible-state.json"
    if p.exists():
        try:
            return json.loads(p.read_text())
        except:
            pass
    return {}

def get_holiday():
    p = LOGS_DIR / "holiday-bot" / "holiday-state.json"
    if p.exists():
        try:
            return json.loads(p.read_text())
        except:
            pass
    return {}

def get_dreams():
    p = LOGS_DIR / "dream-weaver" / "dream-state.json"
    if p.exists():
        try:
            return json.loads(p.read_text())
        except:
            pass
    return {}

def get_content_factory():
    p = LOGS_DIR / "content-factory" / "factory-state.json"
    if p.exists():
        try:
            return json.loads(p.read_text())
        except:
            pass
    return {}

def get_research_army():
    p = LOGS_DIR / "research-army" / "army-state.json"
    if p.exists():
        try:
            return json.loads(p.read_text())
        except:
            pass
    return {}

def get_nss():
    p = LOGS_DIR / "soe" / "nss-optimizer-state.json"
    if p.exists():
        try:
            return json.loads(p.read_text())
        except:
            pass
    return {}

def get_distribution():
    gp = BASE_DIR / "publish" / "for-distribution" / "google-play"
    return {
        "google_play_epubs": len(list(gp.glob("*.epub"))) if gp.exists() else 0,
        "shopify_csv": (BASE_DIR / "publish" / "for-shopify" / "shopify-products.csv").exists(),
        "etsy_csv": (BASE_DIR / "publish" / "for-etsy" / "etsy-listings.csv").exists(),
        "pinterest_csv": (BASE_DIR / "publish" / "pins" / "pinterest-feed.csv").exists(),
    }

def get_magazines():
    corridor = BASE_DIR / "publish" / "magazines" / "gg-corridor-weekly"
    ai = BASE_DIR / "publish" / "magazines" / "ai-weekly"
    return {
        "corridor_issues": len(list(corridor.glob("week-*"))) if corridor.exists() else 0,
        "ai_issues": len(list(ai.glob("week-*"))) if ai.exists() else 0,
    }

def collect_all():
    return {
        "pipeline": get_pipeline(),
        "crons": get_cron_count(),
        "security": get_security(),
        "soe": get_soe(),
        "brain": get_brain(),
        "sales": get_sales(),
        "agents": get_agents(),
        "rating_army": get_rating_army(),
        "chatbots": get_chatbots(),
        "bible": get_bible(),
        "holiday": get_holiday(),
        "dreams": get_dreams(),
        "content_factory": get_content_factory(),
        "research_army": get_research_army(),
        "nss": get_nss(),
        "distribution": get_distribution(),
        "magazines": get_magazines(),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

# ─── HTTP Server ──────────────────────────────────────────────────────────

HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>GGB Control Panel</title>
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #0a0a0a; color: #e0e0e0; padding: 20px; }
  h1 { font-size: 1.5rem; margin-bottom: 4px; color: #f0c040; }
  .sub { color: #888; font-size: 0.85rem; margin-bottom: 20px; }
  .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 12px; }
  .card { background: #1a1a1a; border: 1px solid #2a2a2a; border-radius: 8px; padding: 14px; }
  .card h2 { font-size: 0.9rem; color: #f0c040; margin-bottom: 8px; text-transform: uppercase; letter-spacing: 0.5px; }
  .card .val { font-size: 1.8rem; font-weight: 700; color: #fff; }
  .card .label { font-size: 0.75rem; color: #888; }
  .card .row { display: flex; justify-content: space-between; padding: 2px 0; font-size: 0.8rem; }
  .card .row span:last-child { color: #ccc; }
  .ok { color: #4caf50; }
  .warn { color: #ff9800; }
  .err { color: #f44336; }
  .gold { color: #f0c040; }
  .refresh { text-align: center; margin-top: 16px; font-size: 0.8rem; color: #666; }
  .refresh a { color: #f0c040; text-decoration: none; }
  .refresh a:hover { text-decoration: underline; }
  .bar { height: 4px; border-radius: 2px; margin-top: 6px; background: #2a2a2a; overflow: hidden; }
  .bar-fill { height: 100%; border-radius: 2px; transition: width 0.5s; }
</style>
</head>
<body>
<h1>🏝️ GGB Control Panel</h1>
<div class="sub" id="ts">Loading...</div>
<div class="grid" id="grid"></div>
<div class="refresh">Auto-refreshes every 30s &middot; <a href="/">Refresh now</a></div>
<script>
async function load() {
  const r = await fetch('/api');
  const d = await r.json();
  document.getElementById('ts').textContent = 'Updated ' + new Date(d.timestamp).toLocaleTimeString();
  const g = document.getElementById('grid');
  g.innerHTML = '';

  const cards = [];

  // Pipeline
  const pipe = d.pipeline || {};
  const total = Object.values(pipe).reduce((a,b) => a+b, 0);
  cards.push({ title: '📚 Pipeline', rows: Object.entries(pipe).map(([k,v]) => [k, v]), val: total, label: 'total items' });

  // Distribution
  const dist = d.distribution || {};
  cards.push({ title: '📦 Google Play', val: dist.google_play_epubs || 0, label: 'EPUBs uploaded' });

  // Security
  const sec = d.security || {};
  cards.push({ title: '🛡️ Security', val: (sec.security_score || 0) + '/100', label: 'score', rows: [['Threats', sec.threats_detected || 0], ['Healed', sec.healing_actions || 0]] });

  // SOE
  const soe = d.soe || {};
  cards.push({ title: '🔍 Spirit Weaver', val: soe.optimizations || 0, label: 'pages optimized', rows: [['Trends', soe.trends_predicted || 0]] });

  // Brain
  const brain = d.brain || {};
  cards.push({ title: '🧠 System Brain', val: brain.runs || 0, label: 'cycles', rows: [['Predictions', brain.predictions_made || 0]] });

  // Sales
  const sales = d.sales || {};
  cards.push({ title: '💰 Sales Activation', val: sales.activations || 0, label: 'cycles run' });

  // Agents
  const agents = d.agents || {};
  cards.push({ title: '🤖 20 Agents', val: agents.generations || 0, label: 'generations', rows: [['Evolutions', agents.total_evolutions || 0]] });

  // Rating Army
  const rating = d.rating_army || {};
  cards.push({ title: '⭐ Rating Army', val: rating.total_ratings || 0, label: 'total ratings', rows: [['Products Rated', rating.products_rated || 0]] });

  // Chatbots
  const chat = d.chatbots || {};
  cards.push({ title: '🤖 Chatbot Army', val: chat.total_posts || 0, label: 'posts generated' });

  // Bible Bots
  const bible = d.bible || {};
  cards.push({ title: '📖 Bible Bots', val: bible.products || 0, label: 'products' });

  // Holiday Bot
  const holi = d.holiday || {};
  cards.push({ title: '🎄 Holiday Bot', val: holi.products || 0, label: 'products', rows: [['Holidays', (holi.holidays_covered||[]).length]] });

  // Dreams
  const dreams = d.dreams || {};
  cards.push({ title: '🌙 Dream Weaver', val: dreams.dreams_generated || 0, label: 'dreams' });

  // Content Factory
  const cf = d.content_factory || {};
  cards.push({ title: '🏭 Content Factory', val: cf.items_generated || 0, label: 'items' });

  // Research Army
  const ra = d.research_army || {};
  cards.push({ title: '🔬 Research Army', val: ra.reviews_completed || 0, label: 'reviews' });

  // Magazines
  const mags = d.magazines || {};
  cards.push({ title: '📰 Magazines', val: (mags.corridor_issues||0) + (mags.ai_issues||0), label: 'issues', rows: [['Corridor', mags.corridor_issues||0], ['AI', mags.ai_issues||0]] });

  // Crons
  cards.push({ title: '⏰ Cron Jobs', val: d.crons || 0, label: 'active' });

  for (const c of cards) {
    const card = document.createElement('div');
    card.className = 'card';
    let html = `<h2>${c.title}</h2><div class="val">${c.val}</div><div class="label">${c.label}</div>`;
    if (c.rows) {
      html += '<div style="margin-top:8px">';
      for (const [k,v] of c.rows) {
        html += `<div class="row"><span>${k}</span><span>${v}</span></div>`;
      }
      html += '</div>';
    }
    card.innerHTML = html;
    g.appendChild(card);
  }
}
load();
setInterval(load, 30000);
</script>
</body>
</html>"""

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/api":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps(collect_all()).encode())
        else:
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(HTML.encode())

def main():
    server = HTTPServer(("0.0.0.0", PORT), Handler)
    print(f"\n{'='*55}")
    print(f"  🏝️  GGB CONTROL PANEL")
    print(f"  http://localhost:{PORT}")
    print(f"{'='*55}")
    print(f"  Open in your browser to see every system live.")
    print(f"  Auto-refreshes every 30 seconds.")
    print(f"  Press Ctrl+C to stop.\n")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")

if __name__ == "__main__":
    main()
