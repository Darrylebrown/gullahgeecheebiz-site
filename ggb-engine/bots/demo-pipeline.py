#!/usr/bin/env python3
"""
GGB Full Pipeline Demo — runs all bots with a shared database.
No platform submission. Dry-run safe.
"""
import json, sys, uuid, subprocess
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from publisher import PublishEngine, StateStore
from PIL import Image
import shutil

DEMO_DIR = Path.home() / ".ggb-test" / f"demo-{uuid.uuid4().hex[:8]}"
DEMO_DIR.mkdir(parents=True, exist_ok=True)

pkg = DEMO_DIR / "encyclopedia-vol-01"
pkg.mkdir()
Image.new("RGB", (1600, 2560), color="navy").save(str(pkg / "cover.jpg"))
(pkg / "manuscript.docx").write_bytes(b"PK" + b"\x00" * 1000)
(pkg / "KDP-DRAFT.md").write_text("""# KDP Draft
- **Title:** Encyclopedia Volume 01
- **Author:** Darryl Elliott Brown
- **Publisher:** Gullah Geechee Biz
- **Language:** English
- **Ebook price:** $9.99
- **DRM:** No
- **KDP Select:** Off
## Description
A comprehensive test of the autonomous publishing pipeline.
""")

db_path = DEMO_DIR / "publisher.db"
store = StateStore(db_path)
engine = PublishEngine(db=store)

d = engine.discover(str(pkg))
mid = d[0]["manifest_id"]
print(f"Package: {mid}")
print(f"Title: Encyclopedia Volume 01")
print(f"Price: $9.99")
print()

print("=== Pipeline Bots ===")
r = engine.reconcile(mid)
print(f"  [RECONCILE] files_registered={r.get('files_registered', 0)}")

r = engine.audit(mid)
print(f"  [VALIDATOR] {'PASSED' if r.get('passed') else 'BLOCKED'}")
if not r.get('passed'):
    for e in r.get('errors', []):
        print(f"    - {e}")

r = engine.repair(mid)
print(f"  [REPAIRER]  {r.get('count', 0)} repairs")

r = engine.stage(mid)
print(f"  [STAGER]    {len(r.get('staged_files', []))} files staged")

r = engine.preview(mid)
print(f"  [PREVIEWER] previewer_opened={r.get('previewer_opened', False)}")

print()
print("=== Agent A: Publisher Prime ===")
PYTHON = sys.executable
BOTS = Path(__file__).resolve().parent
r = subprocess.run([PYTHON, str(BOTS / "agent-a-publisher-prime.py"), "--db", str(db_path), "approve", mid],
                   capture_output=True, text=True, timeout=30, cwd=BOTS.parent)
try:
    data = json.loads(r.stdout)
    print(f"  Approve: {data.get('status', data.get('error', '?'))}")
except:
    print(f"  Output: {r.stdout[:200]}")

print()
print("=== Agent B: Submission Specialist ===")
r = subprocess.run([PYTHON, str(BOTS / "agent-b-submission-specialist.py"), "--db", str(db_path), "upload", mid],
                   capture_output=True, text=True, timeout=30, cwd=BOTS.parent)
try:
    data = json.loads(r.stdout)
    print(f"  Upload: {data.get('status', 'error')}")
    if 'error' not in data:
        print(f"  Files: {data.get('files_uploaded', 0)}")
        print(f"  Draft: {data.get('draft_id', '?')}")
        print(f"  Mock: {data.get('_mock', True)}")
except:
    print(f"  Output: {r.stdout[:200]}")

print()
print("=== Final Status ===")
status = engine.get_status(mid)
print(status.get("report", ""))

shutil.rmtree(DEMO_DIR, ignore_errors=True)
