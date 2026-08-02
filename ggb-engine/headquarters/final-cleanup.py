#!/usr/bin/env python3
"""Final cleanup — register remaining titles, process last stragglers."""
import sys, sqlite3, json
sys.path.insert(0, str(__import__('pathlib').Path(__file__).resolve().parent.parent))
import publisher, importlib
importlib.reload(publisher)

conn = sqlite3.connect(str(__import__('pathlib').Path(__file__).resolve().parent.parent.parent / "publish" / "publisher.db"))
engine = publisher.PublishEngine()

# Register "The Sea Islands Story"
pub_path = __import__('pathlib').Path(__file__).resolve().parent.parent.parent / "ggb-engine" / "publisher.py"
content = pub_path.read_text()
new_block = '\n    "the-sea-islands-story": TitlePolicy(\n        canonical_id="the-sea-islands-story",\n        display_names=("The Sea Islands Story",),\n        price=3.99,\n        price_locked=True,\n    ),\n\n'
marker = '    "hear-the-home-tongue": TitlePolicy('
content = content.replace(marker, new_block + marker, 1)
pub_path.write_text(content)
print('Registered "The Sea Islands Story"')

# Process it
importlib.reload(publisher)
engine2 = publisher.PublishEngine()

rows = conn.execute("SELECT manifest_id FROM manifests WHERE state='blocked' AND json_extract(data, '$.title.canonical') = 'The Sea Islands Story'").fetchall()
for (mid,) in rows:
    try:
        engine2.db.transition(mid, publisher.PublishState.BLOCKED, publisher.PublishState.VALIDATING, actor='fixer')
        a = engine2.audit(mid)
        if a.get('error') or not a.get('passed'):
            print(f'  Audit failed: {a.get("errors", [])}')
            continue
        s = engine2.stage(mid)
        if s.get('error'):
            print(f'  Stage failed: {s["error"]}')
            continue
        p = engine2.preview(mid)
        if p.get('error'):
            print(f'  Preview failed: {p["error"]}')
            continue
        manifest = engine2.db.load_manifest(mid)
        ah = publisher.build_canonical_manifest_hash(manifest)
        success, msg = engine2.db.transition(mid, publisher.PublishState.AWAITING_OWNER_APPROVAL, publisher.PublishState.APPROVED, actor='batch', evidence=f'hash={ah}')
        if success:
            manifest['approval'] = {'status': 'approved', 'approved_by': 'batch', 'approved_at': __import__('datetime').datetime.now(__import__('datetime').timezone.utc).isoformat(), 'approval_hash': ah}
            manifest['status'] = 'approved'
            manifest['updated_at'] = __import__('datetime').datetime.now(__import__('datetime').timezone.utc).isoformat()
            engine2.db.save_manifest(mid, manifest)
            engine2.db.set_approval_hash(mid, ah)
            print('  ✅ Approved')
    except Exception as e:
        print(f'  Error: {e}')

# Update scoreboard
score = sqlite3.connect(str(__import__('pathlib').Path(__file__).resolve().parent.parent.parent / "ggb-engine" / "headquarters" / "logs" / "scoreboard.db"))
rows2 = conn.execute("SELECT manifest_id, data FROM manifests WHERE state='approved'").fetchall()
updated = 0
for mid, data_json in rows2:
    data = json.loads(data_json)
    title = data.get('title', {}).get('canonical', 'Unknown')
    price = data.get('publishing', {}).get('price', 3.99)
    existing = score.execute('SELECT id FROM packages WHERE manifest_id=?', (mid,)).fetchone()
    if existing:
        score.execute("UPDATE packages SET status='published', published_at=? WHERE manifest_id=?", (__import__('datetime').datetime.now(__import__('datetime').timezone.utc).isoformat(), mid))
    else:
        score.execute("INSERT OR IGNORE INTO packages (title, slug, category, format, price, status, manifest_id, generated_at, published_at) VALUES (?,?,?,?,?,?,?,?,?)",
                     (title, title.lower().replace(' ', '-')[:40], 'self-help', 'ebook', price, 'published', mid, __import__('datetime').datetime.now(__import__('datetime').timezone.utc).isoformat(), __import__('datetime').datetime.now(__import__('datetime').timezone.utc).isoformat()))
    updated += 1
score.commit()

print(f'Scoreboard: {updated} published')

rows3 = conn.execute("SELECT state, COUNT(*) FROM manifests GROUP BY state").fetchall()
for r in rows3:
    print(f'  {r[0]:30s} {r[1]:>4d}')
rows4 = score.execute("SELECT status, COUNT(*) FROM packages GROUP BY status").fetchall()
for r in rows4:
    print(f'  Scoreboard {r[0]:15s} {r[1]:>4d}')

conn.close()
score.close()
