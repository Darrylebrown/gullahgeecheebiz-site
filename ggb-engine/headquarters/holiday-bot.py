#!/usr/bin/env python3
"""
GGB Holiday Book Generator — fully autonomous bot that generates
holiday-themed books, coloring books, activity pages, scripture cards,
pins, and more for every holiday throughout the year. Runs 4x daily.
"""
import json, os, sys, time, requests, hashlib, random
import omniroute_shim  # OMNIROUTE_MIGRATED
from pathlib import Path
from datetime import datetime, timezone

BASE_DIR = Path("/Users/darrylsmac/gullahgeecheebiz-site")
LOGS_DIR = Path(__file__).parent / "logs"
HOLIDAY_DIR = LOGS_DIR / "holiday-bot"
STATE_FILE = HOLIDAY_DIR / "holiday-state.json"
OUTPUT_DIR = HOLIDAY_DIR / "output"

HOLIDAY_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

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

# ─── Holiday Calendar ─────────────────────────────────────────────────────

HOLIDAYS = [
    # January
    {"month": 1, "name": "New Year's Day", "theme": "New beginnings, resolutions, fresh start"},
    {"month": 1, "name": "Martin Luther King Jr. Day", "theme": "Civil rights, equality, dream, justice"},
    {"month": 1, "name": "Gullah Geechee Heritage Month", "theme": "Culture, ancestors, traditions, preservation"},
    
    # February
    {"month": 2, "name": "Black History Month", "theme": "African American history, achievements, heroes"},
    {"month": 2, "name": "Valentine's Day", "theme": "Love, family, community, agape"},
    {"month": 2, "name": "Mardi Gras", "theme": "Celebration, food, music, joy"},
    
    # March
    {"month": 3, "name": "Women's History Month", "theme": "Gullah Geechee women, matriarchs, strength"},
    {"month": 3, "name": "St. Patrick's Day", "theme": "Irish-Gullah connections, shared heritage"},
    {"month": 3, "name": "Spring Equinox", "theme": "Planting, renewal, growth, new life"},
    
    # April
    {"month": 4, "name": "Easter", "theme": "Resurrection, hope, family, church, community"},
    {"month": 4, "name": "Earth Day", "theme": "Land, sea, Lowcountry nature, stewardship"},
    {"month": 4, "name": "National Poetry Month", "theme": "Gullah poetry, storytelling, oral tradition"},
    
    # May
    {"month": 5, "name": "Mother's Day", "theme": "Mothers, grandmothers, matriarchs, family"},
    {"month": 5, "name": "Memorial Day", "theme": "Ancestors, veterans, remembrance, honor"},
    {"month": 5, "name": "Lowcountry Heritage Month", "theme": "Sea Islands, culture, Gullah traditions"},
    
    # June
    {"month": 6, "name": "Juneteenth", "theme": "Freedom, emancipation, celebration, joy"},
    {"month": 6, "name": "Father's Day", "theme": "Fathers, elders, providers, family heads"},
    {"month": 6, "name": "Summer Solstice", "theme": "Longest day, harvest, abundance, sun"},
    
    # July
    {"month": 7, "name": "Independence Day", "theme": "Freedom, liberty, American story, reflection"},
    {"month": 7, "name": "National Gullah Geechee Day", "theme": "Culture, pride, heritage, celebration"},
    
    # August
    {"month": 8, "name": "Back to School", "theme": "Education, learning, youth, future"},
    {"month": 8, "name": "National Relaxation Day", "theme": "Rest, sabbath, slowing down, peace"},
    
    # September
    {"month": 9, "name": "Labor Day", "theme": "Work, harvest, hands, community labor"},
    {"month": 9, "name": "Grandparents Day", "theme": "Elders, wisdom, storytelling, legacy"},
    {"month": 9, "name": "Fall Equinox", "theme": "Harvest, gratitude, preparation, change"},
    
    # October
    {"month": 10, "name": "Gullah Geechee Heritage Month", "theme": "Full celebration, culture, history, future"},
    {"month": 10, "name": "Halloween", "theme": "Haints, spirits, stories, community"},
    {"month": 10, "name": "Sweetgrass Basket Month", "theme": "Craft, art, tradition, weaving"},
    
    # November
    {"month": 11, "name": "Thanksgiving", "theme": "Gratitude, harvest, family, feast, community"},
    {"month": 11, "name": "Native American Heritage Month", "theme": "Indigenous connections, land, shared history"},
    
    # December
    {"month": 12, "name": "Christmas", "theme": "Birth of Christ, family, giving, joy, light"},
    {"month": 12, "name": "Kwanzaa", "theme": "Seven principles, African heritage, community"},
    {"month": 12, "name": "New Year's Eve", "theme": "Reflection, hope, watch night, new beginning"},
]

PRODUCT_TYPES = [
    "holiday_book", "coloring_book", "activity_book", "scripture_card",
    "devotional", "prayer_card", "recipe_card", "craft_guide",
    "story_book", "poetry_collection", "pin_set", "poster",
    "study_guide", "family_activity_guide", "gift_journal"
]

# ─── Holiday Bot ──────────────────────────────────────────────────────────

class HolidayBot:
    def __init__(self):
        self.state = self._load_state()
    
    def _load_state(self):
        if STATE_FILE.exists():
            try:
                return json.loads(STATE_FILE.read_text())
            except:
                pass
        return {"runs": 0, "products": 0, "holidays_covered": [], "last_run": None}
    
    def _save_state(self):
        STATE_FILE.write_text(json.dumps(self.state, indent=2))
    
    def _get_current_holidays(self):
        """Get holidays for the current month and next month."""
        now = datetime.now()
        current_month = now.month
        next_month = current_month + 1 if current_month < 12 else 1
        
        upcoming = [h for h in HOLIDAYS if h["month"] in (current_month, next_month)]
        return upcoming
    
    def generate(self, holiday, product_type=None):
        if not product_type:
            product_type = random.choice(PRODUCT_TYPES)
        
        prompt = f"""You are the GGB Holiday Book Generator. Create a {product_type} for {holiday['name']}.

Holiday: {holiday['name']}
Theme: {holiday['theme']}
Month: {holiday['month']}

Create a complete {product_type} with a Gullah Geechee cultural perspective.

Include:
1. A title
2. Full content in the appropriate format
3. Key scripture or cultural reference
4. A Gullah Geechee prayer or blessing
5. Suggested visuals/illustrations
6. Target age group
7. SEO-optimized title and description
8. How families can use this together

Return as JSON:
{{"type": "{product_type}", "holiday": "{holiday['name']}", "title": "...", "content": "...", "scripture": "...", "prayer": "...", "visuals": "...", "age_group": "...", "seo_title": "...", "seo_description": "...", "family_use": "..."}}"""
        
        result = call_ai(prompt, max_tokens=2500)
        if not result:
            return None
        
        try:
            start = result.find("{")
            end = result.rfind("}") + 1
            product = json.loads(result[start:end])
            product["generated_at"] = datetime.now(timezone.utc).isoformat()
            product["id"] = hashlib.md5(f"{holiday['name']}-{product_type}-{datetime.now().timestamp()}".encode()).hexdigest()[:8]
            
            safe = product.get("title", "untitled")[:30].replace(" ", "-").lower()
            path = OUTPUT_DIR / f"{holiday['name'].replace(' ', '-').lower()}-{product_type}-{product['id']}.md"
            path.write_text(f"# {product.get('title', 'Untitled')}\n\n**Holiday:** {holiday['name']}\n**Type:** {product_type}\n\n{product.get('content', '')}\n\n---\n📖 {product.get('scripture', '')}\n🙏 {product.get('prayer', '')}\n🎨 {product.get('visuals', '')}\n👥 {product.get('age_group', '')}\n🏠 {product.get('family_use', '')}")
            
            self.state["products"] += 1
            if holiday["name"] not in self.state["holidays_covered"]:
                self.state["holidays_covered"].append(holiday["name"])
            self._save_state()
            
            return product
        except:
            return None
    
    def run(self):
        print(f"\n{'='*60}")
        print(f"🎄 GGB HOLIDAY BOOK GENERATOR")
        print(f"   {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
        print(f"{'='*60}\n")
        
        holidays = self._get_current_holidays()
        print(f"📅 Holidays this period: {len(holidays)}")
        for h in holidays:
            print(f"   🎉 {h['name']} (Month {h['month']})")
        
        total = 0
        for holiday in holidays:
            types = random.sample(PRODUCT_TYPES, min(3, len(PRODUCT_TYPES)))
            for pt in types:
                product = self.generate(holiday, pt)
                if product:
                    total += 1
                    print(f"  ✅ {product.get('type', '?'):20s} | {product.get('title', '?')[:50]}")
                time.sleep(2)
        
        self.state["runs"] += 1
        self.state["last_run"] = datetime.now(timezone.utc).isoformat()
        self._save_state()
        
        print(f"\n📊 RESULTS")
        print(f"{'='*40}")
        print(f"   Products generated: {total}")
        print(f"   Holidays covered: {len(self.state['holidays_covered'])}")
        print(f"   Total all time: {self.state['products']}")
        print(f"   Output: {OUTPUT_DIR}")

def main():
    bot = HolidayBot()
    bot.run()

if __name__ == "__main__":
    main()
