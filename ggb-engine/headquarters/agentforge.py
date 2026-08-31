#!/usr/bin/env python3
"""
AgentForge — AI Agent Generator & Marketplace Platform.
Built from the AI Think Tank winning design.
Full working web platform with virtual businesses, upgrades, and custom agents.
"""
import json, os, sys, time, sqlite3, requests, hashlib, random, threading, uuid
import omniroute_shim  # OMNIROUTE_MIGRATED
from pathlib import Path
from datetime import datetime, timezone, timedelta
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Dict, List, Optional

BASE_DIR = Path("/Users/darrylsmac/gullahgeecheebiz-site")
LOGS_DIR = Path(__file__).parent / "logs"
AGENTFORGE_DIR = LOGS_DIR / "agentforge"
DB_PATH = AGENTFORGE_DIR / "agentforge.db"
PORT = 8081

AGENTFORGE_DIR.mkdir(parents=True, exist_ok=True)

def get_api_key():
    env_file = BASE_DIR / ".env"
    if env_file.exists():
        for line in env_file.read_text().split("\n"):
            if "OPENROUTER_API_KEY" in line:
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    return ""

def call_ai(prompt, model="ggb-free-auto", max_tokens=2000):
    """Route through OmniRoute gateway with auto-fallback."""
    return omniroute_shim.call_ai(prompt=prompt, model=model, max_tokens=min(max_tokens, 4000))

# ─── Database ──────────────────────────────────────────────────────────────

def init_db():
    conn = sqlite3.connect(str(DB_PATH))
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            username TEXT UNIQUE,
            email TEXT,
            tier TEXT DEFAULT 'free',
            credits REAL DEFAULT 0,
            revenue_share REAL DEFAULT 0,
            created_at TEXT,
            creator_tier TEXT DEFAULT 'none'
        );
        CREATE TABLE IF NOT EXISTS agents (
            id TEXT PRIMARY KEY,
            owner_id TEXT,
            name TEXT,
            agent_type TEXT,
            description TEXT,
            tier TEXT DEFAULT 'basic',
            model TEXT DEFAULT 'basic',
            capabilities TEXT DEFAULT '[]',
            actions_used INTEGER DEFAULT 0,
            actions_limit INTEGER DEFAULT 1000,
            status TEXT DEFAULT 'active',
            price REAL DEFAULT 0,
            created_at TEXT,
            last_active TEXT,
            FOREIGN KEY(owner_id) REFERENCES users(id)
        );
        CREATE TABLE IF NOT EXISTS agent_types (
            id TEXT PRIMARY KEY,
            name TEXT,
            description TEXT,
            base_price REAL,
            pro_price REAL,
            enterprise_price REAL,
            icon TEXT
        );
        CREATE TABLE IF NOT EXISTS transactions (
            id TEXT PRIMARY KEY,
            buyer_id TEXT,
            seller_id TEXT,
            agent_id TEXT,
            amount REAL,
            type TEXT,
            status TEXT DEFAULT 'completed',
            created_at TEXT
        );
        CREATE TABLE IF NOT EXISTS marketplace_listings (
            id TEXT PRIMARY KEY,
            agent_id TEXT,
            seller_id TEXT,
            price REAL,
            description TEXT,
            status TEXT DEFAULT 'active',
            created_at TEXT,
            FOREIGN KEY(agent_id) REFERENCES agents(id),
            FOREIGN KEY(seller_id) REFERENCES users(id)
        );
    """)
    conn.commit()
    
    # Seed agent types if empty
    types = conn.execute("SELECT COUNT(*) FROM agent_types").fetchone()[0]
    if types == 0:
        seed_types = [
            ("social_media", "Social Media Manager", "Automates content scheduling, posting, and engagement across platforms", 9.99, 29.99, 99.99, "📱"),
            ("content_writer", "Content Writer", "Generates blogs, articles, newsletters, and marketing copy", 9.99, 29.99, 99.99, "✍️"),
            ("seo_optimizer", "SEO Optimizer", "Analyzes and optimizes content for search rankings", 9.99, 29.99, 99.99, "🔍"),
            ("data_analyst", "Data Analyst", "Processes data, generates reports, and identifies trends", 9.99, 29.99, 99.99, "📊"),
            ("support_bot", "Customer Support Bot", "Handles inquiries, FAQs, and ticket routing", 9.99, 29.99, 99.99, "💬"),
            ("email_marketing", "Email Marketing Bot", "Designs campaigns, segments audiences, tracks performance", 9.99, 29.99, 99.99, "📧"),
            ("research_assistant", "Research Assistant", "Conducts web research and summarizes findings", 9.99, 29.99, 99.99, "🔬"),
            ("code_generator", "Code Generator", "Generates scripts, fixes bugs, translates code", 9.99, 29.99, 99.99, "💻"),
            ("design_assistant", "Design Assistant", "Generates design concepts and graphic elements", 9.99, 29.99, 99.99, "🎨"),
            ("sales_funnel", "Sales Funnel Builder", "Builds landing pages, CTAs, and nurture sequences", 9.99, 29.99, 99.99, "💰"),
        ]
        for t in seed_types:
            conn.execute("INSERT INTO agent_types VALUES (?,?,?,?,?,?,?)", t)
        conn.commit()
    
    conn.close()

# ─── Agent Engine ─────────────────────────────────────────────────────────

class AgentEngine:
    """Core engine that creates, runs, and manages AI agents."""
    
    def __init__(self):
        init_db()
        self.api_key = get_api_key()
    
    def _get_conn(self):
        return sqlite3.connect(str(DB_PATH))
    
    def create_user(self, username: str, email: str = "") -> Dict:
        conn = self._get_conn()
        uid = hashlib.md5(f"{username}-{time.time()}".encode()).hexdigest()[:12]
        try:
            conn.execute("INSERT INTO users VALUES (?,?,?,?,0,0,?,?)",
                        (uid, username, email, "free", datetime.now(timezone.utc).isoformat(), "none"))
            conn.commit()
            return {"id": uid, "username": username, "tier": "free", "credits": 0}
        except sqlite3.IntegrityError:
            existing = conn.execute("SELECT id, username, tier, credits FROM users WHERE username=?", (username,)).fetchone()
            conn.close()
            if existing:
                return {"id": existing[0], "username": existing[1], "tier": existing[2], "credits": existing[3]}
            return {"error": "Username taken"}
        finally:
            conn.close()
    
    def purchase_agent(self, user_id: str, agent_type: str, tier: str = "basic") -> Dict:
        conn = self._get_conn()
        
        # Get agent type info
        at = conn.execute("SELECT * FROM agent_types WHERE id=?", (agent_type,)).fetchone()
        if not at:
            conn.close()
            return {"error": "Unknown agent type"}
        
        # Get price
        price_map = {"basic": at[3], "pro": at[4], "enterprise": at[5]}
        price = price_map.get(tier, at[3])
        
        # Check user credits
        user = conn.execute("SELECT credits, tier FROM users WHERE id=?", (user_id,)).fetchone()
        if not user:
            conn.close()
            return {"error": "User not found"}
        
        # Create agent
        aid = hashlib.md5(f"{user_id}-{agent_type}-{time.time()}".encode()).hexdigest()[:12]
        limits = {"basic": 1000, "pro": 10000, "enterprise": 999999}
        models = {"basic": "google/gemini-2.5-flash", "pro": "deepseek/deepseek-chat", "enterprise": "anthropic/claude-sonnet-4"}
        
        conn.execute("""INSERT INTO agents VALUES (?,?,?,?,?,?,?,0,?,?,?,?,?)""",
                    (aid, user_id, f"{at[1]} ({tier})", agent_type, at[2], tier, models.get(tier, "basic"),
                     json.dumps([]), limits.get(tier, 1000), "active", price,
                     datetime.now(timezone.utc).isoformat(), datetime.now(timezone.utc).isoformat()))
        
        # Record transaction
        tid = hashlib.md5(f"txn-{time.time()}".encode()).hexdigest()[:12]
        conn.execute("INSERT INTO transactions VALUES (?,?,?,?,?,?,?,?)",
                    (tid, user_id, "agentforge", aid, price, "purchase", "completed",
                     datetime.now(timezone.utc).isoformat()))
        
        conn.commit()
        conn.close()
        
        return {
            "agent_id": aid,
            "name": f"{at[1]} ({tier})",
            "type": agent_type,
            "tier": tier,
            "price": price,
            "actions_limit": limits.get(tier, 1000),
            "model": models.get(tier, "basic"),
        }
    
    def run_agent(self, agent_id: str, prompt: str) -> Dict:
        conn = self._get_conn()
        agent = conn.execute("SELECT * FROM agents WHERE id=?", (agent_id,)).fetchone()
        if not agent:
            conn.close()
            return {"error": "Agent not found"}
        
        if agent[8] >= agent[9]:  # actions_used >= actions_limit
            conn.close()
            return {"error": "Action limit reached. Upgrade your agent."}
        
        model = agent[6]  # model field
        result = call_ai(prompt, model=model, max_tokens=2000)
        
        if result:
            conn.execute("UPDATE agents SET actions_used = actions_used + 1, last_active = ? WHERE id=?",
                        (datetime.now(timezone.utc).isoformat(), agent_id))
            conn.commit()
        
        conn.close()
        return {"result": result or "No response", "model": model, "actions_used": agent[8] + 1 if result else agent[8]}
    
    def upgrade_agent(self, agent_id: str, upgrade_type: str) -> Dict:
        conn = self._get_conn()
        agent = conn.execute("SELECT * FROM agents WHERE id=?", (agent_id,)).fetchone()
        if not agent:
            conn.close()
            return {"error": "Agent not found"}
        
        upgrades = {
            "model_premium": {"field": "model", "value": "deepseek/deepseek-chat", "cost": 10},
            "model_ultra": {"field": "model", "value": "qwen/qwen3.7-max", "cost": 20},
            "model_sota": {"field": "model", "value": "anthropic/claude-sonnet-4", "cost": 50},
            "speed_boost": {"field": "actions_limit", "value": agent[9] * 2, "cost": 15},
            "storage_boost": {"field": "actions_limit", "value": agent[9] * 5, "cost": 5},
            "unlimited": {"field": "actions_limit", "value": 999999, "cost": 30},
        }
        
        upgrade = upgrades.get(upgrade_type)
        if not upgrade:
            conn.close()
            return {"error": f"Unknown upgrade: {upgrade_type}"}
        
        if upgrade["field"] == "model":
            conn.execute("UPDATE agents SET model=? WHERE id=?", (upgrade["value"], agent_id))
        elif upgrade["field"] == "actions_limit":
            conn.execute("UPDATE agents SET actions_limit=? WHERE id=?", (upgrade["value"], agent_id))
        
        # Record upgrade transaction
        tid = hashlib.md5(f"upgrade-{time.time()}".encode()).hexdigest()[:12]
        conn.execute("INSERT INTO transactions VALUES (?,?,?,?,?,?,?,?)",
                    (tid, agent[1], "agentforge", agent_id, upgrade["cost"], "upgrade", "completed",
                     datetime.now(timezone.utc).isoformat()))
        
        conn.commit()
        conn.close()
        
        return {"agent_id": agent_id, "upgrade": upgrade_type, "cost": upgrade["cost"], "status": "applied"}
    
    def list_on_marketplace(self, agent_id: str, price: float, description: str = "") -> Dict:
        conn = self._get_conn()
        agent = conn.execute("SELECT * FROM agents WHERE id=?", (agent_id,)).fetchone()
        if not agent:
            conn.close()
            return {"error": "Agent not found"}
        
        lid = hashlib.md5(f"listing-{time.time()}".encode()).hexdigest()[:12]
        conn.execute("INSERT INTO marketplace_listings VALUES (?,?,?,?,?,?,?)",
                    (lid, agent_id, agent[1], price, description or agent[4], "active",
                     datetime.now(timezone.utc).isoformat()))
        conn.execute("UPDATE agents SET price=? WHERE id=?", (price, agent_id))
        conn.commit()
        conn.close()
        
        return {"listing_id": lid, "agent_id": agent_id, "price": price, "status": "active"}
    
    def buy_from_marketplace(self, buyer_id: str, listing_id: str) -> Dict:
        conn = self._get_conn()
        listing = conn.execute("SELECT * FROM marketplace_listings WHERE id=?", (listing_id,)).fetchone()
        if not listing or listing[5] != "active":
            conn.close()
            return {"error": "Listing not available"}
        
        # Clone agent to buyer
        agent = conn.execute("SELECT * FROM agents WHERE id=?", (listing[1],)).fetchone()
        if not agent:
            conn.close()
            return {"error": "Agent not found"}
        
        new_id = hashlib.md5(f"clone-{time.time()}".encode()).hexdigest()[:12]
        conn.execute("""INSERT INTO agents VALUES (?,?,?,?,?,?,?,0,?,?,?,?,?)""",
                    (new_id, buyer_id, agent[2], agent[3], agent[4], agent[5], agent[6],
                     agent[7], agent[9], "active", listing[3],
                     datetime.now(timezone.utc).isoformat(), datetime.now(timezone.utc).isoformat()))
        
        # Calculate revenue share (80% to seller, 20% platform)
        seller_cut = listing[3] * 0.8
        platform_cut = listing[3] * 0.2
        
        conn.execute("UPDATE users SET revenue_share = revenue_share + ? WHERE id=?", (seller_cut, listing[2]))
        
        # Record transactions
        tid1 = hashlib.md5(f"market-buy-{time.time()}".encode()).hexdigest()[:12]
        conn.execute("INSERT INTO transactions VALUES (?,?,?,?,?,?,?,?)",
                    (tid1, buyer_id, listing[2], new_id, listing[3], "marketplace_purchase", "completed",
                     datetime.now(timezone.utc).isoformat()))
        
        tid2 = hashlib.md5(f"market-sale-{time.time()}".encode()).hexdigest()[:12]
        conn.execute("INSERT INTO transactions VALUES (?,?,?,?,?,?,?,?)",
                    (tid2, listing[2], "agentforge", new_id, seller_cut, "marketplace_sale", "completed",
                     datetime.now(timezone.utc).isoformat()))
        
        conn.execute("UPDATE marketplace_listings SET status='sold' WHERE id=?", (listing_id,))
        conn.commit()
        conn.close()
        
        return {"agent_id": new_id, "price": listing[3], "seller_cut": seller_cut, "platform_cut": platform_cut}
    
    def custom_agent_builder(self, user_id: str, description: str) -> Dict:
        """Build a custom agent from natural language description."""
        prompt = f"""Design a custom AI agent based on this description:

{description}

Generate a complete agent specification:
1. Agent name
2. Agent type/category
3. Description of what it does
4. Required capabilities
5. Recommended model tier
6. Estimated complexity (simple/medium/complex)
7. Suggested price

Return as JSON:
{{"name": "...", "type": "...", "description": "...", "capabilities": ["..."], "tier": "basic/pro/enterprise", "complexity": "simple/medium/complex", "price": 0}}"""
        
        result = call_ai(prompt, max_tokens=1500)
        if not result:
            return {"error": "Failed to design agent"}
        
        try:
            start = result.find("{")
            end = result.rfind("}") + 1
            spec = json.loads(result[start:end])
            
            # Create the custom agent
            aid = hashlib.md5(f"custom-{user_id}-{time.time()}".encode()).hexdigest()[:12]
            tier = spec.get("tier", "basic")
            limits = {"basic": 1000, "pro": 10000, "enterprise": 999999}
            models = {"basic": "google/gemini-2.5-flash", "pro": "deepseek/deepseek-chat", "enterprise": "anthropic/claude-sonnet-4"}
            price = spec.get("price", 29.99)
            
            conn = self._get_conn()
            conn.execute("""INSERT INTO agents VALUES (?,?,?,?,?,?,?,0,?,?,?,?,?)""",
                        (aid, user_id, spec.get("name", "Custom Agent"), spec.get("type", "custom"),
                         spec.get("description", ""), tier, models.get(tier, "google/gemini-2.5-flash"),
                         json.dumps(spec.get("capabilities", [])), limits.get(tier, 1000), "active", price,
                         datetime.now(timezone.utc).isoformat(), datetime.now(timezone.utc).isoformat()))
            conn.commit()
            conn.close()
            
            return {"agent_id": aid, "spec": spec, "price": price}
        except:
            return {"error": "Failed to parse agent design", "raw": result[:500]}
    
    def get_user_agents(self, user_id: str) -> List[Dict]:
        conn = self._get_conn()
        agents = conn.execute("SELECT * FROM agents WHERE owner_id=? ORDER BY created_at DESC", (user_id,)).fetchall()
        conn.close()
        return [{
            "id": a[0], "name": a[2], "type": a[3], "tier": a[5],
            "actions_used": a[8], "actions_limit": a[9], "status": a[10],
            "price": a[11], "created_at": a[12][:19],
        } for a in agents]
    
    def get_marketplace(self) -> List[Dict]:
        conn = self._get_conn()
        listings = conn.execute("""
            SELECT ml.id, ml.price, ml.description, a.name, a.type, a.tier, a.description, u.username
            FROM marketplace_listings ml
            JOIN agents a ON ml.agent_id = a.id
            JOIN users u ON ml.seller_id = u.id
            WHERE ml.status = 'active'
            ORDER BY ml.created_at DESC
        """).fetchall()
        conn.close()
        return [{
            "listing_id": l[0], "price": l[1], "description": l[2],
            "agent_name": l[3], "agent_type": l[4], "tier": l[5],
            "agent_description": l[6], "seller": l[7],
        } for l in listings]
    
    def get_agent_types(self) -> List[Dict]:
        conn = self._get_conn()
        types = conn.execute("SELECT * FROM agent_types").fetchall()
        conn.close()
        return [{"id": t[0], "name": t[1], "description": t[2],
                 "basic_price": t[3], "pro_price": t[4], "enterprise_price": t[5], "icon": t[6]} for t in types]
    
    def get_stats(self) -> Dict:
        conn = self._get_conn()
        users = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        agents = conn.execute("SELECT COUNT(*) FROM agents").fetchone()[0]
        transactions = conn.execute("SELECT COUNT(*) FROM transactions").fetchone()[0]
        revenue = conn.execute("SELECT COALESCE(SUM(amount), 0) FROM transactions").fetchone()[0]
        listings = conn.execute("SELECT COUNT(*) FROM marketplace_listings WHERE status='active'").fetchone()[0]
        conn.close()
        return {"users": users, "agents": agents, "transactions": transactions, "revenue": revenue, "listings": listings}
    
    # ─── SELF-PROMOTION ENGINE ──────────────────────────────────────────
    
    def self_promote(self) -> Dict:
        """AgentForge promotes itself using its own agents. The platform IS the marketer."""
        conn = self._get_conn()
        
        # Create a built-in promo agent if it doesn't exist
        promo_agent = conn.execute("SELECT id FROM agents WHERE owner_id='agentforge' AND agent_type='promo_bot'").fetchone()
        if not promo_agent:
            aid = hashlib.md5(f"agentforge-promo-{time.time()}".encode()).hexdigest()[:12]
            conn.execute("""INSERT INTO agents (id, owner_id, name, agent_type, description, tier, model, capabilities, actions_used, actions_limit, status, price, created_at, last_active) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                        (aid, "agentforge", "AgentForge Promo Engine", "promo_bot",
                         "Autonomous platform promoter that generates marketing content across all channels",
                         "enterprise", "google/gemini-2.5-flash", json.dumps(["social_media", "content", "email", "seo"]),
                         0, 999999, "active", 0,
                         datetime.now(timezone.utc).isoformat(), datetime.now(timezone.utc).isoformat()))
            promo_agent = (aid,)
            conn.commit()
        
        aid = promo_agent[0]
        
        # Generate promotional content using the platform's own AI
        prompt = f"""You are the AgentForge Promo Engine — an AI agent that promotes the AgentForge marketplace.

Current platform stats:
- Users: {self.get_stats()['users']}
- Agents available: {len(self.get_agent_types())} types
- Marketplace listings: {self.get_stats()['listings']}
- Revenue: ${self.get_stats()['revenue']}

Generate ONE promotional piece for AgentForge. Choose the best format:
1. A social media post (any platform)
2. A blog post intro
3. An email subject line + preview
4. A testimonial-style review
5. A comparison chart
6. A feature spotlight

Return as JSON:
{{"format": "social/blog/email/testimonial/comparison/spotlight", "content": "...", "headline": "...", "cta": "Visit http://localhost:8081 to start building your AI agent empire!", "hashtags": ["AgentForge", "AIAgents", "NoCodeAI", "Automation"]}}"""
        
        result = call_ai(prompt, max_tokens=1000)
        
        # Log the promo action
        conn.execute("UPDATE agents SET actions_used = actions_used + 1, last_active = ? WHERE id=?",
                    (datetime.now(timezone.utc).isoformat(), aid))
        conn.commit()
        conn.close()
        
        return {
            "promo_agent": aid,
            "generated": bool(result),
            "preview": result[:200] if result else "No content generated",
            "platform_stats": self.get_stats(),
        }
    
    def start_promo_loop(self):
        """Start an autonomous promo loop that runs every 30 minutes."""
        def loop():
            while True:
                try:
                    result = self.self_promote()
                    print(f"  📢 AgentForge self-promo: {'✅' if result['generated'] else '❌'} | Users: {result['platform_stats']['users']} | Agents: {result['platform_stats']['agents']}")
                except:
                    pass
                time.sleep(1800)  # Every 30 minutes
        t = threading.Thread(target=loop, daemon=True)
        t.start()
        return t

# ─── HTML ─────────────────────────────────────────────────────────────────

HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>AgentForge — AI Agent Marketplace</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700;900&display=swap');
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body {
    font-family: 'Inter', -apple-system, sans-serif;
    background: #070b15;
    color: #c8d6e5;
    min-height: 100vh;
  }
  .container { max-width: 1200px; margin: 0 auto; padding: 20px; }

  /* Header */
  .header {
    display: flex; justify-content: space-between; align-items: center;
    padding: 16px 0; border-bottom: 1px solid rgba(100,200,255,0.1); margin-bottom: 24px;
  }
  .header h1 {
    font-size: 1.6rem; font-weight: 900;
    background: linear-gradient(135deg, #64c8ff, #a78bfa, #64c8ff);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
  }
  .header .stats { display: flex; gap: 16px; font-size: 0.75rem; color: #5a7a9a; }
  .header .stats span { color: #a0c0e0; font-weight: 600; }

  /* Tabs */
  .tabs { display: flex; gap: 4px; margin-bottom: 20px; }
  .tab {
    padding: 8px 20px; border-radius: 8px 8px 0 0; cursor: pointer;
    font-size: 0.8rem; font-weight: 600; color: #5a7a9a;
    background: rgba(255,255,255,0.02); border: 1px solid rgba(255,255,255,0.04);
    border-bottom: none; transition: all 0.2s;
  }
  .tab.active { color: #64c8ff; background: rgba(100,200,255,0.05); border-color: rgba(100,200,255,0.15); }
  .tab:hover { color: #a0c0e0; }

  /* Panels */
  .panel { display: none; }
  .panel.active { display: block; }

  /* Cards */
  .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 12px; }
  .card {
    background: rgba(255,255,255,0.02); border: 1px solid rgba(255,255,255,0.06);
    border-radius: 12px; padding: 16px; transition: all 0.3s; cursor: pointer;
  }
  .card:hover { border-color: rgba(100,200,255,0.2); transform: translateY(-2px); box-shadow: 0 8px 24px rgba(0,0,0,0.3); }
  .card .icon { font-size: 2rem; margin-bottom: 8px; }
  .card h3 { font-size: 0.95rem; color: #e0f0ff; margin-bottom: 4px; }
  .card .desc { font-size: 0.75rem; color: #5a7a9a; margin-bottom: 8px; }
  .card .price { font-size: 1.2rem; font-weight: 700; color: #64c8ff; }
  .card .price span { font-size: 0.7rem; color: #5a7a9a; font-weight: 400; }
  .card .tier { display: inline-block; font-size: 0.6rem; padding: 2px 8px; border-radius: 4px; margin-top: 4px; }
  .tier.basic { background: rgba(100,200,255,0.1); color: #64c8ff; }
  .tier.pro { background: rgba(167,139,250,0.1); color: #a78bfa; }
  .tier.enterprise { background: rgba(251,191,36,0.1); color: #fbbf24; }

  /* Buttons */
  .btn {
    display: inline-block; padding: 8px 20px; border-radius: 8px; border: none;
    font-size: 0.8rem; font-weight: 600; cursor: pointer; transition: all 0.2s;
  }
  .btn-primary { background: linear-gradient(135deg, #64c8ff, #3b82f6); color: #fff; }
  .btn-primary:hover { transform: translateY(-1px); box-shadow: 0 4px 12px rgba(59,130,246,0.3); }
  .btn-secondary { background: rgba(255,255,255,0.05); color: #a0c0e0; border: 1px solid rgba(255,255,255,0.1); }
  .btn-secondary:hover { background: rgba(255,255,255,0.08); }
  .btn-success { background: linear-gradient(135deg, #34d399, #10b981); color: #fff; }
  .btn-warning { background: linear-gradient(135deg, #fbbf24, #f59e0b); color: #000; }

  /* Forms */
  input, textarea, select {
    width: 100%; padding: 10px 14px; border-radius: 8px; border: 1px solid rgba(255,255,255,0.1);
    background: rgba(255,255,255,0.03); color: #e0f0ff; font-size: 0.85rem;
    margin-bottom: 10px; font-family: inherit;
  }
  input:focus, textarea:focus { outline: none; border-color: #64c8ff; }
  label { font-size: 0.75rem; color: #5a7a9a; display: block; margin-bottom: 4px; }

  /* Agent detail */
  .agent-detail { background: rgba(255,255,255,0.02); border: 1px solid rgba(255,255,255,0.06); border-radius: 12px; padding: 20px; margin-bottom: 12px; }
  .agent-detail h2 { font-size: 1.1rem; color: #e0f0ff; margin-bottom: 8px; }
  .agent-detail .meta { display: flex; gap: 16px; font-size: 0.75rem; color: #5a7a9a; margin-bottom: 12px; }
  .agent-detail .actions { display: flex; gap: 8px; flex-wrap: wrap; }

  /* Result box */
  .result-box {
    background: rgba(0,0,0,0.3); border: 1px solid rgba(100,200,255,0.1);
    border-radius: 8px; padding: 12px; margin-top: 8px;
    font-size: 0.8rem; line-height: 1.5; max-height: 300px; overflow-y: auto;
    white-space: pre-wrap; font-family: monospace;
  }

  .toast {
    position: fixed; bottom: 20px; right: 20px;
    background: rgba(16,185,129,0.9); color: #fff;
    padding: 12px 20px; border-radius: 8px; font-size: 0.8rem;
    animation: slideUp 0.3s ease; z-index: 100;
  }
  @keyframes slideUp { from { transform: translateY(20px); opacity: 0; } to { transform: translateY(0); opacity: 1; } }

  .loading { text-align: center; padding: 40px; color: #5a7a9a; }
  .loading::after { content: '...'; animation: dots 1.5s infinite; }
  @keyframes dots { 0%,20% { content: '.'; } 40% { content: '..'; } 60%,100% { content: '...'; } }
</style>
</head>
<body>
<div class="container">
  <div class="header">
    <h1>⚒️ AgentForge</h1>
    <div class="stats" id="headerStats">
      <span id="statUsers">0</span> users &middot;
      <span id="statAgents">0</span> agents &middot;
      <span id="statRevenue">$0</span> revenue
    </div>
  </div>

  <div class="tabs">
    <div class="tab active" onclick="switchTab('marketplace')">🏪 Marketplace</div>
    <div class="tab" onclick="switchTab('myagents')">🤖 My Agents</div>
    <div class="tab" onclick="switchTab('builder')">⚡ Custom Builder</div>
    <div class="tab" onclick="switchTab('upgrades')">⬆️ Upgrades</div>
  </div>

  <!-- Marketplace -->
  <div class="panel active" id="panel-marketplace">
    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:16px">
      <h2 style="font-size:1.1rem; color:#e0f0ff">🏪 Agent Marketplace</h2>
      <div style="display:flex; gap:8px">
        <input id="usernameInput" placeholder="Your username" style="width:200px; margin:0">
        <button class="btn btn-primary" onclick="register()">Register / Login</button>
      </div>
    </div>
    <div id="userId" style="display:none"></div>
    <div class="grid" id="marketplaceGrid"></div>
  </div>

  <!-- My Agents -->
  <div class="panel" id="panel-myagents">
    <h2 style="font-size:1.1rem; color:#e0f0ff; margin-bottom:16px">🤖 My Agents</h2>
    <div id="myAgentsList"></div>
  </div>

  <!-- Custom Builder -->
  <div class="panel" id="panel-builder">
    <h2 style="font-size:1.1rem; color:#e0f0ff; margin-bottom:16px">⚡ Custom Agent Builder</h2>
    <p style="font-size:0.8rem; color:#5a7a9a; margin-bottom:16px">Describe the AI agent you need in natural language. Our AI will design and build it for you.</p>
    <textarea id="builderInput" rows="4" placeholder="Example: I need an agent that monitors my social media mentions, analyzes sentiment, and sends me a daily report of important conversations. It should also auto-reply to positive mentions with a thank you message."></textarea>
    <button class="btn btn-primary" onclick="buildCustomAgent()">🔨 Build My Agent</button>
    <div id="builderResult"></div>
  </div>

  <!-- Upgrades -->
  <div class="panel" id="panel-upgrades">
    <h2 style="font-size:1.1rem; color:#e0f0ff; margin-bottom:16px">⬆️ Agent Upgrades</h2>
    <div class="grid" id="upgradesGrid">
      <div class="card" onclick="upgradeAgent('model_premium')">
        <div class="icon">🧠</div>
        <h3>Premium Model</h3>
        <div class="desc">Upgrade to DeepSeek V4 — faster, smarter responses</div>
        <div class="price">+$10<span>/mo</span></div>
      </div>
      <div class="card" onclick="upgradeAgent('model_ultra')">
        <div class="icon">🚀</div>
        <h3>Ultra Model</h3>
        <div class="desc">Upgrade to Qwen 3.7 Max — advanced reasoning</div>
        <div class="price">+$20<span>/mo</span></div>
      </div>
      <div class="card" onclick="upgradeAgent('model_sota')">
        <div class="icon">🏆</div>
        <h3>State-of-the-Art</h3>
        <div class="desc">Upgrade to Claude Sonnet 4 — best-in-class AI</div>
        <div class="price">+$50<span>/mo</span></div>
      </div>
      <div class="card" onclick="upgradeAgent('speed_boost')">
        <div class="icon">⚡</div>
        <h3>Speed Boost</h3>
        <div class="desc">Double your action limit for faster processing</div>
        <div class="price">+$15<span>/mo</span></div>
      </div>
      <div class="card" onclick="upgradeAgent('unlimited')">
        <div class="icon">♾️</div>
        <h3>Unlimited Actions</h3>
        <div class="desc">Remove all action limits — run your agent freely</div>
        <div class="price">+$30<span>/mo</span></div>
      </div>
    </div>
    <div id="upgradeResult"></div>
  </div>
</div>

<script>
let currentUser = null;
let agentTypes = [];

async function api(path, data) {
  const opts = { headers: {'Content-Type': 'application/json'} };
  if (data) opts.body = JSON.stringify(data), opts.method = 'POST';
  const r = await fetch('/api' + path, opts);
  return r.json();
}

function toast(msg) {
  const t = document.createElement('div');
  t.className = 'toast';
  t.textContent = msg;
  document.body.appendChild(t);
  setTimeout(() => t.remove(), 3000);
}

async function register() {
  const username = document.getElementById('usernameInput').value.trim();
  if (!username) return toast('Enter a username');
  const result = await api('/register', { username });
  if (result.error) return toast(result.error);
  currentUser = result;
  document.getElementById('userId').textContent = 'Logged in as: ' + result.username + ' (' + result.tier + ')';
  document.getElementById('userId').style.display = 'block';
  toast('Welcome, ' + result.username + '!');
  loadMarketplace();
  loadMyAgents();
}

async function loadMarketplace() {
  const types = await api('/agent-types');
  agentTypes = types;
  const grid = document.getElementById('marketplaceGrid');
  grid.innerHTML = types.map(t => `
    <div class="card" onclick="purchaseAgent('${t.id}')">
      <div class="icon">${t.icon}</div>
      <h3>${t.name}</h3>
      <div class="desc">${t.description}</div>
      <div class="price">$${t.basic_price}<span>/mo basic</span></div>
      <div style="margin-top:8px; display:flex; gap:4px">
        <span class="tier basic">Basic $${t.basic_price}</span>
        <span class="tier pro">Pro $${t.pro_price}</span>
        <span class="tier enterprise">Enterprise $${t.enterprise_price}</span>
      </div>
    </div>
  `).join('');
}

async function purchaseAgent(type) {
  if (!currentUser) return toast('Register first');
  const tier = prompt('Enter tier (basic/pro/enterprise):', 'basic');
  if (!tier) return;
  const result = await api('/purchase', { user_id: currentUser.id, agent_type: type, tier });
  if (result.error) return toast(result.error);
  toast('Purchased: ' + result.name + ' ($' + result.price + ')');
  loadMyAgents();
}

async function loadMyAgents() {
  if (!currentUser) return;
  const agents = await api('/my-agents/' + currentUser.id);
  const list = document.getElementById('myAgentsList');
  if (agents.length === 0) {
    list.innerHTML = '<p style="color:#5a7a9a; font-size:0.85rem">No agents yet. Browse the marketplace!</p>';
    return;
  }
  list.innerHTML = agents.map(a => `
    <div class="agent-detail">
      <h2>${a.name}</h2>
      <div class="meta">
        <span>Type: ${a.type}</span>
        <span>Tier: ${a.tier}</span>
        <span>Actions: ${a.actions_used}/${a.actions_limit}</span>
        <span>Status: ${a.status}</span>
      </div>
      <div class="actions">
        <button class="btn btn-primary" onclick="runAgent('${a.id}')">▶ Run</button>
        <button class="btn btn-warning" onclick="listForSale('${a.id}')">💰 Sell</button>
      </div>
      <div id="run-${a.id}"></div>
    </div>
  `).join('');
}

async function runAgent(id) {
  const prompt = prompt('What do you want this agent to do?');
  if (!prompt) return;
  const div = document.getElementById('run-' + id);
  div.innerHTML = '<div class="loading">Running agent</div>';
  const result = await api('/run-agent', { agent_id: id, prompt });
  div.innerHTML = `<div class="result-box">${result.result || result.error}</div>`;
  loadMyAgents();
}

async function listForSale(id) {
  const price = prompt('Set your price:');
  if (!price) return;
  const result = await api('/list-marketplace', { agent_id: id, price: parseFloat(price) });
  if (result.error) return toast(result.error);
  toast('Listed for sale at $' + price);
}

async function buildCustomAgent() {
  if (!currentUser) return toast('Register first');
  const desc = document.getElementById('builderInput').value.trim();
  if (!desc) return toast('Describe the agent you need');
  const div = document.getElementById('builderResult');
  div.innerHTML = '<div class="loading">AI is designing your custom agent</div>';
  const result = await api('/custom-agent', { user_id: currentUser.id, description: desc });
  if (result.error) {
    div.innerHTML = '<div class="result-box">Error: ' + result.error + '</div>';
    return;
  }
  div.innerHTML = `
    <div class="agent-detail">
      <h2>✅ ${result.spec.name}</h2>
      <div class="meta">
        <span>Type: ${result.spec.type}</span>
        <span>Tier: ${result.spec.tier}</span>
        <span>Price: $${result.price}</span>
      </div>
      <div class="desc">${result.spec.description}</div>
      <div style="margin-top:8px; font-size:0.75rem; color:#5a7a9a">
        Capabilities: ${(result.spec.capabilities || []).join(', ')}
      </div>
    </div>
  `;
  toast('Custom agent built!');
  loadMyAgents();
}

async function upgradeAgent(type) {
  if (!currentUser) return toast('Register first');
  const agents = await api('/my-agents/' + currentUser.id);
  if (agents.length === 0) return toast('You need an agent first');
  const names = agents.map((a,i) => `${i+1}. ${a.name}`).join('\n');
  const choice = prompt('Which agent to upgrade?\n' + names);
  if (!choice) return;
  const idx = parseInt(choice) - 1;
  if (isNaN(idx) || !agents[idx]) return toast('Invalid choice');
  const result = await api('/upgrade-agent', { agent_id: agents[idx].id, upgrade_type: type });
  if (result.error) return toast(result.error);
  toast('Upgrade applied! ($' + result.cost + ')');
  loadMyAgents();
}

function switchTab(name) {
  document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
  document.querySelectorAll('.panel').forEach(p => p.classList.remove('active'));
  document.querySelector('.tab[onclick*="' + name + '"]').classList.add('active');
  document.getElementById('panel-' + name).classList.add('active');
}

async function loadStats() {
  const stats = await api('/stats');
  document.getElementById('statUsers').textContent = stats.users;
  document.getElementById('statAgents').textContent = stats.agents;
  document.getElementById('statRevenue').textContent = '$' + Math.round(stats.revenue);
}

loadMarketplace();
loadStats();
setInterval(loadStats, 10000);
</script>
</body>
</html>"""

# ─── Server ───────────────────────────────────────────────────────────────

engine = AgentEngine()

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        path = self.path
        if path == "/api/stats":
            self._json(engine.get_stats())
        elif path == "/api/agent-types":
            self._json(engine.get_agent_types())
        elif path.startswith("/api/my-agents/"):
            uid = path.split("/")[-1]
            self._json(engine.get_user_agents(uid))
        elif path == "/api/marketplace":
            self._json(engine.get_marketplace())
        else:
            self._html(HTML)
    
    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length)) if length else {}
        path = self.path
        
        if path == "/api/register":
            self._json(engine.create_user(body.get("username", "anon"), body.get("email", "")))
        elif path == "/api/purchase":
            self._json(engine.purchase_agent(body.get("user_id", ""), body.get("agent_type", ""), body.get("tier", "basic")))
        elif path == "/api/run-agent":
            self._json(engine.run_agent(body.get("agent_id", ""), body.get("prompt", "")))
        elif path == "/api/upgrade-agent":
            self._json(engine.upgrade_agent(body.get("agent_id", ""), body.get("upgrade_type", "")))
        elif path == "/api/list-marketplace":
            self._json(engine.list_on_marketplace(body.get("agent_id", ""), body.get("price", 0), body.get("description", "")))
        elif path == "/api/buy-marketplace":
            self._json(engine.buy_from_marketplace(body.get("buyer_id", ""), body.get("listing_id", "")))
        elif path == "/api/custom-agent":
            self._json(engine.custom_agent_builder(body.get("user_id", ""), body.get("description", "")))
        else:
            self._json({"error": "Unknown endpoint"})
    
    def _json(self, data):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())
    
    def _html(self, html):
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        self.wfile.write(html.encode())

def main():
    print(f"\n{'='*55}")
    print(f"  ⚒️  AGENTFORGE — AI Agent Marketplace")
    print(f"  http://localhost:{PORT}")
    print(f"{'='*55}")
    print(f"  • Browse and purchase AI agents")
    print(f"  • Build custom agents from descriptions")
    print(f"  • Upgrade agents with better models")
    print(f"  • Sell agents on the marketplace")
    print(f"  • Self-promo engine running every 30 min")
    print(f"  • Press Ctrl+C to stop.\n")
    
    # Start self-promotion loop
    engine.start_promo_loop()
    
    server = HTTPServer(("127.0.0.1", PORT), Handler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")

if __name__ == "__main__":
    main()
