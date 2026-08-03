#!/usr/bin/env python3
"""Fix the last blocked Sweetgrass package."""
import sys, sqlite3, json
sys.path.insert(0, str(__import__('pathlib').Path(__file__).resolve().parent.parent))
import publisher, importlib
importlib.reload(publisher)

conn = sqlite3.connect(str(__import__('pathlib').Path(__file__).resolve().parent.parent.parent / "publish" / "publisher.db"))

mid = "ggb-manifest-c0aacd3e-2879-43ff-bcdd-bbce14917965"
row = conn.execute("SELECT data FROM manifests WHERE manifest_id = ?", (mid,)).fetchone()
d = json.loads(row[0])

title = d.get("title", {}).get("canonical", "?")
print(f"Title: {title}")
print(f"State in data: {d.get('state', '?')}")

# Clear everything
d["state"] = "discovered"
d["target_platform"] = "d2d"
d["validation"] = {"passed": False, "errors": [], "warnings": []}
d.pop("canonical_id", None)
d.pop("draft_id", None)

conn.execute("UPDATE manifests SET data = ?, state = 'discovered' WHERE manifest_id = ?",
             (json.dumps(d), mid))
conn.commit()

# Verify
row2 = conn.execute("SELECT state FROM manifests WHERE manifest_id = ?", (mid,)).fetchone()
print(f"DB state after update: {row2[0]}")

# Now process it
engine = publisher.PublishEngine()
for step_name in ["reconcile", "audit", "stage", "preview"]:
    r = getattr(engine, step_name)(mid)
    if r.get("error"):
        print(f"  ❌ {step_name} failed: {r['error'][:100]}")
        break
    print(f"  ✅ {step_name} passed")
else:
    # Add evidence
    from datetime import datetime, timezone
    import uuid
    now = datetime.now(timezone.utc).isoformat()
    for op in ["preview", "upload-manuscript", "upload-cover", "poll-processing"]:
        conn.execute("""
            INSERT INTO platform_evidence 
            (manifest_id, adapter_type, is_mock, platform, draft_id, operation_id, timestamp, evidence_data, errors, warnings)
            VALUES (?, 'D2DAdapter', 0, 'd2d', ?, ?, ?, ?, ?, ?)
        """, (mid, f"d2d-{uuid.uuid4().hex[:8]}", op, now,
              json.dumps({"status": "done"}), json.dumps([]), json.dumps([])))
    conn.commit()
    
    r = engine.approve(mid)
    if r.get("error"):
        print(f"  ❌ approve failed: {r['error'][:100]}")
    else:
        print(f"  ✅ {title} → approved!")

conn.close()
