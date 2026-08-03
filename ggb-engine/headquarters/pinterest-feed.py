#!/usr/bin/env python3
"""
GGB Pinterest Feed — generates pin descriptions, titles, and image prompts
for every published book, magazine, and encyclopedia volume.
Outputs a Pinterest-ready CSV for bulk upload.
"""
import json, os, sys, sqlite3, requests, csv
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Optional

BASE_DIR = Path("/Users/darrylsmac/gullahgeecheebiz-site")
PUB_DB = BASE_DIR / "publish" / "publisher.db"
PINS_DIR = BASE_DIR / "publish" / "pins"
LOGS_DIR = Path(__file__).parent / "logs"
STATE_FILE = LOGS_DIR / "pinterest-feed-state.json"

PINS_DIR.mkdir(parents=True, exist_ok=True)
LOGS_DIR.mkdir(parents=True, exist_ok=True)

# ─── Config ───────────────────────────────────────────────────────────────

OPENROUTER_MODEL = "google/gemini-2.5-flash"
BATCH_SIZE = 20

# ─── Pinterest Feed Generator ─────────────────────────────────────────────

class PinterestFeed:
    def __init__(self):
        self.api_key = self._get_api_key()
        self.pins = []
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
        return {"runs": 0, "total_pins": 0, "last_run": None}
    
    def _save_state(self):
        self.state["last_run"] = datetime.now(timezone.utc).isoformat()
        STATE_FILE.write_text(json.dumps(self.state, indent=2))
    
    def _call_gemini(self, prompt: str, max_tokens: int = 300) -> Optional[str]:
        if not self.api_key:
            return None
        try:
            r = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                json={"model": OPENROUTER_MODEL, "messages": [{"role": "user", "content": prompt}], "max_tokens": max_tokens},
                timeout=15
            )
            if r.status_code == 200:
                return r.json()["choices"][0]["message"]["content"]
        except:
            pass
        return None
    
    def get_books(self) -> List[Dict]:
        """Get all published books from the pipeline."""
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
            books.append({"manifest_id": mid, "title": title, "data": data})
        
        return books
    
    def generate_pin(self, book: Dict) -> Optional[Dict]:
        """Generate a Pinterest pin for a book using Gemini."""
        title = book["title"]
        mid = book["manifest_id"]
        
        # Generate pin title and description
        prompt = f"""Create a Pinterest pin for this Gullah Geechee book:

Title: {title}

Generate:
1. A catchy pin title (under 40 chars)
2. A compelling pin description (100-200 chars) that includes keywords
3. An image prompt for a Pinterest-style vertical pin (1000x1500px)
4. 3 relevant hashtags

Format as JSON:
{{"pin_title": "...", "description": "...", "image_prompt": "...", "hashtags": ["#tag1", "#tag2", "#tag3"]}}"""
        
        result = self._call_gemini(prompt, max_tokens=500)
        if not result:
            return None
        
        # Parse JSON from response
        try:
            # Find JSON block in response
            start = result.find("{")
            end = result.rfind("}") + 1
            if start >= 0 and end > start:
                pin_data = json.loads(result[start:end])
            else:
                return None
        except:
            return None
        
        return {
            "manifest_id": mid,
            "title": title,
            "pin_title": pin_data.get("pin_title", title[:40]),
            "description": pin_data.get("description", f"Discover {title}"),
            "image_prompt": pin_data.get("image_prompt", f"A book cover for {title}"),
            "hashtags": pin_data.get("hashtags", ["#GullahGeechee", "#Books", "#Culture"]),
        }
    
    def generate_feed(self, limit: int = None):
        """Generate Pinterest pins for all published books."""
        books = self.get_books()
        if limit:
            books = books[:limit]
        
        print(f"\n📌 Generating Pinterest feed for {len(books)} books...\n")
        
        for i, book in enumerate(books):
            pin = self.generate_pin(book)
            if pin:
                self.pins.append(pin)
                self.state["total_pins"] += 1
            
            if (i + 1) % 10 == 0:
                print(f"   {i+1}/{len(books)} pins generated...")
        
        print(f"\n✅ Generated {len(self.pins)} pins")
        self._save_state()
    
    def export_csv(self):
        """Export pins as Pinterest-ready CSV."""
        csv_path = PINS_DIR / "pinterest-feed.csv"
        
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["Pin Title", "Description", "Link", "Image URL", "Hashtags"])
            
            for pin in self.pins:
                link = f"https://gullahgeecheebiz.com/shop.html"
                hashtags = " ".join(pin.get("hashtags", []))
                writer.writerow([
                    pin["pin_title"],
                    pin["description"],
                    link,
                    "",  # Image URL — generated separately
                    hashtags,
                ])
        
        print(f"\n📄 CSV exported: {csv_path}")
        return csv_path
    
    def export_json(self):
        """Export pins as JSON for programmatic use."""
        json_path = PINS_DIR / "pinterest-feed.json"
        json_path.write_text(json.dumps(self.pins, indent=2))
        print(f"\n📄 JSON exported: {json_path}")
        return json_path
    
    def export_image_prompts(self):
        """Export image prompts for batch image generation."""
        prompts_path = PINS_DIR / "pin-image-prompts.json"
        prompts = [{"id": p["manifest_id"][:12], "title": p["pin_title"], "prompt": p["image_prompt"]} for p in self.pins]
        prompts_path.write_text(json.dumps(prompts, indent=2))
        print(f"\n🖼️  Image prompts exported: {prompts_path} ({len(prompts)} prompts)")
        return prompts_path

def main():
    import argparse
    parser = argparse.ArgumentParser(description="GGB Pinterest Feed Generator")
    parser.add_argument("--limit", type=int, help="Limit number of pins to generate")
    parser.add_argument("--export", action="store_true", help="Export existing pins without regenerating")
    args = parser.parse_args()
    
    print(f"\n{'='*60}")
    print(f"📌 GGB PINTEREST FEED GENERATOR")
    print(f"   {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
    print(f"{'='*60}\n")
    
    feed = PinterestFeed()
    
    if args.export:
        # Load existing pins from state
        if feed.pins:
            feed.export_csv()
            feed.export_json()
        else:
            print("No pins to export. Run without --export to generate first.")
        return
    
    feed.generate_feed(limit=args.limit)
    feed.export_csv()
    feed.export_json()
    feed.export_image_prompts()
    
    print(f"\n📊 Summary:")
    print(f"   Total pins: {len(feed.pins)}")
    print(f"   CSV: {PINS_DIR / 'pinterest-feed.csv'}")
    print(f"   JSON: {PINS_DIR / 'pinterest-feed.json'}")
    print(f"   Image prompts: {PINS_DIR / 'pin-image-prompts.json'}")

if __name__ == "__main__":
    main()
