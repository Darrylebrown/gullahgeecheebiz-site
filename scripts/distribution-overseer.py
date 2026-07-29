#!/usr/bin/env python3
"""
Gullah Geechee Biz — Distribution Bot Overseer
Runs at 9 AM and 9 PM. Checks all 5 distribution bots.
Reports status, flags failures, and provides oversight.
"""

import json, os, subprocess, sys, time
from pathlib import Path
from datetime import datetime

HOME = Path.home()
SITE_DIR = HOME / "gullahgeecheebiz-site"
STATE_DIR = HOME / ".hermes" / "distribution"
STATE_DIR.mkdir(parents=True, exist_ok=True)

BOTS = {
    "bot-1-kdp": {
        "name": "KDP (Amazon)",
        "script": str(SITE_DIR / "scripts" / "distribute-kdp.py"),
        "description": "Submit ebooks to Amazon KDP",
        "enabled": True
    },
    "bot-2-d2d": {
        "name": "Draft2Digital",
        "script": str(SITE_DIR / "scripts" / "distribute-d2d.py"),
        "description": "Submit ebooks to Draft2Digital network",
        "enabled": True
    },
    "bot-3-etsy": {
        "name": "Etsy",
        "script": str(SITE_DIR / "scripts" / "distribute-etsy.py"),
        "description": "Upload 3 daily listings to Etsy",
        "enabled": True
    },
    "bot-4-site": {
        "name": "Own Site",
        "script": str(SITE_DIR / "scripts" / "distribute-site.py"),
        "description": "Deploy new content to gullahgeecheebiz.com",
        "enabled": True
    },
    "bot-5-ingram": {
        "name": "IngramSpark",
        "script": str(SITE_DIR / "scripts" / "distribute-ingram.py"),
        "description": "Submit to IngramSpark for bookstore distribution",
        "enabled": False
    },
    "bot-6-acx": {
        "name": "ACX (Audiobooks)",
        "script": str(SITE_DIR / "scripts" / "distribute-acx.py"),
        "description": "Submit audiobooks to ACX for Audible/iTunes",
        "enabled": True
    },
    "bot-7-distrokid": {
        "name": "DistroKid",
        "script": str(SITE_DIR / "scripts" / "distribute-distrokid.py"),
        "description": "Submit music/audio to streaming platforms",
        "enabled": True
    },
    "bot-8-spotify": {
        "name": "Spotify",
        "script": str(SITE_DIR / "scripts" / "distribute-spotify.py"),
        "description": "Submit podcasts/audio to Spotify",
        "enabled": True
    }
}

def load_state():
    state_file = STATE_DIR / "overseer-state.json"
    if state_file.exists():
        with open(state_file) as f:
            return json.load(f)
    return {"runs": [], "failures": [], "last_cycle": None}

def save_state(state):
    state_file = STATE_DIR / "overseer-state.json"
    with open(state_file, "w") as f:
        json.dump(state, f, indent=2)

def run_bot(bot_id, bot_info):
    """Run a single distribution bot and return result."""
    script = bot_info["script"]
    if not os.path.exists(script):
        return {"status": "error", "error": f"Script not found: {script}"}
    
    try:
        result = subprocess.run(
            ["python3", script],
            capture_output=True, text=True, timeout=300
        )
        if result.returncode == 0:
            return {"status": "ok", "output": result.stdout[-500:]}
        else:
            return {"status": "failed", "output": result.stderr[-500:], "exit_code": result.returncode}
    except subprocess.TimeoutExpired:
        return {"status": "timeout", "error": "Bot timed out after 5 minutes"}
    except Exception as e:
        return {"status": "error", "error": str(e)}

def main():
    cycle_time = datetime.now().strftime("%Y-%m-%d %H:%M")
    period = "AM" if datetime.now().hour < 12 else "PM"
    
    print(f"\n{'='*50}")
    print(f"🤖 Gullah Geechee Biz — Distribution Bot Overseer")
    print(f"   Cycle: {cycle_time} ({period})")
    print(f"{'='*50}\n")
    
    state = load_state()
    cycle_results = {"time": cycle_time, "period": period, "bots": {}}
    
    for bot_id, bot_info in BOTS.items():
        if not bot_info["enabled"]:
            print(f"  ⏭️  {bot_info['name']}: disabled, skipping")
            cycle_results["bots"][bot_id] = {"status": "skipped"}
            continue
        
        print(f"  🔄 {bot_info['name']}: {bot_info['description']}...", end=" ", flush=True)
        
        result = run_bot(bot_id, bot_info)
        cycle_results["bots"][bot_id] = result
        
        if result["status"] == "ok":
            print("✅")
        elif result["status"] == "failed":
            print(f"❌ (exit {result.get('exit_code', '?')})")
            if result.get("output"):
                print(f"     Last output: {result['output'][:200]}")
        elif result["status"] == "timeout":
            print("⏰ timeout")
        else:
            print(f"⚠️  {result.get('error', 'unknown')}")
    
    # Summary
    print(f"\n{'='*50}")
    ok_count = sum(1 for r in cycle_results["bots"].values() if r["status"] == "ok")
    fail_count = sum(1 for r in cycle_results["bots"].values() if r["status"] in ("failed", "timeout", "error"))
    skip_count = sum(1 for r in cycle_results["bots"].values() if r["status"] == "skipped")
    
    print(f"📊 Results: {ok_count} ok, {fail_count} failed, {skip_count} skipped")
    
    if fail_count > 0:
        print(f"\n⚠️  {fail_count} bot(s) need attention:")
        for bot_id, result in cycle_results["bots"].items():
            if result["status"] in ("failed", "timeout", "error"):
                bot_name = BOTS[bot_id]["name"]
                error_detail = result.get("error") or result.get("output", "")[:100]
                print(f"   ❌ {bot_name}: {error_detail}")
                state["failures"].append({
                    "time": cycle_time,
                    "bot": bot_name,
                    "error": error_detail
                })
    
    state["runs"].append(cycle_results)
    state["last_cycle"] = cycle_time
    # Keep last 30 runs
    state["runs"] = state["runs"][-30:]
    state["failures"] = state["failures"][-50:]
    save_state(state)
    
    print(f"\n✅ Overseer cycle complete")
    return 1 if fail_count > 0 else 0

if __name__ == "__main__":
    sys.exit(main())
