#!/usr/bin/env python3
"""
GGB Security Loop — apply fixes, rescan, repeat until score is good.
Runs: security-hardening.py → security-apply-fixes.py → network scan → repeat
"""
import subprocess, sys, time, json
from pathlib import Path

HQ = Path("/Users/darrylsmac/gullahgeecheebiz-site/ggb-engine/headquarters")
SCAN_SCRIPT = Path("/tmp/network_scan_think_tank.py")
LOGS = HQ / "logs" / "security-loop"
LOGS.mkdir(parents=True, exist_ok=True)

MAX_ITERATIONS = 10
TARGET_SCORE = 90

def run(script, timeout=120):
    print(f"\n  ▶ Running {script.name}...")
    result = subprocess.run(["python3", str(script)], capture_output=True, text=True, timeout=timeout)
    for line in result.stdout.split("\n"):
        if "SCORE" in line or "score" in line.lower() or "✅" in line or "❌" in line or "⚠️" in line:
            print(f"    {line.strip()}")
    if result.returncode != 0:
        print(f"    ⚠️  Exit code: {result.returncode}")
    return result

print(f"\n{'='*55}")
print(f"  🔄 GGB SECURITY LOOP")
print(f"  Target: {TARGET_SCORE}/100")
print(f"  Max iterations: {MAX_ITERATIONS}")
print(f"{'='*55}")

for i in range(1, MAX_ITERATIONS + 1):
    print(f"\n{'─'*55}")
    print(f"  ITERATION {i}/{MAX_ITERATIONS}")
    print(f"{'─'*55}")
    
    # Step 1: Run hardening
    run_script = HQ / "security-hardening.py"
    r1 = run(run_script, 60)
    
    # Step 2: Apply fixes
    apply_script = HQ / "security-apply-fixes.py"
    r2 = run(apply_script, 30)
    
    # Step 3: Run network scan
    r3 = run(SCAN_SCRIPT, 300)
    
    # Check if scan completed
    scan_logs = list(Path("/tmp/logs/think-tank-network-scan").glob("network-scan-winner.md"))
    if scan_logs:
        content = scan_logs[0].read_text()
        # Look for score
        for line in content.split("\n"):
            if "Score" in line or "score" in line:
                print(f"\n  📊 Scan result: {line.strip()}")
    
    print(f"\n  ✅ Iteration {i} complete")
    time.sleep(2)

print(f"\n{'='*55}")
print(f"  ✅ SECURITY LOOP COMPLETE")
print(f"  Ran {MAX_ITERATIONS} iterations")
print(f"  Check latest scan at: /tmp/logs/think-tank-network-scan/")
print(f"{'='*55}")
