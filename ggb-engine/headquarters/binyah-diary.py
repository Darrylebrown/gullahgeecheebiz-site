#!/usr/bin/env python3
"""
GGB Binyah's Diary — Write a new entry and display it.
"""
import json, os, sys, time, hashlib, re
import omniroute_shim
from pathlib import Path
from datetime import datetime, timezone

BASE_DIR = Path("/Users/darrylsmac/gullahgeecheebiz-site")
LOGS_DIR = Path(__file__).parent / "logs"
DIARY_DIR = LOGS_DIR / "binyah-diary"
STATE_FILE = DIARY_DIR / "diary-state.json"
ENTRIES_FILE = DIARY_DIR / "entries.json"

DIARY_DIR.mkdir(parents=True, exist_ok=True)

def call_ai(prompt, model="ggb-free-auto", max_tokens=2000):
    return omniroute_shim.call_ai(prompt=prompt, model=model, max_tokens=min(max_tokens, 4000))

def parse_entry_json(text):
    """Parse JSON, handling common issues with newlines in string values."""
    start = text.find("{")
    end = text.rfind("}") + 1
    if start < 0 or end <= start:
        raise ValueError("No JSON object found")
    
    json_str = text[start:end]
    
    # Fix: replace actual newlines inside strings with \n
    result_chars = []
    i = 0
    in_string = False
    escape = False
    
    while i < len(json_str):
        c = json_str[i]
        
        if escape:
            result_chars.append(c)
            escape = False
            i += 1
            continue
        
        if c == '\\':
            escape = True
            result_chars.append(c)
            i += 1
            continue
        
        if c == '"':
            in_string = not in_string
            result_chars.append(c)
            i += 1
            continue
        
        if in_string and c == '\n':
            result_chars.append('\\')
            result_chars.append('n')
            i += 1
            continue
        
        if not in_string and c == '\n':
            i += 1
            continue
        
        result_chars.append(c)
        i += 1
    
    fixed_json = ''.join(result_chars)
    return json.loads(fixed_json)

def try_multiple_models(prompt):
    """Try multiple models until one succeeds."""
    models = ["ggb-free-auto", "qwen2.5:3b-instruct-q4_K_M", "deepseek-v3"]
    
    for model in models:
        try:
            result = call_ai(prompt, model=model, max_tokens=800)
            if result and "{" in result:
                print(f"Using model: {model}", file=sys.stderr)
                return result
        except:
            continue
    
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

Write a warm, authentic diary entry (150-200 words) as Binyah. Talk about:
- What you did today
- A piece of Gullah Geechee wisdom
- Something you're grateful for

Return ONLY valid JSON with no markdown. Use \\n for line breaks.

{{"date": "{date_str}", "entry": "TEXT HERE", "mood": "bright", "proverb": "PROVERB HERE", "blessing": "BLESSING HERE"}}"""
        
        result = try_multiple_models(prompt)
        if not result:
            return None
        
        try:
            entry = parse_entry_json(result)
            entry["written_at"] = datetime.now(timezone.utc).isoformat()
            entry["id"] = hashlib.md5(date_str.encode()).hexdigest()[:8]
            
            self.entries.append(entry)
            self.state["entries"] += 1
            self.state["last_entry"] = entry["written_at"]
            self.state["mood"] = entry.get("mood", "bright")
            self._save_entries()
            self._save_state()
            
            return entry
        except Exception as e:
            print(f"Failed to parse entry: {e}", file=sys.stderr)
            print(f"Raw result: {result[:800]}", file=sys.stderr)
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
    else:
        print("FAILED to write new entry. Showing latest:", file=sys.stderr)
        latest = diary.latest()
        if latest:
            print(f"\n📔 LATEST (from {latest.get('date', 'N/A')})")
            print(f"{'='*50}")
            print(f"\n{latest.get('entry', '')}")
            print(f"\n{'='*50}")
            print(f"🌿 Proverb: {latest.get('proverb', '')}")
            print(f"🙏 Blessing: {latest.get('blessing', '')}")
            print(f"💫 Mood: {latest.get('mood', '')}")
        else:
            print("No entries found.")

if __name__ == "__main__":
    main()
