#!/usr/bin/env python3
"""
sync_from_airtable.py — Regenerate /season-1/ from the Airtable 'Season 1 Episodes' table.

Airtable is the source of truth. This script:
  1. Fetches all records from the Airtable table (Published/Ready only render).
  2. Writes /season-1/episodes.json (cache/fallback + JSON feed for the world).
  3. Injects the fresh EPISODES list into scripts/build_season1_site.py and runs it.
     That script is the QA-approved renderer — we do NOT reimplement templates here.

USAGE
  export AIRTABLE_TOKEN=patXXXXXXXX
  python3 scripts/sync_from_airtable.py            # sync live from Airtable
  python3 scripts/sync_from_airtable.py --dry      # print diff, don't write files
  python3 scripts/sync_from_airtable.py --from-cache   # rebuild from episodes.json
  python3 scripts/sync_from_airtable.py --ci       # fail if AIRTABLE_TOKEN missing

ENV
  AIRTABLE_TOKEN   Personal Access Token from airtable.com/create/tokens.
                   Scope: data.records:read on the Encyclopedia base only.
  AIRTABLE_BASE    Optional override. Default: appr9ojv124GBNCtR
  AIRTABLE_TABLE   Optional override. Default: tblykMJANGPLZQyPi

DESIGN
  - Slug is LOCKED once assigned. Renaming an episode in Airtable does NOT rename
    its URL. This keeps /season-1/queen-quet-2000.html stable forever.
  - Only records with Status in {Published, Ready} render on the site.
  - We update ONLY the EPISODES = [...] block in build_season1_site.py, then run it.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, date
from pathlib import Path

BASE_ID  = os.environ.get("AIRTABLE_BASE",  "appr9ojv124GBNCtR")
TABLE_ID = os.environ.get("AIRTABLE_TABLE", "tblykMJANGPLZQyPi")
API_ROOT = "https://api.airtable.com/v0"

REPO_ROOT   = Path(__file__).resolve().parent.parent
SEASON_DIR  = REPO_ROOT / "season-1"
CACHE_PATH  = SEASON_DIR / "episodes.json"
BUILD_PATH  = REPO_ROOT / "scripts" / "build_season1_site.py"


def fetch_from_airtable(token: str) -> list[dict]:
    url = f"{API_ROOT}/{BASE_ID}/{TABLE_ID}"
    records, offset = [], None
    while True:
        params = {"pageSize": 100}
        if offset:
            params["offset"] = offset
        req = urllib.request.Request(
            f"{url}?{urllib.parse.urlencode(params)}",
            headers={"Authorization": f"Bearer {token}"},
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                data = json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            raise SystemExit(f"Airtable {e.code}: {e.read().decode('utf-8', errors='replace')}")
        records.extend(data.get("records", []))
        offset = data.get("offset")
        if not offset:
            break
    return records


def records_to_episodes(records: list[dict]) -> list[dict]:
    out = []
    for r in records:
        f = r.get("fields", {})
        if f.get("Status") not in ("Published", "Ready"):
            continue
        slug = (f.get("Slug") or "").strip()
        if not slug:
            print(f"  ! skipping record {r.get('id')} — no Slug", file=sys.stderr)
            continue
        try:
            premiere = date.fromisoformat(f["Premiere Date"])
        except (KeyError, ValueError):
            print(f"  ! skipping {slug} — invalid Premiere Date", file=sys.stderr)
            continue
        out.append({
            "record_id": r["id"],
            "num":       int(f.get("Episode Number", 0)),
            "date":      premiere,
            "book_id":   slug,
            "title":     (f.get("Title") or "").strip(),
            "anchor":    (f.get("Cultural Anchor") or "").strip(),
            "runtime":   int(f.get("Runtime (min)") or 0),
            "era":       (f.get("Era") or "").strip(),
            "logline":   (f.get("Logline") or "").strip(),
            "hero":      (f.get("Hero Line") or "").strip(),
            "beats":     [
                (f.get("Beat 1") or "").strip(),
                (f.get("Beat 2") or "").strip(),
                (f.get("Beat 3") or "").strip(),
            ],
            "notes":     (f.get("Production Notes") or "").strip(),
        })
    out.sort(key=lambda e: e["num"])
    return out


def save_cache(episodes: list[dict]) -> None:
    payload = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "source": "airtable",
        "base_id": BASE_ID,
        "table_id": TABLE_ID,
        "episodes": [
            {**e, "date": e["date"].isoformat()} for e in episodes
        ],
    }
    CACHE_PATH.write_text(json.dumps(payload, indent=2, ensure_ascii=False))


def load_cache() -> list[dict]:
    if not CACHE_PATH.exists():
        raise SystemExit(f"No cache at {CACHE_PATH}. Run once with AIRTABLE_TOKEN first.")
    data = json.loads(CACHE_PATH.read_text())
    return [
        {**e, "date": date.fromisoformat(e["date"])}
        for e in sorted(data["episodes"], key=lambda e: e["num"])
    ]


def format_episodes_block(episodes: list[dict]) -> str:
    """Format episodes as Python source for build_season1_site.py."""
    lines = ["EPISODES = ["]
    for e in episodes:
        d = e["date"]
        beats_lines = ",\n            ".join(repr(b) for b in e["beats"])
        lines.append("    dict(")
        lines.append(f"        num={e['num']},")
        lines.append(f"        date=date({d.year}, {d.month}, {d.day}),")
        lines.append(f"        book_id={e['book_id']!r},")
        lines.append(f"        title={e['title']!r},")
        lines.append(f"        anchor={e['anchor']!r},")
        lines.append(f"        runtime={e['runtime']!r},")
        lines.append(f"        era={e['era']!r},")
        lines.append(f"        logline={e['logline']!r},")
        lines.append(f"        hero={e['hero']!r},")
        lines.append("        beats=[")
        lines.append(f"            {beats_lines},")
        lines.append("        ],")
        lines.append("    ),")
    lines.append("]")
    return "\n".join(lines)


def inject_episodes(episodes_src: str, dry: bool) -> bool:
    """Replace the EPISODES = [...] block in build_season1_site.py. Returns True if changed."""
    src = BUILD_PATH.read_text()
    pattern = re.compile(r"EPISODES\s*=\s*\[.*?\n\]", re.DOTALL)
    if not pattern.search(src):
        raise SystemExit(f"Could not find EPISODES block in {BUILD_PATH}")
    new_src = pattern.sub(episodes_src, src, count=1)
    if new_src == src:
        return False
    if dry:
        print(f"    would rewrite EPISODES block in {BUILD_PATH.name} ({len(episodes_src)} bytes)")
    else:
        BUILD_PATH.write_text(new_src)
        print(f"    rewrote EPISODES block in {BUILD_PATH.name}")
    return True


def run_build(dry: bool) -> None:
    if dry:
        print("    would run scripts/build_season1_site.py")
        return
    print("    running scripts/build_season1_site.py...")
    result = subprocess.run(
        [sys.executable, str(BUILD_PATH)],
        cwd=REPO_ROOT,
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        print(result.stdout)
        print(result.stderr, file=sys.stderr)
        raise SystemExit(f"Build failed with exit {result.returncode}")
    print(result.stdout.strip().split("\n")[-1] if result.stdout else "    build OK")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--from-cache", action="store_true")
    ap.add_argument("--ci",         action="store_true")
    ap.add_argument("--dry",        action="store_true")
    ap.add_argument("--force",      action="store_true",
                    help="Rebuild HTML even if Airtable data hasn't changed")
    args = ap.parse_args()

    print(f"season-1 sync — {datetime.now().isoformat(timespec='seconds')}")

    if args.from_cache:
        episodes = load_cache()
        source = "cache"
    else:
        token = os.environ.get("AIRTABLE_TOKEN")
        if not token:
            if args.ci:
                raise SystemExit("AIRTABLE_TOKEN not set (required in --ci mode)")
            print("  AIRTABLE_TOKEN not set — falling back to cache")
            episodes = load_cache()
            source = "cache-fallback"
        else:
            print(f"  Fetching from Airtable ({BASE_ID}/{TABLE_ID})...")
            records = fetch_from_airtable(token)
            print(f"  Got {len(records)} records")
            episodes = records_to_episodes(records)
            source = "airtable"

    print(f"  {len(episodes)} episodes (source: {source})")

    # Validate slug uniqueness — critical for URL stability
    slugs = [e["book_id"] for e in episodes]
    if len(set(slugs)) != len(slugs):
        dupes = [s for s in slugs if slugs.count(s) > 1]
        raise SystemExit(f"Duplicate slugs found — refusing to write: {set(dupes)}")

    # Inject into the QA-approved renderer + run it
    changed = inject_episodes(format_episodes_block(episodes), args.dry)

    if source == "airtable" and not args.dry:
        save_cache(episodes)
        print(f"    wrote {CACHE_PATH.relative_to(REPO_ROOT)}")
        changed = True

    if not changed and not args.force:
        print("  no changes")
        return

    run_build(args.dry)


if __name__ == "__main__":
    main()
