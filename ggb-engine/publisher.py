#!/usr/bin/env python3
"""
Gullah Geechee Biz — Publisher Control Plane.
Safe, evidence-backed, owner-controlled publishing coordination.

No production platform adapter ships in this build. PRODUCTION_ADAPTERS is empty,
so the default evidence gate refuses every advance past STAGED. That is the honest
state of the system: nothing here can reach a real storefront.
"""

import json, os, sys, time, hashlib, hmac, secrets, uuid, shutil, sqlite3, re, logging, copy, threading
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

def _publish_dir() -> Path:
    """Runtime state root. Overridable only under GGB_TEST_MODE so a test subprocess
    cannot be made to write into the repository tree."""
    if os.environ.get("GGB_TEST_MODE") == "1" and os.environ.get("GGB_TEST_PUBLISH_DIR"):
        return Path(os.environ["GGB_TEST_PUBLISH_DIR"])
    return REPO_ROOT / "publish"

PUBLISH_DIR = _publish_dir()
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

def test_mode_enabled() -> bool:
    return os.environ.get("GGB_TEST_MODE") == "1"

def approved_package_roots() -> List[Path]:
    """Where a package may be discovered from. Curated, operator-owned locations only."""
    roots = [
        Path.home() / "gullah-geechee-project" / "packaged",
        Path.home() / "gullah-geechee-project" / "how-to-test" / "packages",
        Path.home() / "gullah-geechee-project" / "pilot",
    ]
    if test_mode_enabled():
        extra = os.environ.get("GGB_TEST_PACKAGE_ROOT")
        roots.append(Path(extra) if extra else Path.home() / ".ggb-test")
    return roots

def approved_artifact_roots() -> List[Path]:
    """Where a file referenced by a manifest may live.

    A superset of the package roots, adding the engine's own repairs directory. Repair
    derivatives are written by this process and hash-recorded as they are written, so
    they are trustworthy in the same way a discovered package file is — but they are
    deliberately not a place packages get discovered *from*. Keeping the two lists apart
    is what stops "repair output must be stageable" from turning into "the engine's
    scratch directory is a package source".
    """
    return approved_package_roots() + [REPAIRS_DIR]

APPROVED_PACKAGE_ROOTS = approved_package_roots()

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

def check_protected_draft(canonical_id: str, platform: str = None, draft_id: str = None) -> Tuple[bool, str]:
    """Check if a draft is protected. Returns (allowed, message).
    For 'never_duplicate' rules: only the exact protected draft ID is permitted.
    None and any other draft ID are rejected.

    Protection is keyed on canonical_id alone. A protected title stays protected on
    every platform — routing the same title through a non-KDP adapter must not
    launder it past the rule."""
    for pd in PROTECTED_DRAFTS.values():
        if pd.canonical_id == canonical_id:
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

# Operation IDs that must carry bound platform evidence before the paired state.
EVIDENCE_OPERATION_FOR_STATE = {
    PublishState.PLATFORM_UPLOADED: "upload-manuscript",
    PublishState.PLATFORM_PROCESSED: "poll-processing",
    PublishState.PREVIEW_CLEAN: "preview",
    PublishState.AWAITING_OWNER_APPROVAL: "preview",
    PublishState.APPROVED: "preview",
    # SUBMITTED is gated on the submission's own evidence, not the preview's. Keying it
    # on "preview" meant a platform that rejected the submission still advanced the
    # manifest to submitted, because satisfying evidence from an earlier step existed.
    PublishState.SUBMITTED: "submit",
}

PLATFORM_EVIDENCE_REQUIRED = frozenset(EVIDENCE_OPERATION_FOR_STATE)

# Reaching any of these requires a gate token issued by PublishEngine._gate_token,
# which is only minted after evidence and on-disk hashes have been re-verified.
GATED_STATES = frozenset({
    PublishState.PLATFORM_UPLOADED, PublishState.PLATFORM_PROCESSED,
    PublishState.PREVIEW_CLEAN, PublishState.AWAITING_OWNER_APPROVAL,
    PublishState.APPROVED, PublishState.SUBMITTED,
})

# Reaching any of these re-derives every artifact hash and the package hash from disk.
HASH_REVALIDATION_STATES = frozenset({
    PublishState.PLATFORM_UPLOADED, PublishState.PLATFORM_PROCESSED,
    PublishState.PREVIEW_CLEAN, PublishState.AWAITING_OWNER_APPROVAL,
    PublishState.APPROVED, PublishState.SUBMITTED,
})

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


# ─── Evidence Binding ────────────────────────────────────────────────────────

EVIDENCE_MOCK = "mock"
EVIDENCE_ISOLATED_TEST = "isolated-test"
EVIDENCE_PRODUCTION = "production"
EVIDENCE_CLASSES = frozenset({EVIDENCE_MOCK, EVIDENCE_ISOLATED_TEST, EVIDENCE_PRODUCTION})

# Empty on purpose. No adapter in this repository talks to a real storefront, so no
# adapter identity is trusted to emit production-class evidence. The default gate
# below therefore refuses everything. Adding an identity here is the single change
# that would let this system reach a live platform — it must be a reviewed decision.
PRODUCTION_ADAPTERS: frozenset = frozenset()

DEFAULT_EVIDENCE_MAX_AGE_SECONDS = 3600

EVIDENCE_OUTCOME_SUCCESS = "success"
EVIDENCE_OUTCOME_FAILURE = "failure"


def operation_outcome(operation_id: str, data: dict, errors: List = None) -> Tuple[str, str]:
    """Did the platform operation actually work?

    A signature proves an authorised adapter said something. It does not prove the thing
    it said was good news. Without this, a failed upload produces evidence that satisfies
    a gate exactly as well as a successful one. Unknown operations fail closed: a new
    operation must declare its own success criterion before it can advance any state.
    """
    if errors:
        return EVIDENCE_OUTCOME_FAILURE, f"operation reported errors: {list(errors)}"
    data = data or {}
    if data.get("error"):
        return EVIDENCE_OUTCOME_FAILURE, f"operation reported an error: {data['error']}"

    if operation_id.startswith("upload-"):
        if not data.get("success"):
            return EVIDENCE_OUTCOME_FAILURE, "upload did not report success"
    elif operation_id == "poll-processing":
        status = data.get("status")
        if status != "processed":
            return EVIDENCE_OUTCOME_FAILURE, f"processing status is {status!r}, expected 'processed'"
    elif operation_id == "preview":
        preview, capture = data.get("preview") or {}, data.get("capture") or {}
        if not preview.get("opened"):
            return EVIDENCE_OUTCOME_FAILURE, "previewer did not open"
        if capture.get("errors"):
            return EVIDENCE_OUTCOME_FAILURE, f"preview capture reported errors: {capture['errors']}"
        if not capture.get("screenshots"):
            return EVIDENCE_OUTCOME_FAILURE, "preview produced no screenshots"
    elif operation_id == "submit":
        if not data.get("submitted"):
            return EVIDENCE_OUTCOME_FAILURE, "submission did not report success"
    else:
        return EVIDENCE_OUTCOME_FAILURE, f"unknown operation {operation_id!r} — no success criterion"

    return EVIDENCE_OUTCOME_SUCCESS, "operation succeeded"


@dataclass(frozen=True)
class RevisionFingerprint:
    """The exact revision an adapter observed. Evidence that does not carry a matching
    fingerprint proves nothing about the bytes currently on disk."""
    manifest_id: str
    canonical_id: str
    platform: str
    format: str
    draft_id: str
    manifest_hash: str
    package_hash: str
    manuscript_hash: str
    cover_hash: str
    kdp_draft_hash: str
    repair_revision: str
    adapter_identity: str

    def canonical_bytes(self) -> bytes:
        return json.dumps(asdict(self), sort_keys=True, separators=(",", ":")).encode()

    def digest(self) -> str:
        return hashlib.sha256(self.canonical_bytes()).hexdigest()

    def to_dict(self) -> dict:
        return asdict(self)


REQUIRED_BINDING_PROPERTIES = tuple(RevisionFingerprint.__dataclass_fields__.keys())


def repair_revision_of(manifest: dict) -> str:
    history = manifest.get("validation", {}).get("repair_history", [])
    return hashlib.sha256(
        json.dumps(history, sort_keys=True, separators=(",", ":"), default=str).encode()
    ).hexdigest()


def build_revision_fingerprint(manifest: dict, package_hash: str,
                               adapter_identity: str) -> RevisionFingerprint:
    files = manifest.get("files", {})
    return RevisionFingerprint(
        manifest_id=str(manifest.get("manifest_id", "")),
        canonical_id=str(resolve_canonical_id(manifest.get("title", {}).get("canonical", "")) or ""),
        platform=str(manifest.get("target_platform", "")),
        format=str(manifest.get("format", "")),
        draft_id=str(manifest.get("draft_id") or ""),
        manifest_hash=build_canonical_manifest_hash(manifest),
        package_hash=str(package_hash or ""),
        manuscript_hash=str(files.get("manuscript", {}).get("sha256", "")),
        cover_hash=str(files.get("cover", {}).get("sha256", "")),
        kdp_draft_hash=str(files.get("kdp_draft", {}).get("sha256", "")),
        repair_revision=repair_revision_of(manifest),
        adapter_identity=str(adapter_identity),
    )


class EvidenceKeyring:
    """Per-adapter HMAC keys. Only a registered adapter can produce evidence that
    verifies, so a hand-written row in platform_evidence cannot satisfy a gate."""

    def __init__(self):
        self._keys: Dict[str, bytes] = {}

    def register(self, adapter_identity: str, key: bytes = None) -> bytes:
        key = key or secrets.token_bytes(32)
        self._keys[adapter_identity] = key
        return key

    def is_registered(self, adapter_identity: str) -> bool:
        return adapter_identity in self._keys

    def sign(self, adapter_identity: str, payload: bytes) -> str:
        key = self._keys.get(adapter_identity)
        if key is None:
            raise KeyError(f"Adapter '{adapter_identity}' has no evidence signing key")
        return hmac.new(key, payload, hashlib.sha256).hexdigest()

    def verify(self, adapter_identity: str, payload: bytes, signature: str) -> bool:
        try:
            expected = self.sign(adapter_identity, payload)
        except KeyError:
            return False
        return hmac.compare_digest(expected, signature or "")


@dataclass(frozen=True)
class EvidenceGate:
    """Which evidence a state advance will accept. Defaults refuse everything."""
    accepted_classes: frozenset = frozenset()
    accepted_adapters: frozenset = frozenset()
    max_age_seconds: int = DEFAULT_EVIDENCE_MAX_AGE_SECONDS

    @staticmethod
    def production() -> "EvidenceGate":
        return EvidenceGate(
            accepted_classes=frozenset({EVIDENCE_PRODUCTION}),
            accepted_adapters=PRODUCTION_ADAPTERS,
        )

    def describe(self) -> str:
        if not self.accepted_adapters:
            return ("no adapter is authorised to satisfy this gate "
                    "(PRODUCTION_ADAPTERS is empty — this build ships no production adapter)")
        return (f"classes={sorted(self.accepted_classes)} "
                f"adapters={sorted(self.accepted_adapters)} "
                f"max_age={self.max_age_seconds}s")


def evidence_satisfies(row: dict, fingerprint: RevisionFingerprint, gate: EvidenceGate,
                       keyring: EvidenceKeyring, now: float = None) -> Tuple[bool, str]:
    """Every one of the twelve binding properties must match, the evidence must be
    fresh, and the signature must verify under the emitting adapter's key."""
    now = now if now is not None else time.time()

    if row.get("evidence_class") not in gate.accepted_classes:
        return False, f"evidence class '{row.get('evidence_class')}' not accepted by gate"
    if row.get("adapter_type") not in gate.accepted_adapters:
        return False, f"adapter '{row.get('adapter_type')}' not accepted by gate"

    binding = row.get("binding") or {}
    missing = [p for p in REQUIRED_BINDING_PROPERTIES if not binding.get(p)]
    expected = fingerprint.to_dict()
    # kdp_draft_hash and draft_id are legitimately empty for packages without them.
    optional_empty = {"kdp_draft_hash", "draft_id", "canonical_id"}
    missing = [p for p in missing if p not in optional_empty]
    if missing:
        return False, f"evidence binding is missing required properties: {missing}"

    mismatched = [p for p in REQUIRED_BINDING_PROPERTIES if str(binding.get(p, "")) != str(expected[p])]
    if mismatched:
        return False, f"evidence was produced for a different revision (mismatched: {mismatched})"

    if row.get("adapter_type") != binding.get("adapter_identity"):
        return False, "evidence adapter identity does not match its binding"

    # The outcome is inside the signed payload, so a failed operation cannot be
    # relabelled as a successful one without invalidating the signature.
    if row.get("outcome") != EVIDENCE_OUTCOME_SUCCESS:
        return False, (f"operation did not succeed (outcome={row.get('outcome')!r}): "
                       f"{row.get('outcome_reason') or 'no reason recorded'}")

    try:
        ts = datetime.fromisoformat(row.get("timestamp", "")).timestamp()
    except (TypeError, ValueError):
        return False, "evidence timestamp is unreadable"
    age = now - ts
    if age > gate.max_age_seconds:
        return False, f"evidence is stale ({int(age)}s old, max {gate.max_age_seconds}s)"
    if age < -60:
        return False, "evidence timestamp is in the future"

    if not keyring.verify(row.get("adapter_type"),
                          evidence_payload(binding, row.get("operation_id"),
                                           row.get("evidence_class"), row.get("timestamp"),
                                           row.get("outcome")),
                          row.get("signature")):
        return False, "evidence signature does not verify"

    return True, "evidence bound to current revision and attesting success"


def evidence_payload(binding: dict, operation_id: str, evidence_class: str,
                     timestamp: str, outcome: str) -> bytes:
    return json.dumps(
        {"binding": binding, "operation_id": operation_id,
         "evidence_class": evidence_class, "timestamp": timestamp, "outcome": outcome},
        sort_keys=True, separators=(",", ":")).encode()


def sign_evidence(keyring: EvidenceKeyring, adapter_identity: str, operation_id: str,
                  evidence_class: str, fingerprint: RevisionFingerprint,
                  timestamp: str, outcome: str) -> Tuple[dict, str]:
    binding = fingerprint.to_dict()
    payload = evidence_payload(binding, operation_id, evidence_class, timestamp, outcome)
    return binding, keyring.sign(adapter_identity, payload)


# ─── Gate Authority ──────────────────────────────────────────────────────────

class GateAuthority:
    """Mints single-use tokens for gated transitions.

    A token only exists if PublishEngine._gate_token re-verified evidence and on-disk
    hashes first, so StateStore.transition can refuse any advance that did not come
    through those checks. This closes the raw-transition bypass; it is not a defence
    against code running inside the same process, which by construction holds the key."""

    TOKEN_TTL_SECONDS = 300
    MAX_OUTSTANDING = 1024

    def __init__(self):
        self._outstanding: Dict[str, Tuple[str, str, float]] = {}
        self._lock = threading.Lock()

    def _sweep_locked(self, now: float) -> None:
        """Unredeemed tokens are the normal case — every refused transition leaves one
        behind — so they have to be reclaimed or a long-lived process grows without
        bound. Expired tokens are already unusable; dropping them changes nothing."""
        expired = [t for t, (_, _, issued) in self._outstanding.items()
                   if now - issued > self.TOKEN_TTL_SECONDS]
        for token in expired:
            del self._outstanding[token]
        if len(self._outstanding) > self.MAX_OUTSTANDING:
            for token, _ in sorted(self._outstanding.items(), key=lambda kv: kv[1][2]
                                   )[:len(self._outstanding) - self.MAX_OUTSTANDING]:
                del self._outstanding[token]

    def outstanding_count(self) -> int:
        with self._lock:
            return len(self._outstanding)

    def issue(self, manifest_id: str, to_state: PublishState) -> str:
        token = secrets.token_hex(32)
        now = time.time()
        with self._lock:
            self._sweep_locked(now)
            self._outstanding[token] = (manifest_id, to_state.value, now)
        return token

    def redeem(self, token: str, manifest_id: str, to_state: PublishState) -> Tuple[bool, str]:
        with self._lock:
            entry = self._outstanding.pop(token, None) if token else None
        if entry is None:
            return False, (f"transition to '{to_state.value}' requires a gate token; "
                           "call the PublishEngine method instead of StateStore.transition")
        issued_for, issued_state, issued_at = entry
        if issued_for != manifest_id or issued_state != to_state.value:
            return False, "gate token was issued for a different manifest or state"
        if time.time() - issued_at > self.TOKEN_TTL_SECONDS:
            return False, "gate token expired"
        return True, "gate token redeemed"


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

    SCHEMA_VERSION = 4

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
        3: """
            -- Bind evidence to the exact revision an adapter observed
            ALTER TABLE platform_evidence ADD COLUMN evidence_class TEXT NOT NULL DEFAULT 'mock';
            ALTER TABLE platform_evidence ADD COLUMN binding TEXT;
            ALTER TABLE platform_evidence ADD COLUMN signature TEXT;
            CREATE INDEX IF NOT EXISTS idx_evidence_lookup
                ON platform_evidence(manifest_id, operation_id);
        """,
        4: """
            -- Evidence must attest that the operation succeeded, not merely that it ran.
            -- Existing rows default to 'failure': a row written before outcomes were
            -- recorded cannot prove success, so it must not advance anything.
            ALTER TABLE platform_evidence ADD COLUMN outcome TEXT NOT NULL DEFAULT 'failure';
            ALTER TABLE platform_evidence ADD COLUMN outcome_reason TEXT;
        """,
    }

    def __init__(self, db_path: Path = None, gate_authority: "GateAuthority" = None,
                 keyring: EvidenceKeyring = None):
        self.db_path = db_path or DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self.gate_authority = gate_authority or GateAuthority()
        self.keyring = keyring or EvidenceKeyring()
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
                   actor: str = "system", evidence: str = None, idempotency_key: str = None,
                   gate_token: str = None) -> Tuple[bool, str]:
        """THE ONLY state mutation interface. Returns (success, message).

        Advancing into a GATED_STATES member requires a token from GateAuthority, which
        PublishEngine only mints after re-verifying evidence and on-disk hashes."""
        if to_state in GATED_STATES:
            ok, why = self.gate_authority.redeem(gate_token, manifest_id, to_state)
            if not ok:
                return (False, why)

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
            timestamp = evidence.get("timestamp") or datetime.now(timezone.utc).isoformat()
            conn.execute("""
                INSERT INTO platform_evidence (manifest_id, adapter_type, is_mock, platform, draft_id,
                                               operation_id, timestamp, evidence_data, errors, warnings,
                                               evidence_class, binding, signature, outcome, outcome_reason)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (manifest_id, evidence.get("adapter_type", "unknown"),
                  1 if evidence.get("evidence_class", EVIDENCE_MOCK) == EVIDENCE_MOCK else 0,
                  evidence.get("platform", "unknown"),
                  evidence.get("draft_id", ""), evidence.get("operation_id", ""),
                  timestamp, json.dumps(evidence.get("data", {}), default=str),
                  json.dumps(evidence.get("errors", [])),
                  json.dumps(evidence.get("warnings", [])),
                  evidence.get("evidence_class", EVIDENCE_MOCK),
                  json.dumps(evidence.get("binding") or {}, sort_keys=True),
                  evidence.get("signature", ""),
                  evidence.get("outcome", EVIDENCE_OUTCOME_FAILURE),
                  evidence.get("outcome_reason", "")))
        self.atomic(_save)

    _EVIDENCE_COLUMNS = ("adapter_type, is_mock, platform, draft_id, operation_id, timestamp, "
                         "evidence_data, errors, warnings, evidence_class, binding, signature, "
                         "outcome, outcome_reason")

    @staticmethod
    def _evidence_row(r) -> dict:
        return {"adapter_type": r[0], "is_mock": bool(r[1]), "platform": r[2],
                "draft_id": r[3], "operation_id": r[4], "timestamp": r[5],
                "data": json.loads(r[6]), "errors": json.loads(r[7]),
                "warnings": json.loads(r[8]), "evidence_class": r[9],
                "binding": json.loads(r[10] or "{}"), "signature": r[11],
                "outcome": r[12], "outcome_reason": r[13]}

    def get_platform_evidence(self, manifest_id: str, operation_id: str = None) -> List[dict]:
        def _get(conn):
            if operation_id is None:
                rows = conn.execute(
                    f"SELECT {self._EVIDENCE_COLUMNS} FROM platform_evidence WHERE manifest_id=? ORDER BY id",
                    (manifest_id,)).fetchall()
            else:
                rows = conn.execute(
                    f"SELECT {self._EVIDENCE_COLUMNS} FROM platform_evidence "
                    "WHERE manifest_id=? AND operation_id=? ORDER BY id DESC",
                    (manifest_id, operation_id)).fetchall()
            return [self._evidence_row(r) for r in rows]
        return self.atomic(_get)

    def has_bound_evidence(self, manifest_id: str, operation_id: str,
                           fingerprint: RevisionFingerprint,
                           gate: EvidenceGate) -> Tuple[bool, str]:
        """True only if some stored evidence for this operation is bound to the exact
        revision described by `fingerprint`, is fresh, and verifies under the keyring."""
        rows = self.get_platform_evidence(manifest_id, operation_id)
        if not rows:
            return False, f"no platform evidence recorded for operation '{operation_id}'"
        reasons = []
        for row in rows:
            ok, why = evidence_satisfies(row, fingerprint, gate, self.keyring)
            if ok:
                return True, why
            reasons.append(why)
        return False, f"operation '{operation_id}': {reasons[0]}"

    def has_forced_state(self, manifest_id: str) -> bool:
        def _check(conn):
            row = conn.execute(
                "SELECT COUNT(*) FROM audit_log WHERE manifest_id=? AND action='force_state'",
                (manifest_id,)).fetchone()
            return bool(row and row[0] > 0)
        return self.atomic(_check)

    def get_package_hash(self, manifest_id: str) -> Optional[str]:
        def _get(conn):
            row = conn.execute("SELECT package_hash FROM manifests WHERE manifest_id=?",
                               (manifest_id,)).fetchone()
            return row[0] if row else None
        return self.atomic(_get)

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


class MigrationRepairStore(StateStore):
    """Out-of-band state repair for migrations and incident recovery.

    Replaces the old private StateStore._set_state, which let any caller move a manifest
    to any state silently. Forcing a state is loud: it lands in the audit log as
    'force_state' and permanently marks the manifest as not-ready, so a forced manifest
    can never report READY TO SUBMIT."""

    def force_state(self, manifest_id: str, state: str, actor: str, reason: str) -> Tuple[bool, str]:
        if not reason:
            return (False, "force_state requires a reason")
        valid = {s.value for s in PublishState}
        if state not in valid:
            return (False, f"Unknown state: {state}")

        def _force(conn):
            now = datetime.now(timezone.utc).isoformat()
            row = conn.execute("SELECT state FROM manifests WHERE manifest_id=?",
                               (manifest_id,)).fetchone()
            if not row:
                return (False, f"Manifest not found: {manifest_id}")
            conn.execute("UPDATE manifests SET state=?, updated_at=? WHERE manifest_id=?",
                         (state, now, manifest_id))
            conn.execute("""
                INSERT INTO audit_log (manifest_id, timestamp, actor, action, from_state, to_state, evidence, idempotency_key)
                VALUES (?, ?, ?, 'force_state', ?, ?, ?, '')
            """, (manifest_id, now, actor, row[0], state, reason))
            return (True, f"Forced '{row[0]}' -> '{state}' (audited, manifest is now permanently not-ready)")
        return self.atomic(_force)


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
    """Signature-first MIME detection.

    Deliberately does not use libmagic: its answers vary by installed magic database,
    so the same package could validate on one machine and fail on another. Reading the
    signature ourselves gives one answer everywhere."""
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
    evidence_class = EVIDENCE_MOCK

    def __init__(self, name: str, logger=None):
        self.name = name
        self.logger = logger or setup_logger()
        self.keyring: Optional[EvidenceKeyring] = None

    def bind_keyring(self, keyring: EvidenceKeyring) -> "PlatformAdapter":
        """Register this adapter's signing key. Evidence it emits afterwards verifies;
        rows written by anything else do not."""
        self.keyring = keyring
        if not keyring.is_registered(self.name):
            keyring.register(self.name)
        return self

    def is_mock(self) -> bool:
        return self.evidence_class == EVIDENCE_MOCK

    def emit_evidence(self, operation_id: str, fingerprint: RevisionFingerprint,
                      data: Dict, errors: List = None, warnings: List = None) -> Dict:
        if self.keyring is None:
            raise RuntimeError(f"Adapter '{self.name}' cannot emit evidence before bind_keyring()")
        if fingerprint.adapter_identity != self.name:
            raise ValueError("Refusing to sign a fingerprint bound to a different adapter")
        timestamp = datetime.now(timezone.utc).isoformat()
        outcome, outcome_reason = operation_outcome(operation_id, data, errors)
        binding, signature = sign_evidence(self.keyring, self.name, operation_id,
                                           self.evidence_class, fingerprint, timestamp, outcome)
        return {
            "adapter_type": self.name,
            "evidence_class": self.evidence_class,
            "platform": fingerprint.platform,
            "draft_id": fingerprint.draft_id,
            "operation_id": operation_id,
            "timestamp": timestamp,
            "binding": binding,
            "signature": signature,
            "outcome": outcome,
            "outcome_reason": outcome_reason,
            "data": data,
            "errors": errors or [],
            "warnings": warnings or [],
        }

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
    """Mock KDP adapter. Emits mock-class evidence, which no gate in this build accepts."""

    evidence_class = EVIDENCE_MOCK

    def __init__(self, logger=None):
        super().__init__("kdp-mock", logger)

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


class IsolatedTestAdapter(MockKDPAdapter):
    """A real adapter that runs entirely against local state and emits isolated-test
    evidence. Tests use it to exercise the happy path end to end without forging rows
    and without any network. It can never satisfy the production gate, because its
    identity is not in PRODUCTION_ADAPTERS."""

    evidence_class = EVIDENCE_ISOLATED_TEST

    def __init__(self, logger=None):
        PlatformAdapter.__init__(self, "kdp-isolated-test", logger)

    @staticmethod
    def gate(max_age_seconds: int = DEFAULT_EVIDENCE_MAX_AGE_SECONDS) -> EvidenceGate:
        return EvidenceGate(
            accepted_classes=frozenset({EVIDENCE_ISOLATED_TEST}),
            accepted_adapters=frozenset({"kdp-isolated-test"}),
            max_age_seconds=max_age_seconds,
        )


# ─── Publishing Engine ───────────────────────────────────────────────────────

class PublishEngine:
    """Core publishing engine. State machine is the ONLY state mutation interface."""

    def __init__(self, db: StateStore = None, logger=None, adapter: PlatformAdapter = None,
                 evidence_gate: EvidenceGate = None):
        self.db = db or StateStore()
        self.logger = logger or setup_logger()
        self.adapter = (adapter or MockKDPAdapter(self.logger)).bind_keyring(self.db.keyring)
        # Default gate refuses everything: PRODUCTION_ADAPTERS is empty.
        self.evidence_gate = evidence_gate or EvidenceGate.production()

    def _require_valid_manifest_id(self, mid: str):
        if not validate_manifest_id(mid):
            raise ValueError(f"Invalid manifest ID: {mid}")

    @staticmethod
    def _under_any(path: Path, roots: List[Path]) -> bool:
        resolved = path.resolve()
        for root in roots:
            try:
                resolved.relative_to(root.resolve())
                return True
            except ValueError:
                continue
        return False

    def _is_approved_root(self, path: Path) -> bool:
        """Somewhere a manifest artifact is allowed to live — includes repair output."""
        return self._under_any(path, approved_artifact_roots())

    def _is_package_root(self, path: Path) -> bool:
        """Somewhere a package may be discovered from — excludes repair output."""
        return self._under_any(path, approved_package_roots())

    # ─── Re-verification ─────────────────────────────────────────────────────

    def _verify_artifacts(self, manifest: dict) -> List[str]:
        """Re-derive every artifact hash from disk. A manifest that agrees with itself
        proves nothing; only the bytes on disk do."""
        problems = []
        for key, finfo in sorted(manifest.get("files", {}).items()):
            path = Path(finfo.get("path", ""))
            if not path.exists():
                problems.append(f"Artifact '{key}' is missing from disk: {path}")
                continue
            if path.is_symlink():
                problems.append(f"Artifact '{key}' is a symlink: {path}")
                continue
            # Discovery records resolved paths and follows symlinks, so an out-of-root
            # file can be smuggled into a package. Staging catches it, but verification
            # runs earlier and on more paths — it should not be the only chokepoint.
            if not self._is_approved_root(path):
                problems.append(f"Artifact '{key}' is not under an approved root: {path}")
                continue
            actual = hash_file(path)
            if actual != finfo.get("sha256"):
                problems.append(f"Artifact '{key}' changed on disk since it was recorded "
                                f"(expected {finfo.get('sha256', '')[:12]}, found {actual[:12]})")
            actual_size = path.stat().st_size
            if finfo.get("size") is not None and actual_size != finfo["size"]:
                problems.append(f"Artifact '{key}' size changed "
                                f"(expected {finfo['size']}, found {actual_size})")
        return problems

    def _verify_package(self, manifest_id: str, manifest: dict) -> List[str]:
        """Re-derive the whole-package hash. Catches added, removed and edited files that
        an artifact-by-artifact walk would miss."""
        recorded = self.db.get_package_hash(manifest_id)
        if not recorded:
            return ["No package hash recorded for this manifest — cannot prove it is unchanged"]
        pkg = Path(manifest.get("source_package", {}).get("path", ""))
        if not pkg.is_dir():
            return [f"Source package directory is missing: {pkg}"]
        if not self._is_package_root(pkg):
            return [f"Source package is no longer under an approved root: {pkg}"]
        actual = self._hash_package(pkg)
        if actual != recorded:
            return [f"Source package changed on disk since discovery "
                    f"(expected {recorded[:12]}, found {actual[:12]})"]
        return []

    def _verify_kdp_draft(self, manifest: dict) -> List[str]:
        """Re-parse KDP-DRAFT.md and compare the fields it controls. The draft file sets
        price, DRM, Select, draft ID, categories and AI disclosure — editing it after
        discovery must invalidate the manifest, not slip through."""
        finfo = manifest.get("files", {}).get("kdp_draft")
        if not finfo:
            return []
        path = Path(finfo.get("path", ""))
        if not path.exists():
            return [f"KDP-DRAFT.md is missing from disk: {path}"]
        fresh = copy.deepcopy(manifest)
        self._parse_kdp_draft(path, fresh)
        problems = []
        for label, getter in (
            ("title", lambda m: m.get("title", {}).get("canonical")),
            ("author", lambda m: m.get("author")),
            ("publisher", lambda m: m.get("publisher")),
            ("language", lambda m: m.get("language")),
            ("draft_id", lambda m: m.get("draft_id")),
            ("price", lambda m: m.get("publishing", {}).get("price")),
            ("drm", lambda m: m.get("publishing", {}).get("drm")),
            ("kdp_select", lambda m: m.get("publishing", {}).get("kdp_select")),
            ("categories", lambda m: m.get("metadata", {}).get("categories")),
            ("keywords", lambda m: m.get("metadata", {}).get("keywords")),
            ("ai_disclosure", lambda m: m.get("metadata", {}).get("ai_disclosure")),
        ):
            if getter(fresh) != getter(manifest):
                problems.append(f"KDP-DRAFT.md '{label}' drifted from the manifest "
                                f"(manifest={getter(manifest)!r}, file={getter(fresh)!r})")
        return problems

    def _verify_staged(self, manifest: dict) -> List[str]:
        """Re-derive the hash of every staged copy. These are the bytes that actually get
        uploaded, so staging's copy-time hash check is only worth something if the copy is
        re-checked at use time as well."""
        problems = []
        for key, finfo in sorted(manifest.get("files", {}).items()):
            staged = finfo.get("staged_path")
            if not staged:
                continue
            path = Path(staged)
            if path.is_symlink():
                problems.append(f"Staged copy of '{key}' is a symlink: {path}")
                continue
            if not path.is_file():
                problems.append(f"Staged copy of '{key}' is missing: {path}")
                continue
            actual = hash_file(path)
            if actual != finfo.get("sha256"):
                problems.append(f"Staged copy of '{key}' changed since staging "
                                f"(expected {finfo.get('sha256', '')[:12]}, found {actual[:12]})")
        return problems

    def _upload_source(self, manifest: dict, key: str) -> Tuple[Optional[str], Optional[str]]:
        """The staged, hash-verified copy — never the live package file. Uploading the
        original would mean the staging integrity check validated a copy nobody sends."""
        finfo = manifest.get("files", {}).get(key)
        if not finfo:
            return None, None
        staged = finfo.get("staged_path")
        if not staged:
            return None, f"Artifact '{key}' has no staged copy — re-run stage before preview"
        return staged, None

    def _resolve_draft_id(self, manifest_id: str,
                          manifest: dict) -> Tuple[Optional[str], Optional[str]]:
        """Settle which storefront object this revision is about, and persist it.

        The fingerprint binds manifest['draft_id']. If the adapter resolves a different
        draft and the manifest is left alone, every signed row attests to one object
        while the adapter operates on another — and submit() would later fire at the
        stale one. Persisting before fingerprinting makes evidence, preview and
        submission concern the same draft by construction. A declared ID that disagrees
        with the resolved one is a conflict the engine must not silently pick a side in.
        """
        declared = manifest.get("draft_id")
        draft = self.adapter.find_existing_draft(manifest.get("title", {}).get("canonical", ""))
        resolved = (draft or {}).get("draft_id") or declared
        if not resolved:
            return None, "Adapter resolved no draft and the manifest declares none"
        if declared and resolved != declared:
            return None, (f"Draft mismatch: manifest declares {declared!r} but the platform "
                          f"resolved {resolved!r} — re-discover before publishing")
        if manifest.get("draft_id") != resolved:
            manifest["draft_id"] = resolved
            self.db.save_manifest(manifest_id, manifest)
        return resolved, None

    def _revision_fingerprint(self, manifest_id: str, manifest: dict) -> RevisionFingerprint:
        return build_revision_fingerprint(
            manifest, self.db.get_package_hash(manifest_id) or "", self.adapter.name)

    def _preflight(self, manifest_id: str, manifest: dict,
                   to_state: PublishState) -> List[str]:
        """Everything that must hold before an adapter is allowed to touch the platform.

        Split out of _gate_token deliberately. The token cannot be minted until evidence
        exists, but evidence only exists after the adapter has acted — so if the disk
        checks lived only in _gate_token they would always run *after* the irreversible
        call. Callers run this first, then act, then advance."""
        problems: List[str] = []
        if to_state in HASH_REVALIDATION_STATES:
            problems += self._verify_artifacts(manifest)
            problems += self._verify_package(manifest_id, manifest)
            problems += self._verify_kdp_draft(manifest)
            problems += self._verify_staged(manifest)
        if self.db.has_forced_state(manifest_id):
            problems.append("Manifest state was forced out of band — re-discover before publishing")
        return problems

    def _gate_token(self, manifest_id: str, manifest: dict,
                    to_state: PublishState) -> Tuple[Optional[str], List[str]]:
        """Mint a transition token, but only after re-verifying everything that state
        depends on. No token means no advance."""
        problems = self._preflight(manifest_id, manifest, to_state)

        if to_state in PLATFORM_EVIDENCE_REQUIRED:
            operation = EVIDENCE_OPERATION_FOR_STATE[to_state]
            fingerprint = self._revision_fingerprint(manifest_id, manifest)
            ok, why = self.db.has_bound_evidence(manifest_id, operation, fingerprint,
                                                 self.evidence_gate)
            if not ok:
                problems.append(f"{why} [gate: {self.evidence_gate.describe()}]")

        if problems:
            return None, problems
        return self.db.gate_authority.issue(manifest_id, to_state), []

    def _advance(self, manifest_id: str, manifest: dict, from_state: PublishState,
                 to_state: PublishState, actor: str, evidence: str = None) -> Tuple[bool, str]:
        token, problems = self._gate_token(manifest_id, manifest, to_state)
        if token is None:
            return False, "; ".join(problems)
        return self.db.transition(manifest_id, from_state, to_state, actor=actor,
                                  evidence=evidence, gate_token=token)

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
            if not self._is_package_root(pkg):
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
                # Path relative to the package root, not the basename: hashing basenames
                # lets two files swap between subdirectories without changing the digest.
                h.update(f.relative_to(pkg).as_posix().encode())
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

        # KDP-DRAFT.md is hashed like any other artifact. It dictates price, DRM, Select,
        # draft ID and AI disclosure, so leaving it out of the walk would let those change
        # without changing the approval hash.
        for f in sorted(pkg.iterdir()):
            if f.is_file():
                key = self._classify_file(f)
                if key:
                    manifest["files"][key] = {
                        "path": str(f.resolve()),
                        "sha256": hash_file(f),
                        "size": f.stat().st_size,
                        "mime_type": detect_mime(f),
                    }

        draft_file = pkg / "KDP-DRAFT.md"
        if draft_file.exists():
            self._parse_kdp_draft(draft_file, manifest)

        return manifest

    def _classify_file(self, path: Path) -> Optional[str]:
        name = path.name.lower()
        if name == "kdp-draft.md":
            return "kdp_draft"
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

    @staticmethod
    def _split_list(value: str) -> List[str]:
        return [part.strip() for part in re.split(r"[;,]", value) if part.strip()]

    def _parse_kdp_draft(self, path: Path, manifest: dict):
        """Parse every consequential field the draft file carries.

        Fields silently ignored here are fields an owner can change on disk without the
        manifest noticing, so this list must stay in step with _verify_kdp_draft."""
        ai = manifest.setdefault("metadata", {}).setdefault(
            "ai_disclosure", {"text": False, "cover": False, "interior_images": False, "translation": False})
        ai_fields = {
            "ai-generated text": "text",
            "ai text": "text",
            "ai-generated cover": "cover",
            "ai cover": "cover",
            "ai-generated interior images": "interior_images",
            "ai interior images": "interior_images",
            "ai-assisted translation": "translation",
            "ai translation": "translation",
        }

        for raw in path.read_text().split("\n"):
            line = raw.strip()
            if not line.startswith("- **") or ":**" not in line:
                if (manifest["metadata"].get("description", "") == "" and line
                        and not line.startswith("-") and not line.startswith("#")):
                    manifest["metadata"]["description"] = line
                continue

            label = line[4:line.index(":**")].strip()
            value = line.split(":**", 1)[1].strip()
            key = label.lower()

            if key == "title":
                manifest["title"]["canonical"] = value
            elif key == "subtitle":
                manifest["title"]["subtitle"] = value
            elif key == "author":
                manifest["author"] = value
            elif key == "publisher":
                manifest["publisher"] = value
            elif key == "language":
                manifest["language"] = value
            elif key in ("draft id", "draft_id", "kdp draft id"):
                manifest["draft_id"] = None if value.lower() in ("", "none", "null", "new") else value
            elif key in ("ebook price", "price", "list price"):
                try:
                    manifest["publishing"]["price"] = float(value.lstrip("$").replace(",", ""))
                except ValueError:
                    pass
            elif key == "drm":
                manifest["publishing"]["drm"] = DRM_PARSE.get(value, DRM.NO).value
            elif key in ("kdp select", "select"):
                manifest["publishing"]["kdp_select"] = SELECT_PARSE.get(value, KDPSelect.OFF).value
            elif key in ("categories", "category"):
                manifest["metadata"]["categories"] = self._split_list(value)
            elif key in ("keywords", "keyword"):
                manifest["metadata"]["keywords"] = self._split_list(value)
            elif key == "description":
                manifest["metadata"]["description"] = value
            elif key in ai_fields:
                ai[ai_fields[key]] = DRM_PARSE.get(value, DRM.NO) is DRM.YES

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

        # Hash verification — artifacts, whole package, and the draft file's own fields
        errors.extend(self._verify_artifacts(manifest))
        errors.extend(self._verify_package(manifest_id, manifest))
        errors.extend(self._verify_kdp_draft(manifest))

        # Queue checks
        active = self.db.get_active_submission()
        if active and active != manifest_id:
            errors.append(f"Another title is in active submission: {active}")

        passed = len(errors) == 0
        result = {"passed": passed, "errors": errors, "warnings": warnings, "schema_errors": schema_errors}

        history = manifest.get("validation", {}).get("repair_history", [])
        manifest["validation"] = dict(result, repair_history=history,
                                      status="passed" if passed else "failed")
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
                        manifest["files"]["cover"]["size"] = derivative.stat().st_size
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
        if stage_dir.exists():
            return {"error": f"Staging directory already exists: {stage_dir}"}

        # Staging is all-or-nothing. A half-populated staging directory previously
        # survived the failure and then collided with every retry, wedging the manifest.
        # mkdir is inside the try so a failure part-way through it is rolled back too.
        staged = []
        created = False
        try:
            stage_dir.mkdir(parents=True, exist_ok=False)
            created = True
            for key, finfo in sorted(manifest.get("files", {}).items()):
                src = Path(finfo["path"])
                safe_src = self._safe_stage_path(src)

                dst = stage_dir / src.name
                if dst.exists():
                    raise ValueError(f"Destination collision: {dst}")

                shutil.copy2(safe_src, dst)
                if hash_file(dst) != finfo["sha256"]:
                    raise ValueError(f"Hash mismatch after staging for {key}")

                # The staged copy is what gets uploaded. Recording it here is what makes
                # the copy-time hash check load-bearing instead of decorative; the source
                # path stays in "path" so verification keeps watching the live package.
                finfo["staged_path"] = str(dst)
                staged.append(str(dst))

            success, msg = self.db.transition(manifest_id, current_state, PublishState.STAGED,
                                              actor="stage")
            if not success:
                raise ValueError(msg)
            self.db.save_manifest(manifest_id, manifest)
        except FileExistsError as e:
            return {"error": f"Staging directory already exists: {stage_dir} ({e})"}
        except (ValueError, OSError) as e:
            if created:
                shutil.rmtree(stage_dir, ignore_errors=True)
            return {"error": str(e)}

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

        # Nothing may reach the adapter until on-disk state has been re-verified. This
        # runs before check_auth, before draft resolution and before any upload, so a
        # tampered package produces exactly zero adapter calls.
        problems = self._preflight(manifest_id, manifest, PublishState.PLATFORM_UPLOADED)
        if problems:
            return {"error": "; ".join(problems)}

        auth = self.adapter.check_auth()
        if not auth.get("authenticated"):
            return {"error": "Adapter not authenticated"}

        draft_id, err = self._resolve_draft_id(manifest_id, manifest)
        if err:
            return {"error": err}

        cid = resolve_canonical_id(manifest.get("title", {}).get("canonical", ""))
        if cid:
            allowed, msg = check_protected_draft(cid, manifest.get("target_platform"), draft_id)
            if not allowed:
                return {"error": msg}

        # Every piece of evidence is signed against this exact revision, including the
        # resolved draft ID persisted just above. If anything on disk moves after this
        # point, the fingerprint stops matching and the gates close.
        fingerprint = self._revision_fingerprint(manifest_id, manifest)

        for key in ["manuscript", "cover"]:
            if not manifest.get("files", {}).get(key):
                continue
            source, err = self._upload_source(manifest, key)
            if err:
                return {"error": err}
            upload_result = self.adapter.upload_artifact(draft_id, key, source)
            self.db.save_platform_evidence(manifest_id, self.adapter.emit_evidence(
                f"upload-{key}", fingerprint, upload_result,
                errors=[upload_result["error"]] if upload_result.get("error") else []))

        success, msg = self._advance(manifest_id, manifest, current_state,
                                     PublishState.PLATFORM_UPLOADED, actor="preview")
        if not success:
            return {"error": msg, "evidence_recorded": True,
                    "note": "Evidence was stored but did not satisfy the gate; state unchanged."}
        current_state = PublishState.PLATFORM_UPLOADED

        problems = self._preflight(manifest_id, manifest, PublishState.PLATFORM_PROCESSED)
        if problems:
            return {"error": "; ".join(problems)}
        processing = self.adapter.poll_processing(draft_id)
        self.db.save_platform_evidence(manifest_id, self.adapter.emit_evidence(
            "poll-processing", fingerprint, processing,
            errors=processing.get("errors", []), warnings=processing.get("warnings", [])))

        success, msg = self._advance(manifest_id, manifest, current_state,
                                     PublishState.PLATFORM_PROCESSED, actor="preview")
        if not success:
            return {"error": msg}
        current_state = PublishState.PLATFORM_PROCESSED

        problems = self._preflight(manifest_id, manifest, PublishState.PREVIEW_CLEAN)
        if problems:
            return {"error": "; ".join(problems)}
        preview_result = self.adapter.launch_previewer(draft_id)
        capture = self.adapter.capture_preview_evidence(draft_id)
        self.db.save_platform_evidence(manifest_id, self.adapter.emit_evidence(
            "preview", fingerprint, {"preview": preview_result, "capture": capture},
            errors=capture.get("errors", []), warnings=capture.get("warnings", [])))

        success, msg = self._advance(manifest_id, manifest, current_state,
                                     PublishState.PREVIEW_CLEAN, actor="preview")
        if not success:
            return {"error": msg}

        success, msg = self._advance(manifest_id, manifest, PublishState.PREVIEW_CLEAN,
                                     PublishState.AWAITING_OWNER_APPROVAL, actor="preview")
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

        active = self.db.get_active_submission()
        if active and active != manifest_id:
            return {"error": f"Another title is in active submission: {active}"}

        # _advance re-derives every artifact hash, the package hash and the KDP draft
        # fields from disk, and re-checks that the preview evidence is still bound to
        # this revision. Approval must describe the bytes that exist right now.
        approval_hash = build_canonical_manifest_hash(manifest)

        success, msg = self._advance(manifest_id, manifest, state, PublishState.APPROVED,
                                     actor=owner, evidence=f"approval_hash={approval_hash}")
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

        # APPROVED only. AWAITING_OWNER_APPROVAL means the owner has not yet said yes.
        if state != PublishState.APPROVED:
            return {"error": f"Must be APPROVED before submit (current state: {state.value})"}

        approval = manifest.get("approval", {})
        if approval.get("status") != "approved":
            return {"error": "Not approved. Run 'ggb publish approve' first."}

        current_hash = build_canonical_manifest_hash(manifest)
        stored_hash = self.db.get_approval_hash(manifest_id)
        if current_hash != stored_hash:
            return {"error": "Approval expired — manifest changed since approval"}

        # Re-verify every artifact, the package and the KDP draft fields against disk
        # *before* the irreversible platform call. The approval-hash comparison above
        # only reads manifest fields, so on its own it cannot see tampered bytes.
        problems = self._preflight(manifest_id, manifest, PublishState.SUBMITTED)
        if problems:
            return {"error": "; ".join(problems)}

        draft_id = manifest.get("draft_id")
        if not draft_id:
            return {"error": "Manifest has no resolved draft_id — run preview before submit"}

        # The protected-title check ran at preview; the submit chokepoint is where the
        # irreversible call happens, so it has to hold here too.
        cid = resolve_canonical_id(manifest.get("title", {}).get("canonical", ""))
        if cid:
            allowed, msg = check_protected_draft(cid, manifest.get("target_platform"), draft_id)
            if not allowed:
                return {"error": msg}

        if not self.db.acquire_queue_lock(manifest_id, "publisher"):
            return {"error": "Could not acquire submission lock — another title may be active"}

        fingerprint = self._revision_fingerprint(manifest_id, manifest)
        result = self.adapter.submit(draft_id)
        self.db.save_platform_evidence(manifest_id, self.adapter.emit_evidence(
            "submit", fingerprint, result,
            errors=[result["error"]] if result.get("error") else []))

        success, msg = self._advance(manifest_id, manifest, state, PublishState.SUBMITTED,
                                     actor="publisher", evidence=result.get("evidence", ""))
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
            # Re-derive from disk. Reporting readiness off stored values would keep
            # saying READY after someone swapped the manuscript.
            blockers.extend(self._verify_artifacts(manifest))
            blockers.extend(self._verify_package(manifest_id, manifest))
            blockers.extend(self._verify_kdp_draft(manifest))

            fingerprint = self._revision_fingerprint(manifest_id, manifest)
            for operation in ("upload-manuscript", "upload-cover", "poll-processing", "preview"):
                ok, why = self.db.has_bound_evidence(manifest_id, operation, fingerprint,
                                                     self.evidence_gate)
                if not ok:
                    blockers.append(why)

            current_hash = build_canonical_manifest_hash(manifest)
            stored_hash = self.db.get_approval_hash(manifest_id)
            if current_hash != stored_hash:
                blockers.append("Approval expired — manifest changed")

            if self.db.has_forced_state(manifest_id):
                blockers.append("Manifest state was forced out of band — re-discover before publishing")

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

        preview_ok, preview_why = self.db.has_bound_evidence(
            manifest_id, "preview", self._revision_fingerprint(manifest_id, manifest),
            self.evidence_gate)
        report += f"- Previewer: {'CLEAN' if preview_ok else 'NOT ACCEPTED (' + preview_why + ')'}\n"

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
            "awaiting_owner_approval": "approve",
        }
        # preview_clean is deliberately absent: approve() refuses it and preview()
        # requires staged, so no CLI action moves a manifest out of it.

        return {
            "manifest_id": manifest_id,
            "current_state": state,
            "next_action": resume_map.get(state, "status"),
            "can_resume": state in resume_map,
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
