#!/usr/bin/env python3
"""Wait for the Gumroad 10/day creation window to open (probe every 5 min), then create+attach+publish up to 10 missing volumes."""
import json, os, subprocess, sys, time

BASE = '/Users/darrylsmac/gullahgeecheebiz-site/publish'
OUT = '/tmp/gumroad_batch_results.json'
BATCH = [26, 27, 28, 29, 30, 35, 36, 37, 38, 39]  # 10 volumes max per window
MAX_TRIES = 20          # ~100 min of probing; ends ~07:58Z so the 08:00Z cron run takes over cleanly
PROBE_EVERY = 300       # 5 min

def probe():
    r = subprocess.run(['python3', 'create_missing_volumes.py', '26'], cwd=BASE,
                       capture_output=True, text=True, timeout=200)
    out = r.stdout + r.stderr
    return r.returncode, out

def run_batch(vols):
    return subprocess.run(['python3', 'create_missing_volumes.py'] + [str(v) for v in vols],
                          cwd=BASE, capture_output=True, text=True, timeout=900)

tries = 0
while tries < MAX_TRIES:
    tries += 1
    now = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
    rc, out = probe()
    if rc == 0 and 'OK http' in out:  # a volume actually created+published
        print(f'{now} window OPEN (try {tries})', flush=True)
        r2 = run_batch(BATCH[1:])
        final = f'probe_rc={rc}\n{out}\n=== BATCH 27-30,35-39 ===\n{r2.stdout}\n{r2.stderr}'
        open(OUT, 'w').write(final)
        print(final[-3000:], flush=True)
        ok_lines = [l for l in final.splitlines() if 'OK http' in l]
        sys.exit(0 if len(ok_lines) >= 9 else 1)  # expect >=9 of the 10 volumes live
    else:
        print(f'{now} quota still closed (try {tries}/{MAX_TRIES})', flush=True)
        time.sleep(PROBE_EVERY)

open(OUT, 'w').write('TIMED OUT after %d tries' % tries)
print('TIMED OUT', flush=True)
sys.exit(2)
