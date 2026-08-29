#!/usr/bin/env python3
"""
GGB Binyah's Diary — Binyah the avatar writes daily journal entries about
life, culture, and the state of the Gullah Geechee world. Connected to
the Brain, Dream Weaver, and all systems.
"""
import json, os, sys, time, requests, hashlib
import omniroute_shim  # OMNIROUTE_MIGRATED
from pathlib import Path
from datetime import datetime, timezone

BASE_DIR = Path("/Users/darrylsmac/gullahgeecheebiz-site")
LOGS_DIR = Path(__file__).parent / "logs"
DIARY_DIR = LOGS_DIR / "binyah-diary"
STATE_FILE = DIARY_DIR / "diary-state.json"
ENTRIES_FILE = DIARY_DIR / "entries.json"

DIARY_DIR.mkdir(parents=True, exist_ok=True)

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

class BinyahDiary:
    def __init__(self):
        self.state = self._load_state()
        self.entries = self._load_entries()
    
    def _load_state(self):
        if STATE_FILE.exists():
            try:
                return json.loads(STATE_FILE.read_text())
            except:
                pass
        return {"entries": 0, "last_entry": None, "mood": "bright"}
    
    def _save_state(self):
        STATE_FILE.write_text(json.dumps(self.state, indent=2))
    
    def _load_entries(self):
        if ENTRIES_FILE.exists():
            try:
                return json.loads(ENTRIES_FILE.read_text())
            except:
                pass
        return []
    
    def _save_entries(self):
        ENTRIES_FILE.write_text(json.dumps(self.entries[-365:], indent=2))
    
    def write_entry(self):
        now = datetime.now()
        date_str = now.strftime("%B %d, %Y")
        day_of_year = now.timetuple().tm_yday
        season = "Spring" if 80 <= day_of_year <= 172 else "Summer" if 173 <= day_of_year <= 266 else "Fall" if 267 <= day_of_year <= 355 else "Winter"
        
        prompt = f"""You are Binyah — the Gullah Geechee Biz avatar. Write a diary entry for today.

Date: {date_str}
Season: {season}
Your mood: {self.state.get('mood', 'bright')}
Previous entry mood: {self.state.get('mood', 'bright')}

Write a warm, authentic diary entry (200-300 words) as Binyah. Talk about:
- What you did today
- What you're excited about
- A piece of Gullah Geechee wisdom or memory
- Something you're grateful for
- Your hopes for tomorrow

End with a Gullah Geechee blessing or proverb.

Return as JSON:
{{"date": "{date_str}", "entry": "...", "mood": "...", "proverb": "...", "blessing": "..."}}"""
        
        result = call_ai(prompt, max_tokens=1500)
        if not result:
            return None
        
        try:
            start = result.find("{")
            end = result.rfind("}") + 1
            entry = json.loads(result[start:end])
            entry["written_at"] = datetime.now(timezone.utc).isoformat()
            entry["id"] = hashlib.md5(date_str.encode()).hexdigest()[:8]
            
            self.entries.append(entry)
            self.state["entries"] += 1
            self.state["last_entry"] = entry["written_at"]
            self.state["mood"] = entry.get("mood", "bright")
            self._save_entries()
            self._save_state()
            
            return entry
        except:
            return None
    
    def latest(self):
        return self.entries[-1] if self.entries else None

def main():
    diary = BinyahDiary()
    entry = diary.write_entry()
    if entry:
        print(f"\n📔 BINYAH'S DIARY — {entry.get('date', 'Today')}")
        print(f"{'='*50}")
        print(f"\n{entry.get('entry', '')[:500]}")
        print(f"\n{'='*50}")
        print(f"🌿 Proverb: {entry.get('proverb', '')}")
        print(f"🙏 Blessing: {entry.get('blessing', '')}")
        print(f"💫 Mood: {entry.get('mood', '')}")

if __name__ == "__main__":
    main()
