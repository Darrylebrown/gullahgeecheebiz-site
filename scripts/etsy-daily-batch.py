#!/usr/bin/env python3
"""
Gullah Geechee Biz — Etsy daily batch (3 listings/day)
Does NOT upload to Etsy. Prepares/prints today's 3 manifests for human/Hermes upload.

Paths (Hermes Mac defaults):
  ~/etsy-products/ready-to-upload/   preferred manifests
  ~/etsy-products/metadata/          fallback JSON metadata
  ~/etsy-products/state.json         progress cursor
"""
from __future__ import annotations
import json, os, sys
from datetime import date
from pathlib import Path

HOME = Path.home()
ROOT = HOME / "etsy-products"
READY = ROOT / "ready-to-upload"
META = ROOT / "metadata"
STATE = ROOT / "state.json"
BATCH = 3
PRICE = 4.99

def load_state():
    if STATE.exists():
        return json.loads(STATE.read_text())
    return {"cursor": 0, "completed_slugs": [], "history": []}

def save_state(st):
    ROOT.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(st, indent=2))

def list_manifests():
    if READY.exists():
        files = sorted(READY.glob("*.json"))
        if files:
            return files
    if META.exists():
        return sorted(META.glob("*.json"))
    return []

def main():
    print("GGB Etsy daily batch — 3/day @ $4.99 — NO auto-upload")
    print(f"Date: {date.today().isoformat()}")
    files = list_manifests()
    if not files:
        print("No manifests found. Expected ~/etsy-products/ready-to-upload/*.json")
        print("Run: python3 scripts/etsy-product-generator.py  then stage ready-to-upload/")
        return 1

    st = load_state()
    done = set(st.get("completed_slugs") or [])
    pending = []
    for f in files:
        try:
            data = json.loads(f.read_text())
        except Exception:
            continue
        slug = data.get("slug") or f.stem
        if slug in done:
            continue
        pending.append((f, slug, data))

    if not pending:
        print("All manifests marked complete. 100 done or reset state.json")
        return 0

    batch = pending[:BATCH]
    print(f"Pending: {len(pending)} | Today batch: {len(batch)}\n")
    today_dir = ROOT / "today" / date.today().isoformat()
    today_dir.mkdir(parents=True, exist_ok=True)

    for i, (f, slug, data) in enumerate(batch, 1):
        data = dict(data)
        data.setdefault("price", PRICE)
        out = today_dir / f"{i:02d}-{slug}.json"
        out.write_text(json.dumps(data, indent=2))
        print(f"--- {i}/{len(batch)} {slug} ---")
        print(f"Title: {data.get('title','')}")
        print(f"Price: ${data.get('price', PRICE)}")
        print(f"PDF:   {data.get('filename') or data.get('pdf') or '(set path)'}")
        print(f"Tags:  {', '.join(data.get('tags') or [])[:120]}")
        print(f"Manifest: {out}")
        print()

    print("UPLOAD STEPS (owner/Hermes browser — manual):")
    print("1) https://gullahgeecheebiz.etsy.com → Shop Manager → Create listing")
    print("2) Digital download · paste title/description/tags · $4.99")
    print("3) Upload REAL manuscript PDF (not thank-you-only)")
    print("4) Publish · then run: python3 scripts/etsy-daily-batch.py --mark-done slug1 slug2 slug3")
    print(f"\nDays left ~ {(len(pending) + BATCH - 1)//BATCH}")
    return 0

def mark_done(slugs):
    st = load_state()
    done = set(st.get("completed_slugs") or [])
    for s in slugs:
        done.add(s)
    st["completed_slugs"] = sorted(done)
    st["history"].append({"date": date.today().isoformat(), "slugs": slugs})
    save_state(st)
    print(f"Marked done: {slugs} | total complete {len(done)}")

if __name__ == "__main__":
    if len(sys.argv) >= 2 and sys.argv[1] == "--mark-done":
        mark_done(sys.argv[2:])
        raise SystemExit(0)
    raise SystemExit(main())
