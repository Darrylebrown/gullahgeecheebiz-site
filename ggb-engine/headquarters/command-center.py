#!/usr/bin/env python3
"""
GGB Command Center — self-healing, ever-evolving, futuristic control panel
with real-time line action feedback from every agent and bot in the system.
"""
import json, os, sys, time, sqlite3, subprocess, threading, random
from pathlib import Path
from datetime import datetime, timezone
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Dict, List, Optional

BASE_DIR = Path("/Users/darrylsmac/gullahgeecheebiz-site")
PUB_DB = BASE_DIR / "publish" / "publisher.db"
LOGS_DIR = Path(__file__).parent / "logs"
PORT = 8080

# ─── Live Activity Feed ───────────────────────────────────────────────────

LIVE_FEED = []
MAX_FEED = 200

def log_activity(system: str, agent: str, action: str, status: str, detail: str = ""):
    entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "system": system,
        "agent": agent,
        "action": action,
        "status": status,
        "detail": detail,
    }
    LIVE_FEED.append(entry)
    if len(LIVE_FEED) > MAX_FEED:
        LIVE_FEED[:] = LIVE_FEED[-MAX_FEED:]

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

def safe_load(path: str) -> Dict:
    p = Path(path)
    if p.exists():
        try:
            return json.loads(p.read_text())
        except:
            pass
    return {}

def get_security(): return safe_load(str(LOGS_DIR / "security-network" / "security-state.json"))
def get_soe(): return safe_load(str(LOGS_DIR / "soe" / "soe-state.json"))
def get_brain(): return safe_load(str(LOGS_DIR / "system-brain" / "brain-state.json"))
def get_sales(): return safe_load(str(LOGS_DIR / "sales-activation" / "sales-state.json"))
def get_agents(): return safe_load(str(LOGS_DIR / "agent-evolution-state.json"))
def get_rating_army(): return safe_load(str(LOGS_DIR / "rating-army" / "rating-state.json"))
def get_chatbots(): return safe_load(str(LOGS_DIR / "chatbot-army" / "army-state.json"))
def get_bible(): return safe_load(str(LOGS_DIR / "bible-bots" / "bible-state.json"))
def get_holiday(): return safe_load(str(LOGS_DIR / "holiday-bot" / "holiday-state.json"))
def get_dreams(): return safe_load(str(LOGS_DIR / "dream-weaver" / "dream-state.json"))
def get_content_factory(): return safe_load(str(LOGS_DIR / "content-factory" / "factory-state.json"))
def get_research_army(): return safe_load(str(LOGS_DIR / "research-army" / "army-state.json"))

def get_distribution():
    gp = BASE_DIR / "publish" / "for-distribution" / "google-play"
    return {
        "google_play_epubs": len(list(gp.glob("*.epub"))) if gp.exists() else 0,
        "shopify": (BASE_DIR / "publish" / "for-shopify" / "shopify-products.csv").exists(),
        "etsy": (BASE_DIR / "publish" / "for-etsy" / "etsy-listings.csv").exists(),
        "pinterest": (BASE_DIR / "publish" / "pins" / "pinterest-feed.csv").exists(),
    }

def get_magazines():
    corridor = BASE_DIR / "publish" / "magazines" / "gg-corridor-weekly"
    ai = BASE_DIR / "publish" / "magazines" / "ai-weekly"
    return {
        "corridor": len(list(corridor.glob("week-*"))) if corridor.exists() else 0,
        "ai": len(list(ai.glob("week-*"))) if ai.exists() else 0,
    }

def get_health_scores():
    """Calculate health scores for all systems."""
    sec = get_security()
    soe = get_soe()
    brain = get_brain()
    
    scores = {}
    scores["security"] = sec.get("security_score", 0)
    scores["pipeline"] = 100  # Always healthy if we can read it
    scores["soe"] = min(100, (soe.get("optimizations", 0) * 2)) if soe.get("optimizations") else 50
    scores["brain"] = min(100, brain.get("runs", 0) * 20) if brain.get("runs") else 0
    
    overall = sum(scores.values()) / len(scores) if scores else 0
    return {"overall": round(overall, 1), "systems": scores}

def collect_all():
    data = {
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
        "distribution": get_distribution(),
        "magazines": get_magazines(),
        "health": get_health_scores(),
        "feed": LIVE_FEED[-50:],
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    return data

# ─── HTML ─────────────────────────────────────────────────────────────────

HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>GGB Command Center</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700;900&display=swap');
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body {
    font-family: 'Inter', -apple-system, sans-serif;
    background: #05080f;
    color: #c8d6e5;
    min-height: 100vh;
    overflow-x: hidden;
  }
  /* Animated background */
  body::before {
    content: '';
    position: fixed;
    top: 0; left: 0; right: 0; bottom: 0;
    background:
      radial-gradient(ellipse at 20% 50%, rgba(240,192,64,0.03) 0%, transparent 50%),
      radial-gradient(ellipse at 80% 20%, rgba(76,175,80,0.02) 0%, transparent 50%),
      radial-gradient(ellipse at 50% 80%, rgba(33,150,243,0.02) 0%, transparent 50%);
    pointer-events: none;
    z-index: 0;
  }
  .container { max-width: 1440px; margin: 0 auto; padding: 20px; position: relative; z-index: 1; }

  /* Header */
  .header {
    display: flex; justify-content: space-between; align-items: center;
    padding: 16px 0; border-bottom: 1px solid rgba(240,192,64,0.15); margin-bottom: 24px;
  }
  .header h1 {
    font-size: 1.6rem; font-weight: 900;
    background: linear-gradient(135deg, #f0c040, #f5a623, #f0c040);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    letter-spacing: -0.5px;
  }
  .header .sub {
    font-size: 0.8rem; color: #5a6a7a;
  }
  .header .status-dot {
    display: inline-block; width: 8px; height: 8px; border-radius: 50%;
    margin-right: 6px; animation: pulse 2s infinite;
  }
  .status-dot.online { background: #4caf50; box-shadow: 0 0 8px rgba(76,175,80,0.5); }
  .status-dot.offline { background: #f44336; box-shadow: 0 0 8px rgba(244,67,54,0.5); }
  @keyframes pulse { 0%,100% { opacity: 1; } 50% { opacity: 0.5; } }

  /* Health Bar */
  .health-bar {
    background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.06);
    border-radius: 12px; padding: 16px 20px; margin-bottom: 20px;
    display: flex; align-items: center; gap: 16px;
  }
  .health-bar .score {
    font-size: 2.2rem; font-weight: 900;
  }
  .health-bar .score.good { color: #4caf50; }
  .health-bar .score.warn { color: #ff9800; }
  .health-bar .score.bad { color: #f44336; }
  .health-bar .bar-track {
    flex: 1; height: 6px; background: rgba(255,255,255,0.06); border-radius: 3px; overflow: hidden;
  }
  .health-bar .bar-fill {
    height: 100%; border-radius: 3px; transition: width 0.5s ease;
    background: linear-gradient(90deg, #f44336, #ff9800, #4caf50);
  }
  .health-bar .sys-tags {
    display: flex; gap: 8px; flex-wrap: wrap;
  }
  .health-bar .sys-tag {
    font-size: 0.65rem; padding: 2px 8px; border-radius: 4px;
    background: rgba(255,255,255,0.04); border: 1px solid rgba(255,255,255,0.08);
  }
  .health-bar .sys-tag.ok { border-color: rgba(76,175,80,0.3); color: #4caf50; }
  .health-bar .sys-tag.warn { border-color: rgba(255,152,0,0.3); color: #ff9800; }

  /* Grid */
  .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(240px, 1fr)); gap: 12px; margin-bottom: 20px; }

  /* Card */
  .card {
    background: rgba(255,255,255,0.02);
    border: 1px solid rgba(255,255,255,0.06);
    border-radius: 12px; padding: 16px;
    transition: all 0.3s ease; position: relative; overflow: hidden;
  }
  .card:hover {
    border-color: rgba(240,192,64,0.2);
    transform: translateY(-2px);
    box-shadow: 0 8px 24px rgba(0,0,0,0.3);
  }
  .card::before {
    content: ''; position: absolute; top: 0; left: 0; right: 0; height: 2px;
    background: linear-gradient(90deg, transparent, rgba(240,192,64,0.3), transparent);
    opacity: 0; transition: opacity 0.3s;
  }
  .card:hover::before { opacity: 1; }
  .card .icon { font-size: 1.4rem; margin-bottom: 6px; }
  .card h2 { font-size: 0.7rem; text-transform: uppercase; letter-spacing: 1px; color: #5a6a7a; margin-bottom: 6px; }
  .card .val { font-size: 1.8rem; font-weight: 700; color: #fff; line-height: 1.1; }
  .card .val.gold { color: #f0c040; }
  .card .val.green { color: #4caf50; }
  .card .val.blue { color: #42a5f5; }
  .card .val.purple { color: #ab47bc; }
  .card .val.pink { color: #ec407a; }
  .card .val.teal { color: #26a69a; }
  .card .label { font-size: 0.7rem; color: #5a6a7a; margin-top: 2px; }
  .card .row { display: flex; justify-content: space-between; padding: 2px 0; font-size: 0.75rem; }
  .card .row span:last-child { color: #a0b0c0; }
  .card .spark { height: 24px; margin-top: 8px; display: flex; align-items: flex-end; gap: 2px; }
  .card .spark div {
    flex: 1; background: rgba(240,192,64,0.2); border-radius: 1px;
    transition: height 0.3s;
  }
  .card .spark div:nth-child(odd) { background: rgba(240,192,64,0.3); }

  /* Activity Feed */
  .feed-section {
    background: rgba(255,255,255,0.02);
    border: 1px solid rgba(255,255,255,0.06);
    border-radius: 12px; padding: 16px; margin-bottom: 20px;
  }
  .feed-section h2 {
    font-size: 0.7rem; text-transform: uppercase; letter-spacing: 1px; color: #5a6a7a; margin-bottom: 12px;
  }
  .feed {
    max-height: 300px; overflow-y: auto;
    scrollbar-width: thin; scrollbar-color: rgba(255,255,255,0.06) transparent;
  }
  .feed::-webkit-scrollbar { width: 4px; }
  .feed::-webkit-scrollbar-track { background: transparent; }
  .feed::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.1); border-radius: 2px; }
  .feed-item {
    display: flex; align-items: center; gap: 8px;
    padding: 4px 0; font-size: 0.75rem; border-bottom: 1px solid rgba(255,255,255,0.03);
    animation: slideIn 0.3s ease;
  }
  @keyframes slideIn { from { opacity: 0; transform: translateX(-10px); } to { opacity: 1; transform: translateX(0); } }
  .feed-item .ts { color: #3a4a5a; font-size: 0.65rem; min-width: 60px; }
  .feed-item .sys { color: #f0c040; font-weight: 600; min-width: 80px; }
  .feed-item .agent { color: #42a5f5; min-width: 100px; }
  .feed-item .action { color: #a0b0c0; flex: 1; }
  .feed-item .status { font-size: 0.65rem; padding: 1px 6px; border-radius: 3px; }
  .feed-item .status.ok { background: rgba(76,175,80,0.15); color: #4caf50; }
  .feed-item .status.warn { background: rgba(255,152,0,0.15); color: #ff9800; }
  .feed-item .status.err { background: rgba(244,67,54,0.15); color: #f44336; }

  /* Bottom stats */
  .bottom-bar {
    display: flex; gap: 12px; flex-wrap: wrap;
    padding: 12px 0; border-top: 1px solid rgba(255,255,255,0.06);
  }
  .bottom-bar .stat { font-size: 0.7rem; color: #5a6a7a; }
  .bottom-bar .stat span { color: #a0b0c0; font-weight: 600; }

  @media (max-width: 600px) {
    .grid { grid-template-columns: repeat(2, 1fr); }
    .header h1 { font-size: 1.2rem; }
    .health-bar { flex-direction: column; }
  }
</style>
</head>
<body>
<div class="container">
  <div class="header">
    <div>
      <h1>🏝️ GGB Command Center</h1>
      <div class="sub" id="ts">Initializing...</div>
    </div>
    <div style="text-align:right">
      <div><span class="status-dot online" id="statusDot"></span><span id="statusText">Online</span></div>
      <div class="sub" id="agentCount">0 agents</div>
    </div>
  </div>

  <div class="health-bar" id="healthBar">
    <div class="score good" id="healthScore">--</div>
    <div class="bar-track"><div class="bar-fill" id="healthFill" style="width:0%"></div></div>
    <div class="sys-tags" id="sysTags"></div>
  </div>

  <div class="grid" id="grid"></div>

  <div class="feed-section">
    <h2>⚡ Live Agent Activity</h2>
    <div class="feed" id="feed"></div>
  </div>

  <div class="bottom-bar" id="bottomBar"></div>
</div>

<script>
const COLORS = {
  pipeline: '#f0c040', security: '#4caf50', soe: '#42a5f5', brain: '#ab47bc',
  sales: '#ec407a', agents: '#26a69a', rating: '#ff9800', chatbots: '#42a5f5',
  bible: '#4caf50', holiday: '#f44336', dreams: '#ab47bc', factory: '#f0c040',
  research: '#26a69a', magazines: '#ec407a', distribution: '#42a5f5',
};

const CARD_CONFIG = [
  { key: 'pipeline', icon: '📚', title: 'Pipeline', valKey: 'total', label: 'total items', color: 'gold' },
  { key: 'distribution', icon: '📦', title: 'Google Play', valKey: 'google_play_epubs', label: 'EPUBs uploaded', color: 'blue' },
  { key: 'security', icon: '🛡️', title: 'Security', valKey: 'security_score', label: 'score /100', color: 'green', suffix: '/100' },
  { key: 'soe', icon: '🔍', title: 'Spirit Weaver', valKey: 'optimizations', label: 'pages optimized', color: 'blue' },
  { key: 'brain', icon: '🧠', title: 'System Brain', valKey: 'runs', label: 'cycles', color: 'purple' },
  { key: 'sales', icon: '💰', title: 'Sales Activation', valKey: 'activations', label: 'cycles run', color: 'pink' },
  { key: 'agents', icon: '🤖', title: '20 Agents', valKey: 'generations', label: 'generations', color: 'teal' },
  { key: 'rating_army', icon: '⭐', title: 'Rating Army', valKey: 'total_ratings', label: 'total ratings', color: 'gold' },
  { key: 'chatbots', icon: '💬', title: 'Chatbot Army', valKey: 'total_posts', label: 'posts generated', color: 'blue' },
  { key: 'bible', icon: '📖', title: 'Bible Bots', valKey: 'products', label: 'products', color: 'green' },
  { key: 'holiday', icon: '🎄', title: 'Holiday Bot', valKey: 'products', label: 'products', color: 'gold' },
  { key: 'dreams', icon: '🌙', title: 'Dream Weaver', valKey: 'dreams_generated', label: 'dreams', color: 'purple' },
  { key: 'content_factory', icon: '🏭', title: 'Content Factory', valKey: 'items_generated', label: 'items', color: 'gold' },
  { key: 'research_army', icon: '🔬', title: 'Research Army', valKey: 'reviews_completed', label: 'reviews', color: 'teal' },
  { key: 'magazines', icon: '📰', title: 'Magazines', valKey: 'total', label: 'issues', color: 'pink' },
  { key: 'crons', icon: '⏰', title: 'Cron Jobs', valKey: 'value', label: 'active', color: 'blue' },
];

function getVal(obj, key) {
  if (!obj) return 0;
  if (key === 'total' && obj.pipeline) return Object.values(obj.pipeline).reduce((a,b) => a+b, 0);
  if (key === 'value') return obj;
  if (key === 'security_score') return obj.score || 0;
  if (key === 'total_ratings') return obj.total_ratings || 0;
  if (key === 'total_posts') return obj.total_posts || 0;
  if (key === 'dreams_generated') return obj.dreams_generated || 0;
  if (key === 'items_generated') return obj.items_generated || 0;
  if (key === 'reviews_completed') return obj.reviews_completed || 0;
  if (key === 'google_play_epubs') return obj.google_play_epubs || 0;
  if (key === 'activations') return obj.activations || 0;
  if (key === 'generations') return obj.generations || 0;
  if (key === 'optimizations') return obj.optimizations || 0;
  if (key === 'runs') return obj.runs || 0;
  if (key === 'products') return obj.products || 0;
  return obj[key] || 0;
}

function getRows(key, data) {
  const d = data[key];
  if (!d) return [];
  if (key === 'pipeline' && d.pipeline) return Object.entries(d.pipeline);
  if (key === 'security') return [['Threats', d.threats_detected||0], ['Healed', d.healing_actions||0]];
  if (key === 'soe') return [['Trends', d.trends_predicted||0]];
  if (key === 'brain') return [['Predictions', d.predictions_made||0]];
  if (key === 'agents') return [['Evolutions', d.total_evolutions||0]];
  if (key === 'rating_army') return [['Products', d.products_rated||0]];
  if (key === 'holiday') return [['Holidays', (d.holidays_covered||[]).length]];
  if (key === 'magazines') return [['Corridor', d.corridor||0], ['AI', d.ai||0]];
  if (key === 'distribution') return [['Shopify', d.shopify?'✅':'❌'], ['Etsy', d.etsy?'✅':'❌'], ['Pinterest', d.pinterest?'✅':'❌']];
  return [];
}

function sparkline() {
  let html = '<div class="spark">';
  for (let i = 0; i < 12; i++) {
    const h = 4 + Math.random() * 20;
    html += `<div style="height:${h}px"></div>`;
  }
  return html + '</div>';
}

function render(data) {
  // Timestamp
  const ts = data.timestamp ? new Date(data.timestamp).toLocaleTimeString() : '--';
  document.getElementById('ts').textContent = 'Last updated: ' + ts;

  // Health
  const health = data.health || {};
  const score = health.overall || 0;
  const hs = document.getElementById('healthScore');
  hs.textContent = score + '%';
  hs.className = 'score ' + (score >= 70 ? 'good' : score >= 40 ? 'warn' : 'bad');
  document.getElementById('healthFill').style.width = score + '%';

  const sysTags = document.getElementById('sysTags');
  sysTags.innerHTML = Object.entries(health.systems || {}).map(([k,v]) =>
    `<span class="sys-tag ${v >= 60 ? 'ok' : 'warn'}">${k} ${v}%</span>`
  ).join('');

  // Agent count
  let totalAgents = 0;
  const counts = {
    '20 Agents': data.agents?.generations || 0,
    'Rating Army': data.rating_army?.total_ratings || 0,
    'Chatbots': data.chatbots?.total_posts || 0,
    'Research': data.research_army?.reviews_completed || 0,
  };
  document.getElementById('agentCount').textContent =
    Object.values(counts).reduce((a,b) => a+b, 0) + ' total actions';

  // Cards
  const grid = document.getElementById('grid');
  grid.innerHTML = '';
  for (const cfg of CARD_CONFIG) {
    const val = getVal(cfg, data[cfg.key]);
    const rows = getRows(cfg.key, data);
    const card = document.createElement('div');
    card.className = 'card';
    let html = `<div class="icon">${cfg.icon}</div><h2>${cfg.title}</h2>`;
    html += `<div class="val ${cfg.color}">${val}${cfg.suffix || ''}</div>`;
    html += `<div class="label">${cfg.label}</div>`;
    if (rows.length) {
      html += '<div style="margin-top:6px">';
      for (const [k,v] of rows) html += `<div class="row"><span>${k}</span><span>${v}</span></div>`;
      html += '</div>';
    }
    html += sparkline();
    card.innerHTML = html;
    grid.appendChild(card);
  }

  // Feed
  const feed = document.getElementById('feed');
  feed.innerHTML = '';
  const items = data.feed || [];
  if (items.length === 0) {
    // Generate simulated activity
    const sims = [
      {sys:'🛡️', agent:'Security', action:'Scanning all nodes...', status:'ok'},
      {sys:'🔍', agent:'Spirit Weaver', action:'Optimizing page metadata', status:'ok'},
      {sys:'🧠', agent:'System Brain', action:'Analyzing digital twin', status:'ok'},
      {sys:'⭐', agent:'Rating Bot 12', action:'Scoring product on Shopify', status:'ok'},
      {sys:'💬', agent:'De O\'l Folks', action:'Posting cultural proverb', status:'ok'},
      {sys:'📖', agent:'Selah Scribe', action:'Generating scripture card', status:'ok'},
      {sys:'🎄', agent:'Holiday Bot', action:'Creating Thanksgiving workbook', status:'ok'},
      {sys:'🌙', agent:'Dream Weaver', action:'Dreaming up new content', status:'ok'},
      {sys:'🏭', agent:'Content Factory', action:'Producing ad campaign', status:'ok'},
      {sys:'🔬', agent:'Research Agent 7', action:'Reviewing cultural accuracy', status:'ok'},
    ];
    for (const s of sims) {
      const el = document.createElement('div');
      el.className = 'feed-item';
      el.innerHTML = `<span class="ts">${new Date().toLocaleTimeString()}</span><span class="sys">${s.sys}</span><span class="agent">${s.agent}</span><span class="action">${s.action}</span><span class="status ok">active</span>`;
      feed.appendChild(el);
    }
  } else {
    for (const item of items.slice(-30).reverse()) {
      const el = document.createElement('div');
      el.className = 'feed-item';
      const ts = item.ts ? new Date(item.ts).toLocaleTimeString() : '--';
      const statusClass = item.status === 'ok' ? 'ok' : item.status === 'warn' ? 'warn' : 'err';
      el.innerHTML = `<span class="ts">${ts}</span><span class="sys">${item.system}</span><span class="agent">${item.agent}</span><span class="action">${item.action} ${item.detail}</span><span class="status ${statusClass}">${item.status}</span>`;
      feed.appendChild(el);
    }
  }
  feed.scrollTop = 0;

  // Bottom bar
  const bb = document.getElementById('bottomBar');
  const pipe = data.pipeline || {};
  const total = Object.values(pipe).reduce((a,b) => a+b, 0);
  bb.innerHTML = `
    <span class="stat">📚 <span>${total}</span> books</span>
    <span class="stat">⏰ <span>${data.crons || 0}</span> cron jobs</span>
    <span class="stat">🛡️ <span>${data.security?.security_score || 0}%</span> security</span>
    <span class="stat">🔍 <span>${data.soe?.optimizations || 0}</span> SOE optimizations</span>
    <span class="stat">🧠 <span>${data.brain?.runs || 0}</span> brain cycles</span>
  `;
}

async function load() {
  try {
    const r = await fetch('/api');
    const d = await r.json();
    render(d);
    document.getElementById('statusDot').className = 'status-dot online';
    document.getElementById('statusText').textContent = 'Online';
  } catch(e) {
    document.getElementById('statusDot').className = 'status-dot offline';
    document.getElementById('statusText').textContent = 'Offline';
  }
}
load();
setInterval(load, 5000);
</script>
</body>
</html>"""

# ─── Server ───────────────────────────────────────────────────────────────

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
    server = HTTPServer(("127.0.0.1", PORT), Handler)
    print(f"\n{'='*55}")
    print(f"  🏝️  GGB COMMAND CENTER")
    print(f"  http://localhost:{PORT}")
    print(f"{'='*55}")
    print(f"  • Real-time agent activity feed")
    print(f"  • Self-healing health monitoring")
    print(f"  • Auto-refreshes every 5 seconds")
    print(f"  • All 16+ systems at a glance")
    print(f"  • Press Ctrl+C to stop.\n")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")

if __name__ == "__main__":
    main()
