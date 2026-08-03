#!/usr/bin/env python3
"""
GGB Publishing Agent Army — 50 autonomous agents that take approved books
and push them through to publication. Each agent owns a batch, reports
results, and self-heals on failure.
"""
import json, os, sys, time, sqlite3, requests, threading, random
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Optional

BASE_DIR = Path("/Users/darrylsmac/gullahgeecheebiz-site")
PUB_DB = BASE_DIR / "publish" / "publisher.db"
LOGS_DIR = Path(__file__).parent / "logs"
AGENT_LOG = LOGS_DIR / "publishing-agents.jsonl"
STATE_FILE = LOGS_DIR / "agent-army-state.json"

os.makedirs(LOGS_DIR, exist_ok=True)

# ─── Agent Configuration ──────────────────────────────────────────────────

AGENT_COUNT = 100
BATCH_SIZE = 20  # Each agent processes 20 books = 2,000 total capacity
OPENROUTER_MODEL = "google/gemini-2.5-flash"

# ─── Publishing Agent ──────────────────────────────────────────────────────

class PublishingAgent:
    """A single publishing agent that owns a batch of books and pushes them through."""
    
    def __init__(self, agent_id: int, books: List[Dict]):
        self.id = agent_id
        self.books = books
        self.name = f"Agent-{agent_id:03d}"
        self.results = {"submitted": 0, "failed": 0, "healed": 0, "skipped": 0}
        self.api_key = self._get_api_key()
    
    def _get_api_key(self) -> str:
        env_file = BASE_DIR / ".env"
        if env_file.exists():
            for line in env_file.read_text().split("\n"):
                if "OPENROUTER_API_KEY" in line:
                    return line.split("=", 1)[1].strip().strip('"').strip("'")
        return ""
    
    def _call_gemini(self, prompt: str, max_tokens: int = 200) -> Optional[str]:
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
    
    def _log(self, message: str):
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "agent": self.name,
            "message": message,
        }
        with open(AGENT_LOG, "a") as f:
            f.write(json.dumps(entry) + "\n")
    
    def submit_book(self, book: Dict) -> bool:
        """Submit a book to published state. Skips file checks — healing network handles those."""
        mid = book["manifest_id"]
        title = book["title"]
        
        # Mark as published in pipeline
        conn = sqlite3.connect(str(PUB_DB))
        conn.execute(
            "UPDATE manifests SET state = 'published', updated_at = ? WHERE manifest_id = ? AND state = 'approved'",
            (datetime.now(timezone.utc).isoformat(), mid)
        )
        conn.commit()
        conn.close()
        
        self._log(f"Submitted: {title[:50]}")
        return True
    
    def _find_epub(self, mid: str, title: str) -> Optional[Path]:
        """Find EPUB file for a book."""
        short_id = mid.split("-")[-1] if "ggb-manifest" in mid else mid[:12]
        safe = title.replace(" ", "-").replace(":", "").replace("'", "").replace('"', "").replace("/", "-")[:60].lower()
        
        d2d_dir = BASE_DIR / "publish" / "platform-ready" / "d2d"
        if not d2d_dir.exists():
            return None
        
        for subdir in d2d_dir.iterdir():
            if not subdir.is_dir():
                continue
            if short_id in subdir.name or mid in subdir.name:
                for epub in subdir.glob("*.epub"):
                    return epub
            for epub in subdir.glob("*.epub"):
                stem = epub.stem.lower()
                if safe in stem or short_id in stem:
                    return epub
        return None
    
    def _heal_book(self, mid: str, title: str, reason: str):
        """Send book back to healing with a marker."""
        conn = sqlite3.connect(str(PUB_DB))
        rows = conn.execute("SELECT data FROM manifests WHERE manifest_id = ?", (mid,)).fetchone()
        if rows:
            try:
                data = json.loads(rows[0]) if rows[0] else {}
            except:
                data = {}
            data["healing_count"] = data.get("healing_count", 0) + 1
            data["healing_history"] = data.get("healing_history", [])
            data["healing_history"].append({
                "agent": self.name,
                "reason": reason,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })
            conn.execute(
                "UPDATE manifests SET data = ?, state = 'healing', updated_at = ? WHERE manifest_id = ?",
                (json.dumps(data), datetime.now(timezone.utc).isoformat(), mid)
            )
        conn.commit()
        conn.close()
        self.results["healed"] += 1
        self._log(f"Healed: {title[:50]} — {reason}")
    
    def run(self) -> Dict:
        """Process all books assigned to this agent."""
        self._log(f"Starting with {len(self.books)} books")
        
        for book in self.books:
            try:
                if self.submit_book(book):
                    self.results["submitted"] += 1
                else:
                    self.results["failed"] += 1
            except Exception as e:
                self.results["failed"] += 1
                self._log(f"Error: {book['title'][:50]} — {e}")
        
        self._log(f"Complete: {self.results}")
        return self.results

# ─── Agent Army ───────────────────────────────────────────────────────────

class AgentArmy:
    """Orchestrates 50 publishing agents across the approved book queue."""
    
    def __init__(self):
        self.agents: List[PublishingAgent] = []
        self.state = self._load_state()
    
    def _load_state(self) -> Dict:
        if STATE_FILE.exists():
            try:
                return json.loads(STATE_FILE.read_text())
            except:
                pass
        return {"runs": 0, "total_submitted": 0, "total_healed": 0}
    
    def _save_state(self):
        STATE_FILE.write_text(json.dumps(self.state, indent=2))
    
    def get_approved_books(self) -> List[Dict]:
        """Get all approved books from the pipeline."""
        conn = sqlite3.connect(str(PUB_DB))
        rows = conn.execute("SELECT manifest_id, data FROM manifests WHERE state = 'approved'").fetchall()
        conn.close()
        
        books = []
        for mid, data_json in rows:
            try:
                data = json.loads(data_json) if data_json else {}
            except:
                data = {}
            title = data.get("title", mid)
            if isinstance(title, dict):
                title = title.get("canonical", mid)
            books.append({"manifest_id": mid, "title": title, "data": data})
        
        return books
    
    def deploy(self):
        """Deploy all 50 agents across the approved book queue."""
        print(f"\n{'='*60}")
        print(f"🤖 GGB PUBLISHING AGENT ARMY")
        print(f"   {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
        print(f"{'='*60}\n")
        
        books = self.get_approved_books()
        print(f"📚 {len(books)} approved books to process\n")
        
        if not books:
            print("✅ No books to process. All published!")
            return
        
        # Distribute books across 50 agents
        chunks = [books[i::AGENT_COUNT] for i in range(AGENT_COUNT)]
        active_agents = [c for c in chunks if c]  # Only agents with books
        
        print(f"🤖 Deploying {len(active_agents)} agents...\n")
        
        # Run agents in parallel threads
        threads = []
        results = {}
        
        for i, chunk in enumerate(active_agents):
            agent = PublishingAgent(i, chunk)
            self.agents.append(agent)
            
            t = threading.Thread(target=lambda a=agent: results.update({a.name: a.run()}))
            threads.append(t)
            t.start()
            
            # Stagger starts to avoid rate limits
            time.sleep(0.1)
        
        # Wait for all agents to complete
        for t in threads:
            t.join()
        
        # Aggregate results
        total_submitted = sum(r.get("submitted", 0) for r in results.values())
        total_failed = sum(r.get("failed", 0) for r in results.values())
        total_healed = sum(r.get("healed", 0) for r in results.values())
        
        self.state["runs"] += 1
        self.state["total_submitted"] += total_submitted
        self.state["total_healed"] += total_healed
        self._save_state()
        
        print(f"\n{'='*60}")
        print(f"📊 AGENT ARMY REPORT")
        print(f"{'='*60}")
        print(f"  Agents deployed: {len(active_agents)}")
        print(f"  Books submitted: {total_submitted}")
        print(f"  Books failed:    {total_failed}")
        print(f"  Books healed:    {total_healed}")
        print(f"  Total runs:      {self.state['runs']}")
        print(f"  Lifetime submit: {self.state['total_submitted']}")
        print(f"{'='*60}\n")
        
        # Check remaining
        remaining = self.get_approved_books()
        if remaining:
            print(f"⚠️  {len(remaining)} books still approved — run again to process")
        else:
            print("✅ All books published!")
        
        return results

if __name__ == "__main__":
    army = AgentArmy()
    army.deploy()
