#!/usr/bin/env python3
"""
GGB Social Media SOE — autonomous, self-healing, self-improving social media
optimization engine. Wires Twitter/X, TikTok, Pinterest, Facebook, Instagram
into the Spirit Weaver for continuous optimization and connectivity.
"""
import json, os, sys, time, sqlite3, requests, re, random
import omniroute_shim  # OMNIROUTE_MIGRATED
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional

BASE_DIR = Path("/Users/darrylsmac/gullahgeecheebiz-site")
PUB_DB = BASE_DIR / "publish" / "publisher.db"
LOGS_DIR = Path(__file__).parent / "logs"
SOCIAL_DIR = LOGS_DIR / "social-soe"
STATE_FILE = SOCIAL_DIR / "social-soe-state.json"
CONTENT_FILE = SOCIAL_DIR / "content-queue.json"
PERFORMANCE_FILE = SOCIAL_DIR / "platform-performance.json"

SOCIAL_DIR.mkdir(parents=True, exist_ok=True)

def get_api_key():
    env_file = BASE_DIR / ".env"
    if env_file.exists():
        for line in env_file.read_text().split("\n"):
            if "OPENROUTER_API_KEY" in line:
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    return ""

def call_ai(prompt, max_tokens=2000):
    api_key = get_api_key()
    if not api_key:
        return None
    try:
        r = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={"model": "google/gemini-2.5-flash", "messages": [{"role": "user", "content": prompt}], "max_tokens": max_tokens},
            timeout=30
        )
        if r.status_code == 200:
            return r.json()["choices"][0]["message"]["content"]
    except:
        pass
    return None

# ─── Platform Registry ────────────────────────────────────────────────────

PLATFORMS = {
    "twitter": {
        "name": "Twitter/X",
        "url": "https://x.com/gullahgeecheebiz",
        "char_limit": 280,
        "hashtag_limit": 3,
        "image_required": False,
        "best_times": ["7-9 AM", "12-1 PM", "5-7 PM"],
        "content_types": ["thread", "single_post", "poll", "media"],
    },
    "tiktok": {
        "name": "TikTok",
        "url": "https://www.tiktok.com/@gullahgeecheebiz",
        "char_limit": 150,
        "hashtag_limit": 5,
        "image_required": True,
        "best_times": ["7-10 AM", "11 AM-2 PM", "7-11 PM"],
        "content_types": ["video", "story"],
    },
    "pinterest": {
        "name": "Pinterest",
        "url": "https://www.pinterest.com/gullahgeecheebiz/",
        "char_limit": 500,
        "hashtag_limit": 20,
        "image_required": True,
        "best_times": ["8-11 AM", "2-4 PM", "8-11 PM"],
        "content_types": ["pin", "board", "idea_pin"],
    },
    "facebook": {
        "name": "Facebook",
        "url": "https://www.facebook.com/gullahgeecheebiz",
        "char_limit": 63206,
        "hashtag_limit": 5,
        "image_required": False,
        "best_times": ["9 AM-12 PM", "1-4 PM"],
        "content_types": ["post", "story", "event", "live"],
    },
    "instagram": {
        "name": "Instagram",
        "url": "https://www.instagram.com/gullahgeecheebiz/",
        "char_limit": 2200,
        "hashtag_limit": 30,
        "image_required": True,
        "best_times": ["9-11 AM", "11 AM-1 PM", "7-9 PM"],
        "content_types": ["post", "story", "reel", "carousel"],
    },
}

# ─── Social Media SOE ─────────────────────────────────────────────────────

class SocialMediaSOE:
    """Autonomous, self-healing, self-improving social media optimization engine."""
    
    def __init__(self):
        self.api_key = get_api_key()
        self.state = self._load_state()
        self.content_queue = self._load_content_queue()
        self.performance = self._load_performance()
    
    def _load_state(self) -> Dict:
        if STATE_FILE.exists():
            try:
                return json.loads(STATE_FILE.read_text())
            except:
                pass
        return {
            "runs": 0, "posts_generated": 0, "optimizations": 0,
            "healing_actions": 0, "last_cycle": None,
            "platform_states": {k: {"healthy": True, "last_post": None, "errors": 0} for k in PLATFORMS}
        }
    
    def _save_state(self):
        STATE_FILE.write_text(json.dumps(self.state, indent=2))
    
    def _load_content_queue(self) -> List[Dict]:
        if CONTENT_FILE.exists():
            try:
                return json.loads(CONTENT_FILE.read_text())
            except:
                pass
        return []
    
    def _save_content_queue(self):
        CONTENT_FILE.write_text(json.dumps(self.content_queue[-200:], indent=2))
    
    def _load_performance(self) -> Dict:
        if PERFORMANCE_FILE.exists():
            try:
                return json.loads(PERFORMANCE_FILE.read_text())
            except:
                pass
        return {
            "total_posts": 0, "avg_engagement": 0,
            "best_platform": None, "best_content_type": None,
            "platform_metrics": {k: {"posts": 0, "engagement": 0, "best_time": ""} for k in PLATFORMS}
        }
    
    def _save_performance(self):
        PERFORMANCE_FILE.write_text(json.dumps(self.performance, indent=2))
    
    def _get_books(self) -> List[Dict]:
        """Get published books for content generation."""
        try:
            conn = sqlite3.connect(str(PUB_DB))
            rows = conn.execute(
                "SELECT manifest_id, data FROM manifests WHERE state = 'published' ORDER BY RANDOM() LIMIT 20"
            ).fetchall()
            conn.close()
            
            books = []
            for mid, data_json in rows:
                try:
                    data = json.loads(data_json) if data_json else {}
                except:
                    data = {}
                title = data.get("title", mid)
                if isinstance(title, dict):
                    title = title.get("canonical", str(title))
                books.append({"manifest_id": mid, "title": str(title)})
            return books
        except:
            return []
    
    # ─── CONTENT GENERATION ─────────────────────────────────────────────
    
    def generate_post(self, platform: str, book: Dict) -> Optional[Dict]:
        """Generate an optimized social media post for a specific platform."""
        platform_info = PLATFORMS.get(platform)
        if not platform_info:
            return None
        
        prompt = f"""Generate a social media post for {platform_info['name']} promoting this book.

Book: {book['title']}
Publisher: Gullah Geechee Biz
Platform: {platform_info['name']}
Character limit: {platform_info['char_limit']}
Max hashtags: {platform_info['hashtag_limit']}

Requirements:
- Engaging and authentic Gullah Geechee voice
- Under character limit
- Include relevant hashtags (max {platform_info['hashtag_limit']})
- Include a call-to-action
- Optimized for {platform_info['name']}'s algorithm
- Culturally appropriate

Return as JSON:
{{"post_text": "...", "hashtags": ["...", "..."], "cta": "...", "best_time": "...", "alt_text": "..."}}"""
        
        result = call_ai(prompt, max_tokens=1000)
        if not result:
            return None
        
        try:
            start = result.find("{")
            end = result.rfind("}") + 1
            post = json.loads(result[start:end])
            post["platform"] = platform
            post["book_title"] = book["title"]
            post["generated_at"] = datetime.now(timezone.utc).isoformat()
            post["status"] = "queued"
            return post
        except:
            return None
    
    def generate_all_platform_posts(self, book: Optional[Dict] = None) -> List[Dict]:
        """Generate posts for all platforms for a given book."""
        if not book:
            books = self._get_books()
            if not books:
                return []
            book = random.choice(books)
        
        posts = []
        for platform in PLATFORMS:
            post = self.generate_post(platform, book)
            if post:
                posts.append(post)
                self.content_queue.append(post)
                self.state["posts_generated"] += 1
        
        self._save_content_queue()
        self._save_state()
        return posts
    
    # ─── PLATFORM HEALTH CHECK ──────────────────────────────────────────
    
    def check_platform_health(self) -> Dict:
        """Check if social platforms are accessible and healthy."""
        results = {}
        for key, info in PLATFORMS.items():
            try:
                r = requests.get(info["url"], timeout=10, allow_redirects=True)
                healthy = r.status_code < 500
                results[key] = {
                    "healthy": healthy,
                    "status_code": r.status_code,
                    "url": info["url"],
                }
                self.state["platform_states"][key]["healthy"] = healthy
                if not healthy:
                    self.state["platform_states"][key]["errors"] += 1
                    self.state["healing_actions"] += 1
            except:
                results[key] = {
                    "healthy": False,
                    "status_code": 0,
                    "url": info["url"],
                }
                self.state["platform_states"][key]["healthy"] = False
                self.state["platform_states"][key]["errors"] += 1
                self.state["healing_actions"] += 1
        
        self._save_state()
        return results
    
    def heal_platform(self, platform: str) -> Optional[str]:
        """Generate a healing strategy for a broken platform connection."""
        info = PLATFORMS.get(platform)
        if not info:
            return None
        
        prompt = f"""Generate a healing strategy for {info['name']} social media account.

Platform: {info['name']}
URL: {info['url']}
Issue: Account may be unreachable or having connection problems

Generate a step-by-step recovery plan:
1. Check if the account is still active
2. Verify API access or login credentials
3. Test posting capability
4. Re-establish connection
5. Verify content is still visible

Return as JSON:
{{"diagnosis": "...", "steps": ["...", "..."], "verification": "...", "prevention": "..."}}"""
        
        result = call_ai(prompt, max_tokens=1000)
        if not result:
            return None
        
        try:
            start = result.find("{")
            end = result.rfind("}") + 1
            strategy = json.loads(result[start:end])
            strategy["platform"] = platform
            strategy["healed_at"] = datetime.now(timezone.utc).isoformat()
            self.state["healing_actions"] += 1
            self._save_state()
            return strategy
        except:
            return None
    
    def heal_all_platforms(self) -> List[Dict]:
        """Check and heal all platforms."""
        health = self.check_platform_health()
        healed = []
        for key, status in health.items():
            if not status["healthy"]:
                strategy = self.heal_platform(key)
                if strategy:
                    healed.append(strategy)
        return healed
    
    # ─── CONTENT OPTIMIZATION ───────────────────────────────────────────
    
    def optimize_content(self, platform: str, post_text: str) -> Optional[Dict]:
        """Optimize existing content for better engagement."""
        info = PLATFORMS.get(platform)
        if not info:
            return None
        
        prompt = f"""Optimize this social media post for better engagement on {info['name']}.

Platform: {info['name']}
Current Post: {post_text}
Character limit: {info['char_limit']}

Optimize for:
1. Higher engagement (likes, shares, comments)
2. Better algorithm ranking
3. Clearer call-to-action
4. More compelling hook
5. Better hashtag strategy

Return as JSON:
{{"optimized_text": "...", "hashtags": ["..."], "hook": "...", "improvements": ["...", "..."], "expected_boost": "..."}}"""
        
        result = call_ai(prompt, max_tokens=1000)
        if not result:
            return None
        
        try:
            start = result.find("{")
            end = result.rfind("}") + 1
            opt = json.loads(result[start:end])
            opt["platform"] = platform
            opt["optimized_at"] = datetime.now(timezone.utc).isoformat()
            self.state["optimizations"] += 1
            self._save_state()
            return opt
        except:
            return None
    
    def optimize_content_queue(self) -> List[Dict]:
        """Optimize all queued content."""
        optimized = []
        for item in self.content_queue:
            if item.get("status") == "queued":
                opt = self.optimize_content(item["platform"], item["post_text"])
                if opt:
                    item["optimized"] = opt
                    item["status"] = "optimized"
                    optimized.append(opt)
        self._save_content_queue()
        return optimized
    
    # ─── STRATEGY GENERATION ────────────────────────────────────────────
    
    def generate_strategy(self) -> Optional[Dict]:
        """Generate a social media strategy based on performance."""
        books = self._get_books()
        
        prompt = f"""Generate a social media strategy for Gullah Geechee Biz.

Current State:
- Books available: {len(books)}
- Platforms: {', '.join(PLATFORMS.keys())}
- Content queued: {len(self.content_queue)}
- Total posts generated: {self.state['posts_generated']}
- Total optimizations: {self.state['optimizations']}

Generate a strategy for:
1. Best posting schedule across all platforms
2. Content mix (promotional vs. cultural vs. educational)
3. Cross-platform promotion strategy
4. Hashtag strategy
5. Engagement growth tactics
6. How to integrate with Spirit Weaver SOE

Return as JSON:
{{"posting_schedule": {{"twitter": "...", "tiktok": "...", "pinterest": "...", "facebook": "...", "instagram": "..."}}, "content_mix": {{"promotional": 0, "cultural": 0, "educational": 0, "behind_scenes": 0}}, "hashtag_strategy": "...", "growth_tactics": ["...", "..."], "soe_integration": "..."}}"""
        
        result = call_ai(prompt, max_tokens=2000)
        if not result:
            return None
        
        try:
            start = result.find("{")
            end = result.rfind("}") + 1
            return json.loads(result[start:end])
        except:
            return None
    
    # ─── TREND DETECTION ────────────────────────────────────────────────
    
    def detect_trends(self) -> List[Dict]:
        """Detect trending topics relevant to Gullah Geechee content."""
        prompt = """Detect 5 trending topics right now that are relevant to Gullah Geechee culture, African American heritage, self-publishing, or cultural preservation.

For each trend:
- Trend name
- Which platform it's trending on
- Why it matters to Gullah Geechee Biz
- Suggested content type
- Urgency (high/medium/low)

Return as JSON array:
[{"trend": "...", "platform": "...", "relevance": "...", "content_type": "...", "urgency": "..."}]"""
        
        result = call_ai(prompt, max_tokens=1000)
        if not result:
            return []
        
        try:
            start = result.find("[")
            end = result.rfind("]") + 1
            trends = json.loads(result[start:end])
            for t in trends:
                t["detected_at"] = datetime.now(timezone.utc).isoformat()
            return trends
        except:
            return []
    
    # ─── FULL CYCLE ─────────────────────────────────────────────────────
    
    def full_cycle(self) -> Dict:
        """Run full social media SOE cycle."""
        print(f"\n{'='*60}")
        print(f"📱 SOCIAL MEDIA SOE — Full Cycle")
        print(f"   {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
        print(f"{'='*60}\n")
        
        results = {}
        
        # 1. Health check all platforms
        print("🩺 Step 1: Platform health check...")
        health = self.check_platform_health()
        healthy = sum(1 for h in health.values() if h["healthy"])
        results["health"] = {"total": len(health), "healthy": healthy}
        print(f"   {healthy}/{len(health)} platforms healthy")
        
        # 2. Heal any broken platforms
        if healthy < len(health):
            print("🔧 Step 2: Healing broken platforms...")
            healed = self.heal_all_platforms()
            results["healed"] = len(healed)
            print(f"   Healed {len(healed)} platforms")
        
        # 3. Generate content for all platforms
        print("📝 Step 3: Generating content...")
        books = self._get_books()
        posts_generated = 0
        for book in books[:3]:  # Generate for 3 books
            posts = self.generate_all_platform_posts(book)
            posts_generated += len(posts)
        results["posts_generated"] = posts_generated
        print(f"   Generated {posts_generated} posts")
        
        # 4. Optimize queued content
        print("✨ Step 4: Optimizing content...")
        optimized = self.optimize_content_queue()
        results["optimized"] = len(optimized)
        print(f"   Optimized {len(optimized)} posts")
        
        # 5. Detect trends
        print("🔮 Step 5: Detecting trends...")
        trends = self.detect_trends()
        results["trends"] = len(trends)
        for t in trends[:3]:
            print(f"   📈 {t.get('trend', '?')} — {t.get('platform', '?')} ({t.get('urgency', '?')})")
        
        # 6. Generate strategy
        print("🧠 Step 6: Generating strategy...")
        strategy = self.generate_strategy()
        results["strategy"] = bool(strategy)
        if strategy:
            print(f"   Strategy generated")
        
        self.state["runs"] += 1
        self.state["last_cycle"] = datetime.now(timezone.utc).isoformat()
        self._save_state()
        
        print(f"\n✅ Social SOE cycle complete")
        return results
    
    def report(self) -> Dict:
        """Full social media SOE report."""
        return {
            "state": self.state,
            "content_queue": len(self.content_queue),
            "performance": self.performance,
            "platforms": {k: self.state["platform_states"].get(k, {}) for k in PLATFORMS},
        }

def main():
    import argparse
    parser = argparse.ArgumentParser(description="GGB Social Media SOE")
    parser.add_argument("--cycle", action="store_true", help="Run full social SOE cycle")
    parser.add_argument("--report", action="store_true", help="Social SOE report")
    parser.add_argument("--generate", type=str, help="Generate posts for a platform (all, twitter, tiktok, etc.)")
    parser.add_argument("--health", action="store_true", help="Check platform health")
    parser.add_argument("--trends", action="store_true", help="Detect trending topics")
    args = parser.parse_args()
    
    print(f"\n{'='*60}")
    print(f"📱 GGB SOCIAL MEDIA SOE")
    print(f"   {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
    print(f"{'='*60}\n")
    
    soe = SocialMediaSOE()
    
    if args.cycle:
        results = soe.full_cycle()
        return
    
    if args.report:
        report = soe.report()
        print(f"📊 SOCIAL SOE REPORT")
        print(f"{'='*40}")
        print(f"   Runs: {report['state']['runs']}")
        print(f"   Posts generated: {report['state']['posts_generated']}")
        print(f"   Optimizations: {report['state']['optimizations']}")
        print(f"   Healing actions: {report['state']['healing_actions']}")
        print(f"   Content queued: {report['content_queue']}")
        print(f"\n   Platform Health:")
        for k, v in report['platforms'].items():
            status = "✅" if v.get("healthy") else "❌"
            print(f"     {status} {PLATFORMS[k]['name']:20s} | Errors: {v.get('errors', 0)}")
        return
    
    if args.generate:
        platform = args.generate
        if platform == "all":
            books = soe._get_books()
            for book in books[:3]:
                posts = soe.generate_all_platform_posts(book)
                print(f"   Generated {len(posts)} posts for '{book['title'][:30]}'")
        elif platform in PLATFORMS:
            books = soe._get_books()
            if books:
                post = soe.generate_post(platform, books[0])
                if post:
                    print(f"   ✅ Post generated for {PLATFORMS[platform]['name']}")
                    print(f"   📝 {post['post_text'][:100]}...")
        else:
            print(f"   ❌ Unknown platform: {platform}")
            print(f"   Available: {', '.join(PLATFORMS.keys())}")
        return
    
    if args.health:
        health = soe.check_platform_health()
        print(f"📱 Platform Health:")
        for k, v in health.items():
            status = "✅" if v["healthy"] else "❌"
            print(f"  {status} {PLATFORMS[k]['name']:20s} | {v['status_code']}")
        return
    
    if args.trends:
        trends = soe.detect_trends()
        print(f"🔮 Trending Topics:")
        for t in trends:
            print(f"  📈 {t.get('trend', '?')}")
            print(f"     Platform: {t.get('platform', '?')} | Urgency: {t.get('urgency', '?')}")
            print(f"     Content: {t.get('content_type', '?')}")
        return
    
    # Default: run cycle
    soe.full_cycle()

if __name__ == "__main__":
    main()
