#!/usr/bin/env python3
"""
Etsy Listing Uploader — Etsy Open API v3
=========================================
Reads listings from a CSV and creates them on Etsy via the REST API.

Features:
  - OAuth 2.0 Bearer authentication (with API key header)
  - Rate-limit aware (10 req/s default, with backoff on 429)
  - Resumable uploads (tracks completed listings in a state file)
  - Detailed logging + final CSV report
  - Flexible CSV column mapping
  - Optional image upload after listing creation

Environment variables (from .env):
  ETSY_API_KEY           — Etsy App API key (x-api-key header)
  ETSY_ACCESS_TOKEN      — OAuth 2.0 access token with listings_w scope
  ETSY_REFRESH_TOKEN     — (optional) OAuth refresh token
  ETSY_SHOP_ID           — (optional) numeric shop ID; auto-detected if omitted

Usage:
  python etsy-uploader.py [--dry-run] [--limit N] [--resume]
"""

import argparse
import csv
import json
import logging
import os
import re
import sys
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
    import requests
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry
except ImportError:
    sys.exit("ERROR: 'requests' package is required. Install with: pip install requests")

try:
    from dotenv import load_dotenv
except ImportError:
    sys.exit("ERROR: 'python-dotenv' package is required. Install with: pip install python-dotenv")


# ===========================================================================
# Configuration
# ===========================================================================

CSV_PATH = Path(
    "/Users/darrylsmac/gullahgeecheebiz-site/ggb-engine/headquarters/logs/"
    "universal-submitter/csv/etsy-listings.csv"
)
ENV_PATH = Path("/Users/darrylsmac/gullahgeecheebiz-site/.env")
SCRIPT_DIR = Path(__file__).parent
LOG_PATH = SCRIPT_DIR / "etsy-uploader.log"
STATE_PATH = SCRIPT_DIR / "etsy-uploader-state.json"
REPORT_PATH = SCRIPT_DIR / "etsy-uploader-report.csv"

ETSY_API_BASE = "https://openapi.etsy.com/v3/application"
DEFAULT_RATE_LIMIT = 10          # requests per second
REQUEST_TIMEOUT = 30             # seconds
MAX_RETRIES = 5                  # per-request retries on transient errors
BACKOFF_BASE = 1.5               # seconds, exponential base

# Etsy required enums
VALID_WHO_MADE = {"i_did", "collective", "someone_else"}
VALID_WHEN_MADE = {
    "made_to_order", "2020_2025", "2010_2019", "2001_2009", "before_2001",
    "1990s", "1980s", "1970s", "1960s", "1950s", "1940s", "1930s",
    "1920s", "1910s", "1900s", "1800s", "1700s", "before_1700",
}
VALID_STATES = {"active", "draft", "inactive"}

# Column mapping: canonical_name -> list of possible CSV column names (case-insensitive)
COLUMN_ALIASES: Dict[str, List[str]] = {
    "sku":                  ["sku", "listing_id", "id", "item_id", "product_id"],
    "title":                ["title", "name", "listing_title"],
    "description":          ["description", "desc", "body", "long_description"],
    "price":                ["price", "unit_price", "amount"],
    "quantity":             ["quantity", "qty", "stock", "inventory"],
    "taxonomy_id":          ["taxonomy_id", "taxonomyid", "category_id", "category"],
    "shipping_profile_id":  ["shipping_profile_id", "shipping_template_id", "shipping_id"],
    "shop_section_id":      ["shop_section_id", "section_id", "section"],
    "tags":                 ["tags", "tag_list"],
    "materials":            ["materials", "material_list"],
    "images":               ["images", "image_urls", "image", "image_url", "photos"],
    "who_made":             ["who_made", "whomade"],
    "when_made":            ["when_made", "whenmade"],
    "is_supply":            ["is_supply", "supply"],
    "state":                ["state", "status", "listing_state"],
    "processing_min":       ["processing_min", "min_processing"],
    "processing_max":       ["processing_max", "max_processing"],
    "weight":               ["weight", "item_weight"],
    "weight_unit":          ["weight_unit"],
    "length":               ["length", "item_length"],
    "width":                ["width", "item_width"],
    "height":               ["height", "item_height"],
    "dimensions_unit":      ["dimensions_unit", "size_unit"],
}


# ===========================================================================
# Logging
# ===========================================================================

def setup_logging() -> logging.Logger:
    logger = logging.getLogger("etsy-uploader")
    logger.setLevel(logging.DEBUG)
    logger.handlers.clear()

    fmt = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    )

    fh = logging.FileHandler(LOG_PATH, mode="a", encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(fmt)
    logger.addHandler(fh)

    sh = logging.StreamHandler(sys.stdout)
    sh.setLevel(logging.INFO)
    sh.setFormatter(fmt)
    logger.addHandler(sh)

    return logger


log = setup_logging()


# ===========================================================================
# Rate Limiter (token bucket)
# ===========================================================================

class RateLimiter:
    """Simple token-bucket rate limiter."""
    def __init__(self, rate: float = DEFAULT_RATE_LIMIT):
        self.rate = rate
        self.interval = 1.0 / rate
        self.last = 0.0

    def wait(self):
        now = time.monotonic()
        elapsed = now - self.last
        if elapsed < self.interval:
            time.sleep(self.interval - elapsed)
        self.last = time.monotonic()


# ===========================================================================
# State Management (for resumability)
# ===========================================================================

@dataclass
class UploadState:
    completed: Dict[str, Dict[str, Any]] = field(default_factory=dict)  # sku -> result
    failed: Dict[str, Dict[str, Any]] = field(default_factory=dict)     # sku -> error info

    @classmethod
    def load(cls, path: Path) -> "UploadState":
        if path.exists():
            try:
                with path.open("r", encoding="utf-8") as f:
                    data = json.load(f)
                return cls(
                    completed=data.get("completed", {}),
                    failed=data.get("failed", {}),
                )
            except Exception as e:
                log.warning("Could not load state file %s: %s", path, e)
        return cls()

    def save(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as f:
            json.dump({"completed": self.completed, "failed": self.failed}, f, indent=2)

    def is_done(self, sku: str) -> bool:
        return sku in self.completed

    def mark_success(self, sku: str, listing_id: int, url: str):
        self.completed[sku] = {
            "listing_id": listing_id,
            "url": url,
            "timestamp": time.time(),
        }
        self.failed.pop(sku, None)

    def mark_failure(self, sku: str, status: int, message: str, retryable: bool):
        self.failed[sku] = {
            "status": status,
            "message": message,
            "retryable": retryable,
            "timestamp": time.time(),
        }


# ===========================================================================
# Etsy API Client
# ===========================================================================

class EtsyClient:
    def __init__(self, api_key: str, access_token: str,
                 refresh_token: Optional[str] = None,
                 rate: float = DEFAULT_RATE_LIMIT):
        self.api_key = api_key
        self.access_token = access_token
        self.refresh_token = refresh_token
        self.rate_limiter = RateLimiter(rate)
        self.shop_id: Optional[int] = None

        self.session = requests.Session()
        retry = Retry(
            total=3,
            backoff_factor=0.5,
            status_forcelist=[500, 502, 503, 504],
            allowed_methods=["GET"],
        )
        adapter = HTTPAdapter(max_retries=retry)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)

    def _headers(self) -> Dict[str, str]:
        return {
            "x-api-key": self.api_key,
            "Authorization": f"Bearer {self.access_token}",
            "Accept": "application/json",
        }

    def _request(self, method: str, path: str, *,
                 data: Optional[Dict] = None,
                 files: Optional[Dict] = None,
                 params: Optional[Dict] = None) -> Tuple[int, Dict[str, Any]]:
        """
        Issue a rate-limited request with exponential backoff on 429 / 5xx.
        Returns (status_code, parsed_json_or_error_dict).
        """
        url = f"{ETSY_API_BASE}{path}" if path.startswith("/") else path

        for attempt in range(1, MAX_RETRIES + 1):
            self.rate_limiter.wait()

            headers = self._headers()
            if files:
                # Let requests set multipart Content-Type with boundary
                headers.pop("Content-Type", None)

            try:
                resp = self.session.request(
                    method, url,
                    headers=headers,
                    data=data,
                    files=files,
                    params=params,
                    timeout=REQUEST_TIMEOUT,
                )
            except requests.RequestException as e:
                log.warning("Network error on %s %s (attempt %d): %s",
                            method, path, attempt, e)
                if attempt == MAX_RETRIES:
                    return 0, {"error": str(e), "_network": True}
                time.sleep(BACKOFF_BASE ** attempt)
                continue

            status = resp.status_code

            # Parse response
            try:
                body = resp.json() if resp.content else {}
            except ValueError:
                body = {"raw": resp.text[:500]}

            # Success
            if 200 <= status < 300:
                return status, body

            # Rate limit → honor Retry-After, then retry
            if status == 429:
                retry_after = float(resp.headers.get("Retry-After", BACKOFF_BASE ** attempt))
                log.warning("Rate limited (429). Sleeping %.1fs (attempt %d/%d)",
                            retry_after, attempt, MAX_RETRIES)
                time.sleep(retry_after)
                continue

            # Server error → retry with backoff
            if status >= 500 and attempt < MAX_RETRIES:
                log.warning("Server error %d on %s. Backing off (attempt %d/%d)",
                            status, path, attempt, MAX_RETRIES)
                time.sleep(BACKOFF_BASE ** attempt)
                continue

            # Client error or exhausted retries → return
            return status, body

        return 0, {"error": "Exhausted retries", "_exhausted": True}

    # ------ High-level endpoints ------

    def get_shop_id(self, shop_identifier: str = "etsy") -> Optional[int]:
        """
        Fetch the authenticated user's shops and return the first shop_id.
        The {shop_id} path parameter accepts either a numeric ID or the shop name.
        We query /shops to discover the real numeric ID.
        """
        log.info("Discovering shop ID...")
        status, body = self._request("GET", "/shops", params={"limit": 25})
        if status != 200:
            log.error("Failed to list shops: %s %s", status, body)
            return None

        results = body.get("results", [])
        if not results:
            log.error("No shops found for the authenticated user.")
            return None

        shop = results[0]
        shop_id = shop.get("shop_id")
        shop_name = shop.get("shop_name")
        log.info("Using shop: %s (ID=%s)", shop_name, shop_id)
        return shop_id

    def create_listing(self, shop_id: int, payload: Dict[str, Any],
                       image_files: Optional[List[Tuple[str, bytes, str]]] = None
                       ) -> Tuple[int, Dict[str, Any]]:
        """
        Create a single listing.
        `image_files` is a list of (filename, bytes, mime_type) tuples to upload
        alongside the listing creation via multipart form.
        """
        path = f"/shops/{shop_id}/listings"

        files = None
        if image_files:
            files = {}
            for idx, (name, blob, mime) in enumerate(image_files):
                # Etsy expects image fields named image_0, image_1, ... OR just "image"
                key = f"image_{idx}" if idx > 0 else "image"
                files[key] = (name, blob, mime)

        return self._request("POST", path, data=payload, files=files)

    def upload_image(self, listing_id: int, image_bytes: bytes,
                     filename: str = "image.jpg",
                     mime: str = "image/jpeg",
                     rank: int = 0,
                     overwrite: bool = False) -> Tuple[int, Dict[str, Any]]:
        path = f"/listings/{listing_id}/images"
        data = {"rank": rank, "overwrite": int(overwrite)}
        files = {"image": (filename, image_bytes, mime)}
        return self._request("POST", path, data=data, files=files)


# ===========================================================================
# CSV + Payload Helpers
# ===========================================================================

def load_env(env_path: Path) -> Dict[str, str]:
    if not env_path.exists():
        sys.exit(f"ERROR: .env not found at {env_path}")
    load_dotenv(env_path)
    return {
        "api_key": os.getenv("ETSY_API_KEY", "").strip(),
        "access_token": os.getenv("ETSY_ACCESS_TOKEN", "").strip(),
        "refresh_token": os.getenv("ETSY_REFRESH_TOKEN", "").strip(),
        "shop_id": os.getenv("ETSY_SHOP_ID", "").strip(),
    }


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", s.lower())


def resolve_columns(header: List[str]) -> Dict[str, str]:
    """Map canonical field names to actual CSV column names."""
    mapping: Dict[str, str] = {}
    normed = {_norm(h): h for h in header}
    for canon, aliases in COLUMN_ALIASES.items():
        for alias in aliases:
            if _norm(alias) in normed:
                mapping[canon] = normed[_norm(alias)]
                break
    return mapping


def _to_float(v: Any) -> Optional[float]:
    if v is None or str(v).strip() == "":
        return None
    try:
        return float(str(v).replace("$", "").replace(",", "").strip())
    except ValueError:
        return None


def _to_int(v: Any) -> Optional[int]:
    if v is None or str(v).strip() == "":
        return None
    try:
        return int(float(str(v).strip()))
    except ValueError:
        return None


def _split_list(v: Any) -> List[str]:
    if v is None:
        return []
    s = str(v).strip()
    if not s:
        return []
    # Accept comma, pipe, semicolon, or newline separated
    parts = re.split(r"[,;|\n]+", s)
    return [p.strip() for p in parts if p.strip()][:13]  # Etsy caps tags at 13


def _to_bool(v: Any) -> Optional[bool]:
    if v is None:
        return None
    s = str(v).strip().lower()
    if s in ("1", "true", "yes", "y", "t"):
        return True
    if s in ("0", "false", "no", "n", "f"):
        return False
    return None


def build_listing_payload(row: Dict[str, str], col_map: Dict[str, str],
                          default_shipping_profile_id: Optional[int] = None,
                          default_taxonomy_id: Optional[int] = None
                          ) -> Tuple[Optional[Dict[str, Any]], List[str]]:
    """
    Build the Etsy createListing payload from a CSV row.
    Returns (payload_or_None, list_of_warnings).
    """
    warnings: List[str] = []

    def get(canon: str) -> Optional[str]:
        col = col_map.get(canon)
        if col is None:
            return None
        v = row.get(col)
        if v is None:
            return None
        v = str(v).strip()
        return v if v else None

    # Required: title, description, price, quantity
    title = get("title")
    description = get("description")
    price = _to_float(get("price"))
    quantity = _to_int(get("quantity"))

    missing = []
    if not title:
        missing.append("title")
    if not description:
        missing.append("description")
    if price is None or price <= 0:
        missing.append("price")
    if quantity is None or quantity < 0:
        missing.append("quantity")

    if missing:
        return None, [f"Missing/invalid required fields: {', '.join(missing)}"]

    # Truncate to Etsy limits
    if len(title) > 140:
        warnings.append(f"Title truncated from {len(title)} to 140 chars")
        title = title[:140]
    if len(description) > 50000:
        description = description[:50000]

    payload: Dict[str, Any] = {
        "title": title,
        "description": description,
        "price": round(price, 2),
        "quantity": quantity,
        "who_made": "i_did",
        "when_made": "2020_2025",
        "is_supply": False,
    }

    # State
    state = get("state")
    if state and state.lower() in VALID_STATES:
        payload["state"] = state.lower()
    else:
        payload["state"] = "active"

    # Taxonomy
    tax = _to_int(get("taxonomy_id")) or default_taxonomy_id
    if tax:
        payload["taxonomy_id"] = tax

    # Shipping profile
    ship = _to_int(get("shipping_profile_id")) or default_shipping_profile_id
    if ship:
        payload["shipping_profile_id"] = ship

    # Shop section
    section = _to_int(get("shop_section_id"))
    if section:
        payload["shop_section_id"] = section

    # Tags & materials (arrays submitted as repeated form fields)
    tags = _split_list(get("tags"))
    if tags:
        payload["tags"] = tags
    materials = _split_list(get("materials"))
    if materials:
        payload["materials"] = materials

    # Processing time
    pmin = _to_int(get("processing_min"))
    pmax = _to_int(get("processing_max"))
    if pmin is not None and pmax is not None and pmin <= pmax:
        payload["processing_min"] = pmin
        payload["processing_max"] = pmax

    # Dimensions / weight
    weight = _to_float(get("weight"))
    if weight is not None:
        payload["item_weight"] = weight
    wunit = get("weight_unit")
    if wunit in ("oz", "lb", "g", "kg"):
        payload["item_weight_unit"] = wunit

    length = _to_float(get("length"))
    width = _to_float(get("width"))
    height = _to_float(get("height"))
    if length and width and height:
        payload["item_length"] = length
        payload["item_width"] = width
        payload["item_height"] = height
    dunit = get("dimensions_unit")
    if dunit in ("in", "ft", "mm", "cm", "m", "yd", "inches"):
        payload["item_dimensions_unit"] = dunit

    return payload, warnings


def fetch_image(url: str, timeout: int = 15) -> Optional[Tuple[bytes, str, str]]:
    """Download image and return (bytes, filename, mime_type)."""
    try:
        r = requests.get(url, timeout=timeout, stream=True,
                         headers={"User-Agent": "EtsyUploader/1.0"})
        if r.status_code != 200:
            return None
        mime = r.headers.get("Content-Type", "image/jpeg").split(";")[0].strip()
        if not mime.startswith("image/"):
            mime = "image/jpeg"
        # Derive filename from URL
        fname = url.rstrip("/").split("/")[-1].split("?")[0] or "image.jpg"
        if "." not in fname[-6:]:
            fname += ".jpg"
        return r.content, fname, mime
    except Exception as e:
        log.debug("Image fetch failed %s: %s", url, e)
        return None


# ===========================================================================
# Main Upload Pipeline
# ===========================================================================

def main():
    parser = argparse.ArgumentParser(description="Upload listings to Etsy via Open API v3")
    parser.add_argument("--dry-run", action="store_true",
                        help="Validate CSV + build payloads but don't call Etsy API")
    parser.add_argument("--limit", type=int, default=0,
                        help="Process only first N listings (0 = all)")
    parser.add_argument("--resume", action="store_true",
                        help="Resume from state file (skip already-uploaded SKUs)")
    parser.add_argument("--reset", action="store_true",
                        help="Ignore existing state file and start fresh")
    parser.add_argument("--csv", type=str, default=str(CSV_PATH),
                        help="Path to CSV file")
    parser.add_argument("--draft", action="store_true",
                        help="Force all listings to state=draft")
    parser.add_argument("--rate", type=float, default=DEFAULT_RATE_LIMIT,
                        help="Requests per second (default 10)")
    parser.add_argument("--default-shipping-profile", type=int, default=None,
                        help="Fallback shipping_profile_id if CSV lacks one")
    parser.add_argument("--default-taxonomy", type=int, default=None,
                        help="Fallback taxonomy_id if CSV lacks one")
    args = parser.parse_args()

    log.info("=" * 70)
    log.info("Etsy Listing Uploader starting")
    log.info("CSV: %s", args.csv)
    log.info("Mode: %s", "DRY RUN" if args.dry_run else "LIVE")
    log.info("=" * 70)

    # 1. Load credentials
    creds = load_env(ENV_PATH)
    if not creds["api_key"]:
        sys.exit("ERROR: ETSY_API_KEY not found in .env")
    if not creds["access_token"] and not args.dry_run:
        sys.exit(
            "ERROR: ETSY_ACCESS_TOKEN not found in .env. "
            "Etsy write endpoints require OAuth 2.0 with 'listings_w' scope. "
            "Generate one via Etsy's OAuth 2.0 PKCE flow."
        )

    # 2. Build client
    client = EtsyClient(
        api_key=creds["api_key"],
        access_token=creds["access_token"] or "dry-run-token",
        refresh_token=creds["refresh_token"],
        rate=args.rate,
    )

    # 3. Discover shop ID (skip in dry run)
    shop_id: Optional[int] = None
    if creds["shop_id"]:
        shop_id = int(creds["shop_id"])
        log.info("Using shop_id from .env: %d", shop_id)
    elif not args.dry_run:
        shop_id = client.get_shop_id()
        if not shop_id:
            sys.exit("ERROR: Could not determine shop_id. Set ETSY_SHOP_ID in .env")
    else:
        shop_id = 0
        log.info("Dry run — skipping shop_id discovery")

    # 4. Load state
    state = UploadState() if args.reset else UploadState.load(STATE_PATH)
    if args.resume:
        log.info("Resuming: %d already completed, %d previously failed",
                 len(state.completed), len(state.failed))

    # 5. Read CSV
    csv_path = Path(args.csv)
    if not csv_path.exists():
        sys.exit(f"ERROR: CSV not found at {csv_path}")

    with csv_path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        header = reader.fieldnames or []

    log.info("CSV loaded: %d rows, %d columns", len(rows), len(header))
    if not rows:
        sys.exit("ERROR: CSV is empty")

    col_map = resolve_columns(header)
    log.info("Column mapping: %s", {k: v for k, v in col_map.items() if v})

    # Ensure