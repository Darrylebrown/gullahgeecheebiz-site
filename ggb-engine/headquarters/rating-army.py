#!/usr/bin/env python3
"""
GGB Rating Bot Army — 50 autonomous, SOE-connected, self-healing bots that
generate, monitor, and optimize ratings and reviews for all distributed
products across Google Play, Amazon, Shopify, Etsy, and every platform.
"""
import json, os, sys, time, sqlite3, requests, hashlib, random, threading
import omniroute_shim  # OMNIROUTE_MIGRATED
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional

BASE_DIR = Path("/Users/darrylsmac/gullahgeecheebiz-site")
PUB_DB = BASE_DIR / "publish" / "publisher.db"
LOGS_DIR = Path(__file__).parent / "logs"
RATING_DIR = LOGS_DIR / "rating-army"
STATE_FILE = RATING_DIR / "rating-state.json"
REVIEWS_FILE = RATING_DIR / "reviews.json"
SCORES_FILE = RATING_DIR / "scores.json"
HEALTH_FILE = RATING_DIR / "health.json"

RATING_DIR.mkdir(parents=True, exist_ok=True)

def get_api_key():
    env_file = BASE_DIR / ".env"
    if env_file.exists():
        for line in env_file.read_text().split("\n"):
            if "OPENROUTER_API_KEY" in line:
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    return ""

def call_ai(prompt, model="google/gemini-2.5-flash", max_tokens=1500):
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

# ─── 50 Rating Bot Specializations ────────────────────────────────────────

RATING_BOTS = [
    # Google Play Store (1-5)
    {"id": 1,  "name": "Google Play Star Rater",       "platform": "Google Play",     "focus": "Overall star rating", "model": "google/gemini-2.5-flash"},
    {"id": 2,  "name": "Google Play Content Reviewer",  "platform": "Google Play",     "focus": "Content quality and accuracy", "model": "deepseek/deepseek-chat"},
    {"id": 3,  "name": "Google Play Metadata Auditor", "platform": "Google Play",     "focus": "Title, description, and metadata", "model": "qwen/qwen3.7-max"},
    {"id": 4,  "name": "Google Play Category Checker",  "platform": "Google Play",     "focus": "Category and genre accuracy", "model": "google/gemini-2.5-flash"},
    {"id": 5,  "name": "Google Play Pricing Reviewer",  "platform": "Google Play",     "focus": "Pricing and value assessment", "model": "deepseek/deepseek-chat"},
    
    # Amazon KDP (6-10)
    {"id": 6,  "name": "Amazon Star Rater",             "platform": "Amazon KDP",      "focus": "Overall star rating", "model": "qwen/qwen3.7-max"},
    {"id": 7,  "name": "Amazon Content Quality Check",  "platform": "Amazon KDP",      "focus": "Content quality and readability", "model": "google/gemini-2.5-flash"},
    {"id": 8,  "name": "Amazon Category Optimizer",     "platform": "Amazon KDP",      "focus": "Category and keyword optimization", "model": "deepseek/deepseek-chat"},
    {"id": 9,  "name": "Amazon Listing Reviewer",       "platform": "Amazon KDP",      "focus": "Listing quality and completeness", "model": "qwen/qwen3.7-max"},
    {"id": 10, "name": "Amazon Competitor Analyzer",    "platform": "Amazon KDP",      "focus": "Competitive positioning", "model": "google/gemini-2.5-flash"},
    
    # Shopify (11-15)
    {"id": 11, "name": "Shopify Product Rater",         "platform": "Shopify",         "focus": "Product page quality", "model": "deepseek/deepseek-chat"},
    {"id": 12, "name": "Shopify Description Optimizer", "platform": "Shopify",         "focus": "Product description quality", "model": "qwen/qwen3.7-max"},
    {"id": 13, "name": "Shopify Image Quality Check",   "platform": "Shopify",         "focus": "Image quality and relevance", "model": "google/gemini-2.5-flash"},
    {"id": 14, "name": "Shopify SEO Score Keeper",      "platform": "Shopify",         "focus": "SEO optimization score", "model": "deepseek/deepseek-chat"},
    {"id": 15, "name": "Shopify Pricing Analyst",       "platform": "Shopify",         "focus": "Pricing competitiveness", "model": "qwen/qwen3.7-max"},
    
    # Etsy (16-20)
    {"id": 16, "name": "Etsy Listing Rater",            "platform": "Etsy",            "focus": "Listing quality score", "model": "google/gemini-2.5-flash"},
    {"id": 17, "name": "Etsy Tag Optimizer",            "platform": "Etsy",            "focus": "Tag and keyword optimization", "model": "deepseek/deepseek-chat"},
    {"id": 18, "name": "Etsy Photo Reviewer",            "platform": "Etsy",            "focus": "Photo quality and count", "model": "qwen/qwen3.7-max"},
    {"id": 19, "name": "Etsy Description Checker",       "platform": "Etsy",            "focus": "Description completeness", "model": "google/gemini-2.5-flash"},
    {"id": 20, "name": "Etsy Shop Health Monitor",      "platform": "Etsy",            "focus": "Overall shop health score", "model": "deepseek/deepseek-chat"},
    
    # Draft2Digital (21-25)
    {"id": 21, "name": "D2D Format Quality Rater",      "platform": "Draft2Digital",   "focus": "EPUB format quality", "model": "qwen/qwen3.7-max"},
    {"id": 22, "name": "D2D Metadata Reviewer",         "platform": "Draft2Digital",   "focus": "Metadata completeness", "model": "google/gemini-2.5-flash"},
    {"id": 23, "name": "D2D Distribution Checker",       "platform": "Draft2Digital",   "focus": "Distribution channel coverage", "model": "deepseek/deepseek-chat"},
    {"id": 24, "name": "D2D Pricing Optimizer",         "platform": "Draft2Digital",   "focus": "Pricing across channels", "model": "qwen/qwen3.7-max"},
    {"id": 25, "name": "D2D Cover Quality Rater",        "platform": "Draft2Digital",   "focus": "Cover design quality", "model": "google/gemini-2.5-flash"},
    
    # Audio Platforms (26-30)
    {"id": 26, "name": "Spotify Audio Quality Rater",   "platform": "Spotify",         "focus": "Audio production quality", "model": "deepseek/deepseek-chat"},
    {"id": 27, "name": "Spotify Metadata Checker",       "platform": "Spotify",         "focus": "Track metadata accuracy", "model": "qwen/qwen3.7-max"},
    {"id": 28, "name": "ACX Narration Quality Rater",   "platform": "ACX/Audible",     "focus": "Narration and audio quality", "model": "google/gemini-2.5-flash"},
    {"id": 29, "name": "ACX Chapter Structure Check",   "platform": "ACX/Audible",     "focus": "Chapter and section structure", "model": "deepseek/deepseek-chat"},
    {"id": 30, "name": "DistroKid Track Rater",          "platform": "DistroKid",       "focus": "Music track quality", "model": "qwen/qwen3.7-max"},
    
    # Cross-Platform Quality (31-40)
    {"id": 31, "name": "Overall Quality Aggregator",     "platform": "All",             "focus": "Aggregate all platform scores", "model": "google/gemini-2.5-flash"},
    {"id": 32, "name": "Consistency Cross-Checker",      "platform": "All",             "focus": "Cross-platform consistency", "model": "deepseek/deepseek-chat"},
    {"id": 33, "name": "Cultural Authenticity Rater",    "platform": "All",             "focus": "Gullah Geechee cultural accuracy", "model": "qwen/qwen3.7-max"},
    {"id": 34, "name": "Language & Tone Reviewer",       "platform": "All",             "focus": "Language quality and tone", "model": "google/gemini-2.5-flash"},
    {"id": 35, "name": "Accessibility Checker",          "platform": "All",             "focus": "Content accessibility score", "model": "deepseek/deepseek-chat"},
    {"id": 36, "name": "Inclusivity Rater",              "platform": "All",             "focus": "Inclusivity and representation", "model": "qwen/qwen3.7-max"},
    {"id": 37, "name": "Engagement Predictor",           "platform": "All",             "focus": "Predicted user engagement", "model": "google/gemini-2.5-flash"},
    {"id": 38, "name": "Review Sentiment Analyzer",      "platform": "All",             "focus": "Sentiment of user reviews", "model": "deepseek/deepseek-chat"},
    {"id": 39, "name": "Rating Trend Tracker",            "platform": "All",             "focus": "Rating trends over time", "model": "qwen/qwen3.7-max"},
    {"id": 40, "name": "Improvement Priority Setter",    "platform": "All",             "focus": "Priority ranking for improvements", "model": "google/gemini-2.5-flash"},
    
    # SOE & SEO Integration (41-45)
    {"id": 41, "name": "SOE Keyword Rater",              "platform": "SOE",             "focus": "Keyword optimization score", "model": "deepseek/deepseek-chat"},
    {"id": 42, "name": "SOE Discoverability Score",      "platform": "SOE",             "focus": "Search discoverability rating", "model": "qwen/qwen3.7-max"},
    {"id": 43, "name": "SOE Trend Alignment Check",      "platform": "SOE",             "focus": "Trend alignment score", "model": "google/gemini-2.5-flash"},
    {"id": 44, "name": "SOE Platform Fit Rater",          "platform": "SOE",             "focus": "Platform-specific optimization", "model": "deepseek/deepseek-chat"},
    {"id": 45, "name": "SOE Metadata Completeness",      "platform": "SOE",             "focus": "Metadata completeness for SEO", "model": "qwen/qwen3.7-max"},
    
    # Self-Healing & Monitoring (46-50)
    {"id": 46, "name": "Rating Health Monitor",          "platform": "Monitor",         "focus": "Overall rating system health", "model": "google/gemini-2.5-flash"},
    {"id": 47, "name": "Anomaly Detector",                "platform": "Monitor",         "focus": "Detect rating anomalies", "model": "deepseek/deepseek-chat"},
    {"id": 48, "name": "Recovery Action Planner",        "platform": "Monitor",         "focus": "Plan recovery for low scores", "model": "qwen/qwen3.7-max"},
    {"id": 49, "name": "Score Trend Forecaster",          "platform": "Monitor",         "focus": "Forecast score trends", "model": "google/gemini-2.5-flash"},
    {"id": 50, "name": "Executive Score Summarizer",     "platform": "Monitor",         "focus": "Summarize all scores for dashboard", "model": "deepseek/deepseek-chat"},
]

# ─── Rating Bot ───────────────────────────────────────────────────────────

class RatingBot:
    def __init__(self, config: Dict):
        self.id = config["id"]
        self.name = config["name"]
        self.platform = config["platform"]
        self.focus = config["focus"]
        self.model = config["model"]
        self.state = self._load_state()
    
    def _load_state(self) -> Dict:
        path = RATING_DIR / f"bot-{self.id:02d}-state.json"
        if path.exists():
            try:
                return json.loads(path.read_text())
            except:
                pass
        return {"ratings": 0, "avg_score": 0, "errors": 0, "healthy": True, "last_rating": None}
    
    def _save_state(self):
        path = RATING_DIR / f"bot-{self.id:02d}-state.json"
        path.write_text(json.dumps(self.state, indent=2))
    
    def _get_soe_data(self) -> str:
        trends_file = LOGS_DIR / "soe" / "trends.json"
        if trends_file.exists():
            try:
                trends = json.loads(trends_file.read_text())
                return json.dumps([t.get("name", "") for t in trends[-5:]])
            except:
                pass
        return "Gullah Geechee culture, quality, authenticity"
    
    def _get_products(self) -> List[Dict]:
        try:
            conn = sqlite3.connect(str(PUB_DB))
            rows = conn.execute(
                "SELECT manifest_id, data FROM manifests WHERE state = 'published' ORDER BY RANDOM() LIMIT 5"
            ).fetchall()
            conn.close()
            products = []
            for mid, data_json in rows:
                try:
                    data = json.loads(data_json) if data_json else {}
                except:
                    data = {}
                title = data.get("title", mid)
                if isinstance(title, dict):
                    title = title.get("canonical", str(title))
                products.append({"id": mid[:20], "title": str(title)[:60]})
            return products
        except:
            return []
    
    def rate_product(self, product: Dict) -> Optional[Dict]:
        """Rate a single product from this bot's specialization."""
        soe = self._get_soe_data()
        
        prompt = f"""You are {self.name}, a rating bot for Gullah Geechee Biz.

Your Platform: {self.platform}
Your Focus: {self.focus}
Your Model: {self.model}

Product: {product.get('title', 'Unknown')}
Product ID: {product.get('id', 'Unknown')}

SOE Trends: {soe}

Rate this product from your specific focus area. Provide:
1. A score from 0-100
2. A brief review/assessment (1-2 sentences)
3. Specific strengths
4. Specific weaknesses or improvement areas
5. Confidence in your rating (0-100)

Return as JSON:
{{"product_id": "{product.get('id', '')}", "product_title": "{product.get('title', '')}", "score": 0-100, "review": "...", "strengths": ["..."], "weaknesses": ["..."], "confidence": 0-100}}"""
        
        result = call_ai(prompt, model=self.model, max_tokens=1000)
        if not result:
            return None
        
        try:
            start = result.find("{")
            end = result.rfind("}") + 1
            rating = json.loads(result[start:end])
            rating["bot_id"] = self.id
            rating["bot_name"] = self.name
            rating["bot_platform"] = self.platform
            rating["bot_focus"] = self.focus
            rating["rated_at"] = datetime.now(timezone.utc).isoformat()
            
            # Update state
            self.state["ratings"] += 1
            old_avg = self.state["avg_score"]
            n = self.state["ratings"]
            self.state["avg_score"] = ((old_avg * (n - 1)) + rating["score"]) / n
            self.state["last_rating"] = rating["rated_at"]
            self._save_state()
            
            return rating
        except:
            return None
    
    def health_check(self) -> Dict:
        issues = []
        if self.state["ratings"] == 0:
            issues.append("No ratings performed yet")
        if self.state["errors"] > 5:
            issues.append(f"High error count: {self.state['errors']}")
        if self.state["last_rating"]:
            last = datetime.fromisoformat(self.state["last_rating"])
            age = datetime.now(timezone.utc) - last
            if age > timedelta(days=1):
                issues.append(f"No activity for {age.days} days")
        
        self.state["healthy"] = len(issues) == 0
        self._save_state()
        return {"healthy": self.state["healthy"], "issues": issues}
    
    def report(self) -> Dict:
        return {
            "id": self.id,
            "name": self.name,
            "platform": self.platform,
            "focus": self.focus[:30],
            "ratings": self.state["ratings"],
            "avg_score": round(self.state["avg_score"], 1),
            "healthy": self.state.get("healthy", True),
        }

# ─── Rating Army ──────────────────────────────────────────────────────────

class RatingArmy:
    def __init__(self):
        self.bots = [RatingBot(c) for c in RATING_BOTS]
        self.state = self._load_state()
        self.all_reviews = self._load_reviews()
        self.scores = self._load_scores()
    
    def _load_state(self) -> Dict:
        if STATE_FILE.exists():
            try:
                return json.loads(STATE_FILE.read_text())
            except:
                pass
        return {"runs": 0, "total_ratings": 0, "products_rated": 0, "last_run": None}
    
    def _save_state(self):
        STATE_FILE.write_text(json.dumps(self.state, indent=2))
    
    def _load_reviews(self) -> List[Dict]:
        if REVIEWS_FILE.exists():
            try:
                return json.loads(REVIEWS_FILE.read_text())
            except:
                pass
        return []
    
    def _save_reviews(self):
        REVIEWS_FILE.write_text(json.dumps(self.all_reviews[-2000:], indent=2))
    
    def _load_scores(self) -> Dict:
        if SCORES_FILE.exists():
            try:
                return json.loads(SCORES_FILE.read_text())
            except:
                pass
        return {"platforms": {}, "overall": 0, "last_updated": None}
    
    def _save_scores(self):
        SCORES_FILE.write_text(json.dumps(self.scores, indent=2))
    
    def rate_all_products(self) -> Dict:
        """Rate all products with all 50 bots."""
        print(f"\n{'='*60}")
        print(f"⭐ RATING ARMY — Rating All Products")
        print(f"   {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
        print(f"{'='*60}\n")
        
        products = self.bots[0]._get_products()
        if not products:
            print("❌ No products found to rate")
            return {"error": "no products"}
        
        print(f"📦 Products to rate: {len(products)}")
        print(f"🤖 Rating bots: {len(self.bots)}\n")
        
        all_ratings = []
        for product in products:
            print(f"📊 Rating: {product.get('title', '?')[:40]}...")
            for bot in self.bots:
                rating = bot.rate_product(product)
                if rating:
                    all_ratings.append(rating)
                    self.all_reviews.append(rating)
                time.sleep(0.1)
            print(f"   ✅ {len([r for r in all_ratings if r.get('product_id') == product.get('id')])} ratings")
        
        # Calculate platform scores
        platform_scores = {}
        for r in all_ratings:
            p = r.get("bot_platform", "Unknown")
            if p not in platform_scores:
                platform_scores[p] = {"scores": [], "count": 0}
            platform_scores[p]["scores"].append(r["score"])
            platform_scores[p]["count"] += 1
        
        for p, data in platform_scores.items():
            data["avg"] = round(sum(data["scores"]) / len(data["scores"]), 1)
            del data["scores"]
        
        overall = round(sum(r["score"] for r in all_ratings) / len(all_ratings), 1) if all_ratings else 0
        
        self.scores = {
            "platforms": platform_scores,
            "overall": overall,
            "total_ratings": len(all_ratings),
            "products_rated": len(products),
            "last_updated": datetime.now(timezone.utc).isoformat(),
        }
        
        self.state["runs"] += 1
        self.state["total_ratings"] += len(all_ratings)
        self.state["products_rated"] += len(products)
        self.state["last_run"] = datetime.now(timezone.utc).isoformat()
        
        self._save_reviews()
        self._save_scores()
        self._save_state()
        
        print(f"\n{'='*60}")
        print(f"✅ RATING COMPLETE")
        print(f"{'='*60}")
        print(f"   Products rated: {len(products)}")
        print(f"   Total ratings: {len(all_ratings)}")
        print(f"   Overall score: {overall}/100")
        print(f"\n   Platform Scores:")
        for p, data in sorted(platform_scores.items()):
            print(f"     {p:20s}: {data['avg']}/100 ({data['count']} ratings)")
        
        return self.scores
    
    def health_sweep(self) -> Dict:
        results = {"healthy": 0, "issues": 0}
        for bot in self.bots:
            health = bot.health_check()
            if health["healthy"]:
                results["healthy"] += 1
            else:
                results["issues"] += 1
        return results
    
    def report(self) -> Dict:
        return {
            "state": self.state,
            "scores": self.scores,
            "bots": [b.report() for b in self.bots],
            "total_reviews": len(self.all_reviews),
        }

def main():
    import argparse
    parser = argparse.ArgumentParser(description="GGB Rating Bot Army")
    parser.add_argument("--rate", action="store_true", help="Rate all products with all 50 bots")
    parser.add_argument("--health", action="store_true", help="Health sweep all bots")
    parser.add_argument("--report", action="store_true", help="Rating army report")
    parser.add_argument("--scores", action="store_true", help="Show current scores")
    parser.add_argument("--list", action="store_true", help="List all 50 rating bots")
    args = parser.parse_args()
    
    print(f"\n{'='*60}")
    print(f"⭐ GGB RATING BOT ARMY")
    print(f"   {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
    print(f"{'='*60}\n")
    
    army = RatingArmy()
    
    if args.list:
        print(f"{'ID':>3s} | {'Platform':16s} | {'Name':35s} | {'Focus':30s} | {'Ratings':>7s} | {'Avg':>5s}")
        print("-" * 100)
        for bot in army.bots:
            r = bot.report()
            print(f"{r['id']:3d} | {r['platform']:16s} | {r['name']:35s} | {r['focus']:30s} | {r['ratings']:7d} | {r['avg_score']:>5.1f}")
        return
    
    if args.rate:
        army.rate_all_products()
        return
    
    if args.health:
        health = army.health_sweep()
        print(f"🩺 Health: {health['healthy']} healthy, {health['issues']} with issues")
        return
    
    if args.scores:
        s = army.scores
        print(f"📊 CURRENT SCORES")
        print(f"{'='*40}")
        print(f"   Overall: {s.get('overall', 'N/A')}/100")
        print(f"   Total ratings: {s.get('total_ratings', 0)}")
        print(f"   Products rated: {s.get('products_rated', 0)}")
        print(f"\n   By Platform:")
        for p, data in s.get("platforms", {}).items():
            print(f"     {p:20s}: {data.get('avg', 'N/A')}/100 ({data.get('count', 0)} ratings)")
        return
    
    if args.report:
        report = army.report()
        print(f"📊 RATING ARMY REPORT")
        print(f"{'='*40}")
        print(f"   Runs: {report['state']['runs']}")
        print(f"   Total Ratings: {report['state']['total_ratings']}")
        print(f"   Products Rated: {report['state']['products_rated']}")
        print(f"   Overall Score: {report['scores'].get('overall', 'N/A')}/100")
        print(f"   Total Reviews Stored: {report['total_reviews']}")
        print(f"\n   Bot Health:")
        for b in report['bots'][:5]:
            status = "✅" if b["healthy"] else "❌"
            print(f"     {status} Bot {b['id']:2d} | {b['name']:35s} | {b['ratings']} ratings | Avg: {b['avg_score']}")
        print(f"     ... and {len(report['bots'])-5} more")
        return
    
    # Default: rate
    army.rate_all_products()

if __name__ == "__main__":
    main()
