#!/usr/bin/env python3
"""
AgentForge Promo Army — 100 autonomous bots that promote the AgentForge
marketplace across every platform. Uses the existing GGB ecosystem to
drive traffic, signups, and sales.
"""
import json, os, sys, time, sqlite3, requests, hashlib, random, threading
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional

BASE_DIR = Path("/Users/darrylsmac/gullahgeecheebiz-site")
LOGS_DIR = Path(__file__).parent / "logs"
PROMO_DIR = LOGS_DIR / "agentforge-promo"
STATE_FILE = PROMO_DIR / "promo-state.json"
CONTENT_FILE = PROMO_DIR / "promo-content.json"
PERFORMANCE_FILE = PROMO_DIR / "promo-performance.json"

PROMO_DIR.mkdir(parents=True, exist_ok=True)

def get_api_key():
    env_file = BASE_DIR / ".env"
    if env_file.exists():
        for line in env_file.read_text().split("\n"):
            if "OPENROUTER_API_KEY" in line:
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    return ""

def call_ai(prompt, model="google/gemini-2.5-flash", max_tokens=1000):
    api_key = get_api_key()
    if not api_key:
        return None
    try:
        r = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={"model": model, "messages": [{"role": "user", "content": prompt}], "max_tokens": max_tokens},
            timeout=30
        )
        if r.status_code == 200:
            return r.json()["choices"][0]["message"]["content"]
    except:
        pass
    return None

# ─── 100 Promo Bot Specializations ────────────────────────────────────────

PROMO_BOTS = []

# Social Media Promoters (1-20)
platforms_social = [
    ("Twitter/X", "Cultural Curator"), ("Twitter/X", "Tech Evangelist"), ("Twitter/X", "Biz Coach"),
    ("Twitter/X", "AI Enthusiast"), ("Twitter/X", "Community Builder"),
    ("TikTok", "Trend Spotter"), ("TikTok", "HowTo Creator"), ("TikTok", "Storyteller"),
    ("TikTok", "Reviewer"), ("TikTok", "Challenge Host"),
    ("Pinterest", "Pin Designer"), ("Pinterest", "Board Curator"), ("Pinterest", "Infographic Maker"),
    ("Pinterest", "Idea Pinner"), ("Pinterest", "Visual Strategist"),
    ("Instagram", "Feed Poster"), ("Instagram", "Reel Creator"), ("Instagram", "Story Teller"),
    ("Instagram", "Carousel Designer"), ("Instagram", "Influencer Engager"),
]
for i, (p, n) in enumerate(platforms_social, 1):
    PROMO_BOTS.append({"id": i, "platform": p, "name": n, "focus": f"Promote AgentForge on {p}", "model": "google/gemini-2.5-flash"})

# Content Creators (21-40)
content_types = [
    "Blog Writer", "Newsletter Author", "Case Study Writer", "Testimonial Collector",
    "Comparison Writer", "HowTo Guide Writer", "Listicle Creator", "Interviewer",
    "Review Writer", "Tutorial Author", "Ebook Writer", "Whitepaper Author",
    "Social Proof Curator", "Success Story Writer", "FAQ Writer", "Glossary Creator",
    "Checklist Maker", "Template Designer", "Worksheet Creator", "Cheat Sheet Author",
]
for i, n in enumerate(content_types, 21):
    PROMO_BOTS.append({"id": i, "platform": "Content", "name": n, "focus": f"Create {n.lower()} content for AgentForge", "model": "deepseek/deepseek-chat"})

# Community Engagers (41-60)
community_roles = [
    "Reddit Ambassador", "Discord Host", "Telegram Announcer", "Slack Integrator",
    "Forum Responder", "Q&A Answerer", "Group Moderator", "Community Manager",
    "Event Promoter", "Webinar Host", "AMA Organizer", "Meetup Coordinator",
    "Feedback Collector", "Beta Tester Recruiter", "Referral Program Promoter",
    "Affiliate Manager", "Partner Outreach", "Influencer Liaison", "Brand Advocate",
    "Loyalty Program Host",
]
for i, n in enumerate(community_roles, 41):
    PROMO_BOTS.append({"id": i, "platform": "Community", "name": n, "focus": f"Engage communities about AgentForge as {n.lower()}", "model": "qwen/qwen3.7-max"})

# SEO & Discovery (61-75)
seo_roles = [
    "Keyword Researcher", "Backlink Builder", "Meta Description Writer",
    "Alt Text Creator", "Schema Markup Expert", "SERP Tracker",
    "Competitor Analyst", "Trend Spotter", "Content Gap Finder",
    "Topic Cluster Builder", "Internal Link Strategist", "External Link Builder",
    "Featured Snippet Optimizer", "Video SEO Specialist", "Image SEO Optimizer",
]
for i, n in enumerate(seo_roles, 61):
    PROMO_BOTS.append({"id": i, "platform": "SEO", "name": n, "focus": f"Optimize AgentForge for search as {n.lower()}", "model": "google/gemini-2.5-flash"})

# Email & Direct Marketing (76-85)
email_roles = [
    "Welcome Email Writer", "Nurture Sequence Designer", "Launch Email Copywriter",
    "Abandoned Cart Recoverer", "Re-engagement Specialist", "Newsletter Curator",
    "Promotional Email Designer", "Cold Email Outreach", "Follow-up Sequence Writer",
    "Thank You Page Creator",
]
for i, n in enumerate(email_roles, 76):
    PROMO_BOTS.append({"id": i, "platform": "Email", "name": n, "focus": f"Create email marketing for AgentForge as {n.lower()}", "model": "deepseek/deepseek-chat"})

# Analytics & Optimization (86-100)
analytics_roles = [
    "Conversion Tracker", "A/B Test Designer", "Funnel Analyst",
    "User Behavior Analyst", "Retention Analyst", "Churn Predictor",
    "Revenue Forecaster", "ROI Calculator", "Attribution Modeler",
    "Cohort Analyst", "Heatmap Interpreter", "Session Recorder Analyst",
    "Survey Designer", "NPS Tracker", "Customer Journey Mapper",
]
for i, n in enumerate(analytics_roles, 86):
    PROMO_BOTS.append({"id": i, "platform": "Analytics", "name": n, "focus": f"Analyze and optimize AgentForge promotions as {n.lower()}", "model": "qwen/qwen3.7-max"})

# ─── Promo Bot ─────────────────────────────────────────────────────────────

class PromoBot:
    def __init__(self, config: Dict):
        self.id = config["id"]
        self.platform = config["platform"]
        self.name = config["name"]
        self.focus = config["focus"]
        self.model = config["model"]
        self.state = self._load_state()
    
    def _load_state(self) -> Dict:
        path = PROMO_DIR / f"bot-{self.id:03d}-state.json"
        if path.exists():
            try:
                return json.loads(path.read_text())
            except:
                pass
        return {"promos": 0, "clicks": 0, "conversions": 0, "last_promo": None, "healthy": True}
    
    def _save_state(self):
        path = PROMO_DIR / f"bot-{self.id:03d}-state.json"
        path.write_text(json.dumps(self.state, indent=2))
    
    def generate_promo(self) -> Optional[Dict]:
        prompt = f"""You are {self.name}, a promotion bot for AgentForge — the AI Agent Generator & Marketplace.

Your Platform: {self.platform}
Your Focus: {self.focus}

AgentForge is a platform where users can:
- Buy pre-built AI agents (Social Media Manager, Content Writer, SEO Optimizer, etc.)
- Upgrade agents with better models (Gemini → DeepSeek → Claude Sonnet 4)
- Build custom agents by describing what they need in plain English
- Sell their customized agents on the marketplace (80% creator cut)
- Pricing: Basic $9.99/mo, Pro $29.99/mo, Enterprise $99.99/mo

Generate ONE promotion for AgentForge optimized for {self.platform}.

Include:
1. A compelling headline or hook
2. The promotion text (appropriate length for {self.platform})
3. A clear call-to-action
4. 3-5 relevant hashtags
5. Best time to post
6. Visual suggestion

Return as JSON:
{{"platform": "{self.platform}", "headline": "...", "text": "...", "cta": "...", "hashtags": ["..."], "best_time": "...", "visual": "..."}}"""
        
        result = call_ai(prompt, model=self.model, max_tokens=1000)
        if not result:
            return None
        
        try:
            start = result.find("{")
            end = result.rfind("}") + 1
            promo = json.loads(result[start:end])
            promo["bot_id"] = self.id
            promo["bot_name"] = self.name
            promo["generated_at"] = datetime.now(timezone.utc).isoformat()
            promo["status"] = "queued"
            
            self.state["promos"] += 1
            self.state["last_promo"] = promo["generated_at"]
            self._save_state()
            
            return promo
        except:
            return None
    
    def report(self) -> Dict:
        return {
            "id": self.id,
            "name": self.name,
            "platform": self.platform,
            "focus": self.focus[:30],
            "promos": self.state["promos"],
            "healthy": self.state.get("healthy", True),
        }

# ─── Promo Army ────────────────────────────────────────────────────────────

class PromoArmy:
    def __init__(self):
        self.bots = [PromoBot(c) for c in PROMO_BOTS]
        self.state = self._load_state()
        self.content_queue = self._load_content()
    
    def _load_state(self) -> Dict:
        if STATE_FILE.exists():
            try:
                return json.loads(STATE_FILE.read_text())
            except:
                pass
        return {"runs": 0, "total_promos": 0, "last_deployment": None}
    
    def _save_state(self):
        STATE_FILE.write_text(json.dumps(self.state, indent=2))
    
    def _load_content(self) -> List[Dict]:
        if CONTENT_FILE.exists():
            try:
                return json.loads(CONTENT_FILE.read_text())
            except:
                pass
        return []
    
    def _save_content(self):
        CONTENT_FILE.write_text(json.dumps(self.content_queue[-500:], indent=2))
    
    def deploy_all(self) -> Dict:
        print(f"\n{'='*60}")
        print(f"📢 AGENTFORGE PROMO ARMY — Deploying 100 Bots")
        print(f"   {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
        print(f"{'='*60}\n")
        
        results = {"promos_generated": 0, "healthy_bots": 0}
        
        for bot in self.bots:
            promo = bot.generate_promo()
            if promo:
                self.content_queue.append(promo)
                results["promos_generated"] += 1
                results["healthy_bots"] += 1
            time.sleep(0.2)
        
        self.state["runs"] += 1
        self.state["total_promos"] += results["promos_generated"]
        self.state["last_deployment"] = datetime.now(timezone.utc).isoformat()
        self._save_state()
        self._save_content()
        
        print(f"\n📊 DEPLOYMENT RESULTS")
        print(f"{'='*40}")
        print(f"   Bots deployed: {results['healthy_bots']}/100")
        print(f"   Promos generated: {results['promos_generated']}")
        print(f"   Total all time: {self.state['total_promos']}")
        
        return results
    
    def report(self) -> Dict:
        return {
            "state": self.state,
            "bots": [b.report() for b in self.bots],
            "queue_size": len(self.content_queue),
        }

def main():
    import argparse
    parser = argparse.ArgumentParser(description="AgentForge Promo Army")
    parser.add_argument("--deploy", action="store_true", help="Deploy all 100 promo bots")
    parser.add_argument("--report", action="store_true", help="Promo army report")
    parser.add_argument("--list", action="store_true", help="List all 100 bots")
    args = parser.parse_args()
    
    print(f"\n{'='*60}")
    print(f"📢 AGENTFORGE PROMO ARMY")
    print(f"   {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
    print(f"{'='*60}\n")
    
    army = PromoArmy()
    
    if args.list:
        print(f"{'ID':>4s} | {'Platform':15s} | {'Name':30s} | {'Focus':35s} | {'Promos':>6s}")
        print("-" * 95)
        for bot in army.bots:
            r = bot.report()
            print(f"{r['id']:4d} | {r['platform']:15s} | {r['name']:30s} | {r['focus']:35s} | {r['promos']:6d}")
        return
    
    if args.report:
        report = army.report()
        print(f"📊 PROMO ARMY REPORT")
        print(f"{'='*40}")
        print(f"   Runs: {report['state']['runs']}")
        print(f"   Total Promos: {report['state']['total_promos']}")
        print(f"   Queue Size: {report['queue_size']}")
        print(f"\n   Bot Breakdown:")
        platforms = {}
        for b in report['bots']:
            p = b['platform']
            platforms[p] = platforms.get(p, 0) + 1
        for p, c in sorted(platforms.items()):
            print(f"     {p:15s}: {c} bots")
        return
    
    if args.deploy:
        army.deploy_all()
        return
    
    # Default: deploy
    army.deploy_all()

if __name__ == "__main__":
    main()
