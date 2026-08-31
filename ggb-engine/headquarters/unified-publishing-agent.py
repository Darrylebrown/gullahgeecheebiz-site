#!/usr/bin/env python3
"""
GGB Unified Publishing Agent — one agent to rule all platforms.
Handles Google Play, KDP, Draft2Digital, Spotify, ACX, DistroKid, and Pinterest
from a single cohesive system. Uses AI think tank for strategy, Playwright for execution.
import omniroute_shim  # OMNIROUTE_MIGRATED
"""
import json, os, sys, time, sqlite3, hashlib, logging, csv, shutil
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

BASE_DIR = Path("/Users/darrylsmac/gullahgeecheebiz-site")
PUB_DB = BASE_DIR / "publish" / "publisher.db"
LOGS_DIR = Path(__file__).parent / "logs"
STATE_FILE = LOGS_DIR / "unified-publisher-state.json"

os.makedirs(LOGS_DIR, exist_ok=True)

# ─── Logging ───────────────────────────────────────────────────────────────

log_file = LOGS_DIR / f"unified-publisher-{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(message)s",
    handlers=[logging.FileHandler(log_file), logging.StreamHandler()]
)
log = logging.getLogger("UnifiedPublisher")

# ─── Platform Registry ─────────────────────────────────────────────────────

PLATFORMS = {
    "google_play": {
        "name": "Google Play Books",
        "url": "https://play.google.com/books/publish/",
        "catalog_url": "https://play.google.com/books/publish/a/4261777550639003130#book/catalog",
        "files_dir": BASE_DIR / "publish" / "for-distribution" / "google-play",
        "csv_file": "google-play-bulk-import.csv",
        "type": "ebook",
        "status": "csv_uploaded_needs_epubs",
    },
    "kdp": {
        "name": "Amazon KDP",
        "url": "https://kdp.amazon.com/",
        "files_dir": BASE_DIR / "publish" / "platform-ready" / "kdp",
        "type": "ebook",
        "status": "needs_setup",
    },
    "d2d": {
        "name": "Draft2Digital",
        "url": "https://www.draft2digital.com/",
        "files_dir": BASE_DIR / "publish" / "platform-ready" / "d2d",
        "type": "ebook",
        "status": "files_ready",
    },
    "spotify": {
        "name": "Spotify for Creators",
        "url": "https://creators.spotify.com/",
        "type": "audio",
        "status": "needs_audio",
    },
    "acx": {
        "name": "ACX (Audible)",
        "url": "https://www.acx.com/",
        "type": "audio",
        "status": "needs_audio",
    },
    "distrokid": {
        "name": "DistroKid",
        "url": "https://distrokid.com/",
        "type": "music",
        "status": "needs_music",
    },
    "pinterest": {
        "name": "Pinterest",
        "url": "https://www.pinterest.com/",
        "files_dir": BASE_DIR / "publish" / "pins",
        "csv_file": "pinterest-feed.csv",
        "type": "social",
        "status": "csv_ready",
    },
}

# ─── Database ──────────────────────────────────────────────────────────────

class BookDB:
    def __init__(self):
        self.db_path = str(PUB_DB)
    
    def get_published_books(self) -> List[Dict]:
        conn = sqlite3.connect(self.db_path)
        rows = conn.execute(
            "SELECT manifest_id, data FROM manifests WHERE state = 'published'"
        ).fetchall()
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
            books.append({"manifest_id": mid, "title": str(title)})
        return books

# ─── Unified Publisher ─────────────────────────────────────────────────────

class UnifiedPublisher:
    def __init__(self):
        self.db = BookDB()
        self.state = self._load_state()
        self.api_key = self._get_api_key()
    
    def _load_state(self) -> Dict:
        if STATE_FILE.exists():
            try:
                return json.loads(STATE_FILE.read_text())
            except:
                pass
        return {"runs": 0, "platforms": {}, "last_run": None}
    
    def _save_state(self):
        self.state["last_run"] = datetime.now(timezone.utc).isoformat()
        STATE_FILE.write_text(json.dumps(self.state, indent=2))
    
    def _get_api_key(self) -> str:
        env_file = BASE_DIR / ".env"
        if env_file.exists():
            for line in env_file.read_text().split("\n"):
                if "OPENROUTER_API_KEY" in line:
                    return line.split("=", 1)[1].strip().strip('"').strip("'")
        return ""
    
    def _call_ai(self, prompt: str, model: str = "google/gemini-2.5-flash") -> Optional[str]:
        if not self.api_key:
            return None
        try:
            import requests
            r = requests.post(
                "omniroute",
                headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                json={"model": model, "messages": [{"role": "user", "content": prompt}], "max_tokens": 2000},
                timeout=30
            )
            if r.status_code == 200:
                return r.json()["choices"][0]["message"]["content"]
        except:
            pass
        return None
    
    def check_all_platforms(self) -> Dict:
        """Check status of all platforms and report what's ready."""
        log.info("=" * 60)
        log.info("📊 UNIFIED PUBLISHING STATUS")
        log.info("=" * 60)
        
        books = self.db.get_published_books()
        log.info(f"\n📚 Books in pipeline: {len(books)}")
        
        results = {}
        for key, platform in PLATFORMS.items():
            status = self._check_platform(key, platform)
            results[key] = status
            icon = "✅" if status["ready"] else "⏳" if status["has_files"] else "❌"
            log.info(f"  {icon} {platform['name']:25s} | {status['message']}")
        
        return results
    
    def _check_platform(self, key: str, platform: Dict) -> Dict:
        """Check a single platform's readiness."""
        result = {"ready": False, "has_files": False, "message": "Not set up", "files": 0}
        
        # Check if files directory exists
        files_dir = platform.get("files_dir")
        if files_dir and files_dir.exists():
            files = list(files_dir.glob("*"))
            result["has_files"] = True
            result["files"] = len(files)
        
        # Check for CSV
        csv_file = platform.get("csv_file")
        if csv_file and files_dir:
            csv_path = files_dir / csv_file
            if csv_path.exists():
                result["message"] = f"CSV ready ({csv_path.stat().st_size/1024:.0f} KB)"
                result["ready"] = True
                return result
        
        # Check for EPUBs
        if files_dir:
            epubs = list(files_dir.glob("*.epub"))
            if epubs:
                result["message"] = f"{len(epubs)} EPUBs ready"
                result["ready"] = True
                return result
        
        # Check status from platform config
        status = platform.get("status", "")
        if status == "csv_uploaded_needs_epubs":
            result["message"] = "CSV uploaded, EPUBs pending"
        elif status == "files_ready":
            result["message"] = "Files ready for upload"
        elif status == "csv_ready":
            result["message"] = "CSV ready for import"
        elif status == "needs_audio":
            result["message"] = "Needs audio generation"
        elif status == "needs_music":
            result["message"] = "Needs music generation"
        
        return result
    
    def generate_strategy(self, platform_key: str) -> Optional[str]:
        """Use AI to generate a strategy for a specific platform."""
        platform = PLATFORMS.get(platform_key)
        if not platform:
            log.error(f"Unknown platform: {platform_key}")
            return None
        
        books = self.db.get_published_books()
        
        prompt = f"""You are a publishing automation expert. Generate a step-by-step strategy for uploading books to {platform['name']}.

Context:
- {len(books)} books ready in pipeline
- Platform URL: {platform.get('url', 'unknown')}
- Platform type: {platform.get('type', 'unknown')}
- Current status: {platform.get('status', 'unknown')}

Provide:
1. Exact steps to upload
2. What files are needed
3. How to handle authentication
4. How to avoid reCAPTCHA
5. How to scale from 1 to {len(books)} books
6. Common pitfalls to avoid

Be specific and actionable."""
        
        log.info(f"🧠 Generating strategy for {platform['name']}...")
        strategy = self._call_ai(prompt)
        
        if strategy:
            strategy_path = LOGS_DIR / f"strategy-{platform_key}.md"
            strategy_path.write_text(f"# Strategy: {platform['name']}\n\n{strategy}")
            log.info(f"✅ Strategy saved: {strategy_path.name}")
        
        return strategy
    
    def generate_all_strategies(self):
        """Generate strategies for all platforms."""
        log.info("=" * 60)
        log.info("🧠 GENERATING STRATEGIES FOR ALL PLATFORMS")
        log.info("=" * 60)
        
        for key in PLATFORMS:
            self.generate_strategy(key)
            time.sleep(1)  # Rate limit breathing
        
        log.info("\n✅ All strategies generated")
    
    def run_think_tank(self, platform_key: str):
        """Run multiple AI models on a single platform challenge."""
        models = [
            ("Gemini 2.5 Flash", "google/gemini-2.5-flash"),
            ("DeepSeek V4", "deepseek/deepseek-chat"),
            ("Qwen 3.7 Max", "qwen/qwen3.7-max"),
            ("Nemotron 3 Ultra", "nvidia/nemotron-3-ultra-550b-a55b:free"),
            ("Ling 3.0 Flash", "inclusionai/ling-3.0-flash:free"),
        ]
        
        platform = PLATFORMS.get(platform_key)
        if not platform:
            log.error(f"Unknown platform: {platform_key}")
            return
        
        books = self.db.get_published_books()
        
        prompt = f"""Write a complete Python script that automates uploading books to {platform['name']}.

Platform URL: {platform.get('url', 'unknown')}
Books to upload: {len(books)}
Files available: {platform.get('files_dir', 'unknown')}

The script must:
1. Use Playwright for browser automation
2. Handle login/session persistence
3. Upload files in batches
4. Handle errors gracefully
5. Report progress

Write the COMPLETE working script with all imports and functions."""
        
        log.info(f"\n🧠 Think Tank: {platform['name']}")
        log.info(f"   Models competing: {len(models)}")
        
        import threading
        results = {}
        threads = []
        
        for name, model in models:
            t = threading.Thread(
                target=lambda n=name, m=model: results.update({
                    n: self._call_ai(prompt, model=m)
                })
            )
            threads.append(t)
            t.start()
            time.sleep(1)
        
        for t in threads:
            t.join(timeout=45)
        
        # Find winner
        winner = None
        for name, response in results.items():
            if response and len(response) > 100:
                log.info(f"  ✅ {name}: {len(response)} chars")
                if not winner:
                    winner = (name, response)
            else:
                log.info(f"  ❌ {name}: no valid response")
        
        if winner:
            name, response = winner
            log.info(f"\n🏆 Winner: {name}")
            
            # Save winning strategy
            winner_path = LOGS_DIR / f"think-tank-winner-{platform_key}.md"
            winner_path.write_text(f"# 🏆 Think Tank Winner: {name}\n\n{response}")
            log.info(f"✅ Saved: {winner_path.name}")
        
        return results
    
    def research_api_connections(self):
        """Use AI think tank to research the BEST alternative for each distributor."""
        log.info("=" * 60)
        log.info("🔍 FINDING THE BEST ALTERNATIVE FOR EACH DISTRIBUTOR")
        log.info("=" * 60)
        
        for key, platform in PLATFORMS.items():
            log.info(f"\n🔍 Researching: {platform['name']}")
            
            prompt = f"""We already know {platform['name']} has NO public API for automated publishing.

Platform: {platform['name']}
URL: {platform.get('url', 'unknown')}
Type: {platform.get('type', 'unknown')}

Now find the BEST alternative approach. Be specific and actionable:

1. What is the SINGLE best way to automate uploading to this platform?
2. Give me the EXACT steps using Playwright (browser automation)
3. What selectors, buttons, and forms does the upload page have?
4. How to handle login/session persistence?
5. How to batch upload many files?
6. What are the common pitfalls and how to avoid them?
7. Is there a third-party service that bridges this platform with an API?

If browser automation is the only way, write the core Playwright code snippet for the upload flow.

Be extremely specific. Give me code, not theory."""
            
            result = self._call_ai(prompt, model="google/gemini-2.5-flash")
            
            if result:
                path = LOGS_DIR / f"api-research-{key}.md"
                path.write_text(f"# API Research: {platform['name']}\n\n{result}")
                log.info(f"  ✅ Research saved: {path.name}")
            else:
                log.info(f"  ❌ Research failed")
            
            time.sleep(1)
        
        log.info("\n✅ API research complete for all platforms")

def main():
    import argparse
    parser = argparse.ArgumentParser(description="GGB Unified Publishing Agent")
    parser.add_argument("--check", action="store_true", help="Check all platforms")
    parser.add_argument("--strategies", action="store_true", help="Generate strategies for all platforms")
    parser.add_argument("--think-tank", type=str, help="Run think tank on a platform (google_play, kdp, d2d, etc.)")
    parser.add_argument("--api-research", action="store_true", help="Research API connections for all distributors")
    parser.add_argument("--list", action="store_true", help="List available platforms")
    args = parser.parse_args()
    
    print(f"\n{'='*60}")
    print(f"🤖 GGB UNIFIED PUBLISHING AGENT")
    print(f"   {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
    print(f"{'='*60}\n")
    
    publisher = UnifiedPublisher()
    
    if args.list:
        print("Available platforms:")
        for key, p in PLATFORMS.items():
            print(f"  {key:20s} — {p['name']} ({p['type']})")
        return
    
    if args.check:
        publisher.check_all_platforms()
        return
    
    if args.strategies:
        publisher.generate_all_strategies()
        return
    
    if args.think_tank:
        publisher.run_think_tank(args.think_tank)
        return
    
    if args.api_research:
        publisher.research_api_connections()
        return
    
    # Default: check all platforms
    publisher.check_all_platforms()

if __name__ == "__main__":
    main()
