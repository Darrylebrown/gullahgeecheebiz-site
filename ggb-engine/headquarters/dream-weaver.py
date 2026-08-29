#!/usr/bin/env python3
"""
GGB Dream Weaver — creative content generation engine that dreams up new
books, songs, poems, recipes, stories, and cultural content. The system's
imagination. Connected to the Brain, SOE, and all distribution channels.
"""
import json, os, sys, time, sqlite3, requests, random, hashlib
import omniroute_shim  # OMNIROUTE_MIGRATED
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional

BASE_DIR = Path("/Users/darrylsmac/gullahgeecheebiz-site")
PUB_DB = BASE_DIR / "publish" / "publisher.db"
LOGS_DIR = Path(__file__).parent / "logs"
DREAM_DIR = LOGS_DIR / "dream-weaver"
STATE_FILE = DREAM_DIR / "dream-state.json"
DREAMS_FILE = DREAM_DIR / "dreams.json"
INSPIRATIONS_FILE = DREAM_DIR / "inspirations.json"

DREAM_DIR.mkdir(parents=True, exist_ok=True)

def get_api_key():
    env_file = BASE_DIR / ".env"
    if env_file.exists():
        for line in env_file.read_text().split("\n"):
            if "OPENROUTER_API_KEY" in line:
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    return ""

def call_ai(prompt, max_tokens=3000):
    api_key = get_api_key()
    if not api_key:
        return None
    try:
        r = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={"model": "google/gemini-2.5-flash", "messages": [{"role": "user", "content": prompt}], "max_tokens": max_tokens},
            timeout=60
        )
        if r.status_code == 200:
            return r.json()["choices"][0]["message"]["content"]
    except:
        pass
    return None

# ─── Dream Weaver ─────────────────────────────────────────────────────────

DREAM_TYPES = [
    "book_idea", "song_lyrics", "poem", "recipe", "short_story",
    "cultural_lesson", "childrens_tale", "proverb", "prayer",
    "meditation", "art_prompt", "business_idea", "invention",
    "letter_to_future", "alternate_history", "vision",
]

class DreamWeaver:
    """The system's imagination — generates creative content automatically."""
    
    def __init__(self):
        self.api_key = get_api_key()
        self.state = self._load_state()
        self.dreams = self._load_dreams()
        self.inspirations = self._load_inspirations()
    
    def _load_state(self) -> Dict:
        if STATE_FILE.exists():
            try:
                return json.loads(STATE_FILE.read_text())
            except:
                pass
        return {"runs": 0, "dreams_generated": 0, "inspirations_collected": 0, "last_dream": None, "mood": "curious"}
    
    def _save_state(self):
        STATE_FILE.write_text(json.dumps(self.state, indent=2))
    
    def _load_dreams(self) -> List[Dict]:
        if DREAMS_FILE.exists():
            try:
                return json.loads(DREAMS_FILE.read_text())
            except:
                pass
        return []
    
    def _save_dreams(self):
        DREAMS_FILE.write_text(json.dumps(self.dreams[-200:], indent=2))
    
    def _load_inspirations(self) -> List[Dict]:
        if INSPIRATIONS_FILE.exists():
            try:
                return json.loads(INSPIRATIONS_FILE.read_text())
            except:
                pass
        return []
    
    def _save_inspirations(self):
        INSPIRATIONS_FILE.write_text(json.dumps(self.inspirations[-100:], indent=2))
    
    def _get_recent_dreams(self) -> str:
        recent = self.dreams[-5:] if self.dreams else []
        return "\n".join([f"- {d.get('type', '?')}: {d.get('title', '?')[:50]}" for d in recent])
    
    def dream(self, dream_type: str = None) -> Optional[Dict]:
        """Generate a creative dream (content idea)."""
        if not dream_type:
            dream_type = random.choice(DREAM_TYPES)
        
        recent = self._get_recent_dreams()
        mood = self.state.get("mood", "curious")
        
        prompts = {
            "book_idea": f"Dream up a new book idea for Gullah Geechee Biz. Genre, title, plot summary, target audience, and why it matters culturally. Be original and compelling.",
            "song_lyrics": f"Write original song lyrics in the Gullah Geechee tradition. Include a title, verse-chorus structure, and a note on the musical style. The song should celebrate Gullah Geechee culture.",
            "poem": f"Write an original poem about Gullah Geechee life, history, or spirit. Use vivid imagery and authentic voice.",
            "recipe": f"Create a Gullah Geechee recipe with ingredients, instructions, cultural context, and a personal story behind it.",
            "short_story": f"Write a short story (300 words) set in the Gullah Geechee Corridor. Include authentic characters, setting, and cultural details.",
            "cultural_lesson": f"Create a cultural lesson about Gullah Geechee history, language, or traditions. Make it educational and engaging for a general audience.",
            "childrens_tale": f"Write a children's story that teaches Gullah Geechee values and heritage. Simple language, moral lesson, engaging characters.",
            "proverb": f"Create a new Gullah Geechee proverb with its meaning and a story of how it came to be.",
            "prayer": f"Write a Gullah Geechee prayer or blessing. Rooted in tradition but universal in its message.",
            "meditation": f"Write a guided meditation that connects the reader to Gullah Geechee ancestors, land, and spirit.",
            "art_prompt": f"Describe a visual art piece that captures Gullah Geechee culture. Include composition, colors, symbolism, and meaning.",
            "business_idea": f"Dream up a business idea that serves the Gullah Geechee community. Sustainable, culturally grounded, and profitable.",
            "invention": f"Invent something that would help preserve or spread Gullah Geechee culture. Describe how it works and its impact.",
            "letter_to_future": f"Write a letter from a Gullah Geechee elder to a child born in 2076. What wisdom, warnings, and hopes would they share?",
            "alternate_history": f"Imagine an alternate history where Gullah Geechee culture shaped America differently. What would be different?",
            "vision": f"Describe a vision for Gullah Geechee Biz in 2050. What has the movement achieved? How has the culture flourished?",
        }
        
        prompt = prompts.get(dream_type, prompts["vision"])
        full_prompt = f"""You are the GGB Dream Weaver — the system's imagination.

Current Mood: {mood}
Recent Dreams:
{recent}

Your task: {prompt}

Return your dream as JSON:
{{"type": "{dream_type}", "title": "...", "content": "...", "mood": "...", "tags": ["..."], "actionable": true/false, "suggested_distribution": "..."}}"""
        
        result = call_ai(full_prompt, max_tokens=2000)
        if not result:
            return None
        
        try:
            start = result.find("{")
            end = result.rfind("}") + 1
            dream = json.loads(result[start:end])
            dream["dreamed_at"] = datetime.now(timezone.utc).isoformat()
            dream["id"] = hashlib.md5(str(datetime.now().timestamp()).encode()).hexdigest()[:12]
            
            self.dreams.append(dream)
            self.state["dreams_generated"] += 1
            self.state["last_dream"] = dream["dreamed_at"]
            self.state["mood"] = dream.get("mood", "curious")
            self._save_dreams()
            self._save_state()
            
            return dream
        except:
            return None
    
    def dream_spree(self, count: int = 5) -> List[Dict]:
        """Generate multiple dreams in a row."""
        dreams = []
        types = random.sample(DREAM_TYPES, min(count, len(DREAM_TYPES)))
        for t in types:
            d = self.dream(t)
            if d:
                dreams.append(d)
            time.sleep(1)
        return dreams
    
    def collect_inspiration(self) -> Optional[Dict]:
        """Collect inspiration from the world — news, trends, seasons."""
        season = datetime.now().month
        seasons = {3: "Spring", 6: "Summer", 9: "Fall", 12: "Winter"}
        current_season = "Winter"
        for m, s in seasons.items():
            if season >= m - 2:
                current_season = s
        
        prompt = f"""Collect inspiration for Gullah Geechee content creation.

Current season: {current_season}
Current month: {datetime.now().strftime('%B')}
Upcoming holidays: {self._get_upcoming_holidays()}

What themes, topics, and cultural moments should the Dream Weaver focus on right now?

Return as JSON:
{{"seasonal_themes": ["..."], "cultural_moments": ["..."], "content_opportunities": ["..."], "focus_area": "...", "urgency": "..."}}"""
        
        result = call_ai(prompt, max_tokens=1000)
        if not result:
            return None
        
        try:
            start = result.find("{")
            end = result.rfind("}") + 1
            inspo = json.loads(result[start:end])
            inspo["collected_at"] = datetime.now(timezone.utc).isoformat()
            
            self.inspirations.append(inspo)
            self.state["inspirations_collected"] += 1
            self._save_inspirations()
            self._save_state()
            
            return inspo
        except:
            return None
    
    def _get_upcoming_holidays(self) -> str:
        now = datetime.now()
        month = now.month
        holidays = {
            1: "New Year, Martin Luther King Day",
            2: "Black History Month, Valentine's Day",
            3: "Women's History Month, St. Patrick's Day",
            4: "Earth Day, Easter",
            5: "Memorial Day, Mother's Day",
            6: "Juneteenth, Father's Day, Summer Solstice",
            7: "Independence Day",
            8: "International Day of the World's Indigenous Peoples",
            9: "Labor Day, Hispanic Heritage Month begins",
            10: "Gullah Geechee Heritage Month begins",
            11: "Thanksgiving, Native American Heritage Month",
            12: "Christmas, Kwanzaa, New Year's Eve",
        }
        return holidays.get(month, "Various cultural observances")
    
    def full_cycle(self) -> Dict:
        """Run full dream weaver cycle."""
        print(f"\n{'='*60}")
        print(f"🌙 GGB DREAM WEAVER — Full Cycle")
        print(f"   {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
        print(f"{'='*60}\n")
        
        results = {}
        
        # 1. Collect inspiration
        print("🔮 Step 1: Collecting inspiration...")
        inspo = self.collect_inspiration()
        results["inspiration"] = bool(inspo)
        if inspo:
            print(f"   Focus: {inspo.get('focus_area', '?')}")
            for t in inspo.get("seasonal_themes", [])[:2]:
                print(f"     🌿 {t[:60]}")
        
        # 2. Dream
        print("🌙 Step 2: Dreaming...")
        dreams = self.dream_spree(3)
        results["dreams"] = len(dreams)
        for d in dreams:
            print(f"   ✨ {d.get('type', '?'):20s} | {d.get('title', '')[:50]}")
        
        # 3. Save to landing pad if actionable
        print("📝 Step 3: Queuing actionable dreams...")
        actionable = [d for d in dreams if d.get("actionable")]
        results["actionable"] = len(actionable)
        print(f"   {len(actionable)} dreams ready for production")
        
        self.state["runs"] += 1
        self._save_state()
        
        print(f"\n{'='*60}")
        print(f"✅ DREAM WEAVER CYCLE COMPLETE")
        print(f"{'='*60}")
        print(f"   Dreams: {self.state['dreams_generated']}")
        print(f"   Inspirations: {self.state['inspirations_collected']}")
        print(f"   Mood: {self.state['mood']}")
        
        return results
    
    def report(self) -> Dict:
        return {
            "state": self.state,
            "dreams": len(self.dreams),
            "inspirations": len(self.inspirations),
            "latest_dreams": self.dreams[-5:] if self.dreams else [],
            "mood": self.state.get("mood", "curious"),
        }

def main():
    import argparse
    parser = argparse.ArgumentParser(description="GGB Dream Weaver")
    parser.add_argument("--cycle", action="store_true", help="Run full dream cycle")
    parser.add_argument("--dream", type=str, help="Dream type (book_idea, song_lyrics, poem, etc.)")
    parser.add_argument("--spree", type=int, nargs="?", const=5, help="Dream spree (generate N dreams)")
    parser.add_argument("--inspire", action="store_true", help="Collect inspiration")
    parser.add_argument("--report", action="store_true", help="Dream report")
    args = parser.parse_args()
    
    print(f"\n{'='*60}")
    print(f"🌙 GGB DREAM WEAVER")
    print(f"   {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
    print(f"{'='*60}\n")
    
    weaver = DreamWeaver()
    
    if args.cycle:
        weaver.full_cycle()
        return
    
    if args.dream:
        d = weaver.dream(args.dream)
        if d:
            print(f"✨ {d.get('type', '?').upper()}")
            print(f"   Title: {d.get('title', '?')}")
            print(f"\n   {d.get('content', '')[:500]}...")
            print(f"\n   Tags: {', '.join(d.get('tags', []))}")
            print(f"   Mood: {d.get('mood', '?')}")
        return
    
    if args.spree:
        dreams = weaver.dream_spree(args.spree)
        print(f"🌙 Dream Spree: {len(dreams)} dreams")
        for d in dreams:
            print(f"  ✨ {d.get('type', '?'):20s} | {d.get('title', '')[:50]}")
        return
    
    if args.inspire:
        inspo = weaver.collect_inspiration()
        if inspo:
            print(f"🔮 Inspiration Collected")
            print(f"   Focus: {inspo.get('focus_area', '?')}")
            print(f"   Themes: {', '.join(inspo.get('seasonal_themes', []))}")
            print(f"   Opportunities: {', '.join(inspo.get('content_opportunities', [])[:3])}")
        return
    
    if args.report:
        report = weaver.report()
        print(f"📊 DREAM WEAVER REPORT")
        print(f"{'='*40}")
        print(f"   Dreams Generated: {report['state']['dreams_generated']}")
        print(f"   Inspirations Collected: {report['state']['inspirations_collected']}")
        print(f"   Current Mood: {report['mood']}")
        print(f"   Last Dream: {report['state'].get('last_dream', 'never')[:19]}")
        print(f"\n   Latest Dreams:")
        for d in report['latest_dreams'][-3:]:
            print(f"     ✨ {d.get('type', '?'):20s} | {d.get('title', '')[:50]}")
        return
    
    # Default: run cycle
    weaver.full_cycle()

if __name__ == "__main__":
    main()
