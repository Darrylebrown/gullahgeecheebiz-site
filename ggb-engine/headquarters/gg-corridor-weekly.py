#!/usr/bin/env python3
"""
Gullah Geechee Corridor Weekly — a weekly magazine celebrating the people,
places, food, history, and culture of the Gullah Geechee Corridor.
Published in English, Spanish, and Mandarin with EPUB + audio.
"""
import json, os, sys, requests, time, html
import omniroute_shim  # OMNIROUTE_MIGRATED
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List

BASE_DIR = Path("/Users/darrylsmac/gullahgeecheebiz-site")
OUTPUT_DIR = BASE_DIR / "publish" / "magazines" / "gg-corridor-weekly"
LOGS_DIR = Path(__file__).parent / "logs"
STATE_FILE = LOGS_DIR / "gg-corridor-weekly-state.json"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
LOGS_DIR.mkdir(parents=True, exist_ok=True)

OPENROUTER_MODEL = "google/gemini-2.5-flash"

TOPICS = [
    "Gullah Geechee foodways and recipes",
    "Sea Island history and heritage",
    "Gullah Geechee language and storytelling",
    "Lowcountry music and spirituals",
    "Sweetgrass basket weaving and crafts",
    "Gullah Geechee fishing and maritime traditions",
    "Rice culture and its legacy",
    "Gullah Geechee communities today",
    "Preservation of Gullah Geechee sites",
    "Gullah Geechee art and visual culture",
    "Plantation to freedom: Gullah stories",
    "Gullah Geechee elders and oral histories",
    "Sea Island ecology and land stewardship",
    "Gullah Geechee festivals and celebrations",
    "The Gullah Geechee Cultural Heritage Corridor",
    "Gullah Geechee influence on Southern culture",
    "Heirs' property and land rights",
    "Gullah Geechee spiritual traditions",
    "From Africa to the Sea Islands: the journey",
    "Gullah Geechee business and entrepreneurship",
    "Gullah Geechee in the digital age",
    "Sea Island agriculture and farming",
    "Gullah Geechee healing traditions",
    "The art of Gullah Geechee quilting",
    "Gullah Geechee youth and the future",
]

LANGUAGES = {
    "en": {"code": "en", "name": "English", "prompt_suffix": "Write in English."},
    "es": {"code": "es", "name": "Spanish", "prompt_suffix": "Escribe en español."},
    "zh": {"code": "zh", "name": "Mandarin", "prompt_suffix": "用简体中文写作。"},
}

class CorridorWeekly:
    def __init__(self):
        self.api_key = self._get_api_key()
        self.state = self._load_state()
    
    def _get_api_key(self) -> str:
        env_file = BASE_DIR / ".env"
        if env_file.exists():
            for line in env_file.read_text().split("\n"):
                if "OPENROUTER_API_KEY" in line:
                    return line.split("=", 1)[1].strip().strip('"').strip("'")
        return ""
    
    def _load_state(self) -> Dict:
        if STATE_FILE.exists():
            try:
                return json.loads(STATE_FILE.read_text())
            except:
                pass
        return {"issues": 0, "last_run": None}
    
    def _save_state(self):
        self.state["last_run"] = datetime.now(timezone.utc).isoformat()
        STATE_FILE.write_text(json.dumps(self.state, indent=2))
    
    def _call_gemini(self, prompt: str, max_tokens: int = 2500) -> str:
        if not self.api_key:
            return "Content generation unavailable."
        try:
            r = requests.post(
                "omniroute",
                headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                json={"model": OPENROUTER_MODEL, "messages": [{"role": "user", "content": prompt}], "max_tokens": max_tokens},
                timeout=30
            )
            if r.status_code == 200:
                return r.json()["choices"][0]["message"]["content"]
        except:
            pass
        return "Content generation unavailable."
    
    def generate_issue(self, topic: str, lang: str, week: int) -> Dict:
        """Generate one issue of the Corridor Weekly in a specific language."""
        lang_info = LANGUAGES[lang]
        
        prompt = f"""Write a weekly magazine issue for "Gullah Geechee Corridor Weekly".

Topic: {topic}
Week {week}, August 2026

Include:
1. A featured article (400-500 words) exploring this topic in depth
2. A profile of a person or place connected to the topic
3. A recipe, saying, or cultural practice
4. A "Did You Know?" fact
5. A call to action for readers to engage with Gullah Geechee culture

{lang_info['prompt_suffix']}

Format as markdown with a clear title and sections."""
        
        content = self._call_gemini(prompt, max_tokens=3000)
        
        return {
            "topic": topic,
            "language": lang,
            "week": week,
            "name": f"Gullah Geechee Corridor Weekly — {topic[:40]}",
            "content": content,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }
    
    def generate_week(self, week: int = None):
        """Generate one week's issue in all 3 languages."""
        if week is None:
            week = int(datetime.now().timestamp() / 604800) % 52
        
        # Pick a topic for this week
        topic = TOPICS[week % len(TOPICS)]
        
        print(f"\n📰 Gullah Geechee Corridor Weekly — Week {week}")
        print(f"   Topic: {topic}")
        print(f"{'='*50}\n")
        
        issues = []
        for lang in LANGUAGES:
            print(f"   🌐 {LANGUAGES[lang]['name']}...", end=" ")
            issue = self.generate_issue(topic, lang, week)
            issues.append(issue)
            print(f"✅ ({len(issue['content'])} chars)")
            time.sleep(1)
        
        # Save files
        week_dir = OUTPUT_DIR / f"week-{week:02d}"
        week_dir.mkdir(parents=True, exist_ok=True)
        
        for issue in issues:
            filename = f"gg-corridor-weekly-{issue['language']}.md"
            path = week_dir / filename
            content = f"# Gullah Geechee Corridor Weekly\n\n## {issue['topic']}\n\n---\n\n{issue['content']}"
            path.write_text(content)
            
            # Generate EPUB
            epub_path = week_dir / f"gg-corridor-weekly-{issue['language']}.epub"
            self._generate_epub(issue, content, epub_path)
            
            # Generate audio
            audio_dir = week_dir / "audio"
            audio_dir.mkdir(exist_ok=True)
            audio_path = audio_dir / f"gg-corridor-weekly-{issue['language']}.mp3"
            self._generate_audio(issue, content, audio_path)
        
        # Save combined
        json_path = week_dir / "all-languages.json"
        json_path.write_text(json.dumps(issues, indent=2, ensure_ascii=False))
        
        self.state["issues"] += len(issues)
        self._save_state()
        
        print(f"\n✅ Week {week} complete: {len(issues)} issues")
        print(f"   Topic: {topic}")
        print(f"   Location: {week_dir}")
        
        return issues
    
    def _generate_epub(self, issue: Dict, content: str, path: Path):
        try:
            title = f"Gullah Geechee Corridor Weekly — {issue['topic'][:40]}"
            body_html = f"<h1>{html.escape(title)}</h1>\n"
            for line in content.split("\n"):
                if line.startswith("# "):
                    body_html += f"<h2>{html.escape(line[2:])}</h2>\n"
                elif line.startswith("## "):
                    body_html += f"<h3>{html.escape(line[3:])}</h3>\n"
                elif line.strip():
                    body_html += f"<p>{html.escape(line)}</p>\n"
            epub_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<html xmlns="http://www.w3.org/1999/xhtml">
<head><title>{html.escape(title)}</title></head>
<body>{body_html}</body>
</html>"""
            path.write_text(epub_content)
        except:
            pass
    
    def _generate_audio(self, issue: Dict, content: str, path: Path):
        try:
            from gtts import gTTS
            text = content[:2000].replace("#", "").replace("*", "")
            lang_map = {"en": "en", "es": "es", "zh": "zh-CN"}
            tts_lang = lang_map.get(issue["language"], "en")
            tts = gTTS(text=text, lang=tts_lang, slow=False)
            tts.save(str(path))
        except:
            path.with_suffix(".txt").write_text(text[:2000])

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Gullah Geechee Corridor Weekly")
    parser.add_argument("--week", type=int, help="Week number (0-51)")
    parser.add_argument("--check", action="store_true", help="Show topic for this week")
    args = parser.parse_args()
    
    print(f"\n{'='*60}")
    print(f"📰 GULLAH GEECHEE CORRIDOR WEEKLY")
    print(f"   {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
    print(f"{'='*60}\n")
    
    week = args.week if args.week is not None else int(datetime.now().timestamp() / 604800) % 52
    topic = TOPICS[week % len(TOPICS)]
    
    if args.check:
        print(f"Week {week}: {topic}")
        print(f"Languages: EN | ES | ZH")
        print(f"Output: EPUB + Audio")
        return
    
    gen = CorridorWeekly()
    gen.generate_week(week=week)

if __name__ == "__main__":
    main()
