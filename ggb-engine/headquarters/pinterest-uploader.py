#!/usr/bin/env python3
"""
Pinterest API v5 Pin Uploader
------------------------------
Reads pins from a CSV and creates them on Pinterest using the REST v5 API.

Endpoints used:
    GET  https://api.pinterest.com/v5/boards
    POST https://api.pinterest.com/v5/pins

Features:
    - Loads PINTEREST_ACCESS_TOKEN from .env (project root)
    - Resolves board name -> board_id (or uses PINTEREST_BOARD_ID if set)
    - Flexible CSV column mapping (title, description, link, image/media, board)
    - Exponential backoff on 429 / 5xx with Retry-After honoring
    - Resume support: tracks uploaded rows in a JSON progress file
    - Per-run and cumulative reporting (success / failed / skipped / rate-limited)

Author: publishing automation engineer
"""

from __future__ import annotations

import csv
import json
import logging
import os
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = Path("/Users/darrylsmac/gullahgeecheebiz-site")
ENV_PATH = PROJECT_ROOT / ".env"
CSV_PATH = (
    PROJECT_ROOT
    / "ggb-engine/headquarters/logs/universal-submitter/csv/pinterest-feed.csv"
)
PROGRESS_PATH = SCRIPT_DIR / "pinterest-upload-progress.json"
REPORT_PATH = SCRIPT_DIR / f"pinterest-upload-report-{datetime.now():%Y%m%d-%H%M%S}.txt"

API_BASE = "https://api.pinterest.com/v5"

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(message)s",
    datefmt="%H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(
            SCRIPT_DIR / f"pinterest-uploader-{datetime.now():%Y%m%d-%H%M%S}.log",
            encoding="utf-8",
        ),
    ],
)
log = logging.getLogger("pinterest-uploader")

# ---------------------------------------------------------------------------
# .env loader (no dependency on python-dotenv required)
# ---------------------------------------------------------------------------
def load_env(path: Path) -> Dict[str, str]:
    """Minimal .env parser. Returns dict of vars (also exported to os.environ)."""
    env: Dict[str, str] = {}
    if not path.exists():
        return env
    with path.open("r", encoding="utf-8") as fh:
        for raw in fh:
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip()
            # Strip matching quotes
            if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
                value = value[1:-1]
            env[key] = value
            os.environ.setdefault(key, value)
    return env


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------
@dataclass
class PinRow:
    index: int
    title: str
    description: str
    link: str
    media_url: str
    board_name: str = ""
    alt_text: str = ""
    raw: Dict[str, str] = field(default_factory=dict)


@dataclass
class RunStats:
    success: int = 0
    failed: int = 0
    skipped_existing: int = 0
    rate_limited_retried: int = 0
    invalid_rows: int = 0
    errors: List[Dict[str, Any]] = field(default_factory=list)


# ---------------------------------------------------------------------------
# CSV column mapping
# ---------------------------------------------------------------------------
COLUMN_ALIASES = {
    "title": ["title", "pin_title", "name"],
    "description": ["description", "pin_description", "desc", "text"],
    "link": ["link", "url", "destination_link", "destination", "source_url", "pin_url"],
    "media_url": [
        "media_url",
        "image_url",
        "image",
        "media",
        "pin_image",
        "picture",
        "photo",
    ],
    "board_name": ["board", "board_name", "pinterest_board", "target_board"],
    "alt_text": ["alt_text", "alt", "alttext"],
}


def normalize_header(h: str) -> str:
    return h.strip().lower().replace(" ", "_").replace("-", "_")


def map_columns(headers: List[str]) -> Dict[str, Optional[str]]:
    norm = {normalize_header(h): h for h in headers}
    mapping: Dict[str, Optional[str]] = {}
    for canonical, aliases in COLUMN_ALIASES.items():
        found = None
        for alias in aliases:
            if normalize_header(alias) in norm:
                found = norm[normalize_header(alias)]
                break
        mapping[canonical] = found
    return mapping


def parse_csv(path: Path) -> List[PinRow]:
    rows: List[PinRow] = []
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        if not reader.fieldnames:
            raise RuntimeError(f"CSV has no header row: {path}")
        colmap = map_columns(list(reader.fieldnames))
        missing_required = [
            k for k in ("title", "media_url") if colmap.get(k) is None
        ]
        if missing_required:
            raise RuntimeError(
                f"CSV is missing required columns {missing_required}. "
                f"Found headers: {list(reader.fieldnames)}"
            )

        for i, raw in enumerate(reader, start=2):  # row 1 is header
            def get(field: str) -> str:
                col = colmap.get(field)
                return (raw.get(col) or "").strip() if col else ""

            rows.append(
                PinRow(
                    index=i,
                    title=get("title"),
                    description=get("description"),
                    link=get("link"),
                    media_url=get("media_url"),
                    board_name=get("board_name"),
                    alt_text=get("alt_text"),
                    raw=raw,
                )
            )
    return rows


# ---------------------------------------------------------------------------
# Progress file (resume support)
# ---------------------------------------------------------------------------
def load_progress() -> Dict[str, Any]:
    if PROGRESS_PATH.exists():
        try:
            return json.loads(PROGRESS_PATH.read_text(encoding="utf-8"))
        except Exception:
            return {"uploaded_rows": [], "created_pin_ids": {}}
    return {"uploaded_rows": [], "created_pin_ids": {}}


def save_progress(progress: Dict[str, Any]) -> None:
    PROGRESS_PATH.write_text(
        json.dumps(progress, indent=2, ensure_ascii=False), encoding="utf-8"
    )


# ---------------------------------------------------------------------------
# Pinterest API client
# ---------------------------------------------------------------------------
class PinterestClient:
    def __init__(self, token: str):
        if not token:
            raise RuntimeError("Pinterest access token is empty.")
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
                "Accept": "application/json",
                "User-Agent": "GGB-PinterestUploader/1.0",
            }
        )
        # Rate-limit pacing: Pinterest v5 is commonly ~1000 req/hr for writes.
        # We conservatively self-throttle to ~1 request/second baseline.
        self.min_interval = 1.0
        self._last_call = 0.0

    def _pace(self) -> None:
        elapsed = time.time() - self._last_call
        if elapsed < self.min_interval:
            time.sleep(self.min_interval - elapsed)
        self._last_call = time.time()

    def _request(
        self,
        method: str,
        path: str,
        *,
        json_body: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        max_retries: int = 6,
    ) -> Dict[str, Any]:
        url = f"{API_BASE}{path}" if path.startswith("/") else path
        backoff = 5.0
        last_err: Optional[Exception] = None

        for attempt in range(1, max_retries + 1):
            self._pace()
            try:
                resp = self.session.request(
                    method,
                    url,
                    json=json_body,
                    params=params,
                    timeout=60,
                )
            except requests.RequestException as e:
                last_err = e
                log.warning(
                    "Network error on %s %s (attempt %d): %s",
                    method, path, attempt, e,
                )
                time.sleep(backoff)
                backoff = min(backoff * 2, 120)
                continue

            if resp.status_code == 429 or resp.status_code >= 500:
                retry_after = resp.headers.get("Retry-After")
                try:
                    wait = float(retry_after) if retry_after else backoff
                except ValueError:
                    wait = backoff
                log.warning(
                    "Rate limit / server error %d on %s %s (attempt %d). "
                    "Waiting %.1fs.",
                    resp.status_code, method, path, attempt, wait,
                )
                time.sleep(wait)
                backoff = min(backoff * 2, 120)
                continue

            if resp.status_code >= 400:
                # Client error — do not retry.
                try:
                    err_body = resp.json()
                except ValueError:
                    err_body = {"text": resp.text[:500]}
                raise PinterestAPIError(
                    resp.status_code, method, path, err_body
                )

            # Success
            if resp.status_code == 204 or not resp.content:
                return {}
            try:
                return resp.json()
            except ValueError:
                return {"_raw": resp.text}

        raise PinterestAPIError(
            0, method, path, {"error": f"Exhausted retries: {last_err}"}
        )

    # --- High-level helpers ------------------------------------------------
    def list_boards(self) -> List[Dict[str, Any]]:
        boards: List[Dict[str, Any]] = []
        bookmark: Optional[str] = None
        while True:
            params: Dict[str, Any] = {"page_size": 25}
            if bookmark:
                params["bookmark"] = bookmark
            data = self._request("GET", "/boards", params=params)
            items = data.get("items") or []
            boards.extend(items)
            bookmark = data.get("bookmark")
            if not bookmark:
                break
        return boards

    def create_pin(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        return self._request("POST", "/pins", json_body=payload)


class PinterestAPIError(Exception):
    def __init__(self, status: int, method: str, path: str, body: Any):
        self.status = status
        self.method = method
        self.path = path
        self.body = body
        super().__init__(f"{status} {method} {path}: {body}")


# ---------------------------------------------------------------------------
# Board resolution
# ---------------------------------------------------------------------------
def resolve_board(
    client: PinterestClient,
    board_id_override: Optional[str],
    default_board_name: Optional[str],
) -> Dict[str, str]:
    """
    Returns a map: normalized_board_name -> board_id.
    Also ensures a default board is known.
    """
    boards = client.list_boards()
    log.info("Fetched %d boards from Pinterest.", len(boards))
    name_to_id: Dict[str, str] = {}
    id_to_name: Dict[str, str] = {}
    for b in boards:
        bid = b.get("id")
        bname = (b.get("name") or "").strip()
        if bid and bname:
            name_to_id[bname.lower()] = bid
            id_to_name[bid] = bname

    if board_id_override:
        if board_id_override not in id_to_name:
            log.warning(
                "PINTEREST_BOARD_ID=%s was not found among user's boards; "
                "proceeding anyway.", board_id_override,
            )
        else:
            log.info(
                "Using override board: %s (%s)",
                id_to_name[board_id_override], board_id_override,
            )

    if default_board_name and default_board_name.lower() not in name_to_id:
        log.warning(
            "Default board '%s' not found. Will fall back to per-row board "
            "or first available board.", default_board_name,
        )

    return name_to_id


def pick_board_id(
    row: PinRow,
    name_to_id: Dict[str, str],
    default_board_id: Optional[str],
    fallback_board_id: Optional[str],
) -> Optional[str]:
    if row.board_name:
        bid = name_to_id.get(row.board_name.strip().lower())
        if bid:
            return bid
    if default_board_id:
        return default_board_id
    return fallback_board_id


# ---------------------------------------------------------------------------
# Pin payload builder
# ---------------------------------------------------------------------------
def build_pin_payload(row: PinRow, board_id: str) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "board_id": board_id,
        "title": row.title[:100] if row.title else "Pin",
        "description": row.description[:500] if row.description else "",
        "media_source": {
            "source_type": "image_url",
            "url": row.media_url,
        },
    }
    if row.link:
        payload["link"] = row.link
    if row.alt_text:
        payload["alt_text"] = row.alt_text[:500]
    return payload


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------
def validate_row(row: PinRow) -> Optional[str]:
    if not row.media_url:
        return "missing media_url"
    if not (row.media_url.startswith("http://") or row.media_url.startswith("https://")):
        return f"invalid media_url scheme: {row.media_url[:80]}"
    if not row.title:
        return "missing title"
    return None


# ---------------------------------------------------------------------------
# Main orchestration
# ---------------------------------------------------------------------------
def main() -> int:
    log.info("=" * 70)
    log.info("Pinterest API v5 Pin Uploader starting")
    log.info("=" * 70)

    # 1. Load env
    if not ENV_PATH.exists():
        log.error(".env file not found at %s", ENV_PATH)
        return 2
    load_env(ENV_PATH)
    token = os.environ.get("PINTEREST_ACCESS_TOKEN", "").strip()
    if not token:
        log.error("PINTEREST_ACCESS_TOKEN not set in %s", ENV_PATH)
        return 2
    log.info("Loaded access token (%d chars).", len(token))

    board_id_override = os.environ.get("PINTEREST_BOARD_ID", "").strip() or None
    default_board_name = os.environ.get("PINTEREST_DEFAULT_BOARD", "").strip() or None
    dry_run = os.environ.get("PINTEREST_DRY_RUN", "").strip().lower() in ("1", "true", "yes")
    batch_size = int(os.environ.get("PINTEREST_BATCH_PAUSE_EVERY", "50"))
    batch_pause = float(os.environ.get("PINTEREST_BATCH_PAUSE_SECONDS", "30"))

    # 2. Load CSV
    if not CSV_PATH.exists():
        log.error("CSV not found: %s", CSV_PATH)
        return 2
    rows = parse_csv(CSV_PATH)
    log.info("Loaded %d rows from %s", len(rows), CSV_PATH.name)

    # 3. Pinterest client + boards
    client = PinterestClient(token)
    name_to_id: Dict[str, str] = {}
    fallback_board_id: Optional[str] = None
    try:
        name_to_id = resolve_board(client, board_id_override, default_board_name)
        if name_to_id:
            # Choose fallback: override > default name > first board
            if board_id_override:
                fallback_board_id = board_id_override
            elif default_board_name:
                fallback_board_id = name_to_id.get(default_board_name.lower())
            if not fallback_board_id:
                fallback_board_id = next(iter(name_to_id.values()))
            log.info("Fallback board_id = %s", fallback_board_id)
        else:
            log.warning("No boards found on account. Pin creation will fail unless PINTEREST_BOARD_ID is set.")
    except PinterestAPIError as e:
        log.error("Failed to list boards: %s", e)
        return 3

    default_board_id: Optional[str] = board_id_override
    if not default_board_id and default_board_name:
        default_board_id = name_to_id.get(default_board_name.lower())

    # 4. Progress
    progress = load_progress()
    uploaded_set = set(progress.get("uploaded_rows", []))
    created_pin_ids: Dict[str, str] = progress.get("created_pin_ids", {})

    # 5. Upload loop
    stats = RunStats()
    report_lines: List[str] = [
        f"Pinterest Upload Report — {datetime.now():%Y-%m-%d %H:%M:%S}",
        f"CSV: {CSV_PATH}",
        f"Total rows: {len(rows)}",
        f"Already uploaded (resume): {len(uploaded_set)}",
        "",
    ]

    processed_in_batch = 0
    total_target = len(rows)

    for i, row in enumerate(rows, start=1):
        row_key = str(row.index)

        # Resume skip
        if row_key in uploaded_set:
            stats.skipped_existing += 1
            continue

        # Validate
        issue = validate_row(row)
        if issue:
            stats.invalid_rows += 1
            stats.errors.append(
                {"row": row.index, "title": row.title, "error": issue}
            )
            log.warning("Row %d invalid: %s", row.index, issue)
            continue

        # Board resolution
        board_id = pick_board_id(row, name_to_id, default_board_id, fallback_board_id)
        if not board_id:
            stats.failed += 1
            stats.errors.append(
                {"row": row.index, "title": row.title, "error": "no board_id available"}
            )
            log.error("Row %d: no board_id available.", row.index)
            continue

        payload = build_pin_payload(row, board_id)

        if dry_run:
            log.info("[DRY-RUN] Would create pin '%s' on board %s", row.title, board_id)
            stats.success += 1
            uploaded_set.add(row_key)
            continue

        # API call
        try:
            result = client.create_pin(payload)
            pin_id = result.get("id")
            log.info(
                "[%d/%d] OK  row=%d pin_id=%s title=%s",
                i, total_target, row.index, pin_id, row.title[:60],
            )
            stats.success += 1
            uploaded_set.add(row_key)
            if pin_id:
                created_pin_ids[row_key] = pin_id
            processed_in_batch += 1
        except PinterestAPIError as e:
            stats.failed += 1
            stats.errors.append(
                {
                    "row": row.index,
                    "title": row.title,
                    "status": e.status,
                    "error": str(e.body)[:400],
                }
            )
            if e.status == 429:
                stats.rate_limited_retried += 1
            log.error(
                "[%d/%d] FAIL row=%d status=%s body=%s",
                i, total_target, row.index, e.status, str(e.body)[:200],
            )
        except Exception as e:
            stats.failed += 1
            stats.errors.append(
                {"row": row.index, "title": row.title, "error": f"unexpected: {e}"}
            )
            log.exception("Unexpected error on row %d", row.index)

        # Persist progress every N rows
        if i % 10 == 0:
            progress["uploaded_rows"] = sorted(uploaded_set, key=lambda x: int(x))
            progress["created_pin_ids"] = created_pin_ids
            save_progress(progress)

        # Periodic long pause to stay safely under hourly quotas
        if batch_size and processed_in_batch > 0 and processed_in_batch % batch_size == 0:
            log.info(
                "Batch pause: %d pins uploaded so far. Sleeping %.0fs to respect hourly quota.",
                stats.success, batch_pause,
            )
            time.sleep(batch_pause)

    # 6. Final progress save
    progress["uploaded_rows"] = sorted(uploaded_set, key=lambda x: int(x))
    progress["created_pin_ids"] = created_pin_ids
    progress["last_run"] = datetime.now().isoformat()
    save_progress(progress)

    # 7. Report
    report_lines += [
        "SUMMARY",
        "-" * 40,
        f"Success:           {stats.success}",
        f"Failed:            {stats.failed}",
        f"Invalid rows:      {stats.invalid_rows}",
        f"Skipped (resume):  {stats.skipped_existing}",
        f"Rate-limit retries:{stats.rate_limited_retried}",
        "",
    ]
    if stats.errors:
        report_lines.append("ERRORS (first 200)")
        report_lines.append("-" * 40)
        for err in stats.errors[:200]:
            report_lines.append(json.dumps(err, ensure_ascii=False))

    report_text = "\n".join(report_lines)
    REPORT_PATH.write_text(report_text, encoding="utf-8")
    log.info("\n%s", report_text)
    log.info("Report saved to %s", REPORT_PATH)
    log.info("Progress saved to %s", PROGRESS_PATH)

    return 0 if stats.failed == 0 else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        log.warning("Interrupted by user.")
        sys.exit(130)
```

## How to run

1. **Ensure your `.env` contains the token** at `/Users/darrylsmac/gullahgeecheebiz-site/.env`:
   ```
   PINTEREST_ACCESS_TOKEN=pina_XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
   # Optional overrides:
   # PINTEREST_BOARD_ID=1234567890
   # PINTEREST_DEFAULT_BOARD=My Board Name
   # PINTEREST_DRY_RUN=true
   # PINTEREST_BATCH_PAUSE_EVERY=50
   # PINTEREST_BATCH_PAUSE_SECONDS=30
   ```

2. **Install the only external dependency** (ships with most setups, but just in case):
   ```bash
   pip install requests
   ```

3. **Dry run first** (no pins created — validates CSV + auth + boards):
   ```bash
   PINTEREST_DRY_RUN=true python3 /Users/darrylsmac/gullahgeecheebiz-site/ggb-engine/headquarters/pinterest-uploader.py
   ```

4. **Real upload**:
   ```bash
   python3 /Users/darrylsmac/gullahgeecheebiz-site/ggb-engine/headquarters/pinterest-uploader.py
   ```

## Key behaviors to know

- **Resume-safe**: already-uploaded row indices are stored in `pinterest-upload-progress.json` next to the script. Re-running skips them.
- **Rate limits**: honors `Retry-After`, exponential backoff on 429/5xx, plus a 1-second baseline pace and a configurable 30-second pause every 50 pins to stay well under Pinterest's hourly write quota.
- **Flexible CSV columns**: accepts common aliases (`title`/`pin_title`, `image_url`/`media_url`/`image`, `link`/`url`/`destination_link`, `board`/`board_name`, `alt_text`/`alt`). Only `title` and `media_url` are strictly required.
- **Board resolution**: prefers `PINTEREST_BOARD_ID` > per-row `board` column > `PINTEREST_DEFAULT_BOARD` > first board on the account.
- **Outputs**:
  - Live log to stdout + timestamped log file in `headquarters/`
  - `pinterest-upload-report-<timestamp>.txt` with success/fail counts and up to 200 error details
  - `pinterest-upload-progress.json` for safe re-runs

If you get a 401 on the first call, your token is expired or lacks `pins:write` + `boards:read` scopes — regenerate it in the Pinterest developer console with those scopes and re-run.