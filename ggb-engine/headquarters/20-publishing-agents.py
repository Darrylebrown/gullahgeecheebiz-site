#!/usr/bin/env python3
"""
GGB Self-Improving Publishing Agents — 20 autonomous agents that compete,
learn, and improve over time. Each agent specializes in a publishing task,
tracks its success rate, and evolves its strategy based on results.
"""
import json, os, sys, time, sqlite3, requests, random, threading
import omniroute_shim  # OMNIROUTE_MIGRATED
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Optional

BASE_DIR = Path("/Users/darrylsmac/gullahgeecheebiz-site")
PUB_DB = BASE_DIR / "publish" / "publisher.db"
LOGS_DIR = Path(__file__).parent / "logs"
AGENTS_DIR = LOGS_DIR / "agents"
STATE_FILE = LOGS_DIR / "agent-evolution-state.json"

AGENTS_DIR.mkdir(parents=True, exist_ok=True)

# ─── 20 Agent Specializations ─────────────────────────────────────────────

AGENT_SPECS = [
    {"id": 1,  "name": "Google Play Uploader",      "focus": "Upload EPUBs to Google Play Partner Center", "model": "google/gemini-2.5-flash"},
    {"id": 2,  "name": "KDP Publisher",              "focus": "Publish books on Amazon KDP", "model": "deepseek/deepseek-chat"},
    {"id": 3,  "name": "Draft2Digital Connector",    "focus": "Upload books to Draft2Digital", "model": "qwen/qwen3.7-max"},
    {"id": 4,  "name": "Spotify Audio Publisher",    "focus": "Upload audio to Spotify for Creators", "model": "google/gemini-2.5-flash"},
    {"id": 5,  "name": "ACX Audiobook Publisher",    "focus": "Submit audiobooks to ACX/Audible", "model": "deepseek/deepseek-chat"},
    {"id": 6,  "name": "DistroKid Music Distributor","focus": "Upload music to DistroKid", "model": "qwen/qwen3.7-max"},
    {"id": 7,  "name": "Pinterest Pin Creator",      "focus": "Create and schedule Pinterest pins", "model": "google/gemini-2.5-flash"},
    {"id": 8,  "name": "Shopify Product Lister",     "focus": "List products on Shopify", "model": "deepseek/deepseek-chat"},
    {"id": 9,  "name": "Etsy Listing Manager",       "focus": "Create and update Etsy listings", "model": "qwen/qwen3.7-max"},
    {"id": 10, "name": "Content Quality Auditor",    "focus": "Audit book quality before publishing", "model": "google/gemini-2.5-flash"},
    {"id": 11, "name": "SEO Metadata Optimizer",     "focus": "Optimize book metadata for search", "model": "deepseek/deepseek-chat"},
    {"id": 12, "name": "Translation Coordinator",    "focus": "Coordinate multi-language translations", "model": "qwen/qwen3.7-max"},
    {"id": 13, "name": "Audio Generation Lead",     "focus": "Generate audiobooks from manuscripts", "model": "google/gemini-2.5-flash"},
    {"id": 14, "name": "Cover Art Director",         "focus": "Generate and optimize book covers", "model": "deepseek/deepseek-chat"},
    {"id": 15, "name": "Pricing Strategist",         "focus": "Optimize book pricing across markets", "model": "qwen/qwen3.7-max"},
    {"id": 16, "name": "Review Monitor",             "focus": "Monitor store reviews and ratings", "model": "google/gemini-2.5-flash"},
    {"id": 17, "name": "Sales Analyst",              "focus": "Analyze sales data across platforms", "model": "deepseek/deepseek-chat"},
    {"id": 18, "name": "Promotion Coordinator",      "focus": "Coordinate cross-platform promotions", "model": "qwen/qwen3.7-max"},
    {"id": 19, "name": "Pipeline Healer",            "focus": "Detect and fix pipeline bottlenecks", "model": "google/gemini-2.5-flash"},
    {"id": 20, "name": "Strategy Evolver",            "focus": "Evolve all agent strategies based on results", "model": "deepseek/deepseek-chat"},
]

# ─── Self-Improving Agent ─────────────────────────────────────────────────

class SelfImprovingAgent:
    """An agent that learns from its results and improves over time."""
    
    def __init__(self, spec: Dict):
        self.id = spec["id"]
        self.name = spec["name"]
        self.focus = spec["focus"]
        self.model = spec["model"]
        self.api_key = self._get_api_key()
        self.history = self._load_history()
        self.strategy = self._load_strategy()
    
    def _get_api_key(self) -> str:
        env_file = BASE_DIR / ".env"
        if env_file.exists():
            for line in env_file.read_text().split("\n"):
                if "OPENROUTER_API_KEY" in line:
                    return line.split("=", 1)[1].strip().strip('"').strip("'")
        return ""
    
    def _load_history(self) -> List[Dict]:
        path = AGENTS_DIR / f"agent-{self.id:02d}-history.json"
        if path.exists():
            try:
                return json.loads(path.read_text())
            except:
                pass
        return []
    
    def _save_history(self):
        path = AGENTS_DIR / f"agent-{self.id:02d}-history.json"
        path.write_text(json.dumps(self.history[-100:], indent=2))
    
    def _load_strategy(self) -> str:
        path = AGENTS_DIR / f"agent-{self.id:02d}-strategy.md"
        if path.exists():
            return path.read_text()
        return f"Initial strategy for {self.name}: {self.focus}"
    
    def _save_strategy(self, strategy: str):
        path = AGENTS_DIR / f"agent-{self.id:02d}-strategy.md"
        path.write_text(strategy)
        self.strategy = strategy
    
    def _call_ai(self, prompt: str, max_tokens: int = 2000) -> Optional[str]:
        if not self.api_key:
            return None
        try:
            r = requests.post(
                "omniroute",
                headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                json={"model": self.model, "messages": [{"role": "user", "content": prompt}], "max_tokens": max_tokens},
                timeout=30
            )
            if r.status_code == 200:
                return r.json()["choices"][0]["message"]["content"]
        except:
            pass
        return None
    
    def think(self) -> Dict:
        """Generate a strategy or solution for this agent's focus area."""
        prompt = f"""You are {self.name}, a self-improving AI publishing agent.

Your focus: {self.focus}

Your current strategy:
{self.strategy[:500]}

Your past performance ({len(self.history)} attempts):
Success rate: {self._success_rate():.0f}%

Your task: Generate an improved strategy for your focus area. Be specific.
Include exact steps, code snippets, and tools needed.

Your new strategy:"""
        
        result = self._call_ai(prompt, max_tokens=2000)
        
        if result:
            self._save_strategy(result)
            self.history.append({
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "action": "think",
                "result": "strategy_updated",
                "strategy_length": len(result),
            })
            self._save_history()
        
        return {"agent": self.name, "strategy_updated": bool(result), "strategy_length": len(result) if result else 0}
    
    def execute(self) -> Dict:
        """Attempt to execute this agent's task."""
        prompt = f"""You are {self.name}, executing your task.

Your focus: {self.focus}

Your strategy:
{self.strategy[:500]}

Execute your task now. What specific action did you take and what was the result?
Be honest — if you couldn't execute, explain why.

Report format:
- Action taken:
- Result:
- Success (yes/no):
- Lessons learned:"""
        
        result = self._call_ai(prompt, max_tokens=1000)
        
        success = "yes" in (result or "").lower()[:50] if result else False
        
        self.history.append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "action": "execute",
            "result": "success" if success else "failed",
            "details": (result or "")[:200],
        })
        self._save_history()
        
        return {"agent": self.name, "success": success, "details": (result or "")[:200]}
    
    def evolve(self) -> Dict:
        """Evolve strategy based on past results."""
        recent = self.history[-10:] if len(self.history) >= 10 else self.history
        successes = sum(1 for h in recent if h.get("result") == "success")
        failures = sum(1 for h in recent if h.get("result") == "failed")
        
        prompt = f"""You are {self.name}, evolving your strategy.

Your focus: {self.focus}

Recent performance: {successes} successes, {failures} failures out of {len(recent)} attempts

Your current strategy:
{self.strategy[:500]}

Based on your performance, evolve your strategy:
1. What's working? Keep doing it.
2. What's not working? Change it.
3. What new approach should you try?
4. What tools or resources do you need?

Write your evolved strategy:"""
        
        result = self._call_ai(prompt, max_tokens=2000)
        
        if result:
            self._save_strategy(result)
            self.history.append({
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "action": "evolve",
                "result": "strategy_evolved",
                "successes": successes,
                "failures": failures,
            })
            self._save_history()
        
        return {"agent": self.name, "evolved": bool(result)}
    
    def _success_rate(self) -> float:
        if not self.history:
            return 0
        successes = sum(1 for h in self.history if h.get("result") == "success")
        return (successes / len(self.history)) * 100
    
    def report(self) -> Dict:
        return {
            "id": self.id,
            "name": self.name,
            "focus": self.focus,
            "model": self.model,
            "attempts": len(self.history),
            "success_rate": f"{self._success_rate():.0f}%",
            "strategy_length": len(self.strategy),
        }

# ─── Agent Army ────────────────────────────────────────────────────────────

class AgentArmy:
    def __init__(self):
        self.agents = [SelfImprovingAgent(spec) for spec in AGENT_SPECS]
        self.state = self._load_state()
    
    def _load_state(self) -> Dict:
        if STATE_FILE.exists():
            try:
                return json.loads(STATE_FILE.read_text())
            except:
                pass
        return {"generations": 0, "total_evolutions": 0}
    
    def _save_state(self):
        STATE_FILE.write_text(json.dumps(self.state, indent=2))
    
    def deploy_all(self, action: str = "think"):
        """Deploy all 20 agents with a given action."""
        print(f"\n{'='*60}")
        print(f"🤖 DEPLOYING 20 SELF-IMPROVING PUBLISHING AGENTS")
        print(f"   Action: {action}")
        print(f"   {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
        print(f"{'='*60}\n")
        
        results = {}
        threads = []
        
        for agent in self.agents:
            t = threading.Thread(target=lambda a=agent: results.update({a.name: getattr(a, action)()}))
            threads.append(t)
            t.start()
            time.sleep(0.3)
        
        for t in threads:
            t.join(timeout=60)
        
        print(f"\n📊 RESULTS")
        print(f"{'='*40}")
        for name, result in results.items():
            status = "✅" if result.get("success", result.get("strategy_updated", False)) else "❌"
            print(f"  {status} {name:35s} | {str(result)[:60]}")
        
        if action == "evolve":
            self.state["generations"] += 1
            self.state["total_evolutions"] += sum(1 for r in results.values() if r.get("evolved"))
            self._save_state()
        
        print(f"\n📊 ARMY STATUS")
        print(f"{'='*40}")
        print(f"  Generations: {self.state['generations']}")
        print(f"  Total evolutions: {self.state['total_evolutions']}")
        
        return results
    
    def report(self):
        """Report on all 20 agents."""
        print(f"\n{'='*60}")
        print(f"📊 20 AGENT ARMY REPORT")
        print(f"   {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
        print(f"{'='*60}\n")
        
        print(f"{'ID':>3s} | {'Agent':30s} | {'Attempts':>8s} | {'Success':>8s} | {'Model':25s}")
        print("-" * 80)
        
        for agent in self.agents:
            r = agent.report()
            print(f"{r['id']:3d} | {r['name']:30s} | {r['attempts']:8d} | {r['success_rate']:>8s} | {r['model']:25s}")
        
        print(f"\n📁 Strategies saved to: {AGENTS_DIR}")
        print(f"📊 State: {STATE_FILE}")

def main():
    import argparse
    parser = argparse.ArgumentParser(description="GGB 20 Self-Improving Publishing Agents")
    parser.add_argument("--think", action="store_true", help="All agents generate strategies")
    parser.add_argument("--execute", action="store_true", help="All agents attempt execution")
    parser.add_argument("--evolve", action="store_true", help="All agents evolve based on results")
    parser.add_argument("--report", action="store_true", help="Report on all agents")
    parser.add_argument("--cycle", action="store_true", help="Full cycle: think → execute → evolve")
    args = parser.parse_args()
    
    print(f"\n{'='*60}")
    print(f"🤖 GGB 20 SELF-IMPROVING PUBLISHING AGENTS")
    print(f"   {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
    print(f"{'='*60}\n")
    
    army = AgentArmy()
    
    if args.report:
        army.report()
        return
    
    if args.think:
        army.deploy_all("think")
        return
    
    if args.execute:
        army.deploy_all("execute")
        return
    
    if args.evolve:
        army.deploy_all("evolve")
        return
    
    if args.cycle:
        print("🔄 Full cycle: Think → Execute → Evolve\n")
        army.deploy_all("think")
        time.sleep(2)
        army.deploy_all("execute")
        time.sleep(2)
        army.deploy_all("evolve")
        print("\n✅ Full cycle complete")
        return
    
    # Default: report
    army.report()

if __name__ == "__main__":
    main()
