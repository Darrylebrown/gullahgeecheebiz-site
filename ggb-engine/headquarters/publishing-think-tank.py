#!/usr/bin/env python3
"""
GGB Publishing Think Tank — sends the same publishing challenge to multiple
AI models simultaneously via OpenRouter. Models compete to find the best
strategy for getting a book published on a real store.
"""
import json, os, sys, requests, time, threading
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Optional

BASE_DIR = Path("/Users/darrylsmac/gullahgeecheebiz-site")
LOGS_DIR = Path(__file__).parent / "logs"
STATE_FILE = LOGS_DIR / "think-tank-state.json"

LOGS_DIR.mkdir(parents=True, exist_ok=True)

# ─── The Challenge ─────────────────────────────────────────────────────────

CHALLENGE = """You are an AI publishing agent. Your mission is to BUILD a working Python script that automatically publishes books to Google Play Books.

Here is the situation:
- 1,817 books are ready in our internal pipeline at /Users/darrylsmac/gullahgeecheebiz-site/publish/publisher.db
- 1,129 EPUBs + CSV are in /Users/darrylsmac/gullahgeecheebiz-site/publish/for-distribution/google-play/
- The CSV has been uploaded to the Partner Center
- The EPUBs still need to be uploaded
- Google account: deb2020win3@gmail.com
- Publisher account is set up
- Review is pending

WRITE A COMPLETE PYTHON SCRIPT that:
1. Uses Playwright to open Chrome and navigate to the Google Play Books Partner Center
2. Logs in using the saved session
3. Uploads the EPUB files from the distribution folder
4. Monitors review status
5. Reports results

The script should be saved to /Users/darrylsmac/gullahgeecheebiz-site/ggb-engine/headquarters/google-play-auto-publisher.py

Use these imports: from playwright.sync_api import sync_playwright
Use this session file: /Users/darrylsmac/gullahgeecheebiz-site/ggb-engine/headquarters/logs/google-play-session.json
EPUBs are at: /Users/darrylsmac/gullahgeecheebiz-site/publish/for-distribution/google-play/
CSV is at: /Users/darrylsmac/gullahgeecheebiz-site/publish/for-distribution/google-play/google-play-bulk-import.csv

Write the COMPLETE working script. Include error handling, logging, and progress reporting. The best working script wins."""

# ─── Think Tank Models ─────────────────────────────────────────────────────

THINK_TANK = [
    {"name": "Gemini 2.5 Flash", "model": "google/gemini-2.5-flash", "provider": "Google"},
    {"name": "DeepSeek V4", "model": "deepseek/deepseek-chat", "provider": "DeepSeek"},
    {"name": "Qwen 3.7 Max", "model": "qwen/qwen3.7-max", "provider": "Alibaba"},
    {"name": "Nemotron 3 Ultra", "model": "nvidia/nemotron-3-ultra-550b-a55b:free", "provider": "NVIDIA"},
    {"name": "Ling 3.0 Flash", "model": "inclusionai/ling-3.0-flash:free", "provider": "InclusionAI"},
    {"name": "Kimi K3", "model": "kimi-k3", "provider": "Moonshot", "api_base": "https://api.moonshot.ai/v1"},
]

# ─── Publishing Think Tank ────────────────────────────────────────────────

class PublishingThinkTank:
    def __init__(self):
        self.api_key = self._get_api_key()
        self.results = {}
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
        return {"runs": 0, "winner": None, "strategies": []}
    
    def _save_state(self):
        STATE_FILE.write_text(json.dumps(self.state, indent=2))
    
    def query_model(self, model_info: Dict) -> Dict:
        """Query a single model with the publishing challenge."""
        name = model_info["name"]
        model = model_info["model"]
        api_base = model_info.get("api_base", "https://openrouter.ai/api/v1")
        
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            data = {
                "model": model,
                "messages": [
                    {"role": "system", "content": "You are a publishing automation expert. Provide clear, actionable steps."},
                    {"role": "user", "content": CHALLENGE}
                ],
                "max_tokens": 2000,
                "temperature": 0.3,
            }
            
            start = time.time()
            r = requests.post(
                f"{api_base}/chat/completions",
                headers=headers, json=data, timeout=60
            )
            elapsed = time.time() - start
            
            if r.status_code == 200:
                result = r.json()
                # Handle different response formats
                choices = result.get("choices", [])
                if choices:
                    msg = choices[0].get("message", {})
                    content = msg.get("content")
                    # Some models put content in reasoning field
                    if not content:
                        content = msg.get("reasoning", "")
                else:
                    content = ""
                tokens = result.get("usage", {}).get("total_tokens", 0)
                
                return {
                    "name": name,
                    "model": model,
                    "provider": model_info["provider"],
                    "success": True,
                    "response": content or "",
                    "tokens": tokens,
                    "time_seconds": round(elapsed, 1),
                }
            else:
                return {
                    "name": name,
                    "model": model,
                    "provider": model_info["provider"],
                    "success": False,
                    "error": f"HTTP {r.status_code}: {r.text[:200]}",
                    "time_seconds": round(time.time() - start, 1),
                }
        except Exception as e:
            return {
                "name": name,
                "model": model,
                "provider": model_info["provider"],
                "success": False,
                "error": str(e),
                "time_seconds": 0,
            }
    
    def run_think_tank(self):
        """Run all models in parallel and collect their strategies."""
        print(f"\n{'='*60}")
        print(f"🧠 GGB PUBLISHING THINK TANK")
        print(f"   {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
        print(f"{'='*60}\n")
        
        print(f"📋 Challenge: Get one book published on Google Play Books")
        print(f"🤖 Models: {len(THINK_TANK)} agents competing\n")
        
        threads = []
        for model_info in THINK_TANK:
            t = threading.Thread(target=lambda m=model_info: self.results.update({m["name"]: self.query_model(m)}))
            threads.append(t)
            t.start()
            time.sleep(2)  # Stagger to avoid rate limits
        
        for t in threads:
            t.join(timeout=45)
        
        # Print results
        print(f"\n{'='*60}")
        print(f"📊 THINK TANK RESULTS")
        print(f"{'='*60}\n")
        
        sorted_results = sorted(self.results.values(), key=lambda r: r.get("time_seconds", 999))
        
        for i, r in enumerate(sorted_results):
            status = "✅" if r.get("success") else "❌"
            time_str = f"{r.get('time_seconds', 0):.1f}s"
            tokens = r.get("tokens", 0)
            print(f"  {status} {i+1}. {r['name']:25s} | {r['provider']:10s} | {time_str:8s} | {tokens:5d} tokens")
        
        # Find winner (first successful response)
        winner = None
        for r in sorted_results:
            if r.get("success"):
                winner = r
                break
        
        if winner:
            print(f"\n🏆 WINNER: {winner['name']} ({winner['provider']})")
            print(f"   Time: {winner['time_seconds']}s | Tokens: {winner['tokens']}")
            print(f"\n📝 STRATEGY:")
            print(f"{'='*40}")
            response_text = winner.get('response')
            if response_text:
                print(response_text[:2000])
            else:
                print("(No response content)")
            
            self.state["runs"] += 1
            self.state["winner"] = winner["name"]
            self.state["strategies"].append({
                "winner": winner["name"],
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "preview": (winner.get("response") or "")[:500],
            })
            self._save_state()
            
            # Save full response
            winner_path = LOGS_DIR / f"think-tank-winner-{winner['name'].replace(' ', '-').lower()}.md"
            winner_path.write_text(f"# 🏆 Think Tank Winner: {winner['name']}\n\n"
                                  f"**Provider:** {winner['provider']}\n"
                                  f"**Time:** {winner['time_seconds']}s\n"
                                  f"**Tokens:** {winner['tokens']}\n\n"
                                  f"---\n\n{winner['response']}")
            print(f"\n💾 Full strategy saved: {winner_path}")
        
        return self.results

def main():
    print(f"\n{'='*60}")
    print(f"🧠 GGB PUBLISHING THINK TANK")
    print(f"   {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
    print(f"{'='*60}\n")
    
    tank = PublishingThinkTank()
    tank.run_think_tank()

if __name__ == "__main__":
    main()
