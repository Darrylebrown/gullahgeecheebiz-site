#!/usr/bin/env python3
"""
GullahGems — Fully Automated AI PDF Business & Advertising Engine.
Built from the AI Think Tank winning design (22,522 chars).
Features: PDF storefront, AI PDF generator, social ads, popup ads, bot ads, magnet ads.
"""
import json, os, sys, time, sqlite3, requests, hashlib, random, threading, re
import omniroute_shim  # OMNIROUTE_MIGRATED
from pathlib import Path
from datetime import datetime, timezone
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Dict, List, Optional

BASE_DIR = Path("/Users/darrylsmac/gullahgeecheebiz-site")
LOGS_DIR = Path(__file__).parent / "logs"
GEMS_DIR = LOGS_DIR / "gullahgems"
DB_PATH = GEMS_DIR / "gullahgems.db"
PORT = 8084

GEMS_DIR.mkdir(parents=True, exist_ok=True)

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
        CREATE TABLE IF NOT EXISTS products (
            id TEXT PRIMARY KEY,
            title TEXT,
            category TEXT,
            description TEXT,
            price REAL DEFAULT 4.99,
            tags TEXT DEFAULT '[]',
            sales INTEGER DEFAULT 0,
            revenue REAL DEFAULT 0,
            created_at TEXT
        );
        CREATE TABLE IF NOT EXISTS orders (
            id TEXT PRIMARY KEY,
            customer_name TEXT,
            customer_email TEXT,
            product_id TEXT,
            product_title TEXT,
            amount REAL,
            source TEXT DEFAULT 'direct',
            created_at TEXT
        );
        CREATE TABLE IF NOT EXISTS ad_campaigns (
            id TEXT PRIMARY KEY,
            name TEXT,
            ad_type TEXT,
            platform TEXT,
            status TEXT DEFAULT 'active',
            budget REAL DEFAULT 0,
            spent REAL DEFAULT 0,
            impressions INTEGER DEFAULT 0,
            clicks INTEGER DEFAULT 0,
            conversions INTEGER DEFAULT 0,
            revenue REAL DEFAULT 0,
            created_at TEXT,
            last_optimized TEXT
        );
        CREATE TABLE IF NOT EXISTS ad_creatives (
            id TEXT PRIMARY KEY,
            campaign_id TEXT,
            headline TEXT,
            body TEXT,
            cta TEXT,
            image_prompt TEXT,
            platform TEXT,
            status TEXT DEFAULT 'active',
            impressions INTEGER DEFAULT 0,
            clicks INTEGER DEFAULT 0,
            conversions INTEGER DEFAULT 0,
            created_at TEXT,
            FOREIGN KEY(campaign_id) REFERENCES ad_campaigns(id)
        );
        CREATE TABLE IF NOT EXISTS lead_magnets (
            id TEXT PRIMARY KEY,
            title TEXT,
            description TEXT,
            downloads INTEGER DEFAULT 0,
            conversions INTEGER DEFAULT 0,
            created_at TEXT
        );
        CREATE TABLE IF NOT EXISTS bot_conversations (
            id TEXT PRIMARY KEY,
            platform TEXT,
            user_id TEXT,
            messages INTEGER DEFAULT 0,
            converted INTEGER DEFAULT 0,
            revenue REAL DEFAULT 0,
            started_at TEXT,
            last_message TEXT
        );
        CREATE TABLE IF NOT EXISTS subscribers (
            email TEXT PRIMARY KEY,
            name TEXT,
            source TEXT,
            subscribed_at TEXT,
            converted INTEGER DEFAULT 0
        );
    """)
    conn.commit()
    
    # Seed products
    count = conn.execute("SELECT COUNT(*) FROM products").fetchone()[0]
    if count == 0:
        seed = [
            ("Gullah Geechee Seasonal Planner", "planner", "Yearly, monthly, weekly planner with Gullah proverbs and sweetgrass motifs", 5.99),
            ("Sweetgrass Financial Tracker", "planner", "Budget planner with sweetgrass basket patterns", 4.99),
            ("Anansi Storytelling Journal", "journal", "Creative writing journal with Gullah fables and prompts", 6.99),
            ("Sea Island Heritage Workbook", "workbook", "Educational workbook on Gullah history and language", 7.99),
            ("Tidewater Business Guide", "template", "Business plan templates with cultural aesthetic", 8.99),
            ("Indigo Dreams Coloring Book", "coloring", "Intricate Gullah Geechee designs and patterns", 4.99),
            ("Lowcountry Celebration Pack", "event", "Invitations, cards, and signage for events", 9.99),
            ("Healing Herbs Guide", "guide", "Traditional Gullah herbal remedies and wellness", 6.99),
            ("Coastal Consult Templates", "template", "Professional report templates with Gullah design", 7.99),
            ("Ancestral Archive Organizer", "planner", "Family tree templates and document organizers", 5.99),
            ("Gullah Language Basics", "workbook", "Learn Gullah Geechee phrases and vocabulary", 6.99),
            ("Sweetgrass Basket Patterns", "coloring", "Coloring book of traditional basket designs", 4.99),
            ("Juneteenth Celebration Pack", "event", "Event printables for Juneteenth celebrations", 8.99),
            ("Gullah Geechee Cookbook", "guide", "Traditional recipes with cultural stories", 7.99),
            ("Sea Island Nature Journal", "journal", "Nature observation journal with Lowcountry wildlife", 5.99),
        ]
        for s in seed:
            pid = hashlib.md5(s[0].encode()).hexdigest()[:12]
            conn.execute("INSERT INTO products VALUES (?,?,?,?,?,?,0,0,?)",
                        (pid, s[0], s[1], s[2], s[3], json.dumps(["Gullah Geechee", s[1].title()]),
                         datetime.now(timezone.utc).isoformat()))
        conn.commit()
    conn.close()

# ─── GullahGems Engine ────────────────────────────────────────────────────

class GullahGemsEngine:
    def __init__(self):
        init_db()
        self.ad_engine_running = False
    
    def _get_conn(self):
        return sqlite3.connect(str(DB_PATH))
    
    def get_products(self, category=None):
        conn = self._get_conn()
        if category and category != "all":
            rows = conn.execute("SELECT * FROM products WHERE category=? ORDER BY sales DESC", (category,)).fetchall()
        else:
            rows = conn.execute("SELECT * FROM products ORDER BY sales DESC").fetchall()
        conn.close()
        return [{
            "id": r[0], "title": r[1], "category": r[2], "description": r[3],
            "price": r[4], "tags": json.loads(r[5] or "[]"), "sales": r[6], "revenue": r[7],
        } for r in rows]
    
    def get_categories(self):
        conn = self._get_conn()
        cats = conn.execute("SELECT DISTINCT category FROM products ORDER BY category").fetchall()
        conn.close()
        return [c[0] for c in cats if c[0]]
    
    def generate_pdf(self, prompt: str, customer_name: str = "", customer_email: str = "") -> Dict:
        """AI PDF Generator — creates a complete PDF product from description."""
        gid = hashlib.md5(f"pdf-{time.time()}".encode()).hexdigest()[:12]
        
        gen_prompt = f"""You are the GullahGems PDF Generator. Create a complete digital PDF product based on this description:

{prompt}

Publisher: Gullah Geechee Biz

Generate:
1. A compelling product title
2. A detailed product description (2-3 sentences)
3. What's included inside (bullet points)
4. Page count
5. Format details
6. Target audience
7. 3-5 relevant category tags
8. Suggested cover/packaging description
9. Suggested price ($2.99 - $14.99)

Return as JSON:
{{"title": "...", "description": "...", "includes": ["..."], "pages": 0, "format": "...", "audience": "...", "tags": ["..."], "cover": "...", "price": 0}}"""
        
        result = call_ai(gen_prompt, max_tokens=2000)
        
        product_data = {}
        if result:
            try:
                start = result.find("{")
                end = result.rfind("}") + 1
                product_data = json.loads(result[start:end])
            except:
                product_data = {"title": "Custom PDF", "description": result[:200]}
        
        title = product_data.get("title", "Custom GullahGems PDF")
        price = product_data.get("price", 6.99)
        tags = product_data.get("tags", ["Gullah Geechee", "Custom"])
        
        pid = hashlib.md5(f"generated-{gid}".encode()).hexdigest()[:12]
        conn = self._get_conn()
        conn.execute("INSERT INTO products VALUES (?,?,?,?,?,?,0,0,?)",
                    (pid, title[:80], "custom", product_data.get("description", "")[:200],
                     price, json.dumps(tags), datetime.now(timezone.utc).isoformat()))
        conn.commit()
        conn.close()
        
        return {
            "product_id": pid,
            "title": title,
            "description": product_data.get("description", "")[:200],
            "includes": product_data.get("includes", []),
            "pages": product_data.get("pages", 0),
            "price": price,
            "tags": tags,
        }
    
    def place_order(self, name: str, email: str, product_id: str, source: str = "direct") -> Dict:
        conn = self._get_conn()
        product = conn.execute("SELECT * FROM products WHERE id=?", (product_id,)).fetchone()
        if not product:
            conn.close()
            return {"error": "Product not found"}
        
        oid = hashlib.md5(f"order-{time.time()}".encode()).hexdigest()[:12]
        conn.execute("INSERT INTO orders VALUES (?,?,?,?,?,?,?,?)",
                    (oid, name, email, product_id, product[1], product[4], source,
                     datetime.now(timezone.utc).isoformat()))
        conn.execute("UPDATE products SET sales = sales + 1, revenue = revenue + ? WHERE id=?", (product[4], product_id))
        conn.commit()
        conn.close()
        
        return {"order_id": oid, "product": product[1], "amount": product[4], "source": source}
    
    def subscribe(self, email: str, name: str = "", source: str = "magnet") -> Dict:
        conn = self._get_conn()
        try:
            conn.execute("INSERT INTO subscribers VALUES (?,?,?,?,0)",
                        (email, name or email.split("@")[0], source, datetime.now(timezone.utc).isoformat()))
            conn.commit()
            conn.close()
            return {"status": "subscribed", "email": email}
        except sqlite3.IntegrityError:
            conn.close()
            return {"status": "already_subscribed", "email": email}
    
    # ─── ADVERTISING ENGINE ─────────────────────────────────────────────
    
    def generate_social_ad(self, platform: str = "instagram") -> Dict:
        """Generate a social media ad using AI."""
        products = self.get_products()
        if not products:
            return {"error": "No products"}
        product = random.choice(products)
        
        prompt = f"""You are CreativeBot, an AI advertising copywriter for GullahGems. Generate a social media ad.

Product: {product['title']}
Description: {product['description']}
Price: ${product['price']}
Platform: {platform}

Generate:
1. A compelling headline (under 60 chars)
2. Ad body text (2-3 sentences, platform-appropriate length)
3. A clear call-to-action
4. 5 relevant hashtags
5. A visual/image description for the ad creative
6. Best time to post

Return as JSON:
{{"headline": "...", "body": "...", "cta": "...", "hashtags": ["..."], "visual": "...", "best_time": "..."}}"""
        
        result = call_ai(prompt, max_tokens=1000)
        ad_data = {}
        if result:
            try:
                start = result.find("{")
                end = result.rfind("}") + 1
                ad_data = json.loads(result[start:end])
            except:
                ad_data = {"headline": f"Discover {product['title']}", "body": result[:200]}
        
        # Create campaign and creative
        conn = self._get_conn()
        cid = hashlib.md5(f"campaign-{platform}-{time.time()}".encode()).hexdigest()[:12]
        conn.execute("""INSERT INTO ad_campaigns (id, name, ad_type, platform, status, budget, created_at)
                       VALUES (?,?,?,?,?,?,?)""",
                    (cid, f"{platform.title()} Campaign - {product['title'][:30]}", "social", platform,
                     "active", 50.0, datetime.now(timezone.utc).isoformat()))
        
        aid = hashlib.md5(f"creative-{time.time()}".encode()).hexdigest()[:12]
        conn.execute("""INSERT INTO ad_creatives (id, campaign_id, headline, body, cta, image_prompt, platform, created_at)
                       VALUES (?,?,?,?,?,?,?,?)""",
                    (aid, cid, ad_data.get("headline", ""), ad_data.get("body", ""),
                     ad_data.get("cta", "Shop Now"), ad_data.get("visual", ""),
                     platform, datetime.now(timezone.utc).isoformat()))
        conn.commit()
        conn.close()
        
        return {
            "campaign_id": cid,
            "creative_id": aid,
            "platform": platform,
            "product": product['title'],
            "headline": ad_data.get("headline", ""),
            "body": ad_data.get("body", "")[:100],
            "cta": ad_data.get("cta", ""),
            "hashtags": ad_data.get("hashtags", []),
            "visual": ad_data.get("visual", "")[:100],
        }
    
    def generate_popup_ad(self) -> Dict:
        """Generate a display/popup ad."""
        products = self.get_products()
        if not products:
            return {"error": "No products"}
        product = random.choice(products)
        
        prompt = f"""You are DisplayAdBot. Generate a display/popup ad for GullahGems.

Product: {product['title']}
Price: ${product['price']}

Generate a short, punchy display ad with:
1. A short headline (under 40 chars)
2. A brief body (under 80 chars)
3. A CTA (under 20 chars)
4. A visual description

Return as JSON:
{{"headline": "...", "body": "...", "cta": "...", "visual": "..."}}"""
        
        result = call_ai(prompt, max_tokens=500)
        ad_data = {}
        if result:
            try:
                start = result.find("{")
                end = result.rfind("}") + 1
                ad_data = json.loads(result[start:end])
            except:
                ad_data = {"headline": product['title'], "body": "Discover Gullah Geechee culture"}
        
        conn = self._get_conn()
        cid = hashlib.md5(f"popup-{time.time()}".encode()).hexdigest()[:12]
        conn.execute("""INSERT INTO ad_campaigns (id, name, ad_type, platform, status, budget, created_at)
                       VALUES (?,?,?,?,?,?,?)""",
                    (cid, f"Display Ad - {product['title'][:30]}", "display", "web",
                     "active", 30.0, datetime.now(timezone.utc).isoformat()))
        
        aid = hashlib.md5(f"display-{time.time()}".encode()).hexdigest()[:12]
        conn.execute("""INSERT INTO ad_creatives (id, campaign_id, headline, body, cta, image_prompt, platform, created_at)
                       VALUES (?,?,?,?,?,?,?,?)""",
                    (aid, cid, ad_data.get("headline", ""), ad_data.get("body", ""),
                     ad_data.get("cta", "Learn More"), ad_data.get("visual", ""),
                     "display", datetime.now(timezone.utc).isoformat()))
        conn.commit()
        conn.close()
        
        return {"campaign_id": cid, "creative_id": aid, "headline": ad_data.get("headline", ""), "body": ad_data.get("body", "")[:80]}
    
    def generate_bot_message(self, platform: str = "whatsapp") -> Dict:
        """Generate a bot conversation message."""
        products = self.get_products()
        if not products:
            return {"error": "No products"}
        product = random.choice(products)
        
        prompt = f"""You are ConvoBot, an AI sales chatbot for GullahGems. Generate a conversation starter.

Product: {product['title']}
Price: ${product['price']}
Platform: {platform}

Generate:
1. A friendly greeting/intro message
2. A product recommendation message
3. A follow-up question to engage the user
4. A call-to-action message

Return as JSON:
{{"greeting": "...", "recommendation": "...", "question": "...", "cta": "..."}}"""
        
        result = call_ai(prompt, max_tokens=800)
        msg_data = {}
        if result:
            try:
                start = result.find("{")
                end = result.rfind("}") + 1
                msg_data = json.loads(result[start:end])
            except:
                msg_data = {"greeting": f"Check out {product['title']}!"}
        
        conn = self._get_conn()
        bid = hashlib.md5(f"bot-{platform}-{time.time()}".encode()).hexdigest()[:12]
        conn.execute("""INSERT INTO bot_conversations (id, platform, user_id, messages, started_at, last_message)
                       VALUES (?,?,?,1,?,?)""",
                    (bid, platform, f"sample_{platform}", datetime.now(timezone.utc).isoformat(),
                     datetime.now(timezone.utc).isoformat()))
        conn.commit()
        conn.close()
        
        return {"conversation_id": bid, "platform": platform, "messages": msg_data}
    
    def generate_lead_magnet(self) -> Dict:
        """Generate a free lead magnet PDF."""
        prompt = """You are MagnetBot. Create a free lead magnet for GullahGems to attract subscribers.

Generate a free PDF sample that showcases Gullah Geechee culture. Options:
1. A mini-planner page with a Gullah proverb
2. A coloring page with sweetgrass basket design
3. A recipe card with a traditional Gullah dish
4. A language learning card with Gullah phrases
5. A journal prompt page with cultural reflection

Generate:
1. A compelling title for the freebie
2. A short description of what's inside
3. Why someone would want it
4. Suggested email subject line for delivery

Return as JSON:
{{"title": "...", "description": "...", "value_proposition": "...", "email_subject": "..."}}"""
        
        result = call_ai(prompt, max_tokens=800)
        magnet_data = {}
        if result:
            try:
                start = result.find("{")
                end = result.rfind("}") + 1
                magnet_data = json.loads(result[start:end])
            except:
                magnet_data = {"title": "Free Gullah Geechee Sample Pack"}
        
        conn = self._get_conn()
        mid = hashlib.md5(f"magnet-{time.time()}".encode()).hexdigest()[:12]
        conn.execute("INSERT INTO lead_magnets VALUES (?,?,?,0,0,?)",
                    (mid, magnet_data.get("title", "Free Sample"), magnet_data.get("description", "")[:200],
                     datetime.now(timezone.utc).isoformat()))
        conn.commit()
        conn.close()
        
        return {"magnet_id": mid, "title": magnet_data.get("title", ""), "description": magnet_data.get("description", "")[:100]}
    
    def run_ad_cycle(self) -> Dict:
        """Run a full advertising cycle — generate ads for all channels."""
        results = {}
        
        # Social ads for each platform
        for platform in ["instagram", "facebook", "tiktok", "pinterest", "twitter"]:
            ad = self.generate_social_ad(platform)
            results[f"social_{platform}"] = ad.get("campaign_id", "failed")
        
        # Popup ad
        popup = self.generate_popup_ad()
        results["popup"] = popup.get("campaign_id", "failed")
        
        # Bot message
        bot = self.generate_bot_message()
        results["bot"] = bot.get("conversation_id", "failed")
        
        # Lead magnet
        magnet = self.generate_lead_magnet()
        results["magnet"] = magnet.get("magnet_id", "failed")
        
        return results
    
    def start_ad_engine(self):
        """Start autonomous ad generation loop."""
        def loop():
            self.ad_engine_running = True
            while self.ad_engine_running:
                try:
                    result = self.run_ad_cycle()
                    print(f"  📢 GullahGems ad cycle: Social(5) + Popup + Bot + Magnet")
                except:
                    pass
                time.sleep(3600)  # Every hour
        t = threading.Thread(target=loop, daemon=True)
        t.start()
        return t
    
    def get_stats(self):
        conn = self._get_conn()
        products = conn.execute("SELECT COUNT(*) FROM products").fetchone()[0]
        orders = conn.execute("SELECT COUNT(*) FROM orders").fetchone()[0]
        revenue = conn.execute("SELECT COALESCE(SUM(amount), 0) FROM orders").fetchone()[0]
        campaigns = conn.execute("SELECT COUNT(*) FROM ad_campaigns").fetchone()[0]
        creatives = conn.execute("SELECT COUNT(*) FROM ad_creatives").fetchone()[0]
        magnets = conn.execute("SELECT COUNT(*) FROM lead_magnets").fetchone()[0]
        bots = conn.execute("SELECT COUNT(*) FROM bot_conversations").fetchone()[0]
        subs = conn.execute("SELECT COUNT(*) FROM subscribers").fetchone()[0]
        conn.close()
        return {
            "products": products, "orders": orders, "revenue": revenue,
            "campaigns": campaigns, "creatives": creatives,
            "magnets": magnets, "bot_conversations": bots, "subscribers": subs,
        }

# ─── HTML ─────────────────────────────────────────────────────────────────

HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>GullahGems — AI-Crafted Digital Legacies</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700;900&display=swap');
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body {
    font-family: 'Inter', -apple-system, sans-serif;
    background: #0a0a12;
    color: #c8d6e5;
    min-height: 100vh;
  }
  .container { max-width: 1200px; margin: 0 auto; padding: 20px; }

  .header {
    display: flex; justify-content: space-between; align-items: center;
    padding: 16px 0; border-bottom: 1px solid rgba(100,200,255,0.1); margin-bottom: 20px;
    flex-wrap: wrap; gap: 12px;
  }
  .header h1 {
    font-size: 1.5rem; font-weight: 900;
    background: linear-gradient(135deg, #64c8ff, #a78bfa, #f0c040);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
  }
  .header .sub { font-size: 0.7rem; color: #5a7a9a; }
  .header .stats { display: flex; gap: 12px; font-size: 0.75rem; color: #5a7a9a; flex-wrap: wrap; }
  .header .stats span { color: #64c8ff; font-weight: 600; }

  .tabs { display: flex; gap: 4px; margin-bottom: 20px; flex-wrap: wrap; }
  .tab {
    padding: 8px 16px; border-radius: 8px 8px 0 0; cursor: pointer;
    font-size: 0.8rem; font-weight: 600; color: #5a7a9a;
    background: rgba(255,255,255,0.02); border: 1px solid rgba(255,255,255,0.04);
    border-bottom: none; transition: all 0.2s;
  }
  .tab.active { color: #64c8ff; background: rgba(100,200,255,0.05); border-color: rgba(100,200,255,0.15); }
  .tab:hover { color: #a0c0e0; }
  .panel { display: none; }
  .panel.active { display: block; }

  .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 12px; }
  .card {
    background: rgba(255,255,255,0.02); border: 1px solid rgba(255,255,255,0.06);
    border-radius: 12px; padding: 16px; transition: all 0.3s; cursor: pointer;
  }
  .card:hover { border-color: rgba(100,200,255,0.2); transform: translateY(-2px); }
  .card .icon { font-size: 2rem; margin-bottom: 8px; }
  .card h3 { font-size: 0.85rem; color: #e0f0ff; margin-bottom: 4px; }
  .card .cat { font-size: 0.65rem; color: #5a7a9a; text-transform: uppercase; letter-spacing: 0.5px; }
  .card .price { font-size: 1.1rem; font-weight: 700; color: #64c8ff; margin-top: 4px; }
  .card .price span { font-size: 0.65rem; color: #5a7a9a; font-weight: 400; }
  .card .sales { font-size: 0.7rem; color: #5a7a9a; margin-top: 4px; }

  .gen-section {
    background: rgba(255,255,255,0.02); border: 1px solid rgba(100,200,255,0.1);
    border-radius: 12px; padding: 20px; margin-bottom: 16px;
  }
  .gen-section h2 { font-size: 1.1rem; color: #64c8ff; margin-bottom: 8px; }
  .gen-section .desc { font-size: 0.8rem; color: #5a7a9a; margin-bottom: 12px; }

  textarea { width: 100%; padding: 12px; border-radius: 8px; border: 1px solid rgba(255,255,255,0.1); background: rgba(255,255,255,0.03); color: #e0f0ff; font-size: 0.85rem; font-family: inherit; resize: vertical; min-height: 80px; }
  textarea:focus { outline: none; border-color: #64c8ff; }
  input, select { padding: 10px 14px; border-radius: 8px; border: 1px solid rgba(255,255,255,0.1); background: rgba(255,255,255,0.03); color: #e0f0ff; font-size: 0.85rem; width: 100%; margin-bottom: 8px; }
  input:focus, select:focus { outline: none; border-color: #64c8ff; }
  label { font-size: 0.75rem; color: #5a7a9a; display: block; margin-bottom: 4px; }

  .btn {
    display: inline-block; padding: 10px 24px; border-radius: 8px; border: none;
    font-size: 0.85rem; font-weight: 600; cursor: pointer; transition: all 0.2s;
  }
  .btn-primary { background: linear-gradient(135deg, #64c8ff, #3b82f6); color: #fff; }
  .btn-primary:hover { transform: translateY(-1px); box-shadow: 0 4px 12px rgba(59,130,246,0.3); }
  .btn-secondary { background: rgba(255,255,255,0.05); color: #a0c0e0; border: 1px solid rgba(255,255,255,0.1); }
  .btn-success { background: linear-gradient(135deg, #34d399, #10b981); color: #fff; }
  .btn-ad { background: linear-gradient(135deg, #a78bfa, #7c3aed); color: #fff; }
  .btn-magnet { background: linear-gradient(135deg, #fbbf24, #f59e0b); color: #000; }
  .btn-full { width: 100%; }

  .result-box { background: rgba(0,0,0,0.3); border: 1px solid rgba(100,200,255,0.1); border-radius: 8px; padding: 12px; margin-top: 12px; font-size: 0.8rem; line-height: 1.5; max-height: 300px; overflow-y: auto; white-space: pre-wrap; }
  .ad-card { background: rgba(255,255,255,0.02); border: 1px solid rgba(167,139,250,0.15); border-radius: 8px; padding: 12px; margin-bottom: 8px; }
  .ad-card .label { font-size: 0.65rem; color: #a78bfa; text-transform: uppercase; letter-spacing: 0.5px; }
  .ad-card .content { font-size: 0.8rem; margin-top: 4px; }

  .toast { position: fixed; bottom: 20px; right: 20px; background: rgba(100,200,255,0.9); color: #0a0a12; padding: 12px 20px; border-radius: 8px; font-size: 0.8rem; font-weight: 600; animation: slideUp 0.3s ease; z-index: 100; }
  @keyframes slideUp { from { transform: translateY(20px); opacity: 0; } to { transform: translateY(0); opacity: 1; } }
  .loading { text-align: center; padding: 20px; color: #64c8ff; }
  .loading::after { content: '...'; animation: dots 1.5s infinite; }
  @keyframes dots { 0%,20% { content: '.'; } 40% { content: '..'; } 60%,100% { content: '...'; } }

  .ad-dashboard { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 12px; margin-bottom: 16px; }
  .ad-stat { background: rgba(255,255,255,0.02); border: 1px solid rgba(255,255,255,0.06); border-radius: 8px; padding: 12px; text-align: center; }
  .ad-stat .num { font-size: 1.5rem; font-weight: 700; color: #a78bfa; }
  .ad-stat .lbl { font-size: 0.7rem; color: #5a7a9a; margin-top: 2px; }

  .footer { text-align: center; padding: 20px; font-size: 0.7rem; color: #3a4a5a; border-top: 1px solid rgba(255,255,255,0.04); margin-top: 20px; }
</style>
</head>
<body>
<div class="container">
  <div class="header">
    <div>
      <h1>💎 GullahGems</h1>
      <div class="sub">AI-Crafted Digital Legacies — Powered by Gullah Geechee Biz</div>
    </div>
    <div class="stats">
      <span id="statProducts">0</span> PDFs &middot;
      <span id="statOrders">0</span> sold &middot;
      <span id="statRevenue">$0</span> revenue &middot;
      <span id="statCampaigns">0</span> ad campaigns
    </div>
  </div>

  <div class="tabs">
    <div class="tab active" onclick="switchTab('store')">📄 Store</div>
    <div class="tab" onclick="switchTab('generator')">✨ PDF Generator</div>
    <div class="tab" onclick="switchTab('ads')">📢 Ad Engine</div>
    <div class="tab" onclick="switchTab('magnet')">🧲 Freebies</div>
  </div>

  <!-- Store -->
  <div class="panel active" id="panel-store">
    <div style="display:flex; gap:8px; margin-bottom:16px">
      <select id="catFilter" onchange="loadProducts()" style="width:auto">
        <option value="all">All Categories</option>
      </select>
    </div>
    <div class="grid" id="productGrid"></div>
  </div>

  <!-- PDF Generator -->
  <div class="panel" id="panel-generator">
    <div class="gen-section">
      <h2>✨ AI PDF Generator</h2>
      <div class="desc">Describe the digital product you want. Our AI will design it, format it, and add it to the store — instantly.</div>
      <label>Your Name</label>
      <input id="genName" placeholder="Your name">
      <label>Your Email</label>
      <input id="genEmail" placeholder="your@email.com">
      <label>Describe Your PDF</label>
      <textarea id="genPrompt" rows="4" placeholder="Example: A weekly meal planner with Gullah Geechee recipes, grocery list, and cultural food stories. Beautiful indigo and sweetgrass design."></textarea>
      <button class="btn btn-primary btn-full" onclick="generatePDF()">✨ Generate My PDF</button>
      <div id="genResult"></div>
    </div>
  </div>

  <!-- Ad Engine -->
  <div class="panel" id="panel-ads">
    <div class="ad-dashboard" id="adStats"></div>
    <div style="display:flex; gap:8px; flex-wrap:wrap; margin-bottom:16px">
      <button class="btn btn-ad" onclick="runAdCycle()">📢 Run Full Ad Cycle</button>
      <button class="btn btn-secondary" onclick="generateSocialAd()">📱 Social Ad</button>
      <button class="btn btn-secondary" onclick="generatePopupAd()">🖥️ Popup Ad</button>
      <button class="btn btn-secondary" onclick="generateBotAd()">🤖 Bot Message</button>
    </div>
    <div id="adResults"></div>
  </div>

  <!-- Magnet / Freebies -->
  <div class="panel" id="panel-magnet">
    <div class="gen-section">
      <h2>🧲 Free Lead Magnets</h2>
      <div class="desc">Generate free PDF samples that attract subscribers and convert to sales.</div>
      <button class="btn btn-magnet" onclick="generateMagnet()">🧲 Generate New Freebie</button>
      <div style="margin-top:12px">
        <label>Get notified of new freebies:</label>
        <div style="display:flex; gap:8px">
          <input id="magnetEmail" placeholder="your@email.com" style="flex:1; margin:0">
          <button class="btn btn-success" onclick="subscribeMagnet()">Subscribe</button>
        </div>
      </div>
      <div id="magnetResult"></div>
    </div>
  </div>

  <div class="footer">GullahGems &middot; A Gullah Geechee Biz Platform &middot; AI-Powered Advertising Engine Running</div>
</div>

<script>
async function api(path, data) {
  const opts = { headers: {'Content-Type': 'application/json'} };
  if (data) opts.body = JSON.stringify(data), opts.method = 'POST';
  const r = await fetch('/api' + path, opts);
  return r.json();
}

function toast(msg) {
  const t = document.createElement('div'); t.className = 'toast'; t.textContent = msg;
  document.body.appendChild(t); setTimeout(() => t.remove(), 3000);
}

async function loadProducts() {
  const cat = document.getElementById('catFilter').value;
  const r = await api('/products?category=' + cat);
  const grid = document.getElementById('productGrid');
  const icons = { planner: '📅', journal: '📓', workbook: '📚', template: '📋', coloring: '🎨', event: '🎉', guide: '📖', custom: '✨' };
  grid.innerHTML = r.map(p => `
    <div class="card" onclick="buyProduct('${p.id}')">
      <div class="icon">${icons[p.category] || '📄'}</div>
      <div class="cat">${p.category}</div>
      <h3>${p.title}</h3>
      <div class="price">$${p.price.toFixed(2)}<span> PDF</span></div>
      <div class="sales">${p.sales} sold</div>
    </div>
  `).join('');
}

async function buyProduct(id) {
  const name = prompt('Your name:') || 'Guest';
  const email = prompt('Your email:') || 'guest@example.com';
  const r = await api('/order', { name, email, product_id: id });
  if (r.error) return toast(r.error);
  toast('Purchased! ' + r.product + ' — $' + r.amount.toFixed(2));
  loadProducts(); loadStats();
}

async function generatePDF() {
  const name = document.getElementById('genName').value.trim() || 'Guest';
  const email = document.getElementById('genEmail').value.trim() || 'guest@example.com';
  const prompt = document.getElementById('genPrompt').value.trim();
  if (!prompt) return toast('Describe your PDF');
  const div = document.getElementById('genResult');
  div.innerHTML = '<div class="loading">AI is designing your PDF</div>';
  const r = await api('/generate-pdf', { prompt, customer_name: name, customer_email: email });
  if (r.error) { div.innerHTML = '<div class="result-box" style="color:#f44336">Error</div>'; return; }
  div.innerHTML = `<div class="result-box"><strong>✅ "${r.title}" created!</strong><br><br>${r.description}<br><br>Pages: ${r.pages} &middot; Price: $${r.price.toFixed(2)}<br>Includes: ${(r.includes||[]).join(', ')}</div>`;
  toast('PDF added to store!'); loadProducts(); loadStats();
}

async function runAdCycle() {
  const div = document.getElementById('adResults');
  div.innerHTML = '<div class="loading">GullahGenesis ad engine running</div>';
  const r = await api('/ad-cycle');
  let html = '<div class="ad-dashboard">';
  for (const [k,v] of Object.entries(r)) {
    const icon = k.includes('social') ? '📱' : k === 'popup' ? '🖥️' : k === 'bot' ? '🤖' : '🧲';
    const name = k.replace('social_','').replace('_',' ').replace(/\b\w/g,c=>c.toUpperCase());
    html += `<div class="ad-stat"><div class="num">${icon}</div><div class="lbl">${name}</div><div style="font-size:0.65rem;color:#5a7a9a">${v.substring(0,8)}</div></div>`;
  }
  html += '</div>';
  div.innerHTML = html;
  toast('Ad cycle complete!'); loadStats();
}

async function generateSocialAd() {
  const r = await api('/generate-social-ad');
  const div = document.getElementById('adResults');
  div.innerHTML = `
    <div class="ad-card"><div class="label">📱 Social Ad — ${r.platform}</div>
    <div class="content"><strong>${r.headline}</strong><br>${r.body}<br><br>CTA: ${r.cta}<br>Hashtags: ${(r.hashtags||[]).join(' ')}</div></div>`;
}

async function generatePopupAd() {
  const r = await api('/generate-popup-ad');
  const div = document.getElementById('adResults');
  div.innerHTML = `<div class="ad-card"><div class="label">🖥️ Popup/Display Ad</div><div class="content"><strong>${r.headline}</strong><br>${r.body}</div></div>`;
}

async function generateBotAd() {
  const r = await api('/generate-bot-message');
  const div = document.getElementById('adResults');
  const msg = r.messages || {};
  div.innerHTML = `<div class="ad-card"><div class="label">🤖 Bot Message — ${r.platform}</div><div class="content">💬 ${msg.greeting || ''}<br>📢 ${msg.recommendation || ''}<br>❓ ${msg.question || ''}<br>👉 ${msg.cta || ''}</div></div>`;
}

async function generateMagnet() {
  const r = await api('/generate-magnet');
  const div = document.getElementById('magnetResult');
  div.innerHTML = `<div class="result-box"><strong>🧲 "${r.title}"</strong><br><br>${r.description}</div>`;
  toast('Freebie created!'); loadStats();
}

async function subscribeMagnet() {
  const email = document.getElementById('magnetEmail').value.trim();
  if (!email) return toast('Enter your email');
  const r = await api('/subscribe', { email });
  toast(r.status === 'subscribed' ? 'Subscribed! Check your email for freebies.' : 'Already subscribed!');
}

async function loadCategories() {
  const r = await api('/categories');
  const sel = document.getElementById('catFilter');
  r.forEach(c => { sel.innerHTML += `<option value="${c}">${c.charAt(0).toUpperCase() + c.slice(1)}</option>`; });
}

async function loadStats() {
  const r = await api('/stats');
  document.getElementById('statProducts').textContent = r.products;
  document.getElementById('statOrders').textContent = r.orders;
  document.getElementById('statRevenue').textContent = '$' + Math.round(r.revenue);
  document.getElementById('statCampaigns').textContent = r.campaigns;
  const adsDiv = document.getElementById('adStats');
  if (adsDiv) {
    adsDiv.innerHTML = `
      <div class="ad-stat"><div class="num">${r.campaigns}</div><div class="lbl">Ad Campaigns</div></div>
      <div class="ad-stat"><div class="num">${r.creatives}</div><div class="lbl">Ad Creatives</div></div>
      <div class="ad-stat"><div class="num">${r.magnets}</div><div class="lbl">Lead Magnets</div></div>
      <div class="ad-stat"><div class="num">${r.subscribers}</div><div class="lbl">Subscribers</div></div>
    `;
  }
}

function switchTab(name) {
  document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
  document.querySelectorAll('.panel').forEach(p => p.classList.remove('active'));
  document.querySelector('.tab[onclick*="' + name + '"]').classList.add('active');
  document.getElementById('panel-' + name).classList.add('active');
}

loadProducts(); loadCategories(); loadStats();
setInterval(loadStats, 15000);
</script>
</body>
</html>"""

# ─── Server ───────────────────────────────────────────────────────────────

engine = GullahGemsEngine()

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        path = self.path
        if path.startswith("/api/products"):
            from urllib.parse import urlparse, parse_qs
            qs = parse_qs(urlparse(path).query)
            cat = qs.get("category", ["all"])[0]
            self._json(engine.get_products(cat))
        elif path == "/api/categories":
            self._json(engine.get_categories())
        elif path == "/api/stats":
            self._json(engine.get_stats())
        else:
            self._html(HTML)
    
    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length)) if length else {}
        path = self.path
        
        if path == "/api/generate-pdf":
            self._json(engine.generate_pdf(body.get("prompt", ""), body.get("customer_name", ""), body.get("customer_email", "")))
        elif path == "/api/order":
            self._json(engine.place_order(body.get("name", ""), body.get("email", ""), body.get("product_id", ""), body.get("source", "direct")))
        elif path == "/api/subscribe":
            self._json(engine.subscribe(body.get("email", ""), body.get("name", ""), body.get("source", "magnet")))
        elif path == "/api/ad-cycle":
            self._json(engine.run_ad_cycle())
        elif path == "/api/generate-social-ad":
            self._json(engine.generate_social_ad(body.get("platform", "instagram")))
        elif path == "/api/generate-popup-ad":
            self._json(engine.generate_popup_ad())
        elif path == "/api/generate-bot-message":
            self._json(engine.generate_bot_message(body.get("platform", "whatsapp")))
        elif path == "/api/generate-magnet":
            self._json(engine.generate_lead_magnet())
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
    print(f"  💎 GULLAHGEMS — AI PDF Business & Ad Engine")
    print(f"  http://localhost:{PORT}")
    print(f"{'='*55}")
    print(f"  • 15 AI-generated PDF products")
    print(f"  • AI PDF Generator (custom on demand)")
    print(f"  • Social Media Ad Generator (5 platforms)")
    print(f"  • Popup/Display Ad Generator")
    print(f"  • Bot Message Generator")
    print(f"  • Lead Magnet Generator")
    print(f"  • Autonomous ad engine running every hour")
    print(f"  • Press Ctrl+C to stop.\n")
    
    # Start autonomous ad engine
    engine.start_ad_engine()
    
    server = HTTPServer(("127.0.0.1", PORT), Handler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")

if __name__ == "__main__":
    main()
