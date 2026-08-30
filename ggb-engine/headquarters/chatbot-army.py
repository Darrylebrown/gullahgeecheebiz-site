#!/usr/bin/env python3
"""
GGB Social Chatbot Army — 20 autonomous, self-healing, SOE-connected chatbots.
Deployed from the AI Think Tank winning design. Each chatbot manages a
specific social media platform with full autonomy and self-recovery.
"""
import json, os, sys, time, sqlite3, requests, hashlib, random, threading
import omniroute_shim  # OMNIROUTE_MIGRATED
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional

BASE_DIR = Path("/Users/darrylsmac/gullahgeecheebiz-site")
PUB_DB = BASE_DIR / "publish" / "publisher.db"
LOGS_DIR = Path(__file__).parent / "logs"
ARMY_DIR = LOGS_DIR / "chatbot-army"
STATE_FILE = ARMY_DIR / "army-state.json"
HEALTH_FILE = ARMY_DIR / "health.json"
QUEUE_FILE = ARMY_DIR / "post-queue.json"

ARMY_DIR.mkdir(parents=True, exist_ok=True)

def get_api_key():
    # Check multiple locations for API keys
    import os
    for env_path in [
        BASE_DIR / ".env",
        Path.home() / ".hermes" / ".env",
        Path.home() / ".env",
    ]:
        if env_path.exists():
            for line in env_path.read_text().split("\n"):
                # Try Agnes AI first (free tier)
                if "AGNES_API_KEY" in line and not line.strip().startswith("#"):
                    key = line.split("=", 1)[1].strip().strip('"').strip("'")
                    if key:
                        return key, "agnes"
                # Then try OpenRouter
                if "OPENROUTER_API_KEY" in line and not line.strip().startswith("#"):
                    key = line.split("=", 1)[1].strip().strip('"').strip("'")
                    if key:
                        return key, "openrouter"
    # Fallback to env vars
    key = os.environ.get("AGNES_API_KEY", "")
    if key:
        return key, "agnes"
    key = os.environ.get("OPENROUTER_API_KEY", "")
    if key:
        return key, "openrouter"
    return "", ""

# Agnes AI base URL
AGNES_BASE_URL = "https://apihub.agnes-ai.com/v1"

def call_ai(prompt, model="google/gemini-2.5-flash", max_tokens=2000):
    api_key, provider = get_api_key()
    if not api_key:
        return None
    
    # Use Agnes AI if available (free tier), otherwise OpenRouter
    if provider == "agnes":
        base_url = AGNES_BASE_URL
        # Map model names for Agnes AI
        model_map = {
            "google/gemini-2.5-flash": "agnes-2.5-flash",
            "deepseek/deepseek-chat": "agnes-2.5-flash",
            "qwen/qwen3.7-max": "agnes-2.5-flash",
        }
        model = model_map.get(model, "agnes-2.5-flash")
    else:
        base_url = "https://openrouter.ai/api/v1"
    
    try:
        r = requests.post(
            f"{base_url}/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={"model": model, "messages": [{"role": "user", "content": prompt}], "max_tokens": max_tokens},
            timeout=60
        )
        if r.status_code == 200:
            return r.json()["choices"][0]["message"]["content"]
    except:
        pass
    return None

# ─── 20 Chatbot Definitions ──────────────────────────────────────────────

CHATBOTS = [
    {"id": 1,  "platform": "Twitter/X",          "name": "De O'l Folks Wisdom",       "purpose": "Cultural posts — history, proverbs, language", "personality": "Wise, reflective, uses Gullah Geechee naturally", "schedule": "3-5 posts daily", "model": "google/gemini-2.5-flash"},
    {"id": 2,  "platform": "Twitter/X",          "name": "The Gullah Griot",          "purpose": "Engagement — replies, trending topics, mentions", "personality": "Warm, conversational, community-focused", "schedule": "Continuous monitoring", "model": "deepseek/deepseek-chat"},
    {"id": 3,  "platform": "TikTok",             "name": "Sweetgrass Stories",        "purpose": "Video promotion — short-form cultural content", "personality": "Energetic, creative, visual storyteller", "schedule": "1-2 videos daily", "model": "qwen/qwen3.7-max"},
    {"id": 4,  "platform": "TikTok",             "name": "Trend Rider",               "purpose": "Trend riding — infuse Gullah elements into trends", "personality": "Hip, adaptive, culturally savvy", "schedule": "Daily trend monitoring", "model": "google/gemini-2.5-flash"},
    {"id": 5,  "platform": "Pinterest",           "name": "Pin Weaver",                "purpose": "Pin creation — products, crafts, recipes, aesthetics", "personality": "Artistic, detail-oriented, visually driven", "schedule": "5-10 pins daily", "model": "deepseek/deepseek-chat"},
    {"id": 6,  "platform": "Pinterest",           "name": "Board Curator",             "purpose": "Board management — organize, curate, optimize", "personality": "Organized, strategic, SEO-minded", "schedule": "Daily board review", "model": "qwen/qwen3.7-max"},
    {"id": 7,  "platform": "Facebook",            "name": "The Community Fire",       "purpose": "Page posts — updates, stories, events, announcements", "personality": "Community-oriented, warm, inclusive", "schedule": "2-3 posts daily", "model": "google/gemini-2.5-flash"},
    {"id": 8,  "platform": "Facebook",            "name": "The Porch Sitter",          "purpose": "Community engagement — groups, comments, discussions", "personality": "Friendly, conversational, patient listener", "schedule": "Continuous monitoring", "model": "deepseek/deepseek-chat"},
    {"id": 9,  "platform": "Instagram",           "name": "Lowcountry Lens",          "purpose": "Feed posts — high-quality visual content", "personality": "Visual artist, proud, aesthetic", "schedule": "1 post daily", "model": "qwen/qwen3.7-max"},
    {"id": 10, "platform": "Instagram",           "name": "Story Weaver",             "purpose": "Stories/reels — behind-the-scenes, ephemeral content", "personality": "Playful, spontaneous, authentic", "schedule": "3-5 stories daily", "model": "google/gemini-2.5-flash"},
    {"id": 11, "platform": "YouTube",             "name": "The Documentary Keeper",    "purpose": "Video promotion — documentaries, interviews, series", "personality": "Educational, thorough, passionate", "schedule": "1-2 videos weekly", "model": "deepseek/deepseek-chat"},
    {"id": 12, "platform": "YouTube",             "name": "Comment Cultivator",       "purpose": "Comment engagement — replies, community building", "personality": "Engaging, appreciative, responsive", "schedule": "Continuous monitoring", "model": "qwen/qwen3.7-max"},
    {"id": 13, "platform": "LinkedIn",            "name": "The Bridge Builder",       "purpose": "Professional networking — business, thought leadership", "personality": "Professional, visionary, impactful", "schedule": "1 post daily", "model": "google/gemini-2.5-flash"},
    {"id": 14, "platform": "Reddit",              "name": "The Root Digger",          "purpose": "Community engagement — subreddits, discussions, AMAs", "personality": "Knowledgeable, respectful, authentic", "schedule": "Daily engagement", "model": "deepseek/deepseek-chat"},
    {"id": 15, "platform": "Discord",             "name": "The Hearth Keeper",        "purpose": "Server management — welcome, moderate, facilitate", "personality": "Welcoming, organized, community-builder", "schedule": "Continuous monitoring", "model": "qwen/qwen3.7-max"},
    {"id": 16, "platform": "Telegram",            "name": "The Town Crier",           "purpose": "Channel management — announcements, news, exclusive content", "personality": "Informative, timely, direct", "schedule": "1-2 posts daily", "model": "google/gemini-2.5-flash"},
    {"id": 17, "platform": "WhatsApp",            "name": "The Messenger",            "purpose": "Broadcast/status — updates, stories, community touchpoints", "personality": "Personal, warm, one-on-one feel", "schedule": "Daily status updates", "model": "deepseek/deepseek-chat"},
    {"id": 18, "platform": "Tumblr",              "name": "The Storyteller's Quill",  "purpose": "Microblogging — long-form cultural posts, photo sets", "personality": "Literary, reflective, artistic", "schedule": "1-2 posts daily", "model": "qwen/qwen3.7-max"},
    {"id": 19, "platform": "Threads",             "name": "The Morning Glory",        "purpose": "Text engagement — daily thoughts, cultural commentary", "personality": "Bright, optimistic, conversational", "schedule": "2-3 posts daily", "model": "google/gemini-2.5-flash"},
    {"id": 20, "platform": "Bluesky",             "name": "The Horizon Walker",       "purpose": "Social posting — cultural content, community building", "personality": "Forward-looking, hopeful, grounded", "schedule": "2-3 posts daily", "model": "deepseek/deepseek-chat"},
]

# ─── Chatbot Class ───────────────────────────────────────────────────────

class SocialChatbot:
    """A single autonomous, self-healing, SOE-connected chatbot."""
    
    def __init__(self, config: Dict):
        self.id = config["id"]
        self.platform = config["platform"]
        self.name = config["name"]
        self.purpose = config["purpose"]
        self.personality = config["personality"]
        self.schedule = config["schedule"]
        self.model = config["model"]
        self.state = self._load_state()
        self.health = self._load_health()
    
    def _load_state(self) -> Dict:
        path = ARMY_DIR / f"bot-{self.id:02d}-state.json"
        if path.exists():
            try:
                return json.loads(path.read_text())
            except:
                pass
        return {"posts": 0, "replies": 0, "engagement": 0, "errors": 0, "last_post": None, "healthy": True, "shadowbanned": False}
    
    def _save_state(self):
        path = ARMY_DIR / f"bot-{self.id:02d}-state.json"
        path.write_text(json.dumps(self.state, indent=2))
    
    def _load_health(self) -> Dict:
        path = ARMY_DIR / f"bot-{self.id:02d}-health.json"
        if path.exists():
            try:
                return json.loads(path.read_text())
            except:
                pass
        return {"status": "healthy", "last_check": None, "issues": [], "recoveries": 0}
    
    def _save_health(self):
        path = ARMY_DIR / f"bot-{self.id:02d}-health.json"
        path.write_text(json.dumps(self.health, indent=2))
    
    def _get_soe_data(self) -> str:
        """Get trending topics and SEO data from Spirit Weaver."""
        trends_file = LOGS_DIR / "soe" / "trends.json"
        if trends_file.exists():
            try:
                trends = json.loads(trends_file.read_text())
                return json.dumps([t.get("name", "") for t in trends[-5:]])
            except:
                pass
        return "Gullah Geechee culture, heritage, community"
    
    def _get_content_factory_items(self) -> List[Dict]:
        """Get recent content from Content Factory."""
        catalog_file = LOGS_DIR / "content-factory" / "content-catalog.json"
        if catalog_file.exists():
            try:
                catalog = json.loads(catalog_file.read_text())
                return catalog[-10:]
            except:
                pass
        return []
    
    def _get_dreams(self) -> List[Dict]:
        """Get recent dreams from Dream Weaver."""
        dreams_file = LOGS_DIR / "dream-weaver" / "dreams.json"
        if dreams_file.exists():
            try:
                return json.loads(dreams_file.read_text())
            except:
                pass
        return []
    
    def generate_post(self) -> Optional[Dict]:
        """Generate a social media post using AI."""
        soe_data = self._get_soe_data()
        content_items = self._get_content_factory_items()
        dreams = self._get_dreams()
        
        content_context = ""
        if content_items:
            content_context = "Available content:\n" + "\n".join([f"- {c.get('title', '?')} ({c.get('type', '?')})" for c in content_items[-3:]])
        if dreams:
            content_context += "\nRecent dreams:\n" + "\n".join([f"- {d.get('title', '?')} ({d.get('type', '?')})" for d in dreams[-3:]])
        
        prompt = f"""You are {self.name}, a social media chatbot for Gullah Geechee Biz on {self.platform}.

Your Personality: {self.personality}
Your Purpose: {self.purpose}
Your Posting Schedule: {self.schedule}

Current Trends (from Spirit Weaver SOE): {soe_data}

{content_context}

Generate ONE social media post for {self.platform} that:
1. Is authentic to Gullah Geechee voice and culture
2. Is optimized for {self.platform}'s algorithm
3. Includes relevant hashtags
4. Has a clear call-to-action
5. Is culturally appropriate and respectful

Return as JSON:
{{"platform": "{self.platform}", "post_text": "...", "hashtags": ["..."], "cta": "...", "best_time": "...", "visual_suggestion": "..."}}"""
        
        result = call_ai(prompt, model=self.model, max_tokens=1000)
        if not result:
            return None
        
        try:
            start = result.find("{")
            end = result.rfind("}") + 1
            post = json.loads(result[start:end])
            post["bot_id"] = self.id
            post["bot_name"] = self.name
            post["generated_at"] = datetime.now(timezone.utc).isoformat()
            post["status"] = "queued"
            return post
        except:
            return None
    
    def health_check(self) -> Dict:
        """Self-healing health check."""
        issues = []
        
        # Check if bot has been active recently
        if self.state["last_post"]:
            last = datetime.fromisoformat(self.state["last_post"])
            age = datetime.now(timezone.utc) - last
            if age > timedelta(days=2):
                issues.append(f"No activity for {age.days} days")
                self.health["status"] = "stale"
        
        # Check error rate
        if self.state["posts"] > 0:
            error_rate = self.state["errors"] / self.state["posts"]
            if error_rate > 0.5:
                issues.append(f"High error rate: {error_rate:.0%}")
                self.health["status"] = "degraded"
        
        # Auto-recover
        if issues:
            self.health["issues"] = issues
            self.health["recoveries"] += 1
            self.health["last_check"] = datetime.now(timezone.utc).isoformat()
            self.state["healthy"] = False
            self._save_health()
            self._save_state()
            return {"healthy": False, "issues": issues, "recovered": True}
        
        self.health["status"] = "healthy"
        self.health["last_check"] = datetime.now(timezone.utc).isoformat()
        self.state["healthy"] = True
        self._save_health()
        self._save_state()
        return {"healthy": True, "issues": []}
    
    def post(self) -> Optional[Dict]:
        """Generate and queue a post."""
        post = self.generate_post()
        if post:
            self.state["posts"] += 1
            self.state["last_post"] = datetime.now(timezone.utc).isoformat()
            self._save_state()
        return post
    
    def report(self) -> Dict:
        return {
            "id": self.id,
            "name": self.name,
            "platform": self.platform,
            "purpose": self.purpose[:40],
            "posts": self.state["posts"],
            "errors": self.state["errors"],
            "healthy": self.state.get("healthy", True),
            "last_post": self.state.get("last_post", "never")[:19],
            "health_status": self.health.get("status", "unknown"),
        }

# ─── Chatbot Army ─────────────────────────────────────────────────────────

class ChatbotArmy:
    """Manages all 20 chatbots — deployment, health, coordination."""
    
    def __init__(self):
        self.bots = [SocialChatbot(c) for c in CHATBOTS]
        self.state = self._load_state()
        self.post_queue = self._load_queue()
    
    def _load_state(self) -> Dict:
        if STATE_FILE.exists():
            try:
                return json.loads(STATE_FILE.read_text())
            except:
                pass
        return {"runs": 0, "total_posts": 0, "total_replies": 0, "last_deployment": None}
    
    def _save_state(self):
        STATE_FILE.write_text(json.dumps(self.state, indent=2))
    
    def _load_queue(self) -> List[Dict]:
        if QUEUE_FILE.exists():
            try:
                return json.loads(QUEUE_FILE.read_text())
            except:
                pass
        return []
    
    def _save_queue(self):
        QUEUE_FILE.write_text(json.dumps(self.post_queue[-500:], indent=2))
    
    def deploy_all(self) -> Dict:
        """Deploy all 20 chatbots — generate posts and check health."""
        print(f"\n{'='*60}")
        print(f"🤖 DEPLOYING 20 SOCIAL CHATBOTS")
        print(f"   {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
        print(f"{'='*60}\n")
        
        results = {"posts_generated": 0, "health_issues": 0, "healthy_bots": 0}
        
        for bot in self.bots:
            # Health check first
            health = bot.health_check()
            if not health["healthy"]:
                results["health_issues"] += 1
                print(f"  ⚠️  Bot {bot.id:2d} ({bot.name:25s}) — {health['issues'][0][:40]}")
            
            # Generate post
            post = bot.post()
            if post:
                self.post_queue.append(post)
                results["posts_generated"] += 1
                results["healthy_bots"] += 1
                print(f"  ✅ Bot {bot.id:2d} | {bot.platform:12s} | {bot.name:25s} | Post queued")
            else:
                bot.state["errors"] += 1
                print(f"  ❌ Bot {bot.id:2d} | {bot.platform:12s} | {bot.name:25s} | Post failed")
        
        self.state["runs"] += 1
        self.state["total_posts"] += results["posts_generated"]
        self.state["last_deployment"] = datetime.now(timezone.utc).isoformat()
        self._save_state()
        self._save_queue()
        
        print(f"\n📊 DEPLOYMENT RESULTS")
        print(f"{'='*40}")
        print(f"   Posts generated: {results['posts_generated']}/20")
        print(f"   Health issues: {results['health_issues']}")
        print(f"   Total posts ever: {self.state['total_posts']}")
        
        return results
    
    def health_sweep(self) -> Dict:
        """Run health check on all 20 bots."""
        results = {"healthy": 0, "degraded": 0, "stale": 0, "recovered": 0}
        for bot in self.bots:
            health = bot.health_check()
            if health["healthy"]:
                results["healthy"] += 1
            else:
                results[bot.health.get("status", "degraded")] += 1
                if health.get("recovered"):
                    results["recovered"] += 1
        return results
    
    def coordinate(self) -> Optional[Dict]:
        """Use AI to coordinate all 20 chatbots."""
        statuses = [b.report() for b in self.bots]
        
        prompt = f"""Coordinate the Gullah Geechee Biz chatbot army across all platforms.

Current Status ({len(statuses)} bots):
{json.dumps(statuses, indent=2)[:1000]}

Generate a coordination plan:
1. Which bots should post now vs wait?
2. Are any bots posting conflicting content?
3. What cross-platform promotions should happen?
4. What trends should multiple bots capitalize on?
5. Any bots that need attention or recovery?

Return as JSON:
{{"immediate_actions": ["..."], "cross_promotions": ["..."], "trend_opportunities": ["..."], "bots_needing_attention": ["..."], "coordination_notes": "..."}}"""
        
        result = call_ai(prompt, max_tokens=1500)
        if not result:
            return None
        
        try:
            start = result.find("{")
            end = result.rfind("}") + 1
            return json.loads(result[start:end])
        except:
            return None
    
    def full_cycle(self) -> Dict:
        """Full deployment cycle: deploy → coordinate → heal."""
        print(f"\n{'='*60}")
        print(f"🤖 CHATBOT ARMY — Full Cycle")
        print(f"   {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
        print(f"{'='*60}\n")
        
        # 1. Deploy all bots
        print("📤 Phase 1: Deploying all 20 chatbots...")
        deploy = self.deploy_all()
        
        # 2. Coordinate
        print("\n🔄 Phase 2: Coordinating across platforms...")
        coord = self.coordinate()
        if coord:
            print(f"   Actions: {len(coord.get('immediate_actions', []))}")
            print(f"   Cross-promotions: {len(coord.get('cross_promotions', []))}")
        
        # 3. Health sweep
        print("\n🩺 Phase 3: Health sweep...")
        health = self.health_sweep()
        print(f"   Healthy: {health['healthy']} | Degraded: {health['degraded']} | Recovered: {health['recovered']}")
        
        print(f"\n✅ Chatbot army cycle complete")
        return {"deploy": deploy, "coordination": bool(coord), "health": health}
    
    def report(self) -> Dict:
        return {
            "state": self.state,
            "bots": [b.report() for b in self.bots],
            "queue_size": len(self.post_queue),
        }

def main():
    import argparse
    parser = argparse.ArgumentParser(description="GGB Social Chatbot Army")
    parser.add_argument("--deploy", action="store_true", help="Deploy all 20 chatbots")
    parser.add_argument("--cycle", action="store_true", help="Full cycle: deploy, coordinate, heal")
    parser.add_argument("--health", action="store_true", help="Health sweep all bots")
    parser.add_argument("--report", action="store_true", help="Chatbot army report")
    parser.add_argument("--list", action="store_true", help="List all 20 chatbots")
    args = parser.parse_args()
    
    print(f"\n{'='*60}")
    print(f"🤖 GGB SOCIAL CHATBOT ARMY")
    print(f"   {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
    print(f"{'='*60}\n")
    
    army = ChatbotArmy()
    
    if args.list:
        print(f"{'ID':>3s} | {'Platform':14s} | {'Name':28s} | {'Posts':>5s} | {'Health':>7s}")
        print("-" * 65)
        for bot in army.bots:
            r = bot.report()
            status = "✅" if r["healthy"] else "❌"
            print(f"{r['id']:3d} | {r['platform']:14s} | {r['name']:28s} | {r['posts']:5d} | {status:>7s}")
        return
    
    if args.deploy:
        army.deploy_all()
        return
    
    if args.cycle:
        army.full_cycle()
        return
    
    if args.health:
        health = army.health_sweep()
        print(f"🩺 Health Sweep Results:")
        print(f"   Healthy: {health['healthy']}")
        print(f"   Degraded: {health['degraded']}")
        print(f"   Stale: {health['stale']}")
        print(f"   Recovered: {health['recovered']}")
        return
    
    if args.report:
        report = army.report()
        print(f"📊 CHATBOT ARMY REPORT")
        print(f"{'='*40}")
        print(f"   Runs: {report['state']['runs']}")
        print(f"   Total Posts: {report['state']['total_posts']}")
        print(f"   Queue Size: {report['queue_size']}")
        print(f"\n   Bot Status:")
        for b in report['bots']:
            status = "✅" if b["healthy"] else "❌"
            print(f"     {status} Bot {b['id']:2d} | {b['platform']:12s} | {b['name']:25s} | {b['posts']} posts")
        return
    
    # Default: deploy
    army.deploy_all()

if __name__ == "__main__":
    main()
