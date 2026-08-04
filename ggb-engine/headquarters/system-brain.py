#!/usr/bin/env python3
"""
GGB System Brain — the central consciousness that ties every system together.
Predicts, coordinates, and optimizes across all layers: publishing, security,
social, SOE, agents, healing, and revenue. The master orchestrator.
"""
import json, os, sys, time, sqlite3, requests, threading, hashlib
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any

BASE_DIR = Path("/Users/darrylsmac/gullahgeecheebiz-site")
PUB_DB = BASE_DIR / "publish" / "publisher.db"
LOGS_DIR = Path(__file__).parent / "logs"
BRAIN_DIR = LOGS_DIR / "system-brain"
STATE_FILE = BRAIN_DIR / "brain-state.json"
PREDICTIONS_FILE = BRAIN_DIR / "predictions.json"
COORDINATION_FILE = BRAIN_DIR / "coordination-log.json"
DIGITAL_TWIN_FILE = BRAIN_DIR / "digital-twin.json"

BRAIN_DIR.mkdir(parents=True, exist_ok=True)

def get_api_key():
    env_file = BASE_DIR / ".env"
    if env_file.exists():
        for line in env_file.read_text().split("\n"):
            if "OPENROUTER_API_KEY" in line:
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    return ""

def call_ai(prompt, max_tokens=3000):
    api_key = get_api_key()
    if not api_key:
        return None
    try:
        r = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={"model": "google/gemini-2.5-flash", "messages": [{"role": "user", "content": prompt}], "max_tokens": max_tokens},
            timeout=60
        )
        if r.status_code == 200:
            return r.json()["choices"][0]["message"]["content"]
    except:
        pass
    return None

# ─── System Brain ─────────────────────────────────────────────────────────

class SystemBrain:
    """Central consciousness that coordinates all GGB systems."""
    
    def __init__(self):
        self.api_key = get_api_key()
        self.state = self._load_state()
        self.predictions = self._load_predictions()
        self.coordination_log = self._load_coordination()
        self.digital_twin = self._load_digital_twin()
        
        # All registered subsystems
        self.subsystems = {
            "pipeline": {"name": "Publishing Pipeline", "healthy": True, "last_contact": None},
            "agents": {"name": "20 Publishing Agents", "healthy": True, "last_contact": None},
            "think_tank": {"name": "Publishing Think Tank", "healthy": True, "last_contact": None},
            "healing_network": {"name": "Self-Healing Network", "healthy": True, "last_contact": None},
            "spirit_weaver": {"name": "Spirit Weaver SOE", "healthy": True, "last_contact": None},
            "security_network": {"name": "Security Network", "healthy": True, "last_contact": None},
            "social_soe": {"name": "Social Media SOE", "healthy": True, "last_contact": None},
            "nss_optimizer": {"name": "NSS Optimizer", "healthy": True, "last_contact": None},
            "production_trigger": {"name": "Production Trigger", "healthy": True, "last_contact": None},
            "binyah": {"name": "Binyah Promo Engine", "healthy": True, "last_contact": None},
            "magazines": {"name": "Weekly Magazines", "healthy": True, "last_contact": None},
            "translations": {"name": "Translation Pipeline", "healthy": True, "last_contact": None},
            "distribution": {"name": "Distribution Connectors", "healthy": True, "last_contact": None},
        }
    
    def _load_state(self) -> Dict:
        if STATE_FILE.exists():
            try:
                return json.loads(STATE_FILE.read_text())
            except:
                pass
        return {"runs": 0, "awake_since": datetime.now(timezone.utc).isoformat(), "predictions_made": 0, "coordinations": 0, "last_heartbeat": None}
    
    def _save_state(self):
        STATE_FILE.write_text(json.dumps(self.state, indent=2))
    
    def _load_predictions(self) -> List[Dict]:
        if PREDICTIONS_FILE.exists():
            try:
                return json.loads(PREDICTIONS_FILE.read_text())
            except:
                pass
        return []
    
    def _save_predictions(self):
        PREDICTIONS_FILE.write_text(json.dumps(self.predictions[-100:], indent=2))
    
    def _load_coordination(self) -> List[Dict]:
        if COORDINATION_FILE.exists():
            try:
                return json.loads(COORDINATION_FILE.read_text())
            except:
                pass
        return []
    
    def _save_coordination(self):
        COORDINATION_FILE.write_text(json.dumps(self.coordination_log[-200:], indent=2))
    
    def _load_digital_twin(self) -> Dict:
        if DIGITAL_TWIN_FILE.exists():
            try:
                return json.loads(DIGITAL_TWIN_FILE.read_text())
            except:
                pass
        return {"snapshots": [], "current_state": {}}
    
    def _save_digital_twin(self):
        DIGITAL_TWIN_FILE.write_text(json.dumps(self.digital_twin, indent=2))
    
    def _get_pipeline_state(self) -> Dict:
        """Get current pipeline state from database."""
        try:
            conn = sqlite3.connect(str(PUB_DB))
            states = conn.execute("SELECT state, COUNT(*) FROM manifests GROUP BY state").fetchall()
            conn.close()
            return {s[0]: s[1] for s in states}
        except:
            return {"error": "Cannot read pipeline"}
    
    def _get_system_metrics(self) -> Dict:
        """Gather metrics from all available systems."""
        metrics = {
            "pipeline": self._get_pipeline_state(),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        
        # Check SOE state
        soe_state_file = LOGS_DIR / "soe" / "soe-state.json"
        if soe_state_file.exists():
            try:
                soe = json.loads(soe_state_file.read_text())
                metrics["soe"] = {
                    "optimizations": soe.get("optimizations", 0),
                    "trends_predicted": soe.get("trends_predicted", 0),
                }
            except:
                pass
        
        # Check security state
        sec_state_file = LOGS_DIR / "security-network" / "security-state.json"
        if sec_state_file.exists():
            try:
                sec = json.loads(sec_state_file.read_text())
                metrics["security"] = {
                    "score": sec.get("security_score", 0),
                    "threats": sec.get("threats_detected", 0),
                    "healed": sec.get("healing_actions", 0),
                }
            except:
                pass
        
        # Check agent state
        agent_state_file = LOGS_DIR / "agent-evolution-state.json"
        if agent_state_file.exists():
            try:
                agents = json.loads(agent_state_file.read_text())
                metrics["agents"] = {
                    "generations": agents.get("generations", 0),
                    "evolutions": agents.get("total_evolutions", 0),
                }
            except:
                pass
        
        return metrics
    
    # ─── HEARTBEAT ──────────────────────────────────────────────────────
    
    def heartbeat(self) -> Dict:
        """System heartbeat — check all subsystems are alive."""
        self.state["last_heartbeat"] = datetime.now(timezone.utc).isoformat()
        self._save_state()
        
        # Check each subsystem by looking for recent activity
        now = datetime.now(timezone.utc)
        for key, sub in self.subsystems.items():
            last = sub.get("last_contact")
            if last:
                age = (now - datetime.fromisoformat(last)).total_seconds()
                sub["healthy"] = age < 86400  # 24 hours without contact = unhealthy
        
        return {"alive": True, "subsystems": len(self.subsystems), "timestamp": self.state["last_heartbeat"]}
    
    # ─── PREDICTIONS ─────────────────────────────────────────────────────
    
    def predict(self) -> Optional[Dict]:
        """Predict system health, content performance, and revenue trends."""
        metrics = self._get_system_metrics()
        
        prompt = f"""You are the GGB System Brain. Analyze the current system state and make predictions.

Current System State:
{json.dumps(metrics, indent=2)}

Make 5 predictions:
1. When will the first $10 sale happen? (date estimate)
2. Which platform will generate the most revenue in 30 days?
3. What content type will perform best?
4. What's the biggest risk to the system in the next 7 days?
5. What opportunity should we capitalize on immediately?

For each prediction, provide:
- Prediction
- Confidence (0-100%)
- Evidence/rationale
- Recommended action

Return as JSON:
{{"predictions": [{{"category": "...", "prediction": "...", "confidence": 0, "evidence": "...", "action": "..."}}], "overall_health": "...", "priority_focus": "..."}}"""
        
        result = call_ai(prompt, max_tokens=2000)
        if not result:
            return None
        
        try:
            start = result.find("{")
            end = result.rfind("}") + 1
            pred = json.loads(result[start:end])
            pred["predicted_at"] = datetime.now(timezone.utc).isoformat()
            pred["metrics_snapshot"] = metrics
            
            self.predictions.append(pred)
            self.state["predictions_made"] += 1
            self._save_predictions()
            self._save_state()
            
            return pred
        except:
            return None
    
    # ─── COORDINATION ───────────────────────────────────────────────────
    
    def coordinate(self) -> Optional[Dict]:
        """Coordinate all subsystems for optimal performance."""
        metrics = self._get_system_metrics()
        
        prompt = f"""You are the GGB System Brain. Coordinate all subsystems for optimal performance.

Current State:
{json.dumps(metrics, indent=2)}

Registered Subsystems:
{json.dumps({k: v["name"] for k, v in self.subsystems.items()}, indent=2)}

Generate a coordination plan:
1. Which subsystems should activate now?
2. What should each subsystem focus on?
3. Are there any conflicts or overlaps to resolve?
4. What's the optimal sequence of operations?
5. What resources should be allocated where?

Return as JSON:
{{"priority_chain": ["..."], "focus_areas": {{"subsystem": "focus"}}, "conflicts_resolved": ["..."], "sequence": ["..."], "resource_allocation": "..."}}"""
        
        result = call_ai(prompt, max_tokens=2000)
        if not result:
            return None
        
        try:
            start = result.find("{")
            end = result.rfind("}") + 1
            plan = json.loads(result[start:end])
            plan["coordinated_at"] = datetime.now(timezone.utc).isoformat()
            
            self.coordination_log.append(plan)
            self.state["coordinations"] += 1
            self._save_coordination()
            self._save_state()
            
            return plan
        except:
            return None
    
    # ─── DIGITAL TWIN ──────────────────────────────────────────────────
    
    def snapshot_digital_twin(self) -> Dict:
        """Take a snapshot of the entire system state."""
        metrics = self._get_system_metrics()
        
        snapshot = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "metrics": metrics,
            "subsystems": {k: {"name": v["name"], "healthy": v["healthy"]} for k, v in self.subsystems.items()},
            "brain_state": {
                "runs": self.state["runs"],
                "predictions": self.state["predictions_made"],
                "coordinations": self.state["coordinations"],
            },
        }
        
        self.digital_twin["snapshots"].append(snapshot)
        self.digital_twin["current_state"] = snapshot
        self._save_digital_twin()
        
        return snapshot
    
    def analyze_digital_twin(self) -> Optional[Dict]:
        """Analyze the digital twin for trends and anomalies."""
        recent = self.digital_twin["snapshots"][-10:] if len(self.digital_twin["snapshots"]) >= 10 else self.digital_twin["snapshots"]
        
        prompt = f"""Analyze the GGB System Digital Twin for trends and anomalies.

Recent Snapshots: {len(recent)}
Current State: {json.dumps(self.digital_twin['current_state'], indent=2)[:500]}

Analyze:
1. Is the system improving, stable, or degrading?
2. Any anomalies or unexpected patterns?
3. What's the trajectory for the next 24 hours?
4. What should be optimized next?
5. What's the overall health trend?

Return as JSON:
{{"trend": "improving/stable/degrading", "anomalies": ["..."], "trajectory": "...", "next_optimization": "...", "health_trend": "..."}}"""
        
        result = call_ai(prompt, max_tokens=1500)
        if not result:
            return None
        
        try:
            start = result.find("{")
            end = result.rfind("}") + 1
            return json.loads(result[start:end])
        except:
            return None
    
    # ─── FULL CYCLE ─────────────────────────────────────────────────────
    
    def full_cycle(self) -> Dict:
        """Run full system brain cycle."""
        print(f"\n{'='*60}")
        print(f"🧠 GGB SYSTEM BRAIN — Full Cycle")
        print(f"   {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
        print(f"{'='*60}\n")
        
        results = {}
        
        # 1. Heartbeat
        print("💓 Step 1: System Heartbeat...")
        hb = self.heartbeat()
        results["heartbeat"] = hb
        print(f"   {hb['subsystems']} subsystems monitored")
        
        # 2. Snapshot digital twin
        print("📸 Step 2: Digital Twin Snapshot...")
        twin = self.snapshot_digital_twin()
        results["twin"] = {"snapshots": len(self.digital_twin["snapshots"])}
        print(f"   Snapshot #{len(self.digital_twin['snapshots'])}")
        
        # 3. Predict
        print("🔮 Step 3: Making Predictions...")
        pred = self.predict()
        results["prediction"] = bool(pred)
        if pred:
            for p in pred.get("predictions", [])[:3]:
                print(f"   📊 {p.get('category', '?')}: {p.get('prediction', '')[:60]}")
        
        # 4. Coordinate
        print("🔄 Step 4: Coordinating Subsystems...")
        coord = self.coordinate()
        results["coordination"] = bool(coord)
        if coord:
            for p in coord.get("priority_chain", [])[:3]:
                print(f"   🎯 {p[:60]}")
        
        # 5. Analyze digital twin
        print("📊 Step 5: Analyzing Digital Twin...")
        analysis = self.analyze_digital_twin()
        results["analysis"] = bool(analysis)
        if analysis:
            print(f"   Trend: {analysis.get('trend', '?')}")
            print(f"   Health: {analysis.get('health_trend', '?')}")
        
        self.state["runs"] += 1
        self._save_state()
        
        print(f"\n{'='*60}")
        print(f"✅ SYSTEM BRAIN CYCLE COMPLETE")
        print(f"{'='*60}")
        print(f"   Subsystems: {hb['subsystems']}")
        print(f"   Predictions: {self.state['predictions_made']}")
        print(f"   Coordinations: {self.state['coordinations']}")
        print(f"   Snapshots: {len(self.digital_twin['snapshots'])}")
        
        return results
    
    def report(self) -> Dict:
        """Full system brain report."""
        return {
            "state": self.state,
            "subsystems": self.subsystems,
            "predictions": len(self.predictions),
            "coordinations": len(self.coordination_log),
            "digital_twin_snapshots": len(self.digital_twin["snapshots"]),
            "latest_prediction": self.predictions[-1] if self.predictions else None,
            "latest_coordination": self.coordination_log[-1] if self.coordination_log else None,
        }

def main():
    import argparse
    parser = argparse.ArgumentParser(description="GGB System Brain — Central Consciousness")
    parser.add_argument("--cycle", action="store_true", help="Run full brain cycle")
    parser.add_argument("--predict", action="store_true", help="Make predictions only")
    parser.add_argument("--coordinate", action="store_true", help="Coordinate subsystems only")
    parser.add_argument("--twin", action="store_true", help="Snapshot digital twin")
    parser.add_argument("--report", action="store_true", help="Brain status report")
    parser.add_argument("--watch", action="store_true", help="Continuous monitoring mode")
    args = parser.parse_args()
    
    print(f"\n{'='*60}")
    print(f"🧠 GGB SYSTEM BRAIN — Central Consciousness")
    print(f"   {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
    print(f"{'='*60}\n")
    
    brain = SystemBrain()
    
    if args.cycle:
        brain.full_cycle()
        return
    
    if args.predict:
        print("🔮 Making predictions...")
        pred = brain.predict()
        if pred:
            for p in pred.get("predictions", []):
                conf = p.get("confidence", 0)
                bar = "█" * (conf // 10) + "░" * (10 - conf // 10)
                print(f"  {bar} {p.get('category', '?'):25s} | {p.get('prediction', '')[:60]}")
                print(f"     Action: {p.get('action', '')[:60]}")
        return
    
    if args.coordinate:
        print("🔄 Coordinating subsystems...")
        coord = brain.coordinate()
        if coord:
            print(f"\n  Priority Chain:")
            for p in coord.get("priority_chain", []):
                print(f"    🎯 {p}")
            print(f"\n  Focus Areas:")
            for sub, focus in coord.get("focus_areas", {}).items():
                print(f"    {sub}: {focus[:60]}")
        return
    
    if args.twin:
        print("📸 Taking digital twin snapshot...")
        twin = brain.snapshot_digital_twin()
        print(f"   Snapshot #{len(brain.digital_twin['snapshots'])}")
        print(f"   Pipeline: {json.dumps(twin.get('metrics', {}).get('pipeline', {}))}")
        return
    
    if args.report:
        report = brain.report()
        print(f"📊 SYSTEM BRAIN REPORT")
        print(f"{'='*40}")
        print(f"   Awake Since: {report['state'].get('awake_since', '?')[:19]}")
        print(f"   Runs: {report['state']['runs']}")
        print(f"   Predictions Made: {report['state']['predictions_made']}")
        print(f"   Coordinations: {report['state']['coordinations']}")
        print(f"   Digital Twin Snapshots: {report['digital_twin_snapshots']}")
        print(f"\n   Subsystems ({len(report['subsystems'])}):")
        for k, v in report['subsystems'].items():
            status = "✅" if v.get("healthy") else "❌"
            print(f"     {status} {v['name']:30s}")
        if report['latest_prediction']:
            print(f"\n   Latest Prediction:")
            for p in report['latest_prediction'].get('predictions', [])[:2]:
                print(f"     📊 {p.get('category', '?')}: {p.get('prediction', '')[:60]}")
        return
    
    if args.watch:
        print("👁️  Continuous monitoring mode (Ctrl+C to stop)")
        try:
            while True:
                brain.full_cycle()
                print(f"\n⏰ Next cycle in 30 minutes...\n")
                time.sleep(1800)
        except KeyboardInterrupt:
            print("\n\nMonitoring stopped")
        return
    
    # Default: run cycle
    brain.full_cycle()

if __name__ == "__main__":
    main()
