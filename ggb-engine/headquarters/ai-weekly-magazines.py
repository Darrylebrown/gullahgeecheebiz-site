#!/usr/bin/env python3
"""
GGB AI Weekly Magazine Generator — produces 5 AI-focused magazines
every week in English, Spanish, and Mandarin. Runs as a cron job.
"""
import json, os, sys, sqlite3, requests, time, csv
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List

BASE_DIR = Path("/Users/darrylsmac/gullahgeecheebiz-site")
OUTPUT_DIR = BASE_DIR / "publish" / "magazines" / "ai-weekly"
LOGS_DIR = Path(__file__).parent / "logs"
STATE_FILE = LOGS_DIR / "ai-magazines-state.json"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
LOGS_DIR.mkdir(parents=True, exist_ok=True)

OPENROUTER_MODEL = "google/gemini-2.5-flash"

AI_MAGAZINES = [
    {
        "slug": "ai-for-the-culture",
        "name_en": "AI for the Culture",
        "name_es": "IA para la Cultura",
        "name_zh": "文化人工智能",
        "tagline_en": "AI tools for heritage creators",
        "tagline_es": "Herramientas de IA para creadores de herencia cultural",
        "tagline_zh": "为文化遗产创作者提供的人工智能工具",
    },
    {
        "slug": "the-ai-publisher",
        "name_en": "The AI Publisher",
        "name_es": "El Editor de IA",
        "name_zh": "人工智能出版人",
        "tagline_en": "Weekly deep-dive on AI publishing",
        "tagline_es": "Inmersión semanal en la publicación con IA",
        "tagline_zh": "每周深入探讨人工智能出版",
    },
    {
        "slug": "ai-side-hustle",
        "name_en": "AI Side Hustle Weekly",
        "name_es": "Ingresos Extra con IA Semanal",
        "name_zh": "人工智能副业周刊",
        "tagline_en": "Real ways to make money with AI",
        "tagline_es": "Formas reales de ganar dinero con IA",
        "tagline_zh": "用人工智能赚钱的真实方法",
    },
    {
        "slug": "prompt-and-publish",
        "name_en": "Prompt & Publish",
        "name_es": "Prompt y Publica",
        "name_zh": "提示与出版",
        "tagline_en": "10 new prompts every week",
        "tagline_es": "10 nuevos prompts cada semana",
        "tagline_zh": "每周10个新提示",
    },
    {
        "slug": "the-autonomous-creator",
        "name_en": "The Autonomous Creator",
        "name_es": "El Creador Autónomo",
        "name_zh": "自主创作者",
        "tagline_en": "AI agents that create while you sleep",
        "tagline_es": "Agentes de IA que crean mientras duermes",
        "name_zh": "在你睡觉时创作的人工智能代理",
    },
]

LANGUAGES = {
    "en": {"code": "en", "name": "English", "prompt_suffix": "Write in English."},
    "es": {"code": "es", "name": "Spanish", "prompt_suffix": "Escribe en español."},
    "zh": {"code": "zh", "name": "Mandarin", "prompt_suffix": "用简体中文写作。"},
}

class AIMagazineGenerator:
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
    
    def _call_gemini(self, prompt: str, max_tokens: int = 2000) -> str:
        if not self.api_key:
            return "Content generation unavailable."
        try:
            r = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                json={"model": OPENROUTER_MODEL, "messages": [{"role": "user", "content": prompt}], "max_tokens": max_tokens},
                timeout=30
            )
            if r.status_code == 200:
                return r.json()["choices"][0]["message"]["content"]
        except:
            pass
        return "Content generation unavailable."
    
    def generate_issue(self, magazine: Dict, lang: str, week: int) -> Dict:
        """Generate one issue of a magazine in a specific language."""
        lang_info = LANGUAGES[lang]
        name_key = f"name_{lang}"
        tagline_key = f"tagline_{lang}"
        name = magazine.get(name_key, magazine["name_en"])
        tagline = magazine.get(tagline_key, magazine["tagline_en"])
        
        prompt = f"""Write a weekly magazine issue for "{name}".

Tagline: {tagline}
Week {week}, August 2026

Include:
1. A featured article (300-400 words) on the latest AI trend relevant to this topic
2. 3 quick tips or tools
3. A quote or insight
4. A call to action

{lang_info['prompt_suffix']}

Format as markdown with a clear title and sections."""
        
        content = self._call_gemini(prompt, max_tokens=2500)
        
        return {
            "magazine": magazine["slug"],
            "language": lang,
            "week": week,
            "name": name,
            "tagline": tagline,
            "content": content,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }
    
    def generate_week(self, week: int = None):
        """Generate all 5 magazines in all 3 languages for a given week."""
        if week is None:
            # Calculate week number from epoch
            week = int(datetime.now().timestamp() / 604800) % 52
        
        print(f"\n📰 Generating AI Weekly — Week {week}")
        print(f"{'='*50}\n")
        
        all_issues = []
        
        for mag in AI_MAGAZINES:
            print(f"📰 {mag['name_en']}...")
            for lang in LANGUAGES:
                print(f"   🌐 {LANGUAGES[lang]['name']}...", end=" ")
                issue = self.generate_issue(mag, lang, week)
                all_issues.append(issue)
                print(f"✅ ({len(issue['content'])} chars)")
                time.sleep(1)  # Rate limit breathing
        
        # Save all issues
        week_dir = OUTPUT_DIR / f"week-{week:02d}"
        week_dir.mkdir(parents=True, exist_ok=True)
        
        for issue in all_issues:
            filename = f"{issue['magazine']}-{issue['language']}.md"
            path = week_dir / filename
            content = f"# {issue['name']}\n\n*{issue['tagline']}*\n\n---\n\n{issue['content']}"
            path.write_text(content)
            
            # Generate EPUB
            epub_path = week_dir / f"{issue['magazine']}-{issue['language']}.epub"
            self._generate_epub(issue, content, epub_path)
            
            # Generate audio
            audio_dir = week_dir / "audio"
            audio_dir.mkdir(exist_ok=True)
            audio_path = audio_dir / f"{issue['magazine']}-{issue['language']}.mp3"
            self._generate_audio(issue, content, audio_path)
        
        # Save combined JSON
        json_path = week_dir / "all-issues.json"
        json_path.write_text(json.dumps(all_issues, indent=2, ensure_ascii=False))
        
        self.state["issues"] += len(all_issues)
        self._save_state()
        
        print(f"\n✅ Week {week} complete: {len(all_issues)} issues")
        print(f"   Location: {week_dir}")
        
        return all_issues
    
    def _generate_epub(self, issue: Dict, content: str, path: Path):
        """Generate a simple EPUB from markdown content."""
        try:
            import html
            title = issue["name"]
            author = "Gullah Geechee Biz"
            
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
        """Generate audio using TTS."""
        try:
            from gtts import gTTS
            
            # Extract first 2000 chars for audio
            text = content[:2000].replace("#", "").replace("*", "")
            
            lang_map = {"en": "en", "es": "es", "zh": "zh-CN"}
            tts_lang = lang_map.get(issue["language"], "en")
            
            tts = gTTS(text=text, lang=tts_lang, slow=False)
            tts.save(str(path))
        except ImportError:
            # Fallback: save text for later TTS
            path.with_suffix(".txt").write_text(text[:2000])
        except:
            pass

def main():
    import argparse
    parser = argparse.ArgumentParser(description="GGB AI Weekly Magazine Generator")
    parser.add_argument("--week", type=int, help="Week number (0-51)")
    parser.add_argument("--check", action="store_true", help="Check what would be generated")
    args = parser.parse_args()
    
    print(f"\n{'='*60}")
    print(f"📰 GGB AI WEEKLY MAGAZINE GENERATOR")
    print(f"   {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
    print(f"{'='*60}\n")
    
    if args.check:
        print("5 magazines × 3 languages = 15 issues per week\n")
        for mag in AI_MAGAZINES:
            print(f"  📰 {mag['name_en']}")
            print(f"     🌐 EN | 🇪🇸 ES | 🇨🇳 ZH")
        return
    
    gen = AIMagazineGenerator()
    gen.generate_week(week=args.week)

if __name__ == "__main__":
    main()
