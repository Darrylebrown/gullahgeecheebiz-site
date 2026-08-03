#!/usr/bin/env python3
"""
GGB Production Trigger System — monitors pipeline capacity and
automatically triggers full-spectrum production when thresholds are met.
25% capacity → triggers books, audio, pins, social, ads, SEO across the board.
"""
import json, os, sys, sqlite3, time, subprocess, threading
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
PUB_DB = REPO_ROOT / "publish" / "publisher.db"
LOGS_DIR = Path(__file__).resolve().parent / "logs"
TRIGGER_LOG = LOGS_DIR / "trigger-log.jsonl"
STATE_FILE = LOGS_DIR / "trigger-state.json"

LOGS_DIR.mkdir(parents=True, exist_ok=True)

# ─── Thresholds ────────────────────────────────────────────────────────────

THRESHOLDS = {
    "capacity_pct": 25,  # Trigger at 25% pipeline capacity
    "min_approved": 10,   # Minimum approved books to trigger
    "cooldown_minutes": 60,  # Don't re-trigger within this window
}

# ─── Production Triggers ───────────────────────────────────────────────────

TRIGGERS = {
    "zero_error": {
        "name": "Zero-Error Pipeline",
        "script": "zero-error-pipeline.py",
        "args": [],
        "description": "Quality check and fix all packages",
        "priority": 0,
    },
    "content_engine": {
        "name": "Content Engine",
        "script": "content-engine.py",
        "args": ["--all"],
        "description": "SEO metadata, book pages, social posts, ads, pins",
        "priority": 1,
    },
    "spanish_translation": {
        "name": "Spanish Translation",
        "script": "content-engine.py",
        "args": ["--translate", "--all"],
        "description": "Translate all books to Spanish (standard)",
        "priority": 2,
    },
    "multi_platform": {
        "name": "Multi-Platform Publisher",
        "script": "multi-platform-publisher.py",
        "args": ["--all"],
        "description": "Generate platform-ready files (EPUB, DOCX, MP3)",
        "priority": 3,
    },
    "audio_prep": {
        "name": "Audio Preparation",
        "script": "content-engine.py",
        "args": ["--batch", "10"],
        "description": "Generate narration scripts and audio files",
        "priority": 4,
    },
    "publishing_ops": {
        "name": "Publishing Operations",
        "script": "publishing-ops.py",
        "args": ["--once"],
        "description": "Upload to platforms via browser automation",
        "priority": 5,
    },
    "alexandria_import": {
        "name": "Alexandria AI Import",
        "script": "alexandria-api-importer.py",
        "args": ["--batch", "10"],
        "description": "Push new books to Alexandria AI for publishing",
        "priority": 6,
    },
    "unified_connector": {
        "name": "Unified Publishing Connector",
        "script": "unified-connector.py",
        "args": ["--batch", "999"],
        "description": "Export to Google Play, D2D, Apple, Kobo, PublishDrive",
        "priority": 7,
    },
    "phase2_distribution": {
        "name": "Phase 2 Distribution",
        "script": "phase2-distribution.py",
        "args": [],
        "description": "Landing pad → pipeline → distribution → submission with self-healing",
        "priority": 8,
    },
    "healing_network": {
        "name": "Self-Healing Network",
        "script": "healing-network.py",
        "args": [],
        "description": "Monitor and heal pipeline, stores, payments, connections, site",
        "priority": 9,
    },
    "sitemap": {
        "name": "Sitemap Update",
        "script": "content-engine.py",
        "args": ["--sitemap"],
        "description": "Regenerate sitemap with all book URLs",
        "priority": 7,
    },
}

class ProductionTrigger:
    """
    Monitors pipeline capacity and triggers full-spectrum production
    when thresholds are met. Self-regulating — won't over-trigger.
    """
    
    def __init__(self):
        self.conn = sqlite3.connect(str(PUB_DB))
        self.state = self._load_state()
        self.trigger_count = 0
    
    def _load_state(self) -> dict:
        """Load persistent trigger state."""
        if STATE_FILE.exists():
            try:
                return json.loads(STATE_FILE.read_text())
            except:
                pass
        return {
            "last_trigger": "",
            "trigger_count": 0,
            "total_books_processed": 0,
            "triggers_fired": [],
        }
    
    def _save_state(self):
        """Save trigger state."""
        self.state["trigger_count"] = self.trigger_count
        STATE_FILE.write_text(json.dumps(self.state, indent=2))
    
    def _log_trigger(self, trigger_name: str, reason: str, results: Dict):
        """Log a trigger event."""
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "trigger": trigger_name,
            "reason": reason,
            "results": results,
        }
        with open(TRIGGER_LOG, "a") as f:
            f.write(json.dumps(entry) + "\n")
    
    def get_capacity(self) -> Dict:
        """Calculate pipeline capacity metrics."""
        total = self.conn.execute("SELECT COUNT(*) FROM manifests").fetchone()[0]
        approved = self.conn.execute(
            "SELECT COUNT(*) FROM manifests WHERE state = 'approved'"
        ).fetchone()[0]
        published = self.conn.execute(
            "SELECT COUNT(*) FROM manifests WHERE state = 'published'"
        ).fetchone()[0]
        blocked = self.conn.execute(
            "SELECT COUNT(*) FROM manifests WHERE state = 'blocked'"
        ).fetchone()[0]
        
        # Capacity = approved / (approved + published) as percentage
        # 0% = nothing approved, 100% = everything approved and waiting to publish
        denominator = approved + published
        if denominator == 0:
            capacity_pct = 0
        else:
            capacity_pct = round((approved / denominator) * 100)
        
        return {
            "total": total,
            "approved": approved,
            "published": published,
            "blocked": blocked,
            "capacity_pct": capacity_pct,
            "ready_to_process": approved - published if approved > published else 0,
        }
    
    def should_trigger(self) -> Tuple[bool, str]:
        """Check if production should be triggered."""
        capacity = self.get_capacity()
        
        # Check minimum approved
        if capacity["approved"] < THRESHOLDS["min_approved"]:
            return False, f"Only {capacity['approved']} approved (need {THRESHOLDS['min_approved']})"
        
        # Check capacity threshold
        if capacity["capacity_pct"] < THRESHOLDS["capacity_pct"]:
            return False, f"Capacity at {capacity['capacity_pct']}% (need {THRESHOLDS['capacity_pct']}%)"
        
        # Check cooldown
        if self.state["last_trigger"]:
            last = datetime.fromisoformat(self.state["last_trigger"])
            elapsed = (datetime.now(timezone.utc) - last).total_seconds() / 60
            if elapsed < THRESHOLDS["cooldown_minutes"]:
                return False, f"Cooldown: {elapsed:.0f}m elapsed (need {THRESHOLDS['cooldown_minutes']}m)"
        
        # Check if there's actually work to do
        ready = capacity["ready_to_process"]
        if ready < 5:
            return False, f"Only {ready} books ready to process"
        
        return True, f"Capacity at {capacity['capacity_pct']}% with {capacity['approved']} approved"
    
    def fire_triggers(self) -> Dict:
        """Fire all production triggers in priority order."""
        capacity = self.get_capacity()
        results = {
            "triggered_at": datetime.now(timezone.utc).isoformat(),
            "capacity": capacity,
            "triggers": [],
        }
        
        print(f"\n{'='*60}")
        print(f"🔥 PRODUCTION TRIGGER FIRED")
        print(f"   Capacity: {capacity['capacity_pct']}%")
        print(f"   Approved: {capacity['approved']}")
        print(f"   Ready:    {capacity['ready_to_process']}")
        print(f"{'='*60}")
        
        # Sort triggers by priority
        sorted_triggers = sorted(TRIGGERS.items(), key=lambda x: x[1]["priority"])
        
        for name, config in sorted_triggers:
            print(f"\n   🔄 {config['name']}: {config['description']}")
            
            script_path = REPO_ROOT / "ggb-engine" / "headquarters" / config["script"]
            if not script_path.exists():
                print(f"      ❌ Script not found: {script_path}")
                results["triggers"].append({
                    "name": name,
                    "success": False,
                    "error": "Script not found",
                })
                continue
            
            try:
                cmd = [sys.executable, str(script_path)] + config["args"]
                start = time.time()
                proc = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=600,  # 10 min per trigger
                    cwd=str(REPO_ROOT / "ggb-engine" / "headquarters"),
                )
                elapsed = time.time() - start
                
                if proc.returncode == 0:
                    print(f"      ✅ Completed in {elapsed:.0f}s")
                    results["triggers"].append({
                        "name": name,
                        "success": True,
                        "duration_s": round(elapsed),
                    })
                else:
                    error = proc.stderr[:200] if proc.stderr else "Unknown error"
                    print(f"      ⚠️  Exit code {proc.returncode}: {error}")
                    results["triggers"].append({
                        "name": name,
                        "success": False,
                        "error": error,
                        "duration_s": round(elapsed),
                    })
            
            except subprocess.TimeoutExpired:
                print(f"      ❌ Timed out after 600s")
                results["triggers"].append({
                    "name": name,
                    "success": False,
                    "error": "Timeout",
                })
            
            except Exception as e:
                print(f"      ❌ Error: {str(e)[:100]}")
                results["triggers"].append({
                    "name": name,
                    "success": False,
                    "error": str(e)[:100],
                })
        
        # Update state
        self.state["last_trigger"] = results["triggered_at"]
        self.state["triggers_fired"].append({
            "timestamp": results["triggered_at"],
            "capacity": capacity["capacity_pct"],
            "approved": capacity["approved"],
            "success_count": sum(1 for t in results["triggers"] if t["success"]),
            "total_triggers": len(results["triggers"]),
        })
        self.trigger_count += 1
        self.state["total_books_processed"] = capacity["published"]
        self._save_state()
        
        # Log
        self._log_trigger("full_production", f"Capacity at {capacity['capacity_pct']}%", results)
        
        print(f"\n{'='*60}")
        print(f"📊 TRIGGER SUMMARY")
        success = sum(1 for t in results["triggers"] if t["success"])
        total = len(results["triggers"])
        print(f"   {success}/{total} triggers completed successfully")
        print(f"{'='*60}")
        
        return results
    
    def check_and_trigger(self) -> Optional[Dict]:
        """Check thresholds and trigger if conditions are met."""
        should, reason = self.should_trigger()
        
        if should:
            print(f"\n✅ Trigger conditions met: {reason}")
            return self.fire_triggers()
        else:
            print(f"⏸️  No trigger: {reason}")
            return None
    
    def monitor(self, interval_seconds: int = 300):
        """Continuously monitor and trigger production."""
        print(f"\n🔄 Production Trigger Monitor started")
        print(f"   Checking every {interval_seconds}s")
        print(f"   Threshold: {THRESHOLDS['capacity_pct']}% capacity")
        print(f"   Cooldown: {THRESHOLDS['cooldown_minutes']}m")
        
        while True:
            try:
                capacity = self.get_capacity()
                print(f"\n{'─'*40}")
                print(f"📊 Pipeline Status: {datetime.now().strftime('%H:%M:%S')}")
                print(f"   Capacity: {capacity['capacity_pct']}%")
                print(f"   Approved: {capacity['approved']}")
                print(f"   Published: {capacity['published']}")
                print(f"   Ready: {capacity['ready_to_process']}")
                
                result = self.check_and_trigger()
                
                if result:
                    print(f"\n💤 Cooldown: {THRESHOLDS['cooldown_minutes']}m")
                    time.sleep(THRESHOLDS['cooldown_minutes'] * 60)
                else:
                    time.sleep(interval_seconds)
            
            except KeyboardInterrupt:
                print("\n\n🛑 Monitor stopped")
                break
            except Exception as e:
                print(f"\n❌ Monitor error: {e}")
                time.sleep(60)
    
    def status(self) -> Dict:
        """Show current trigger status."""
        capacity = self.get_capacity()
        should, reason = self.should_trigger()
        
        return {
            "capacity": capacity,
            "should_trigger": should,
            "reason": reason,
            "last_trigger": self.state.get("last_trigger", "never"),
            "total_triggers": len(self.state.get("triggers_fired", [])),
            "total_books_processed": self.state.get("total_books_processed", 0),
            "thresholds": THRESHOLDS,
        }

# ─── CLI ────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="GGB Production Trigger System")
    parser.add_argument("--check", action="store_true", help="Check if trigger should fire")
    parser.add_argument("--fire", action="store_true", help="Force fire all triggers")
    parser.add_argument("--monitor", action="store_true", help="Start continuous monitoring")
    parser.add_argument("--interval", type=int, default=300, help="Monitor check interval (s)")
    parser.add_argument("--status", action="store_true", help="Show trigger status")
    parser.add_argument("--dry-run", action="store_true", help="Show what would trigger without running")
    
    args = parser.parse_args()
    trigger = ProductionTrigger()
    
    if args.status:
        s = trigger.status()
        print(f"\n📊 PRODUCTION TRIGGER STATUS")
        print(f"{'='*50}")
        print(f"Pipeline capacity: {s['capacity']['capacity_pct']}%")
        print(f"Approved: {s['capacity']['approved']}")
        print(f"Published: {s['capacity']['published']}")
        print(f"Ready to process: {s['capacity']['ready_to_process']}")
        print(f"Should trigger: {'✅ YES' if s['should_trigger'] else '❌ NO'}")
        print(f"Reason: {s['reason']}")
        print(f"Last trigger: {s['last_trigger']}")
        print(f"Total triggers fired: {s['total_triggers']}")
        print(f"Threshold: {s['thresholds']['capacity_pct']}% capacity")
        print(f"Cooldown: {s['thresholds']['cooldown_minutes']}m")
        
        if args.dry_run and s['should_trigger']:
            print(f"\n🔥 WOULD FIRE THESE TRIGGERS:")
            for name, config in sorted(TRIGGERS.items(), key=lambda x: x[1]["priority"]):
                print(f"   {config['name']:25s} → {config['description']}")
    
    elif args.check:
        should, reason = trigger.should_trigger()
        print(f"{'✅ Would trigger' if should else '❌ Would not trigger'}: {reason}")
    
    elif args.fire:
        trigger.fire_triggers()
    
    elif args.monitor:
        trigger.monitor(args.interval)
    
    else:
        parser.print_help()
