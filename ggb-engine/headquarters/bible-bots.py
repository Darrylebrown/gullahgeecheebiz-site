#!/usr/bin/env python3
"""
GGB Bible Content Bots — 2 fully autonomous bots that generate Bible-centered
products: workbooks, coloring books, scriptures, pins, and more. 4x daily.
"""
import json, os, sys, time, requests, hashlib, random
import omniroute_shim  # OMNIROUTE_MIGRATED
from pathlib import Path
from datetime import datetime, timezone

BASE_DIR = Path("/Users/darrylsmac/gullahgeecheebiz-site")
LOGS_DIR = Path(__file__).parent / "logs"
BIBLE_DIR = LOGS_DIR / "bible-bots"
STATE_FILE = BIBLE_DIR / "bible-state.json"
OUTPUT_DIR = BIBLE_DIR / "output"

BIBLE_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def get_api_key():
    env_file = BASE_DIR / ".env"
    if env_file.exists():
        for line in env_file.read_text().split("\n"):
            if "OPENROUTER_API_KEY" in line:
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    return ""

def call_ai(prompt, model="google/gemini-2.5-flash", max_tokens=3000):
    api_key = get_api_key()
    if not api_key:
        return None
    try:
        r = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={"model": model, "messages": [{"role": "user", "content": prompt}], "max_tokens": max_tokens},
            timeout=60
        )
        if r.status_code == 200:
            return r.json()["choices"][0]["message"]["content"]
    except:
        pass
    return None

PRODUCT_TYPES = ["workbook", "coloring_book", "scripture_card", "pin", "study_guide", "devotional", "activity_page", "verse_meme", "bible_journal", "prayer_card"]

BOTS = [
    {
        "id": 1,
        "name": "Selah Scribe",
        "personality": "Deep, contemplative, rooted in scripture and Gullah Geechee spiritual tradition",
        "focus": "Workbooks, study guides, devotionals, scripture cards",
        "model": "google/gemini-2.5-flash",
    },
    {
        "id": 2,
        "name": "Joyful Creator",
        "personality": "Bright, creative, visual, makes faith fun and accessible",
        "focus": "Coloring books, activity pages, verse memes, pins, prayer cards",
        "model": "deepseek/deepseek-chat",
    },
]

class BibleBot:
    def __init__(self, config):
        self.id = config["id"]
        self.name = config["name"]
        self.personality = config["personality"]
        self.focus = config["focus"]
        self.model = config["model"]
        self.state = self._load_state()
    
    def _load_state(self):
        path = BIBLE_DIR / f"bot-{self.id}-state.json"
        if path.exists():
            try:
                return json.loads(path.read_text())
            except:
                pass
        return {"products": 0, "last_run": None, "total": 0}
    
    def _save_state(self):
        path = BIBLE_DIR / f"bot-{self.id}-state.json"
        path.write_text(json.dumps(self.state, indent=2))
    
    def generate(self, product_type=None):
        if not product_type:
            product_type = random.choice(PRODUCT_TYPES)
        
        prompt = f"""You are {self.name}, a Bible content creation bot for Gullah Geechee Biz.

Your Personality: {self.personality}
Your Focus: {self.focus}

Generate ONE {product_type} with a Gullah Geechee spiritual perspective.

Include:
1. A title
2. Full content in the appropriate format
3. A key scripture verse (book, chapter, verse)
4. A Gullah Geechee prayer or blessing
5. Suggested visuals/illustrations
6. Target age group
7. SEO-optimized title and description

Return as JSON:
{{"type": "{product_type}", "title": "...", "content": "...", "scripture": "...", "prayer": "...", "visuals": "...", "age_group": "...", "seo_title": "...", "seo_description": "..."}}"""
        
        result = call_ai(prompt, model=self.model, max_tokens=2500)
        if not result:
            return None
        
        try:
            start = result.find("{")
            end = result.rfind("}") + 1
            product = json.loads(result[start:end])
            product["bot_id"] = self.id
            product["bot_name"] = self.name
            product["generated_at"] = datetime.now(timezone.utc).isoformat()
            product["id"] = hashlib.md5(f"{product_type}-{datetime.now().timestamp()}".encode()).hexdigest()[:8]
            
            safe = product.get("title", "untitled")[:30].replace(" ", "-").lower()
            path = OUTPUT_DIR / f"{product_type}-{safe}-{product['id']}.md"
            path.write_text(f"# {product.get('title', 'Untitled')}\n\n{product.get('content', '')}\n\n---\n📖 {product.get('scripture', '')}\n🙏 {product.get('prayer', '')}\n🎨 {product.get('visuals', '')}\n👥 {product.get('age_group', '')}")
            
            self.state["products"] += 1
            self.state["total"] += 1
            self.state["last_run"] = datetime.now(timezone.utc).isoformat()
            self._save_state()
            
            return product
        except:
            return None
    
    def run_batch(self, count=4):
        items = []
        types = random.sample(PRODUCT_TYPES, min(count, len(PRODUCT_TYPES)))
        for t in types:
            item = self.generate(t)
            if item:
                items.append(item)
            time.sleep(2)
        return items

def main():
    print(f"\n{'='*60}")
    print(f"📖 GGB BIBLE CONTENT BOTS")
    print(f"   {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
    print(f"{'='*60}\n")
    
    for bot_config in BOTS:
        bot = BibleBot(bot_config)
        print(f"🤖 {bot.name} generating...")
        items = bot.run_batch(4)
        for item in items:
            print(f"  ✅ {item.get('type', '?'):20s} | {item.get('title', '?')[:50]}")
        print(f"   Total: {bot.state['total']} products\n")
    
    print(f"📁 Output: {OUTPUT_DIR}")

if __name__ == "__main__":
    main()
