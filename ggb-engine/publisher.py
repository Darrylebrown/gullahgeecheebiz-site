#!/usr/bin/env python3
"""
Gullah Geechee Biz — Publisher Control Plane (P0 Corrected)
Safe, evidence-backed, owner-controlled publishing coordination.

P0 corrections:
  - Hear the Home Tongue registered and enforced
  - Unknown/mistyped titles fail closed (block, never auto-approve)
  - save_manifest cannot change state (state machine is ONLY mutation interface)
  - Concurrent discovery produces exactly one manifest (SQLite UNIQUE)
  - Approval binds ALL consequential fields
  - STAGED → PLATFORM_UPLOADED → PLATFORM_PROCESSED → PREVIEW_CLEAN (correct path)
  - Staging roots are narrow and configurable
  - CLI subprocess tests with exit-code assertions
"""

import json, os, sys, time, hashlib, uuid, shutil, sqlite3, re, logging, copy, threading, subprocess
from pathlib import Path
from datetime import datetime, timezone
from enum import Enum
from typing import Optional, Dict, List, Any, Tuple, Set
from dataclasses import dataclass, field, asdict

# ─── Repository-relative paths ──────────────────────────────────────────────

def _repo_root() -> Path:
    mod = Path(__file__).resolve().parent
    if (mod / ".." / ".." / "package.json").resolve().exists():
        return (mod / ".." / "..").resolve()
    if (mod / ".." / "package.json").resolve().exists():
        return (mod / "..").resolve()
    cwd = Path.cwd().resolve()
    if (cwd / "package.json").exists():
        return cwd
    for p in [cwd] + list(cwd.parents):
        if (p / "package.json").exists():
            return p
    return cwd

REPO_ROOT = _repo_root()
ENGINE_DIR = REPO_ROOT / "ggb-engine"
PUBLISH_DIR = REPO_ROOT / "publish"
REGISTRY_DIR = PUBLISH_DIR / "registry"
MANIFESTS_DIR = PUBLISH_DIR / "manifests"
LOGS_DIR = PUBLISH_DIR / "logs"
STATE_DIR = PUBLISH_DIR / "state"
STAGING_DIR = PUBLISH_DIR / "staging"
REPAIRS_DIR = PUBLISH_DIR / "repairs"
SCHEMAS_DIR = ENGINE_DIR / "schemas"
DB_PATH = PUBLISH_DIR / "publisher.db"

MANIFEST_SCHEMA_VERSION = "1.0.0"
MANIFEST_ID_PATTERN = re.compile(r"^ggb-manifest-[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$")
MAX_REPAIR_ATTEMPTS = 3
QUEUE_LOCK_TIMEOUT_SECONDS = 3600

# ─── Approved Package Roots ──────────────────────────────────────────────────
# Only packages under these roots may be discovered or staged.
APPROVED_PACKAGE_ROOTS = [
    Path.home() / "gullah-geechee-project" / "packaged",
    Path.home() / "gullah-geechee-project" / "how-to-test" / "packages",
    Path.home() / "gullah-geechee-project" / "pilot",
    Path.home() / ".ggb-test",  # Test packages
    REPO_ROOT / "ggb-engine" / "headquarters" / "training",  # Agent training
    REPO_ROOT / "publish" / "landing-pad",  # Landing pad for auto-discovery
]

# ─── Canonical Title Registry ────────────────────────────────────────────────

@dataclass(frozen=True)
class TitlePolicy:
    canonical_id: str
    display_names: Tuple[str, ...]
    price: Optional[float] = None
    price_locked: bool = False
    protected: bool = False

TITLE_REGISTRY = {
    "sweetgrass": TitlePolicy(
        canonical_id="sweetgrass",
        display_names=("Sweetgrass", "Sweetgrass Basket", "Sweetgrass Basketry",
                       "Sweetgrass in the Hands"),
        price=3.99,
        price_locked=True,
    ),
    "encyclopedia-volume-01": TitlePolicy(
        canonical_id="encyclopedia-volume-01",
        display_names=(
            "Encyclopedia Volume 1", "Encyclopedia Volume 01",
            "Encyclopedia Vol 1", "Encyclopedia Vol. 1",
            "Historiography of Gullah Geechee Studies",
            "The Gullah Geechee Encyclopedia: Volume 1",
        ),
        price=9.99,
        price_locked=True,
    ),
    "blood-remembers": TitlePolicy(
        canonical_id="blood-remembers",
        display_names=("Blood Remembers",),
        price=None,
        price_locked=True,
        protected=True,
    ),
    "hear-the-home-tongue": TitlePolicy(
        canonical_id="hear-the-home-tongue",
        display_names=("Hear the Home Tongue",),
        price=None,
        price_locked=True,
        protected=True,
    ),
}

# ─── Protected Drafts ────────────────────────────────────────────────────────

@dataclass(frozen=True)
class ProtectedDraft:
    canonical_id: str
    platform: str
    draft_id: str
    status: str
    rule: str

PROTECTED_DRAFTS = {
    "sweetgrass": ProtectedDraft(
        canonical_id="sweetgrass",
        platform="kdp",
        draft_id="AYK5W5QVJCJOE",
        status="active",
        rule="never_duplicate",
    ),
    "hear-the-home-tongue": ProtectedDraft(
        canonical_id="hear-the-home-tongue",
        platform="kdp",
        draft_id="A11PYUZCEIJZPV",
        status="in_review",
        rule="never_modify",
    ),
}

def resolve_canonical_id(title: str) -> Optional[str]:
    """Resolve a display title to its canonical ID. Uses word-boundary matching.
    Returns None if unknown or ambiguous. Fuzzy matches are NOT accepted."""
    t = title.lower().strip()
    matches = []
    for cid, policy in TITLE_REGISTRY.items():
        for name in policy.display_names:
            pattern = r'\b' + re.escape(name.lower()) + r'\b'
            if re.search(pattern, t):
                matches.append(cid)
                break
    if len(matches) == 1:
        return matches[0]
    return None  # Unknown or ambiguous — block

def enforce_price(canonical_id: Optional[str], requested_price: float) -> Tuple[bool, str]:
    """Enforce price policy. Unknown/None canonical_id blocks."""
    if canonical_id is None:
        return False, "Unknown title — cannot auto-approve price. Owner approval required."
    policy = TITLE_REGISTRY.get(canonical_id)
    if not policy:
        return False, f"Unregistered title '{canonical_id}' — owner approval required."
    if policy.protected:
        return False, f"Protected title '{canonical_id}' — price cannot be modified"
    if policy.price_locked and policy.price is not None:
        if abs(requested_price - policy.price) > 0.01:
            return False, f"Price must be ${policy.price:.2f} for '{canonical_id}' (got ${requested_price:.2f})"
    return True, "Price approved"

def check_protected_draft(canonical_id: str, platform: str, draft_id: str = None) -> Tuple[bool, str]:
    """Check if a draft is protected. Returns (allowed, message).
    For 'never_duplicate' rules: only the exact protected draft ID is permitted.
    None and any other draft ID are rejected."""
    for pd in PROTECTED_DRAFTS.values():
        if pd.canonical_id == canonical_id and pd.platform == platform:
            if pd.rule == "never_duplicate":
                if draft_id != pd.draft_id:
                    return False, f"Protected draft '{canonical_id}' already exists as {pd.draft_id} — only that draft ID is permitted (got '{draft_id}')"
            if pd.rule == "never_modify":
                return False, f"Protected draft '{canonical_id}' is {pd.status} — never modify"
    return True, "Draft allowed"


# ─── State Machine ───────────────────────────────────────────────────────────

class PublishState(str, Enum):
    DISCOVERED = "discovered"
    PACKAGED = "packaged"
    VALIDATING = "validating"
    BLOCKED = "blocked"
    VALIDATED = "validated"
    STAGED = "staged"
    PLATFORM_UPLOADED = "platform_uploaded"
    PLATFORM_PROCESSED = "platform_processed"
    PREVIEW_CLEAN = "preview_clean"
    AWAITING_OWNER_APPROVAL = "awaiting_owner_approval"
    APPROVED = "approved"
    SUBMITTED = "submitted"
    IN_REVIEW = "in_review"
    LIVE = "live"
    REJECTED = "rejected"
    NEEDS_REVISION = "needs_revision"
    WITHDRAWN = "withdrawn"
    ARCHIVED = "archived"

STATE_TRANSITIONS: Dict[PublishState, List[PublishState]] = {
    PublishState.DISCOVERED: [PublishState.PACKAGED, PublishState.ARCHIVED],
    PublishState.PACKAGED: [PublishState.VALIDATING, PublishState.REJECTED],
    PublishState.VALIDATING: [PublishState.VALIDATED, PublishState.BLOCKED],
    PublishState.BLOCKED: [PublishState.VALIDATING, PublishState.NEEDS_REVISION, PublishState.ARCHIVED],
    PublishState.VALIDATED: [PublishState.STAGED, PublishState.ARCHIVED],
    PublishState.STAGED: [PublishState.PLATFORM_UPLOADED, PublishState.BLOCKED],
    PublishState.PLATFORM_UPLOADED: [PublishState.PLATFORM_PROCESSED, PublishState.BLOCKED],
    PublishState.PLATFORM_PROCESSED: [PublishState.PREVIEW_CLEAN, PublishState.BLOCKED],
    PublishState.PREVIEW_CLEAN: [PublishState.AWAITING_OWNER_APPROVAL, PublishState.NEEDS_REVISION],
    PublishState.AWAITING_OWNER_APPROVAL: [PublishState.APPROVED, PublishState.REJECTED, PublishState.NEEDS_REVISION],
    PublishState.APPROVED: [PublishState.SUBMITTED, PublishState.WITHDRAWN],
    PublishState.SUBMITTED: [PublishState.IN_REVIEW, PublishState.BLOCKED],
    PublishState.IN_REVIEW: [PublishState.LIVE, PublishState.NEEDS_REVISION, PublishState.BLOCKED],
    PublishState.LIVE: [PublishState.ARCHIVED, PublishState.NEEDS_REVISION],
    PublishState.REJECTED: [PublishState.NEEDS_REVISION, PublishState.ARCHIVED],
    PublishState.NEEDS_REVISION: [PublishState.PACKAGED, PublishState.ARCHIVED],
    PublishState.WITHDRAWN: [PublishState.ARCHIVED],
    PublishState.ARCHIVED: [],
}

ILLEGAL_APPROVAL_STATES = {
    PublishState.DISCOVERED, PublishState.PACKAGED, PublishState.VALIDATING,
    PublishState.BLOCKED, PublishState.ARCHIVED, PublishState.SUBMITTED,
    PublishState.IN_REVIEW, PublishState.REJECTED, PublishState.LIVE,
    PublishState.WITHDRAWN, PublishState.NEEDS_REVISION,
}

PLATFORM_EVIDENCE_REQUIRED = {
    PublishState.PLATFORM_UPLOADED, PublishState.PLATFORM_PROCESSED,
    PublishState.PREVIEW_CLEAN, PublishState.AWAITING_OWNER_APPROVAL,
}

# ─── DRM / Select Enums ──────────────────────────────────────────────────────

class DRM(str, Enum):
    NO = "no"
    YES = "yes"

class KDPSelect(str, Enum):
    OFF = "off"
    ON = "on"

DRM_PARSE = {
    "no": DRM.NO, "No": DRM.NO, "NO": DRM.NO, "false": DRM.NO, "False": DRM.NO,
    "yes": DRM.YES, "Yes": DRM.YES, "YES": DRM.YES, "true": DRM.YES, "True": DRM.YES,
}

SELECT_PARSE = {
    "off": KDPSelect.OFF, "Off": KDPSelect.OFF, "OFF": KDPSelect.OFF,
    "no": KDPSelect.OFF, "No": KDPSelect.OFF, "NO": KDPSelect.OFF, "false": KDPSelect.OFF,
    "on": KDPSelect.ON, "On": KDPSelect.ON, "ON": KDPSelect.ON,
    "yes": KDPSelect.ON, "Yes": KDPSelect.ON, "YES": KDPSelect.ON, "true": KDPSelect.ON,
    "enroll": KDPSelect.ON, "Enroll": KDPSelect.ON, "enrolled": KDPSelect.ON,
    "not enrolled": KDPSelect.OFF, "not enroll": KDPSelect.OFF,
}


# ─── Logging ─────────────────────────────────────────────────────────────────

def setup_logger(workflow_id: str = None, log_file: Path = None):
    logger = logging.getLogger(f"ggb-publish-{workflow_id or 'default'}")
    logger.setLevel(logging.INFO)
    if logger.handlers:
        logger.handlers.clear()
    handler = logging.StreamHandler(sys.stderr)
    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S"
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    if log_file:
        fh = logging.FileHandler(log_file)
        fh.setFormatter(formatter)
        logger.addHandler(fh)
    return logger


# ─── Database / State Store ──────────────────────────────────────────────────

class StateStore:
    """SQLite-backed state store.
    State machine is the ONLY state mutation interface.
    save_manifest() cannot change state — it only persists manifest data."""

    SCHEMA_VERSION = 2

    MIGRATIONS = {
        1: """
            CREATE TABLE IF NOT EXISTS schema_version (
                version INTEGER PRIMARY KEY,
                applied_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS manifests (
                manifest_id TEXT PRIMARY KEY,
                data TEXT NOT NULL,
                state TEXT NOT NULL DEFAULT 'discovered',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                approval_hash TEXT,
                queue_position INTEGER,
                queue_locked_until TEXT
            );
            CREATE TABLE IF NOT EXISTS artifacts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sha256 TEXT NOT NULL,
                path TEXT NOT NULL,
                size INTEGER NOT NULL,
                mime_type TEXT NOT NULL,
                provenance TEXT,
                created_at TEXT NOT NULL,
                UNIQUE(sha256)
            );
            CREATE TABLE IF NOT EXISTS audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                manifest_id TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                actor TEXT NOT NULL,
                action TEXT NOT NULL,
                from_state TEXT,
                to_state TEXT,
                evidence TEXT,
                idempotency_key TEXT,
                FOREIGN KEY (manifest_id) REFERENCES manifests(manifest_id)
            );
            CREATE TABLE IF NOT EXISTS queue (
                manifest_id TEXT PRIMARY KEY,
                canonical_id TEXT NOT NULL,
                priority INTEGER NOT NULL DEFAULT 0,
                depends_on TEXT,
                created_at TEXT NOT NULL,
                locked_by TEXT,
                locked_until TEXT,
                FOREIGN KEY (manifest_id) REFERENCES manifests(manifest_id)
            );
            CREATE TABLE IF NOT EXISTS platform_evidence (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                manifest_id TEXT NOT NULL,
                adapter_type TEXT NOT NULL,
                is_mock INTEGER NOT NULL DEFAULT 1,
                platform TEXT NOT NULL,
                draft_id TEXT,
                operation_id TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                evidence_data TEXT,
                errors TEXT,
                warnings TEXT,
                FOREIGN KEY (manifest_id) REFERENCES manifests(manifest_id)
            );
        """,
        2: """
            -- Add package_hash column for duplicate detection
            ALTER TABLE manifests ADD COLUMN package_hash TEXT;
            CREATE UNIQUE INDEX IF NOT EXISTS idx_manifests_package_hash ON manifests(package_hash);
        """,
    }

    def __init__(self, db_path: Path = None):
        self.db_path = db_path or DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._run_migrations()

    def _run_migrations(self):
        with self._lock:
            conn = sqlite3.connect(str(self.db_path))
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA foreign_keys=ON")
            conn.execute("""
                CREATE TABLE IF NOT EXISTS schema_version (
                    version INTEGER PRIMARY KEY,
                    applied_at TEXT NOT NULL
                )
            """)
            current = conn.execute("SELECT MAX(version) FROM schema_version").fetchone()[0] or 0
            for version in range(current + 1, self.SCHEMA_VERSION + 1):
                if version in self.MIGRATIONS:
                    conn.executescript(self.MIGRATIONS[version])
                    conn.execute("INSERT INTO schema_version (version, applied_at) VALUES (?, ?)",
                                 (version, datetime.now(timezone.utc).isoformat()))
            conn.commit()
            conn.close()

    def _conn(self):
        return sqlite3.connect(str(self.db_path))

    def atomic(self, fn):
        with self._lock:
            conn = self._conn()
            try:
                conn.execute("BEGIN IMMEDIATE")
                result = fn(conn)
                conn.commit()
                return result
            except Exception:
                conn.rollback()
                raise
            finally:
                conn.close()

    def save_manifest(self, manifest_id: str, data: dict):
        """Persist manifest data. Does NOT change state — use transition() for that."""
        def _save(conn):
            now = datetime.now(timezone.utc).isoformat()
            existing = conn.execute("SELECT data, state FROM manifests WHERE manifest_id = ?",
                                    (manifest_id,)).fetchone()
            if existing:
                conn.execute("UPDATE manifests SET data=?, updated_at=? WHERE manifest_id=?",
                             (json.dumps(data), now, manifest_id))
            else:
                conn.execute("INSERT INTO manifests (manifest_id, data, state, created_at, updated_at) VALUES (?, ?, 'discovered', ?, ?)",
                             (manifest_id, json.dumps(data), now, now))
        self.atomic(_save)

    def load_manifest(self, manifest_id: str) -> Optional[dict]:
        def _load(conn):
            row = conn.execute("SELECT data FROM manifests WHERE manifest_id = ?",
                               (manifest_id,)).fetchone()
            return json.loads(row[0]) if row else None
        return self.atomic(_load)

    def get_state(self, manifest_id: str) -> Optional[str]:
        def _get(conn):
            row = conn.execute("SELECT state FROM manifests WHERE manifest_id = ?",
                              (manifest_id,)).fetchone()
            return row[0] if row else None
        return self.atomic(_get)

    def transition(self, manifest_id: str, from_state: PublishState, to_state: PublishState,
                   actor: str = "system", evidence: str = None, idempotency_key: str = None) -> Tuple[bool, str]:
        """THE ONLY state mutation interface. Returns (success, message)."""
        def _trans(conn):
            now = datetime.now(timezone.utc).isoformat()
            current = conn.execute("SELECT state FROM manifests WHERE manifest_id = ?",
                                   (manifest_id,)).fetchone()
            if not current:
                return (False, f"Manifest not found: {manifest_id}")
            if current[0] != from_state.value:
                return (False, f"Invalid transition: current state is '{current[0]}', expected '{from_state.value}'")
            if to_state not in STATE_TRANSITIONS.get(from_state, []):
                return (False, f"Transition '{from_state.value}' -> '{to_state.value}' not allowed")
            conn.execute("UPDATE manifests SET state=?, updated_at=? WHERE manifest_id=?",
                         (to_state.value, now, manifest_id))
            conn.execute("""
                INSERT INTO audit_log (manifest_id, timestamp, actor, action, from_state, to_state, evidence, idempotency_key)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (manifest_id, now, actor, f"transition:{from_state.value}->{to_state.value}",
                  from_state.value, to_state.value, evidence or "", idempotency_key or ""))
            return (True, f"Transitioned from '{from_state.value}' to '{to_state.value}'")
        return self.atomic(_trans)

    def register_artifact(self, sha256: str, path: str, size: int, mime_type: str, provenance: str = None):
        def _reg(conn):
            now = datetime.now(timezone.utc).isoformat()
            try:
                conn.execute("INSERT INTO artifacts (sha256, path, size, mime_type, provenance, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                             (sha256, path, size, mime_type, provenance or "", now))
            except sqlite3.IntegrityError:
                pass
        self.atomic(_reg)

    def find_artifact(self, sha256: str) -> Optional[dict]:
        def _find(conn):
            row = conn.execute("SELECT * FROM artifacts WHERE sha256 = ?", (sha256,)).fetchone()
            if row:
                return {"sha256": row[1], "path": row[2], "size": row[3],
                        "mime_type": row[4], "provenance": row[5], "created_at": row[6]}
            return None
        return self.atomic(_find)

    def get_audit_trail(self, manifest_id: str) -> List[dict]:
        def _audit(conn):
            rows = conn.execute("SELECT timestamp, actor, action, from_state, to_state, evidence, idempotency_key FROM audit_log WHERE manifest_id=? ORDER BY id",
                               (manifest_id,)).fetchall()
            return [{"timestamp": r[0], "actor": r[1], "action": r[2],
                     "from_state": r[3], "to_state": r[4], "evidence": r[5],
                     "idempotency_key": r[6]} for r in rows]
        return self.atomic(_audit)

    def enqueue(self, manifest_id: str, canonical_id: str, priority: int = 0, depends_on: str = None):
        def _enq(conn):
            now = datetime.now(timezone.utc).isoformat()
            conn.execute("INSERT OR REPLACE INTO queue (manifest_id, canonical_id, priority, depends_on, created_at) VALUES (?, ?, ?, ?, ?)",
                         (manifest_id, canonical_id, priority, depends_on, now))
        self.atomic(_enq)

    def get_queue(self) -> List[dict]:
        def _q(conn):
            rows = conn.execute("""
                SELECT q.manifest_id, q.canonical_id, q.priority, q.depends_on, q.created_at,
                       q.locked_by, q.locked_until, m.state
                FROM queue q JOIN manifests m ON q.manifest_id = m.manifest_id
                ORDER BY q.priority DESC, q.created_at ASC
            """).fetchall()
            return [{"manifest_id": r[0], "canonical_id": r[1], "priority": r[2],
                     "depends_on": r[3], "created_at": r[4], "locked_by": r[5],
                     "locked_until": r[6], "state": r[7]} for r in rows]
        return self.atomic(_q)

    def acquire_queue_lock(self, manifest_id: str, owner: str) -> bool:
        def _lock(conn):
            now = datetime.now(timezone.utc).isoformat()
            active = conn.execute("SELECT manifest_id FROM queue WHERE locked_until > ? AND locked_by IS NOT NULL AND manifest_id != ?",
                                 (now, manifest_id)).fetchone()
            if active:
                return False
            until = (datetime.now(timezone.utc).timestamp() + QUEUE_LOCK_TIMEOUT_SECONDS)
            until_iso = datetime.fromtimestamp(until, tz=timezone.utc).isoformat()
            conn.execute("UPDATE queue SET locked_by=?, locked_until=? WHERE manifest_id=?",
                        (owner, until_iso, manifest_id))
            return True
        return self.atomic(_lock)

    def release_queue_lock(self, manifest_id: str):
        def _rel(conn):
            conn.execute("UPDATE queue SET locked_by=NULL, locked_until=NULL WHERE manifest_id=?",
                        (manifest_id,))
        self.atomic(_rel)

    def get_active_submission(self) -> Optional[str]:
        def _get(conn):
            now = datetime.now(timezone.utc).isoformat()
            row = conn.execute("SELECT manifest_id FROM queue WHERE locked_until > ? AND locked_by IS NOT NULL LIMIT 1",
                              (now,)).fetchone()
            return row[0] if row else None
        return self.atomic(_get)

    def _set_state(self, manifest_id: str, state: str):
        """Set state directly. PRIVATE — for migration/repair only.
        Production code must use transition()."""
        def _set(conn):
            now = datetime.now(timezone.utc).isoformat()
            conn.execute("UPDATE manifests SET state=?, updated_at=? WHERE manifest_id=?",
                         (state, now, manifest_id))
        self.atomic(_set)

    def set_approval_hash(self, manifest_id: str, approval_hash: str):
        def _set(conn):
            conn.execute("UPDATE manifests SET approval_hash=? WHERE manifest_id=?",
                        (approval_hash, manifest_id))
        self.atomic(_set)

    def get_approval_hash(self, manifest_id: str) -> Optional[str]:
        def _get(conn):
            row = conn.execute("SELECT approval_hash FROM manifests WHERE manifest_id=?",
                              (manifest_id,)).fetchone()
            return row[0] if row else None
        return self.atomic(_get)

    def save_platform_evidence(self, manifest_id: str, evidence: dict):
        def _save(conn):
            now = datetime.now(timezone.utc).isoformat()
            conn.execute("""
                INSERT INTO platform_evidence (manifest_id, adapter_type, is_mock, platform, draft_id, operation_id, timestamp, evidence_data, errors, warnings)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (manifest_id, evidence.get("adapter_type", "unknown"),
                  evidence.get("is_mock", True), evidence.get("platform", "unknown"),
                  evidence.get("draft_id", ""), evidence.get("operation_id", ""),
                  now, json.dumps(evidence.get("data", {})),
                  json.dumps(evidence.get("errors", [])),
                  json.dumps(evidence.get("warnings", []))))
        self.atomic(_save)

    def get_platform_evidence(self, manifest_id: str) -> List[dict]:
        def _get(conn):
            rows = conn.execute("""
                SELECT adapter_type, is_mock, platform, draft_id, operation_id, timestamp, evidence_data, errors, warnings
                FROM platform_evidence WHERE manifest_id=? ORDER BY id
            """, (manifest_id,)).fetchall()
            return [{"adapter_type": r[0], "is_mock": bool(r[1]), "platform": r[2],
                     "draft_id": r[3], "operation_id": r[4], "timestamp": r[5],
                     "data": json.loads(r[6]), "errors": json.loads(r[7]),
                     "warnings": json.loads(r[8])} for r in rows]
        return self.atomic(_get)

    def has_production_platform_evidence(self, manifest_id: str, operation: str) -> bool:
        def _check(conn):
            row = conn.execute("""
                SELECT COUNT(*) FROM platform_evidence
                WHERE manifest_id=? AND is_mock=0 AND operation_id=?
            """, (manifest_id, operation)).fetchone()
            return row[0] > 0 if row else False
        return self.atomic(_check)

    def find_manifest_by_package_hash(self, pkg_hash: str) -> Optional[str]:
        """Find existing manifest by package hash. Uses dedicated column with UNIQUE enforcement."""
        def _find(conn):
            row = conn.execute(
                "SELECT manifest_id FROM manifests WHERE package_hash = ?",
                (pkg_hash,)
            ).fetchone()
            return row[0] if row else None
        return self.atomic(_find)

    def check_state_consistency(self, manifest_id: str) -> Tuple[bool, str]:
        """Verify reported state matches database state."""
        def _check(conn):
            row = conn.execute("SELECT state FROM manifests WHERE manifest_id = ?",
                              (manifest_id,)).fetchone()
            if not row:
                return (False, f"Manifest not found: {manifest_id}")
            # Reconstruct state from audit trail
            last_event = conn.execute("""
                SELECT to_state FROM audit_log WHERE manifest_id=? ORDER BY id DESC LIMIT 1
            """, (manifest_id,)).fetchone()
            if last_event and last_event[0] != row[0]:
                return (False, f"State mismatch: DB says '{row[0]}', audit trail says '{last_event[0]}'")
            return (True, "State consistent")
        return self.atomic(_check)


# ─── Manifest ID Validation ──────────────────────────────────────────────────

def validate_manifest_id(mid: str) -> bool:
    if not mid or not isinstance(mid, str):
        return False
    if not MANIFEST_ID_PATTERN.match(mid):
        return False
    for dangerous in ("/", "\\", "..", ".", "\x00", "%00", "%2e%2e"):
        if dangerous in mid:
            return False
    return True


# ─── JSON Schema Validation ──────────────────────────────────────────────────

def validate_against_schema(manifest_data: dict) -> List[str]:
    schema_path = SCHEMAS_DIR / "release-manifest.json"
    if not schema_path.exists():
        return ["Schema file not found"]
    try:
        import jsonschema
        schema = json.loads(schema_path.read_text())
        validator = jsonschema.Draft202012Validator(schema)
        errors = sorted(validator.iter_errors(manifest_data), key=lambda e: e.path)
        return [f"{'.'.join(str(p) for p in e.path)}: {e.message}" for e in errors]
    except ImportError:
        return ["jsonschema library not available — cannot validate"]
    except json.JSONDecodeError as e:
        return [f"Schema file is invalid JSON: {e}"]
    except Exception as e:
        return [f"Schema validation error: {e}"]


# ─── Artifact Hashing ────────────────────────────────────────────────────────

def hash_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def detect_mime(path: Path) -> str:
    try:
        import magic
        return magic.from_file(str(path), mime=True)
    except ImportError:
        pass
    with open(path, "rb") as f:
        header = f.read(16)
    if header.startswith(b"\x89PNG"):
        return "image/png"
    if header.startswith(b"\xff\xd8"):
        return "image/jpeg"
    if header.startswith(b"PK"):
        if path.suffix.lower() == ".epub":
            return "application/epub+zip"
        if path.suffix.lower() == ".docx":
            return "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        return "application/zip"
    if header.startswith(b"ID3") or header.startswith(b"\xff\xfb"):
        return "audio/mpeg"
    if path.suffix.lower() == ".json":
        return "application/json"
    if path.suffix.lower() == ".md":
        return "text/markdown"
    return "application/octet-stream"


# ─── Cover Validation ────────────────────────────────────────────────────────

def validate_cover(cover_path: Path) -> Dict:
    errors = []
    warnings = []
    evidence = {}

    if not cover_path.exists():
        return {"passed": False, "errors": ["Cover file not found"], "warnings": [], "evidence": {}}

    mime = detect_mime(cover_path)
    if mime not in ("image/jpeg", "image/png"):
        errors.append(f"Cover MIME type '{mime}' not supported (expected image/jpeg or image/png)")

    if cover_path.stat().st_size == 0:
        errors.append("Cover file is empty")
    if cover_path.stat().st_size > 50 * 1024 * 1024:
        errors.append(f"Cover file too large: {cover_path.stat().st_size} bytes (max 50MB)")

    try:
        from PIL import Image
        img = Image.open(cover_path)
        w, h = img.size
        evidence["dimensions"] = f"{w}x{h}"
        evidence["color_mode"] = img.mode

        if w < 1000 or h < 625:
            errors.append(f"Cover too small: {w}x{h} (minimum 1000x625)")
        ratio = w / h
        if ratio < 0.6 or ratio > 0.75:
            warnings.append(f"Cover aspect ratio {ratio:.3f} (expected ~0.667 for 6x9)")
        if img.mode not in ("RGB", "CMYK"):
            warnings.append(f"Cover color mode: {img.mode} (expected RGB or CMYK)")
        img.verify()
    except ImportError:
        errors.append("PIL not available — cover validation requires Pillow")
    except Exception as e:
        errors.append(f"Cover validation error: {e}")

    return {"passed": len(errors) == 0, "errors": errors, "warnings": warnings, "evidence": evidence}


# ─── Canonical Manifest Hash ─────────────────────────────────────────────────

def build_canonical_manifest_hash(manifest_data: dict) -> str:
    """Build a deterministic hash from ALL consequential fields."""
    h = hashlib.sha256()

    # Schema and identity
    h.update(str(manifest_data.get("schema_version", "")).encode())
    h.update(str(manifest_data.get("manifest_id", "")).encode())

    # Title
    title = manifest_data.get("title", {})
    h.update(str(title.get("canonical", "")).encode())
    h.update(str(title.get("subtitle", "")).encode())
    h.update(str(title.get("series", "")).encode())
    h.update(str(title.get("edition", "")).encode())

    # Author and publisher
    h.update(str(manifest_data.get("author", "")).encode())
    h.update(str(manifest_data.get("publisher", "")).encode())

    # Platform and format
    h.update(str(manifest_data.get("target_platform", "")).encode())
    h.update(str(manifest_data.get("draft_id", "")).encode())
    h.update(str(manifest_data.get("format", "")).encode())
    h.update(str(manifest_data.get("language", "")).encode())

    # Publishing
    pub = manifest_data.get("publishing", {})
    h.update(str(pub.get("price", 0)).encode())
    h.update(str(pub.get("currency", "")).encode())
    h.update(str(pub.get("drm", "")).encode())
    h.update(str(pub.get("kdp_select", "")).encode())
    h.update(str(pub.get("release_date", "")).encode())

    # Rights
    rights = manifest_data.get("rights", {})
    h.update(str(rights.get("territories", "")).encode())
    h.update(str(rights.get("copyright_owner", "")).encode())
    h.update(str(rights.get("copyright_year", "")).encode())

    # Metadata
    meta = manifest_data.get("metadata", {})
    h.update(str(meta.get("description", "")).encode())
    for kw in meta.get("keywords", []):
        h.update(str(kw).encode())
    for cat in meta.get("categories", []):
        h.update(str(cat).encode())
    ai = meta.get("ai_disclosure", {})
    h.update(str(ai.get("text", False)).encode())
    h.update(str(ai.get("cover", False)).encode())
    h.update(str(ai.get("interior_images", False)).encode())
    h.update(str(ai.get("translation", False)).encode())

    # Identifiers
    ids = manifest_data.get("identifiers", {})
    h.update(str(ids.get("isbn", "")).encode())
    h.update(str(ids.get("asin", "")).encode())
    h.update(str(ids.get("isrc", "")).encode())
    h.update(str(ids.get("upc", "")).encode())
    h.update(str(ids.get("acx_title_id", "")).encode())

    # Artifact hashes
    for key in sorted(manifest_data.get("files", {}).keys()):
        h.update(key.encode())
        h.update(manifest_data["files"][key].get("sha256", "").encode())

    # Repair history
    for repair in manifest_data.get("validation", {}).get("repair_history", []):
        h.update(str(repair).encode())

    return h.hexdigest()


# ─── Platform Adapter Contract ────────────────────────────────────────────────

class PlatformAdapter:
    def __init__(self, name: str, logger=None):
        self.name = name
        self.logger = logger or setup_logger()
        self._is_mock = True

    def is_mock(self) -> bool:
        return self._is_mock

    def check_auth(self) -> Dict:
        raise NotImplementedError

    def find_existing_draft(self, title: str) -> Optional[Dict]:
        raise NotImplementedError

    def verify_draft_identity(self, draft_id: str, expected_title: str) -> bool:
        raise NotImplementedError

    def map_fields(self, manifest: dict) -> Dict:
        raise NotImplementedError

    def upload_artifact(self, draft_id: str, artifact_type: str, file_path: str) -> Dict:
        raise NotImplementedError

    def poll_processing(self, draft_id: str) -> Dict:
        raise NotImplementedError

    def launch_previewer(self, draft_id: str) -> Dict:
        raise NotImplementedError

    def capture_preview_evidence(self, draft_id: str) -> Dict:
        raise NotImplementedError

    def save_draft(self, draft_id: str) -> bool:
        raise NotImplementedError

    def submit(self, draft_id: str) -> Dict:
        raise NotImplementedError

    def refresh_status(self, draft_id: str) -> str:
        raise NotImplementedError

    def resume(self, draft_id: str, checkpoint: str) -> bool:
        raise NotImplementedError


class MockKDPAdapter(PlatformAdapter):
    """Mock KDP adapter. All evidence is marked as mock — never satisfies production readiness."""

    def __init__(self, logger=None):
        super().__init__("kdp-mock", logger)
        self._is_mock = True

    def check_auth(self) -> Dict:
        return {"authenticated": True, "session_info": "mock-session", "error": None}

    def find_existing_draft(self, title: str) -> Optional[Dict]:
        return None

    def verify_draft_identity(self, draft_id: str, expected_title: str) -> bool:
        return True

    def map_fields(self, manifest: dict) -> Dict:
        return {"mapped": True, "fields": manifest.get("metadata", {})}

    def upload_artifact(self, draft_id: str, artifact_type: str, file_path: str) -> Dict:
        return {"success": True, "evidence": f"MOCK: {artifact_type} uploaded to draft {draft_id}", "error": None, "_mock": True}

    def poll_processing(self, draft_id: str) -> Dict:
        return {"status": "processed", "errors": [], "warnings": [], "evidence": f"MOCK: processing complete for draft {draft_id}", "_mock": True}

    def launch_previewer(self, draft_id: str) -> Dict:
        return {"opened": True, "screenshots": ["mock-preview-screenshot-1.png"], "warnings": [], "evidence": f"MOCK: previewer launched for draft {draft_id}", "_mock": True}

    def capture_preview_evidence(self, draft_id: str) -> Dict:
        return {"screenshots": ["mock-preview-screenshot-1.png"], "warnings": [], "evidence": f"MOCK: preview evidence captured for draft {draft_id}", "_mock": True}

    def save_draft(self, draft_id: str) -> bool:
        return True

    def submit(self, draft_id: str) -> Dict:
        return {"submitted": True, "confirmation_id": f"mock-conf-{uuid.uuid4().hex[:8]}", "evidence": f"MOCK: submitted draft {draft_id}", "error": None, "_mock": True}

    def refresh_status(self, draft_id: str) -> str:
        return "draft"

    def resume(self, draft_id: str, checkpoint: str) -> bool:
        return True


# ─── Publishing Engine ───────────────────────────────────────────────────────

class PublishEngine:
    """Core publishing engine. State machine is the ONLY state mutation interface."""

    def __init__(self, db: StateStore = None, logger=None):
        self.db = db or StateStore()
        self.logger = logger or setup_logger()
        self.adapter = MockKDPAdapter(self.logger)

    def _require_valid_manifest_id(self, mid: str):
        if not validate_manifest_id(mid):
            raise ValueError(f"Invalid manifest ID: {mid}")

    def _is_approved_root(self, path: Path) -> bool:
        """Check if a path is under an approved package root."""
        resolved = path.resolve()
        for root in APPROVED_PACKAGE_ROOTS:
            try:
                resolved.relative_to(root.resolve())
                return True
            except ValueError:
                continue
        return False

    def _safe_stage_path(self, path: Path) -> Path:
        """Verify a path is safe for staging."""
        if path.is_symlink():
            raise ValueError(f"Symlinks not allowed: {path}")
        if not path.is_file():
            raise ValueError(f"Not a regular file: {path}")
        resolved = path.resolve()
        if not self._is_approved_root(resolved):
            raise ValueError(f"File not in approved package root: {path}")
        # Reject hard links (st_nlink > 1 means linked from elsewhere)
        st = path.stat()
        if st.st_nlink > 1:
            raise ValueError(f"Hard links not allowed: {path} (nlink={st.st_nlink})")
        return resolved

    def discover(self, package_path: str = None, dry_run: bool = False) -> List[Dict]:
        if dry_run:
            self.logger.info("DRY RUN: would discover packages")
            return []

        discovered = []
        if package_path:
            pkg = Path(package_path).resolve()
            if not self._is_approved_root(pkg):
                self.logger.warning(f"Package not in approved root: {pkg}")
                return []
            if pkg.is_dir():
                pkg_hash = self._hash_package(pkg)

                # Atomic check-and-create with UNIQUE index enforcement
                def _discover(conn):
                    # Check for existing
                    row = conn.execute(
                        "SELECT manifest_id FROM manifests WHERE package_hash = ?",
                        (pkg_hash,)
                    ).fetchone()
                    if row:
                        return [{"path": str(pkg), "manifest_id": row[0], "duplicate": True}]

                    # Create new
                    manifest_data = self._build_manifest_from_package(pkg)
                    mid = manifest_data["manifest_id"]
                    manifest_data["_package_hash"] = pkg_hash
                    now = datetime.now(timezone.utc).isoformat()
                    try:
                        conn.execute(
                            "INSERT INTO manifests (manifest_id, data, state, package_hash, created_at, updated_at) VALUES (?, ?, 'discovered', ?, ?, ?)",
                            (mid, json.dumps(manifest_data), pkg_hash, now, now)
                        )
                    except sqlite3.IntegrityError:
                        # Race condition: another thread inserted first
                        row = conn.execute(
                            "SELECT manifest_id FROM manifests WHERE package_hash = ?",
                            (pkg_hash,)
                        ).fetchone()
                        if row:
                            return [{"path": str(pkg), "manifest_id": row[0], "duplicate": True}]
                        raise
                    cid = resolve_canonical_id(manifest_data.get("title", {}).get("canonical", "")) or "unknown"
                    conn.execute(
                        "INSERT OR REPLACE INTO queue (manifest_id, canonical_id, priority, created_at) VALUES (?, ?, 0, ?)",
                        (mid, cid, now)
                    )
                    return [{"path": str(pkg), "manifest_id": mid}]

                result = self.db.atomic(_discover)
                discovered.extend(result)
                if result and not result[0].get("duplicate"):
                    self.logger.info(f"Discovered: {pkg} → {result[0]['manifest_id']}")
                else:
                    self.logger.info(f"Duplicate package detected: {pkg} → existing {result[0]['manifest_id']}")
        return discovered
    def _hash_package(self, pkg: Path) -> str:
        """Compute a deterministic hash of a package directory.
        Includes all consequential files: manuscripts, covers, KDP-DRAFT.md.
        Excludes only truly transient files."""
        h = hashlib.sha256()
        h.update(pkg.name.encode())
        for f in sorted(pkg.rglob("*")):
            if f.is_file():
                h.update(f.name.encode())
                h.update(str(f.stat().st_size).encode())
                h.update(hash_file(f).encode())
        return h.hexdigest()

    def _build_manifest_from_package(self, pkg: Path) -> dict:
        mid = f"ggb-manifest-{uuid.uuid4()}"
        now = datetime.now(timezone.utc).isoformat()
        manifest = {
            "schema_version": MANIFEST_SCHEMA_VERSION,
            "manifest_id": mid,
            "created_at": now,
            "updated_at": now,
            "title": {"canonical": pkg.name.replace("-", " ").title(), "subtitle": ""},
            "author": "Darryl Elliott Brown",
            "publisher": "Gullah Geechee Biz",
            "language": "en",
            "format": "ebook",
            "target_platform": "kdp",
            "draft_id": None,
            "source_package": {"path": str(pkg.resolve()), "record_ids": {}},
            "files": {},
            "metadata": {
                "description": "",
                "keywords": [],
                "categories": [],
                "ai_disclosure": {"text": False, "cover": False, "interior_images": False, "translation": False}
            },
            "rights": {
                "copyright_owner": "Darryl Elliott Brown",
                "copyright_year": 2026,
                "publishing_rights": "owner_confirmed",
                "territories": "Worldwide"
            },
            "publishing": {
                "drm": "no",
                "kdp_select": "off",
                "price": 0,
                "currency": "USD"
            },
            "validation": {"status": "pending", "repair_history": []},
            "approval": {"status": "pending"},
            "status": "discovered",
            "submission": {},
        }

        for f in sorted(pkg.iterdir()):
            if f.is_file() and f.name != "KDP-DRAFT.md":
                key = self._classify_file(f)
                if key:
                    sha = hash_file(f)
                    manifest["files"][key] = {
                        "path": str(f.resolve()),
                        "sha256": sha,
                        "size": f.stat().st_size,
                        "mime_type": detect_mime(f),
                    }

        draft_file = pkg / "KDP-DRAFT.md"
        if draft_file.exists():
            self._parse_kdp_draft(draft_file, manifest)

        return manifest

    def _classify_file(self, path: Path) -> Optional[str]:
        name = path.name.lower()
        if "manuscript" in name or name.endswith(".docx"):
            return "manuscript"
        if "cover" in name and (name.endswith(".jpg") or name.endswith(".png")):
            return "cover"
        if "audio" in name or name.endswith(".mp3"):
            return "audio"
        if "artwork" in name:
            return "artwork"
        if "metadata" in name or name.endswith(".json"):
            return "metadata"
        return None

    def _parse_kdp_draft(self, path: Path, manifest: dict):
        text = path.read_text()
        for line in text.split("\n"):
            line = line.strip()
            if line.startswith("- **Title:**"):
                manifest["title"]["canonical"] = line.split(":**", 1)[1].strip()
            elif line.startswith("- **Author:**"):
                manifest["author"] = line.split(":**", 1)[1].strip()
            elif line.startswith("- **Publisher:**"):
                manifest["publisher"] = line.split(":**", 1)[1].strip()
            elif line.startswith("- **Language:**"):
                manifest["language"] = line.split(":**", 1)[1].strip()
            elif line.startswith("- **Ebook price:**"):
                try:
                    manifest["publishing"]["price"] = float(line.split(":**", 1)[1].strip().lstrip("$"))
                except ValueError:
                    pass
            elif line.startswith("- **DRM:**"):
                val = line.split(":**", 1)[1].strip()
                manifest["publishing"]["drm"] = DRM_PARSE.get(val, DRM.NO).value
            elif line.startswith("- **KDP Select:**"):
                val = line.split(":**", 1)[1].strip()
                manifest["publishing"]["kdp_select"] = SELECT_PARSE.get(val, KDPSelect.OFF).value
            elif manifest["metadata"]["description"] == "" and line and not line.startswith("-") and not line.startswith("#"):
                manifest["metadata"]["description"] = line

    def reconcile(self, manifest_id: str, dry_run: bool = False) -> Dict:
        self._require_valid_manifest_id(manifest_id)
        if dry_run:
            return {"dry_run": True, "message": "Would reconcile"}

        manifest = self.db.load_manifest(manifest_id)
        if not manifest:
            return {"error": f"Manifest not found: {manifest_id}"}

        for key, finfo in manifest.get("files", {}).items():
            path = Path(finfo["path"])
            if path.exists():
                self.db.register_artifact(
                    finfo["sha256"], str(path), finfo["size"],
                    finfo.get("mime_type", "application/octet-stream"),
                    provenance=f"manifest:{manifest_id}"
                )

        return {
            "manifest_id": manifest_id,
            "title": manifest.get("title", {}).get("canonical", "Unknown"),
            "status": manifest.get("status", "unknown"),
            "files_registered": len(manifest.get("files", {})),
        }

    def audit(self, manifest_id: str, dry_run: bool = False) -> Dict:
        self._require_valid_manifest_id(manifest_id)
        if dry_run:
            return {"dry_run": True, "message": "Would audit"}

        manifest = self.db.load_manifest(manifest_id)
        if not manifest:
            return {"error": f"Manifest not found: {manifest_id}"}

        # Read authoritative state from DB
        db_state = self.db.get_state(manifest_id)
        if not db_state:
            return {"error": f"Manifest not found in state store: {manifest_id}"}
        current_state = PublishState(db_state)

        # Use state machine for transition
        if current_state == PublishState.DISCOVERED:
            success, msg = self.db.transition(manifest_id, PublishState.DISCOVERED, PublishState.PACKAGED, actor="audit")
            if success:
                current_state = PublishState.PACKAGED
        if current_state in (PublishState.PACKAGED, PublishState.BLOCKED):
            success, msg = self.db.transition(manifest_id, current_state, PublishState.VALIDATING, actor="audit")
            if not success:
                return {"error": msg}

        errors = []
        warnings = []

        # Schema validation
        schema_errors = validate_against_schema(manifest)
        if schema_errors:
            errors.extend(schema_errors)

        # Cover validation
        cover_info = manifest.get("files", {}).get("cover")
        if cover_info:
            cover_path = Path(cover_info["path"])
            if cover_path.exists():
                cover_result = validate_cover(cover_path)
                if not cover_result["passed"]:
                    errors.extend(cover_result["errors"])
                warnings.extend(cover_result["warnings"])
        else:
            errors.append("No cover file in manifest")

        if "manuscript" not in manifest.get("files", {}):
            errors.append("No manuscript file in manifest")

        meta = manifest.get("metadata", {})
        if not meta.get("description") or len(meta.get("description", "")) < 20:
            errors.append("Description too short or missing")
        if not meta.get("keywords"):
            warnings.append("No keywords set")

        # Price enforcement — unknown titles block
        title = manifest.get("title", {}).get("canonical", "")
        cid = resolve_canonical_id(title)
        allowed, msg = enforce_price(cid, manifest.get("publishing", {}).get("price", 0))
        if not allowed:
            errors.append(msg)

        # Protected draft check
        if cid:
            allowed, msg = check_protected_draft(cid, manifest.get("target_platform", "kdp"),
                                                  manifest.get("draft_id"))
            if not allowed:
                errors.append(msg)

        # DRM / Select checks
        drm = manifest.get("publishing", {}).get("drm", "no")
        if drm not in ("no", "yes"):
            errors.append(f"Invalid DRM value: {drm}")
        select = manifest.get("publishing", {}).get("kdp_select", "off")
        if select not in ("off", "on"):
            errors.append(f"Invalid KDP Select value: {select}")

        # Hash verification
        for key, finfo in manifest.get("files", {}).items():
            path = Path(finfo["path"])
            if path.exists():
                actual = hash_file(path)
                if actual != finfo["sha256"]:
                    errors.append(f"Hash mismatch for {key}")

        # Queue checks
        active = self.db.get_active_submission()
        if active and active != manifest_id:
            errors.append(f"Another title is in active submission: {active}")

        passed = len(errors) == 0
        result = {"passed": passed, "errors": errors, "warnings": warnings, "schema_errors": schema_errors}

        manifest["validation"] = result
        manifest["validation"]["status"] = "passed" if passed else "failed"
        manifest["updated_at"] = datetime.now(timezone.utc).isoformat()
        self.db.save_manifest(manifest_id, manifest)

        if passed:
            self.db.transition(manifest_id, PublishState.VALIDATING, PublishState.VALIDATED, actor="audit")
        else:
            self.db.transition(manifest_id, PublishState.VALIDATING, PublishState.BLOCKED, actor="audit")

        return result

    def repair(self, manifest_id: str, dry_run: bool = False) -> Dict:
        self._require_valid_manifest_id(manifest_id)
        if dry_run:
            return {"dry_run": True, "message": "Would repair"}

        manifest = self.db.load_manifest(manifest_id)
        if not manifest:
            return {"error": f"Manifest not found: {manifest_id}"}

        repair_dir = REPAIRS_DIR / manifest_id
        repair_dir.mkdir(parents=True, exist_ok=True)

        repairs = []
        cover_info = manifest.get("files", {}).get("cover")
        if cover_info:
            cover_path = Path(cover_info["path"])
            if cover_path.exists():
                try:
                    from PIL import Image
                    img = Image.open(cover_path)
                    if img.mode == "CMYK":
                        derivative = repair_dir / cover_path.name
                        rgb = img.convert("RGB")
                        rgb.save(derivative, "JPEG", quality=95)
                        repairs.append({
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                            "action": "cover_color_conversion",
                            "before_hash": hash_file(cover_path),
                            "after_hash": hash_file(derivative),
                            "description": "Converted cover from CMYK to RGB",
                        })
                        manifest["files"]["cover"]["path"] = str(derivative)
                        manifest["files"]["cover"]["sha256"] = hash_file(derivative)
                        manifest["files"]["cover"]["size"] = derivative.stat().st_size

                    w, h = img.size
                    if w < 1000 or h < 625:
                        ratio = max(1000 / w, 625 / h)
                        new_w = int(w * ratio)
                        new_h = int(h * ratio)
                        derivative = repair_dir / cover_path.name
                        resized = img.resize((new_w, new_h), Image.LANCZOS)
                        resized.save(derivative, "JPEG", quality=95)
                        repairs.append({
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                            "action": "cover_size_upscale",
                            "before_hash": hash_file(cover_path),
                            "after_hash": hash_file(derivative),
                            "description": f"Upscaled cover from {w}x{h} to {new_w}x{new_h}",
                        })
                        manifest["files"]["cover"]["path"] = str(derivative)
                        manifest["files"]["cover"]["sha256"] = hash_file(derivative)
                except ImportError:
                    pass

        if repairs:
            manifest["validation"]["repair_history"] = manifest["validation"].get("repair_history", [])
            manifest["validation"]["repair_history"].extend(repairs)
            manifest["updated_at"] = datetime.now(timezone.utc).isoformat()
            self.db.save_manifest(manifest_id, manifest)

        return {"repairs": repairs, "count": len(repairs)}

    def stage(self, manifest_id: str, dry_run: bool = False) -> Dict:
        self._require_valid_manifest_id(manifest_id)
        if dry_run:
            return {"dry_run": True, "message": "Would stage files"}

        manifest = self.db.load_manifest(manifest_id)
        if not manifest:
            return {"error": f"Manifest not found: {manifest_id}"}

        # Read authoritative state from DB
        db_state = self.db.get_state(manifest_id)
        if not db_state:
            return {"error": f"Manifest not found in state store: {manifest_id}"}
        current_state = PublishState(db_state)

        if current_state != PublishState.VALIDATED:
            return {"error": f"Must be in VALIDATED state to stage (current: {current_state.value})"}

        stage_dir = STAGING_DIR / manifest_id
        stage_dir.mkdir(parents=True, exist_ok=True)

        staged = []
        for key, finfo in manifest.get("files", {}).items():
            src = Path(finfo["path"])
            try:
                safe_src = self._safe_stage_path(src)
            except ValueError as e:
                return {"error": str(e)}

            dst = stage_dir / src.name
            if dst.exists():
                return {"error": f"Destination collision: {dst}"}

            shutil.copy2(safe_src, dst)
            actual_hash = hash_file(dst)
            if actual_hash != finfo["sha256"]:
                dst.unlink()
                return {"error": f"Hash mismatch after staging for {key}"}

            staged.append(str(dst))

        # Use state machine — only transition if we succeed
        success, msg = self.db.transition(manifest_id, current_state, PublishState.STAGED, actor="stage")
        if not success:
            return {"error": msg}

        return {"staged_files": staged, "stage_dir": str(stage_dir)}

    def preview(self, manifest_id: str, dry_run: bool = False) -> Dict:
        self._require_valid_manifest_id(manifest_id)
        if dry_run:
            return {"dry_run": True, "message": "Would preview"}

        manifest = self.db.load_manifest(manifest_id)
        if not manifest:
            return {"error": f"Manifest not found: {manifest_id}"}

        # Read authoritative state from DB
        db_state = self.db.get_state(manifest_id)
        if not db_state:
            return {"error": f"Manifest not found in state store: {manifest_id}"}
        current_state = PublishState(db_state)

        if current_state != PublishState.STAGED:
            return {"error": f"Must be in STAGED state to preview (current: {current_state.value})"}

        auth = self.adapter.check_auth()
        if not auth.get("authenticated"):
            return {"error": "Adapter not authenticated"}

        draft_id = manifest.get("draft_id", "mock-draft")
        draft = self.adapter.find_existing_draft(manifest.get("title", {}).get("canonical", ""))
        if draft:
            draft_id = draft.get("draft_id", draft_id)

        # Upload artifacts
        for key in ["manuscript", "cover"]:
            finfo = manifest.get("files", {}).get(key)
            if finfo:
                upload_result = self.adapter.upload_artifact(draft_id, key, finfo["path"])
                evidence = {
                    "adapter_type": self.adapter.name,
                    "is_mock": self.adapter.is_mock(),
                    "platform": "kdp",
                    "draft_id": draft_id,
                    "operation_id": f"upload-{key}",
                    "data": upload_result,
                    "errors": [upload_result.get("error")] if upload_result.get("error") else [],
                    "warnings": [],
                }
                self.db.save_platform_evidence(manifest_id, evidence)

        # Transition through platform states
        success, msg = self.db.transition(manifest_id, current_state, PublishState.PLATFORM_UPLOADED, actor="preview")
        if not success:
            return {"error": msg}
        current_state = PublishState.PLATFORM_UPLOADED

        # Poll processing
        processing = self.adapter.poll_processing(draft_id)
        evidence = {
            "adapter_type": self.adapter.name,
            "is_mock": self.adapter.is_mock(),
            "platform": "kdp",
            "draft_id": draft_id,
            "operation_id": "poll-processing",
            "data": processing,
            "errors": processing.get("errors", []),
            "warnings": processing.get("warnings", []),
        }
        self.db.save_platform_evidence(manifest_id, evidence)

        success, msg = self.db.transition(manifest_id, current_state, PublishState.PLATFORM_PROCESSED, actor="preview")
        if not success:
            return {"error": msg}
        current_state = PublishState.PLATFORM_PROCESSED

        # Launch previewer
        preview_result = self.adapter.launch_previewer(draft_id)
        capture = self.adapter.capture_preview_evidence(draft_id)
        evidence = {
            "adapter_type": self.adapter.name,
            "is_mock": self.adapter.is_mock(),
            "platform": "kdp",
            "draft_id": draft_id,
            "operation_id": "preview",
            "data": {"preview": preview_result, "capture": capture},
            "errors": [],
            "warnings": capture.get("warnings", []),
        }
        self.db.save_platform_evidence(manifest_id, evidence)

        success, msg = self.db.transition(manifest_id, current_state, PublishState.PREVIEW_CLEAN, actor="preview")
        if not success:
            return {"error": msg}

        # Transition to AWAITING_OWNER_APPROVAL after successful preview
        success, msg = self.db.transition(manifest_id, PublishState.PREVIEW_CLEAN, PublishState.AWAITING_OWNER_APPROVAL, actor="preview")
        if not success:
            return {"error": msg}

        result = {
            "manifest_id": manifest_id,
            "title": manifest.get("title", {}).get("canonical", "Unknown"),
            "previewer_opened": preview_result.get("opened", False),
            "screenshots": capture.get("screenshots", []),
            "warnings": capture.get("warnings", []),
            "_mock": self.adapter.is_mock(),
            "note": "MOCK EVIDENCE — not production-ready" if self.adapter.is_mock() else "",
        }

        return result

    def manifest(self, manifest_id: str) -> Dict:
        self._require_valid_manifest_id(manifest_id)
        manifest = self.db.load_manifest(manifest_id)
        if not manifest:
            return {"error": f"Manifest not found: {manifest_id}"}
        return manifest

    def approve(self, manifest_id: str, owner: str = "owner", dry_run: bool = False) -> Dict:
        self._require_valid_manifest_id(manifest_id)
        if dry_run:
            return {"dry_run": True, "message": "Would approve"}

        manifest = self.db.load_manifest(manifest_id)
        if not manifest:
            return {"error": f"Manifest not found: {manifest_id}"}

        db_state = self.db.get_state(manifest_id)
        if not db_state:
            return {"error": f"Manifest not found in state store: {manifest_id}"}
        state = PublishState(db_state)

        if state in ILLEGAL_APPROVAL_STATES:
            return {"error": f"Cannot approve from state: {state.value}"}

        if state not in (PublishState.AWAITING_OWNER_APPROVAL,):
            return {"error": f"Must be in AWAITING_OWNER_APPROVAL state to approve (current state: {state.value})"}

        # Must have production platform evidence for approval
        if not self.db.has_production_platform_evidence(manifest_id, "preview"):
            return {"error": "Production platform evidence required for approval (mock evidence rejected)"}

        active = self.db.get_active_submission()
        if active and active != manifest_id:
            return {"error": f"Another title is in active submission: {active}"}

        approval_hash = build_canonical_manifest_hash(manifest)

        success, msg = self.db.transition(manifest_id, state, PublishState.APPROVED, actor=owner,
                                          evidence=f"approval_hash={approval_hash}")
        if not success:
            return {"error": msg}

        manifest["approval"] = {
            "status": "approved",
            "approved_by": owner,
            "approved_at": datetime.now(timezone.utc).isoformat(),
            "approval_hash": approval_hash,
        }
        manifest["status"] = "approved"
        manifest["updated_at"] = datetime.now(timezone.utc).isoformat()
        self.db.save_manifest(manifest_id, manifest)
        self.db.set_approval_hash(manifest_id, approval_hash)

        return {"manifest_id": manifest_id, "approval_hash": approval_hash, "status": "approved"}

    def submit(self, manifest_id: str, platform: str = "kdp", dry_run: bool = False) -> Dict:
        self._require_valid_manifest_id(manifest_id)
        if dry_run:
            return {"dry_run": True, "message": "Would submit"}

        manifest = self.db.load_manifest(manifest_id)
        if not manifest:
            return {"error": f"Manifest not found: {manifest_id}"}

        db_state = self.db.get_state(manifest_id)
        if not db_state:
            return {"error": f"Manifest not found in state store: {manifest_id}"}
        state = PublishState(db_state)

        if state not in (PublishState.AWAITING_OWNER_APPROVAL, PublishState.APPROVED):
            return {"error": f"Must be approved before submit (current state: {state.value})"}

        approval = manifest.get("approval", {})
        if approval.get("status") != "approved":
            return {"error": "Not approved. Run 'ggb publish approve' first."}

        current_hash = build_canonical_manifest_hash(manifest)
        stored_hash = self.db.get_approval_hash(manifest_id)
        if current_hash != stored_hash:
            return {"error": "Approval expired — manifest changed since approval"}

        if not self.db.has_production_platform_evidence(manifest_id, "preview"):
            return {"error": "Production platform evidence required before submit"}

        if not self.db.acquire_queue_lock(manifest_id, "publisher"):
            return {"error": "Could not acquire submission lock — another title may be active"}

        draft_id = manifest.get("draft_id", "new")
        result = self.adapter.submit(draft_id)

        evidence = {
            "adapter_type": self.adapter.name,
            "is_mock": self.adapter.is_mock(),
            "platform": platform,
            "draft_id": draft_id,
            "operation_id": "submit",
            "data": result,
            "errors": [result.get("error")] if result.get("error") else [],
            "warnings": [],
        }
        self.db.save_platform_evidence(manifest_id, evidence)

        success, msg = self.db.transition(manifest_id, state, PublishState.SUBMITTED, actor="publisher",
                                          evidence=result.get("evidence", ""))
        if not success:
            self.db.release_queue_lock(manifest_id)
            return {"error": msg}

        manifest["status"] = "submitted"
        manifest["submission"] = {
            "submitted_at": datetime.now(timezone.utc).isoformat(),
            "confirmation_id": result.get("confirmation_id", ""),
            "platform": platform,
            "evidence": result.get("evidence", ""),
            "_mock": self.adapter.is_mock(),
        }
        manifest["updated_at"] = datetime.now(timezone.utc).isoformat()
        self.db.save_manifest(manifest_id, manifest)

        return {
            "manifest_id": manifest_id,
            "status": "submitted",
            "confirmation_id": result.get("confirmation_id", ""),
            "_mock": self.adapter.is_mock(),
        }

    def get_status(self, manifest_id: str) -> Dict:
        try:
            self._require_valid_manifest_id(manifest_id)
        except ValueError as e:
            return {"error": str(e)}
        manifest = self.db.load_manifest(manifest_id)
        if not manifest:
            return {"error": f"Manifest not found: {manifest_id}"}

        # Read authoritative state from DB
        db_state = self.db.get_state(manifest_id)
        if not db_state:
            return {"error": f"Manifest not found in state store: {manifest_id}"}
        state = db_state
        validation = manifest.get("validation", {})
        approval = manifest.get("approval", {})

        is_ready = False
        blockers = []

        if state != "approved":
            blockers.append(f"State is '{state}', must be 'approved'")
        else:
            has_upload = self.db.has_production_platform_evidence(manifest_id, "upload-manuscript")
            has_cover = self.db.has_production_platform_evidence(manifest_id, "upload-cover")
            has_processing = self.db.has_production_platform_evidence(manifest_id, "poll-processing")
            has_preview = self.db.has_production_platform_evidence(manifest_id, "preview")

            if not has_upload:
                blockers.append("No production upload evidence")
            if not has_cover:
                blockers.append("No production cover upload evidence")
            if not has_processing:
                blockers.append("No production processing evidence")
            if not has_preview:
                blockers.append("No production preview evidence")

            current_hash = build_canonical_manifest_hash(manifest)
            stored_hash = self.db.get_approval_hash(manifest_id)
            if current_hash != stored_hash:
                blockers.append("Approval expired — manifest changed")

            active = self.db.get_active_submission()
            if active and active != manifest_id:
                blockers.append(f"Another title is in active submission: {active}")

        is_ready = len(blockers) == 0

        if is_ready:
            report = "STATUS: READY TO SUBMIT\n"
        else:
            report = f"STATUS: {state.upper()}\n"

        report += f"- Title: {manifest.get('title', {}).get('canonical', 'Unknown')}\n"
        report += f"- Draft ID: {manifest.get('draft_id', 'none')}\n"
        report += f"- Format: {manifest.get('format', 'unknown')}\n"
        report += f"- Price: ${manifest.get('publishing', {}).get('price', 0)}\n"
        report += f"- Select: {manifest.get('publishing', {}).get('kdp_select', 'off')}\n"
        report += f"- DRM: {manifest.get('publishing', {}).get('drm', 'no')}\n"

        has_preview = self.db.has_production_platform_evidence(manifest_id, "preview")
        if has_preview:
            report += "- Previewer: CLEAN\n"
        else:
            report += "- Previewer: NOT RUN (mock only)\n"

        if blockers:
            report += f"- Blockers: {len(blockers)} errors\n"
            for b in blockers[:5]:
                report += f"  - {b}\n"
        else:
            report += "- Blockers: none\n"

        report += f"- Next action: {'waiting for owner publish now' if is_ready else 'run ggb publish audit'}\n"

        return {
            "manifest_id": manifest_id,
            "title": manifest.get("title", {}).get("canonical", "Unknown"),
            "status": state,
            "ready": is_ready,
            "report": report,
            "blockers": blockers,
        }

    def resume(self, manifest_id: str) -> Dict:
        self._require_valid_manifest_id(manifest_id)
        state = self.db.get_state(manifest_id)
        if not state:
            return {"error": f"Manifest not found: {manifest_id}"}

        resume_map = {
            "discovered": "reconcile",
            "packaged": "audit",
            "validating": "audit",
            "blocked": "repair",
            "validated": "stage",
            "staged": "preview",
            "platform_uploaded": "preview",
            "platform_processed": "preview",
            "preview_clean": "approve",
            "awaiting_owner_approval": "approve",
        }

        return {
            "manifest_id": manifest_id,
            "current_state": state,
            "next_action": resume_map.get(state, "status"),
            "can_resume": state not in ("live", "archived", "submitted", "approved"),
        }


# ─── CLI ─────────────────────────────────────────────────────────────────────

def cli():
    import argparse
    parser = argparse.ArgumentParser(description="GGB Publisher Control Plane")
    parser.add_argument("--dry-run", action="store_true", help="Dry run — no mutations")
    parser.add_argument("--json", action="store_true", help="JSON output")
    parser.add_argument("--trace", type=str, help="Workflow trace ID")
    sub = parser.add_subparsers(dest="command", required=True)

    for cmd in ["discover", "reconcile", "audit", "repair", "stage", "preview",
                "manifest", "approve", "submit", "status", "resume"]:
        p = sub.add_parser(cmd, help=f"{cmd} publishing package")
        if cmd == "discover":
            p.add_argument("package", nargs="?", help="Package path")
        else:
            p.add_argument("manifest_id", help="Manifest ID")
        if cmd == "submit":
            p.add_argument("--platform", default="kdp", help="Target platform")

    args = parser.parse_args()
    workflow_id = args.trace or f"ggb-pub-{uuid.uuid4().hex[:8]}"
    logger = setup_logger(workflow_id)

    engine = PublishEngine(logger=logger)

    cmd_map = {
        "discover": lambda: engine.discover(getattr(args, 'package', None), args.dry_run),
        "reconcile": lambda: engine.reconcile(args.manifest_id, args.dry_run),
        "audit": lambda: engine.audit(args.manifest_id, args.dry_run),
        "repair": lambda: engine.repair(args.manifest_id, args.dry_run),
        "stage": lambda: engine.stage(args.manifest_id, args.dry_run),
        "preview": lambda: engine.preview(args.manifest_id, args.dry_run),
        "manifest": lambda: engine.manifest(args.manifest_id),
        "approve": lambda: engine.approve(args.manifest_id, dry_run=args.dry_run),
        "submit": lambda: engine.submit(args.manifest_id, getattr(args, 'platform', 'kdp'), args.dry_run),
        "status": lambda: engine.get_status(args.manifest_id),
        "resume": lambda: engine.resume(args.manifest_id),
    }

    try:
        result = cmd_map[args.command]()
    except ValueError as e:
        if args.json:
            print(json.dumps({"error": str(e)}))
        else:
            print(f"ERROR: {e}")
        return 1
    except Exception as e:
        if args.json:
            print(json.dumps({"error": str(e)}))
        else:
            print(f"UNEXPECTED ERROR: {e}")
        return 1

    exit_code = 0
    if isinstance(result, dict):
        if result.get("error"):
            exit_code = 1
        elif "passed" in result and not result["passed"]:
            exit_code = 1
        elif "ready" in result and not result["ready"] and result.get("blockers"):
            exit_code = 1

    if args.json:
        print(json.dumps(result, indent=2, default=str))
    else:
        if isinstance(result, dict):
            if "report" in result:
                print(result["report"])
            elif "error" in result:
                print(f"ERROR: {result['error']}")
            else:
                for k, v in result.items():
                    if isinstance(v, list):
                        print(f"{k}: {len(v)} items")
                        for item in v[:3]:
                            print(f"  - {item}")
                    elif isinstance(v, dict):
                        print(f"{k}:")
                        for sk, sv in v.items():
                            print(f"  {sk}: {sv}")
                    else:
                        print(f"{k}: {v}")
        else:
            print(result)

    return exit_code


if __name__ == "__main__":
    sys.exit(cli())
