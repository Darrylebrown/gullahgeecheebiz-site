#!/usr/bin/env python3
"""
GGB Mandarin Translator — translates all published books to Mandarin Chinese
using Gemini. Same architecture as the Spanish pipeline, new language.
"""
import json, os, sys, sqlite3, requests, time
import omniroute_shim  # OMNIROUTE_MIGRATED
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Optional

BASE_DIR = Path("/Users/darrylsmac/gullahgeecheebiz-site")
PUB_DB = BASE_DIR / "publish" / "publisher.db"
MANDARIN_DIR = BASE_DIR / "publish" / "mandarin"
LOGS_DIR = Path(__file__).parent / "logs"
STATE_FILE = LOGS_DIR / "mandarin-translator-state.json"

MANDARIN_DIR.mkdir(parents=True, exist_ok=True)
LOGS_DIR.mkdir(parents=True, exist_ok=True)

OPENROUTER_MODEL = "google/gemini-2.5-flash"
BATCH_SIZE = 5

class MandarinTranslator:
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
        return {"runs": 0, "total_translated": 0, "last_run": None}
    
    def _save_state(self):
        self.state["last_run"] = datetime.now(timezone.utc).isoformat()
        STATE_FILE.write_text(json.dumps(self.state, indent=2))
    
    def _call_gemini(self, prompt: str, max_tokens: int = 2000) -> Optional[str]:
        if not self.api_key:
            return None
        try:
            r = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                json={"model": OPENROUTER_MODEL, "messages": [{"role": "user", "content": prompt}], "max_tokens": max_tokens},
                timeout=30
            )
            if r.status_code == 200:
                return r.json()["choices"][0]["message"]["content"]
        except Exception as e:
            print(f"     ⚠️  Error: {e}")
        return None
    
    def get_books(self) -> List[Dict]:
        conn = sqlite3.connect(str(PUB_DB))
        rows = conn.execute("SELECT manifest_id, data FROM manifests WHERE state = 'published'").fetchall()
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
            description = data.get("description", "")
            if isinstance(description, dict):
                description = description.get("en", str(description))
            
            books.append({
                "manifest_id": mid,
                "title": str(title),
                "description": str(description)[:500],
            })
        
        return books
    
    def translate_book(self, book: Dict) -> Optional[Dict]:
        """Translate a book's title and description to Mandarin."""
        title = book["title"]
        description = book["description"]
        
        prompt = f"""Translate this Gullah Geechee book to Mandarin Chinese (Simplified):

Title: {title}
Description: {description}

Return ONLY valid JSON:
{{"title_zh": "...", "description_zh": "..."}}"""
        
        result = self._call_gemini(prompt, max_tokens=1000)
        if not result:
            return None
        
        try:
            start = result.find("{")
            end = result.rfind("}") + 1
            if start >= 0 and end > start:
                data = json.loads(result[start:end])
            else:
                return None
        except:
            return None
        
        return {
            "manifest_id": book["manifest_id"],
            "title_en": title,
            "title_zh": data.get("title_zh", title),
            "description_zh": data.get("description_zh", description),
        }
    
    def translate_all(self, limit: int = None):
        """Translate all published books to Mandarin."""
        books = self.get_books()
        if limit:
            books = books[:limit]
        
        print(f"\n🌏 Translating {len(books)} books to Mandarin Chinese...\n")
        
        translated = []
        for i, book in enumerate(books):
            result = self.translate_book(book)
            if result:
                translated.append(result)
                self.state["total_translated"] += 1
            
            if (i + 1) % 5 == 0:
                print(f"   {i+1}/{len(books)} translated...")
                time.sleep(1)  # Rate limit breathing
        
        # Save translations
        json_path = MANDARIN_DIR / "mandarin-translations.json"
        json_path.write_text(json.dumps(translated, indent=2, ensure_ascii=False))
        
        # Also save as CSV for reference
        csv_path = MANDARIN_DIR / "mandarin-translations.csv"
        import csv
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["Manifest ID", "English Title", "Mandarin Title", "Mandarin Description"])
            for t in translated:
                writer.writerow([t["manifest_id"], t["title_en"], t["title_zh"], t["description_zh"]])
        
        self.state["runs"] += 1
        self._save_state()
        
        print(f"\n✅ Translated {len(translated)} books to Mandarin")
        print(f"   JSON: {json_path}")
        print(f"   CSV: {csv_path}")
        
        return translated

def main():
    import argparse
    parser = argparse.ArgumentParser(description="GGB Mandarin Translator")
    parser.add_argument("--limit", type=int, help="Limit number of books")
    parser.add_argument("--check", action="store_true", help="Check what would be translated")
    args = parser.parse_args()
    
    print(f"\n{'='*60}")
    print(f"🌏 GGB MANDARIN TRANSLATOR")
    print(f"   {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
    print(f"{'='*60}\n")
    
    translator = MandarinTranslator()
    books = translator.get_books()
    print(f"📚 {len(books)} books to translate\n")
    
    if args.check:
        print("Sample books:")
        for b in books[:3]:
            print(f"  📖 {b['title'][:50]}")
        return
    
    translator.translate_all(limit=args.limit)

if __name__ == "__main__":
    main()
