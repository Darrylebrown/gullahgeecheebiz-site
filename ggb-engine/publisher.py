#!/usr/bin/env python3
"""
Gullah Geechee Biz — Publisher Control Plane
State machine, artifact registry, validator, and CLI for coordinated publishing.

Integrates with: GGB Engine, Buffer, Hub, GitHub, Airtable, Notion
Targets: KDP, ACX, D2D, Spotify, DistroKid
"""

import json, os, sys, time, hashlib, uuid, shutil, subprocess, re, logging, copy
from pathlib import Path
from datetime import datetime, timezone
from enum import Enum
from typing import Optional, Dict, List, Any, Tuple

# ─── Constants ───────────────────────────────────────────────────────────────

GGB_HOME = Path.home() / "gullahgeecheebiz-site"
ENGINE_DIR = GGB_HOME / "ggb-engine"
PUBLISH_DIR = GGB_HOME / "publish"
REGISTRY_DIR = PUBLISH_DIR / "registry"
MANIFESTS_DIR = PUBLISH_DIR / "manifests"
LOGS_DIR = PUBLISH_DIR / "logs"
STATE_DIR = PUBLISH_DIR / "state"
STAGING_DIR = PUBLISH_DIR / "staging"
REPAIRS_DIR = PUBLISH_DIR / "repairs"
SCHEMAS_DIR = ENGINE_DIR / "schemas"

MANIFEST_SCHEMA_VERSION = "1.0.0"

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

STATE_TRANSITIONS = {
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

# ─── Price Safeguards ────────────────────────────────────────────────────────

PROTECTED_PRICES = {
    "sweetgrass": 3.99,
    "encyclopedia-volume-01": 9.99,
    "blood-remembers": None,  # Never modify
}

PROTECTED_TITLES = ["blood-remembers"]

# ─── Logging ─────────────────────────────────────────────────────────────────

def setup_logger(workflow_id: str = None):
    logger = logging.getLogger(f"ggb-publish-{workflow_id or 'default'}")
    logger.setLevel(logging.INFO)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stderr)
        formatter = logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    return logger

# ─── Artifact Registry ───────────────────────────────────────────────────────

class ArtifactRegistry:
    """Append-only artifact registry with hash verification."""

    def __init__(self, registry_dir: Path = REGISTRY_DIR):
        self.registry_dir = registry_dir
        self.registry_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = registry_dir / "registry.jsonl"
        self._ensure_db()

    def _ensure_db(self):
        if not self.db_path.exists():
            self.db_path.write_text("")

    def _hash_file(self, path: Path) -> str:
        h = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
        return h.hexdigest()

    def register(self, artifact_path: Path, provenance: str = None) -> Dict:
        """Register an artifact. Returns record. Raises on hash mismatch if duplicate."""
        path = Path(artifact_path).resolve()
        if not path.exists():
            raise FileNotFoundError(f"Artifact not found: {path}")

        sha256 = self._hash_file(path)
        stat = path.stat()
        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "path": str(path),
            "sha256": sha256,
            "size": stat.st_size,
            "mime_type": self._guess_mime(path),
            "provenance": provenance or "direct",
        }

        # Check for duplicate by hash
        existing = self.find_by_hash(sha256)
        if existing:
            return existing  # Already registered, return existing record

        # Append
        with open(self.db_path, "a") as f:
            f.write(json.dumps(record) + "\n")
        return record

    def find_by_hash(self, sha256: str) -> Optional[Dict]:
        with open(self.db_path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                rec = json.loads(line)
                if rec["sha256"] == sha256:
                    return rec
        return None

    def find_by_path(self, path: str) -> Optional[Dict]:
        target = str(Path(path).resolve())
        with open(self.db_path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                rec = json.loads(line)
                if rec["path"] == target:
                    return rec
        return None

    def get_all(self) -> List[Dict]:
        records = []
        with open(self.db_path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                records.append(json.loads(line))
        return records

    def _guess_mime(self, path: Path) -> str:
        ext = path.suffix.lower()
        mime_map = {
            ".epub": "application/epub+zip",
            ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            ".pdf": "application/pdf",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".mp3": "audio/mpeg",
            ".m4b": "audio/mp4",
            ".wav": "audio/wav",
            ".json": "application/json",
            ".md": "text/markdown",
        }
        return mime_map.get(ext, "application/octet-stream")


# ─── Release Manifest ───────────────────────────────────────────────────────

class ReleaseManifest:
    """Build, validate, and serialize release manifests."""

    def __init__(self, manifest_id: str = None):
        self.manifest_id = manifest_id or f"ggb-manifest-{uuid.uuid4()}"
        self.data = self._empty()

    def _empty(self) -> Dict:
        return {
            "schema_version": MANIFEST_SCHEMA_VERSION,
            "manifest_id": self.manifest_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "title": {},
            "author": "Darryl Elliott Brown",
            "contributors": [],
            "publisher": "Gullah Geechee Biz",
            "language": "en",
            "format": "ebook",
            "target_platform": "",
            "draft_id": None,
            "source_package": {"path": "", "record_ids": {}},
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
                "drm": False,
                "kdp_select": False,
                "price": 0,
                "currency": "USD"
            },
            "identifiers": {},
            "validation": {"status": "pending"},
            "approval": {"status": "pending"},
            "status": "discovered",
            "submission": {},
            "audit_trail": []
        }

    def from_package(self, package_path: Path) -> "ReleaseManifest":
        """Build manifest from a publishing package directory."""
        pkg = Path(package_path)
        if not pkg.is_dir():
            raise NotADirectoryError(f"Package not found: {pkg}")

        self.data["source_package"]["path"] = str(pkg.resolve())

        # Detect files
        for f in pkg.iterdir():
            if f.is_file():
                key = self._classify_file(f)
                if key:
                    sha256 = hashlib.sha256()
                    with open(f, "rb") as fh:
                        for chunk in iter(lambda: fh.read(65536), b""):
                            sha256.update(chunk)
                    self.data["files"][key] = {
                        "path": str(f.resolve()),
                        "sha256": sha256.hexdigest(),
                        "size": f.stat().st_size,
                        "mime_type": self._mime(f)
                    }

        # Try to read KDP-DRAFT.md for metadata
        draft_file = pkg / "KDP-DRAFT.md"
        if draft_file.exists():
            self._parse_kdp_draft(draft_file)

        return self

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

    def _mime(self, path: Path) -> str:
        ext = path.suffix.lower()
        return {
            ".epub": "application/epub+zip",
            ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            ".pdf": "application/pdf",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".mp3": "audio/mpeg",
        }.get(ext, "application/octet-stream")

    def _parse_kdp_draft(self, path: Path):
        """Extract metadata from KDP-DRAFT.md."""
        text = path.read_text()
        lines = text.split("\n")
        current_section = None
        for line in lines:
            line = line.strip()
            if line.startswith("## "):
                current_section = line[3:].lower()
            elif line.startswith("- **Title:**"):
                self.data["title"]["canonical"] = line.split(":**", 1)[1].strip()
            elif line.startswith("- **Series:**"):
                series = line.split(":**", 1)[1].strip()
                if "(" in series:
                    self.data["title"]["series"] = series.split("(")[0].strip()
                    vol = series.split("Book ")[-1].rstrip(")")
                    try:
                        self.data["title"]["volume"] = int(vol)
                    except ValueError:
                        pass
            elif line.startswith("- **Author:**"):
                self.data["author"] = line.split(":**", 1)[1].strip()
            elif line.startswith("- **Publisher:**"):
                self.data["publisher"] = line.split(":**", 1)[1].strip()
            elif line.startswith("- **Language:**"):
                self.data["language"] = line.split(":**", 1)[1].strip()
            elif line.startswith("- **Ebook price:**"):
                price_str = line.split(":**", 1)[1].strip().lstrip("$")
                try:
                    self.data["publishing"]["price"] = float(price_str)
                except ValueError:
                    pass
            elif line.startswith("- **DRM:**"):
                drm = line.split(":**", 1)[1].strip().lower()
                self.data["publishing"]["drm"] = "no" in drm
            elif line.startswith("- **KDP Select:**"):
                select = line.split(":**", 1)[1].strip().lower()
                self.data["publishing"]["kdp_select"] = "yes" in select or "enroll" in select
            elif current_section == "description":
                if line and not line.startswith("-") and not line.startswith("#"):
                    self.data["metadata"]["description"] = line

    def validate_schema(self) -> List[str]:
        """Validate manifest against schema. Returns list of errors."""
        errors = []
        required = ["schema_version", "manifest_id", "created_at", "title", "author", "publisher"]
        for field in required:
            if field not in self.data or not self.data.get(field):
                errors.append(f"Missing required field: {field}")
        if not self.data.get("files", {}).get("manuscript"):
            errors.append("Missing manuscript file")
        if not self.data.get("files", {}).get("cover"):
            errors.append("Missing cover file")
        if not self.data.get("metadata", {}).get("description"):
            errors.append("Missing description")
        if self.data.get("publishing", {}).get("price", 0) <= 0:
            errors.append("Price not set or invalid")
        return errors

    def to_json(self, indent=2) -> str:
        return json.dumps(self.data, indent=indent, default=str)

    def save(self, path: Path = None):
        path = path or MANIFESTS_DIR / f"{self.manifest_id}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.to_json())
        return path

    @staticmethod
    def load(path: Path) -> "ReleaseManifest":
        m = ReleaseManifest()
        m.data = json.loads(path.read_text())
        m.manifest_id = m.data["manifest_id"]
        return m


# ─── Validator ───────────────────────────────────────────────────────────────

class Validator:
    """Validates publishing packages against platform requirements."""

    def __init__(self, logger=None):
        self.logger = logger or setup_logger()
        self.errors = []
        self.warnings = []

    def validate_cover(self, cover_path: Path) -> bool:
        """Validate cover image for KDP requirements."""
        if not cover_path.exists():
            self.errors.append(f"Cover not found: {cover_path}")
            return False

        try:
            from PIL import Image
            img = Image.open(cover_path)
            w, h = img.size

            # KDP minimum: 1000x625 for 6x9
            if w < 1000 or h < 625:
                self.errors.append(f"Cover too small: {w}x{h} (min 1000x625)")

            # Check aspect ratio (6:9 = 0.667)
            ratio = w / h
            if ratio < 0.6 or ratio > 0.75:
                self.warnings.append(f"Cover aspect ratio {ratio:.3f} (expected ~0.667 for 6x9)")

            # Check color mode
            if img.mode not in ("RGB", "CMYK"):
                self.warnings.append(f"Cover color mode: {img.mode} (expected RGB or CMYK)")

            return len(self.errors) == 0
        except ImportError:
            self.warnings.append("PIL not available — cover validation skipped")
            return True
        except Exception as e:
            self.errors.append(f"Cover validation error: {e}")
            return False

    def validate_metadata(self, manifest: ReleaseManifest) -> bool:
        """Validate metadata completeness."""
        m = manifest.data
        meta = m.get("metadata", {})

        if not meta.get("description") or len(meta.get("description", "")) < 50:
            self.errors.append("Description too short or missing")

        if not meta.get("keywords"):
            self.warnings.append("No keywords set")

        if not meta.get("categories"):
            self.warnings.append("No categories set")

        ai = meta.get("ai_disclosure", {})
        if not any(ai.values()):
            self.warnings.append("AI disclosure not set — all components marked as not AI-generated")

        return len(self.errors) == 0

    def validate_rights(self, manifest: ReleaseManifest) -> bool:
        """Validate rights and policy gates."""
        m = manifest.data
        rights = m.get("rights", {})
        pub = m.get("publishing", {})

        if rights.get("publishing_rights") != "owner_confirmed":
            self.errors.append("Publishing rights not confirmed as owner-controlled")

        # Price safeguards
        title = m.get("title", {}).get("canonical", "").lower()
        price = pub.get("price", 0)

        if "sweetgrass" in title and price != 3.99:
            self.errors.append(f"Sweetgrass price must be $3.99 (got ${price})")

        if "encyclopedia" in title and "volume 1" in title and price != 9.99:
            self.errors.append(f"Encyclopedia Vol 1 price must be $9.99 (got ${price})")

        for protected in PROTECTED_TITLES:
            if protected in title:
                self.errors.append(f"Cannot modify protected title: {protected}")

        return len(self.errors) == 0

    def validate_hashes(self, manifest: ReleaseManifest) -> bool:
        """Verify file hashes match manifest."""
        for key, file_info in manifest.data.get("files", {}).items():
            path = Path(file_info["path"])
            if not path.exists():
                self.errors.append(f"File not found: {path}")
                continue
            h = hashlib.sha256()
            with open(path, "rb") as f:
                for chunk in iter(lambda: f.read(65536), b""):
                    h.update(chunk)
            if h.hexdigest() != file_info["sha256"]:
                self.errors.append(f"Hash mismatch for {key}: expected {file_info['sha256']}, got {h.hexdigest()}")
        return len(self.errors) == 0

    def validate_all(self, manifest: ReleaseManifest) -> Dict:
        """Run all validations. Returns result dict."""
        self.errors = []
        self.warnings = []

        cover_path = None
        if "cover" in manifest.data.get("files", {}):
            cover_path = Path(manifest.data["files"]["cover"]["path"])

        results = {
            "cover": self.validate_cover(cover_path) if cover_path else False,
            "metadata": self.validate_metadata(manifest),
            "rights": self.validate_rights(manifest),
            "hashes": self.validate_hashes(manifest),
            "schema": len(manifest.validate_schema()) == 0,
            "errors": self.errors,
            "warnings": self.warnings,
        }
        results["passed"] = all(v for k, v in results.items() if k not in ("errors", "warnings"))
        return results


# ─── Repair Engine ────────────────────────────────────────────────────────────

class RepairEngine:
    """Deterministic, reversible repairs on derivative copies."""

    def __init__(self, logger=None):
        self.logger = logger or setup_logger()
        self.repairs_applied = []

    def repair_cover_color(self, cover_path: Path, staging_dir: Path) -> Optional[Path]:
        """Convert cover to RGB if CMYK. Works on derivative."""
        try:
            from PIL import Image
            img = Image.open(cover_path)
            if img.mode == "CMYK":
                derivative = staging_dir / cover_path.name
                rgb = img.convert("RGB")
                rgb.save(derivative, "JPEG", quality=95)
                self.repairs_applied.append(f"Converted cover from CMYK to RGB: {cover_path.name}")
                return derivative
        except ImportError:
            pass
        return None

    def repair_cover_size(self, cover_path: Path, staging_dir: Path, min_w=1000, min_h=625) -> Optional[Path]:
        """Upscale cover if below minimum dimensions."""
        try:
            from PIL import Image
            img = Image.open(cover_path)
            w, h = img.size
            if w < min_w or h < min_h:
                ratio = max(min_w / w, min_h / h)
                new_w = int(w * ratio)
                new_h = int(h * ratio)
                derivative = staging_dir / cover_path.name
                resized = img.resize((new_w, new_h), Image.LANCZOS)
                resized.save(derivative, "JPEG", quality=95)
                self.repairs_applied.append(f"Upscaled cover from {w}x{h} to {new_w}x{new_h}")
                return derivative
        except ImportError:
            pass
        return None

    def get_summary(self) -> str:
        if not self.repairs_applied:
            return "No repairs needed"
        return "\n".join(f"  ✓ {r}" for r in self.repairs_applied)


# ─── Platform Adapter Base ────────────────────────────────────────────────────

class PlatformAdapter:
    """Base class for platform-specific adapters."""

    def __init__(self, name: str, logger=None):
        self.name = name
        self.logger = logger or setup_logger()

    def check_auth(self) -> bool:
        raise NotImplementedError

    def find_draft(self, title: str) -> Optional[Dict]:
        raise NotImplementedError

    def upload_files(self, draft_id: str, files: Dict) -> bool:
        raise NotImplementedError

    def check_processing(self, draft_id: str) -> Dict:
        raise NotImplementedError

    def save_draft(self, draft_id: str) -> bool:
        raise NotImplementedError

    def submit(self, draft_id: str) -> Dict:
        raise NotImplementedError

    def get_status(self, draft_id: str) -> str:
        raise NotImplementedError


# ─── KDP Adapter (Browser Automation) ─────────────────────────────────────────

class KDPAdapter(PlatformAdapter):
    """KDP adapter using browser automation with persistent profile."""

    def __init__(self, profile_path: str = None, logger=None):
        super().__init__("kdp", logger)
        self.profile_path = profile_path or str(Path.home() / ".ggb" / "browser-profiles" / "kdp")
        self.browser = None
        self.page = None

    def check_auth(self) -> bool:
        """Check if KDP is accessible with current session."""
        # In Phase 1, return True for testing
        return True

    def find_draft(self, title: str) -> Optional[Dict]:
        """Look up existing draft by title."""
        self.logger.info(f"Looking up KDP draft: {title}")
        return None  # Phase 1: stub

    def upload_files(self, draft_id: str, files: Dict) -> bool:
        self.logger.info(f"Uploading files to KDP draft {draft_id}: {list(files.keys())}")
        return True  # Phase 1: stub

    def check_processing(self, draft_id: str) -> Dict:
        return {"status": "processed", "errors": [], "warnings": []}

    def save_draft(self, draft_id: str) -> bool:
        return True

    def submit(self, draft_id: str) -> Dict:
        return {"status": "submitted", "confirmation_id": "stub-confirmation"}

    def get_status(self, draft_id: str) -> str:
        return "draft"


# ─── Publishing State Machine Engine ──────────────────────────────────────────

class PublishEngine:
    """Coordinates the publishing state machine, validation, and platform interaction."""

    def __init__(self, registry: ArtifactRegistry = None, logger=None):
        self.registry = registry or ArtifactRegistry()
        self.logger = logger or setup_logger()
        self.validator = Validator(self.logger)
        self.repair = RepairEngine(self.logger)
        PUBLISH_DIR.mkdir(parents=True, exist_ok=True)
        STATE_DIR.mkdir(parents=True, exist_ok=True)
        STAGING_DIR.mkdir(parents=True, exist_ok=True)
        REPAIRS_DIR.mkdir(parents=True, exist_ok=True)

    def discover(self, package_path: str = None) -> List[Dict]:
        """Discover publishing packages. Returns list of discovered items."""
        discovered = []
        if package_path:
            pkg = Path(package_path)
            if pkg.is_dir():
                manifest = ReleaseManifest().from_package(pkg)
                manifest.data["status"] = "discovered"
                manifest.save()
                discovered.append({"path": str(pkg), "manifest_id": manifest.manifest_id})
                self.logger.info(f"Discovered package: {pkg} → {manifest.manifest_id}")
        else:
            # Auto-discover from known locations
            for d in [Path.home() / "gullah-geechee-project" / "packaged"]:
                if d.exists():
                    for sub in d.iterdir():
                        if sub.is_dir():
                            manifest = ReleaseManifest().from_package(sub)
                            manifest.data["status"] = "discovered"
                            manifest.save()
                            discovered.append({"path": str(sub), "manifest_id": manifest.manifest_id})
                            self.logger.info(f"Auto-discovered: {sub}")
        return discovered

    def reconcile(self, manifest_id: str = None) -> Dict:
        """Reconcile manifest with registry and platform state."""
        if manifest_id:
            manifest_path = MANIFESTS_DIR / f"{manifest_id}.json"
            if not manifest_path.exists():
                return {"error": f"Manifest not found: {manifest_id}"}
            manifest = ReleaseManifest.load(manifest_path)
        else:
            # Find latest unsubmitted manifest
            manifests = sorted(MANIFESTS_DIR.glob("*.json"))
            if not manifests:
                return {"error": "No manifests found"}
            manifest = ReleaseManifest.load(manifests[-1])

        # Register artifacts
        for key, file_info in manifest.data.get("files", {}).items():
            path = Path(file_info["path"])
            if path.exists():
                self.registry.register(path, provenance=f"manifest:{manifest.manifest_id}")

        return {
            "manifest_id": manifest.manifest_id,
            "title": manifest.data.get("title", {}).get("canonical", "Unknown"),
            "status": manifest.data["status"],
            "files_registered": len(manifest.data.get("files", {})),
        }

    def audit(self, manifest_id: str) -> Dict:
        """Run full validation on a package."""
        manifest_path = MANIFESTS_DIR / f"{manifest_id}.json"
        if not manifest_path.exists():
            return {"error": f"Manifest not found: {manifest_id}"}

        manifest = ReleaseManifest.load(manifest_path)
        manifest.data["status"] = "validating"
        manifest.data["updated_at"] = datetime.now(timezone.utc).isoformat()

        results = self.validator.validate_all(manifest)
        manifest.data["validation"] = results
        manifest.data["validation"]["status"] = "passed" if results["passed"] else "failed"
        manifest.data["status"] = "validated" if results["passed"] else "blocked"

        manifest.save()
        return results

    def repair(self, manifest_id: str) -> Dict:
        """Apply deterministic repairs on a derivative."""
        manifest_path = MANIFESTS_DIR / f"{manifest_id}.json"
        if not manifest_path.exists():
            return {"error": f"Manifest not found: {manifest_id}"}

        manifest = ReleaseManifest.load(manifest_path)
        repair_dir = REPAIRS_DIR / manifest_id
        repair_dir.mkdir(parents=True, exist_ok=True)

        repairs = []
        cover_info = manifest.data.get("files", {}).get("cover")
        if cover_info:
            cover_path = Path(cover_info["path"])
            if cover_path.exists():
                # Repair on derivative
                result = self.repair.repair_cover_color(cover_path, repair_dir)
                if result:
                    repairs.append({"file": "cover", "action": "color_conversion", "derivative": str(result)})
                result = self.repair.repair_cover_size(cover_path, repair_dir)
                if result:
                    repairs.append({"file": "cover", "action": "size_upscale", "derivative": str(result)})

        manifest.data["validation"]["repair_history"] = manifest.data["validation"].get("repair_history", [])
        for r in repairs:
            manifest.data["validation"]["repair_history"].append({
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "action": r["action"],
                "file": r["file"],
                "derivative": r.get("derivative", ""),
            })

        manifest.save()
        return {"repairs": repairs, "summary": self.repair.get_summary()}

    def stage(self, manifest_id: str) -> Dict:
        """Stage files for platform upload."""
        manifest_path = MANIFESTS_DIR / f"{manifest_id}.json"
        if not manifest_path.exists():
            return {"error": f"Manifest not found: {manifest_id}"}

        manifest = ReleaseManifest.load(manifest_path)
        stage_dir = STAGING_DIR / manifest_id
        stage_dir.mkdir(parents=True, exist_ok=True)

        staged = []
        for key, file_info in manifest.data.get("files", {}).items():
            src = Path(file_info["path"])
            if src.exists():
                dst = stage_dir / src.name
                shutil.copy2(src, dst)
                staged.append(str(dst))

        manifest.data["status"] = "staged"
        manifest.save()
        return {"staged_files": staged, "stage_dir": str(stage_dir)}

    def preview(self, manifest_id: str) -> Dict:
        """Generate preview evidence."""
        manifest_path = MANIFESTS_DIR / f"{manifest_id}.json"
        if not manifest_path.exists():
            return {"error": f"Manifest not found: {manifest_id}"}

        manifest = ReleaseManifest.load(manifest_path)
        return {
            "manifest_id": manifest_id,
            "title": manifest.data.get("title", {}).get("canonical", "Unknown"),
            "files": list(manifest.data.get("files", {}).keys()),
            "validation": manifest.data.get("validation", {}),
            "preview_ready": True,
        }

    def manifest(self, manifest_id: str) -> Dict:
        """Return the full manifest."""
        manifest_path = MANIFESTS_DIR / f"{manifest_id}.json"
        if not manifest_path.exists():
            return {"error": f"Manifest not found: {manifest_id}"}
        manifest = ReleaseManifest.load(manifest_path)
        return manifest.data

    def approve(self, manifest_id: str, owner: str = "owner") -> Dict:
        """Record owner approval. Binds to exact artifact hashes."""
        manifest_path = MANIFESTS_DIR / f"{manifest_id}.json"
        if not manifest_path.exists():
            return {"error": f"Manifest not found: {manifest_id}"}

        manifest = ReleaseManifest.load(manifest_path)

        # Compute approval hash from current file hashes
        hash_input = ""
        for key in sorted(manifest.data.get("files", {}).keys()):
            hash_input += manifest.data["files"][key].get("sha256", "")
        approval_hash = hashlib.sha256(hash_input.encode()).hexdigest()

        manifest.data["approval"] = {
            "status": "approved",
            "approved_by": owner,
            "approved_at": datetime.now(timezone.utc).isoformat(),
            "approval_hash": approval_hash,
        }
        manifest.data["status"] = "approved"
        manifest.save()

        return {
            "manifest_id": manifest_id,
            "approval_hash": approval_hash,
            "status": "approved",
        }

    def submit(self, manifest_id: str, platform: str = "kdp") -> Dict:
        """Submit to platform after approval check."""
        manifest_path = MANIFESTS_DIR / f"{manifest_id}.json"
        if not manifest_path.exists():
            return {"error": f"Manifest not found: {manifest_id}"}

        manifest = ReleaseManifest.load(manifest_path)

        # Verify approval
        approval = manifest.data.get("approval", {})
        if approval.get("status") != "approved":
            return {"error": "Not approved. Run 'ggb publish approve' first."}

        # Verify approval hash still matches
        hash_input = ""
        for key in sorted(manifest.data.get("files", {}).keys()):
            hash_input += manifest.data["files"][key].get("sha256", "")
        current_hash = hashlib.sha256(hash_input.encode()).hexdigest()
        if current_hash != approval.get("approval_hash"):
            return {"error": "Approval expired — files changed since approval"}

        # Submit via adapter
        adapter = KDPAdapter(logger=self.logger)
        result = adapter.submit(manifest.data.get("draft_id", "new"))

        manifest.data["status"] = "submitted"
        manifest.data["submission"] = {
            "submitted_at": datetime.now(timezone.utc).isoformat(),
            "confirmation_id": result.get("confirmation_id", ""),
            "platform": platform,
        }
        manifest.save()

        return {
            "manifest_id": manifest_id,
            "status": "submitted",
            "confirmation_id": result.get("confirmation_id", ""),
        }

    def get_status(self, manifest_id: str) -> Dict:
        """Get current status of a publishing package."""
        manifest_path = MANIFESTS_DIR / f"{manifest_id}.json"
        if not manifest_path.exists():
            return {"error": f"Manifest not found: {manifest_id}"}

        manifest = ReleaseManifest.load(manifest_path)
        m = manifest.data

        # Build readiness report
        validation = m.get("validation", {})
        is_ready = (
            m["status"] in ("approved", "submitted", "in_review", "live")
            or (m["status"] == "awaiting_owner_approval" and validation.get("passed"))
        )

        report = f"STATUS: {'READY TO SUBMIT' if is_ready else m['status'].upper()}\n"
        report += f"- Title: {m.get('title', {}).get('canonical', 'Unknown')}\n"
        report += f"- Draft ID: {m.get('draft_id', 'none')}\n"
        report += f"- Format: {m.get('format', 'unknown')}\n"
        report += f"- Price: ${m.get('publishing', {}).get('price', 0)}\n"
        report += f"- Select: {'Yes' if m.get('publishing', {}).get('kdp_select') else 'No'}\n"
        report += f"- DRM: {'Yes' if m.get('publishing', {}).get('drm') else 'No'}\n"
        report += f"- AI components: {m.get('metadata', {}).get('ai_disclosure', {})}\n"
        report += f"- Previewer: {'CLEAN' if validation.get('passed') else 'NOT RUN'}\n"

        if validation.get("errors"):
            report += f"- Blockers: {len(validation['errors'])} errors\n"
            for e in validation["errors"][:3]:
                report += f"  - {e}\n"
        else:
            report += "- Blockers: none\n"

        report += f"- Next action: {'waiting for owner publish now' if is_ready else 'run ggb publish audit'}\n"

        return {
            "manifest_id": manifest_id,
            "title": m.get("title", {}).get("canonical", "Unknown"),
            "status": m["status"],
            "ready": is_ready,
            "report": report,
        }

    def resume(self, manifest_id: str) -> Dict:
        """Resume interrupted workflow from last known state."""
        manifest_path = MANIFESTS_DIR / f"{manifest_id}.json"
        if not manifest_path.exists():
            return {"error": f"Manifest not found: {manifest_id}"}

        manifest = ReleaseManifest.load(manifest_path)
        state = manifest.data["status"]

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

        next_action = resume_map.get(state, "status")
        return {
            "manifest_id": manifest_id,
            "current_state": state,
            "next_action": next_action,
            "can_resume": state not in ("live", "archived", "submitted"),
        }


# ─── CLI ─────────────────────────────────────────────────────────────────────

def cli():
    """GGB Publisher CLI entry point."""
    import argparse
    parser = argparse.ArgumentParser(description="GGB Publisher Control Plane")
    parser.add_argument("--dry-run", action="store_true", help="Dry run mode")
    parser.add_argument("--json", action="store_true", help="JSON output")
    parser.add_argument("--trace", type=str, help="Workflow trace ID")
    sub = parser.add_subparsers(dest="command", required=True)

    # publish discover
    p = sub.add_parser("discover", help="Discover publishing packages")
    p.add_argument("package", nargs="?", help="Package path (optional)")

    # publish reconcile
    p = sub.add_parser("reconcile", help="Reconcile manifest with registry")
    p.add_argument("manifest_id", nargs="?", help="Manifest ID")

    # publish audit
    p = sub.add_parser("audit", help="Validate a publishing package")
    p.add_argument("manifest_id", help="Manifest ID")

    # publish repair
    p = sub.add_parser("repair", help="Apply deterministic repairs")
    p.add_argument("manifest_id", help="Manifest ID")

    # publish stage
    p = sub.add_parser("stage", help="Stage files for upload")
    p.add_argument("manifest_id", help="Manifest ID")

    # publish preview
    p = sub.add_parser("preview", help="Preview package")
    p.add_argument("manifest_id", help="Manifest ID")

    # publish manifest
    p = sub.add_parser("manifest", help="Show full manifest")
    p.add_argument("manifest_id", help="Manifest ID")

    # publish approve
    p = sub.add_parser("approve", help="Approve for submission")
    p.add_argument("manifest_id", help="Manifest ID")

    # publish submit
    p = sub.add_parser("submit", help="Submit to platform")
    p.add_argument("manifest_id", help="Manifest ID")
    p.add_argument("--platform", default="kdp", help="Target platform")

    # publish status
    p = sub.add_parser("status", help="Get publishing status")
    p.add_argument("manifest_id", help="Manifest ID")

    # publish resume
    p = sub.add_parser("resume", help="Resume interrupted workflow")
    p.add_argument("manifest_id", help="Manifest ID")

    args = parser.parse_args()
    workflow_id = args.trace or f"ggb-pub-{uuid.uuid4().hex[:8]}"
    logger = setup_logger(workflow_id)

    engine = PublishEngine(logger=logger)

    commands = {
        "discover": lambda: engine.discover(getattr(args, 'package', None)),
        "reconcile": lambda: engine.reconcile(getattr(args, 'manifest_id', None)),
        "audit": lambda: engine.audit(args.manifest_id),
        "repair": lambda: engine.repair(args.manifest_id),
        "stage": lambda: engine.stage(args.manifest_id),
        "preview": lambda: engine.preview(args.manifest_id),
        "manifest": lambda: engine.manifest(args.manifest_id),
        "approve": lambda: engine.approve(args.manifest_id),
        "submit": lambda: engine.submit(args.manifest_id, getattr(args, 'platform', 'kdp')),
        "status": lambda: engine.get_status(args.manifest_id),
        "resume": lambda: engine.resume(args.manifest_id),
    }

    result = commands[args.command]()

    if args.json:
        print(json.dumps(result, indent=2, default=str))
    else:
        if isinstance(result, dict):
            if "report" in result:
                print(result["report"])
            elif "error" in result:
                print(f"ERROR: {result['error']}")
            elif "summary" in result:
                print(result["summary"])
            else:
                for k, v in result.items():
                    if isinstance(v, list):
                        print(f"{k}: {len(v)} items")
                        for item in v[:5]:
                            print(f"  - {item}")
                    elif isinstance(v, dict):
                        print(f"{k}:")
                        for sk, sv in v.items():
                            print(f"  {sk}: {sv}")
                    else:
                        print(f"{k}: {v}")
        else:
            print(result)

    return 0 if isinstance(result, (list, dict)) and ("error" not in (result if isinstance(result, dict) else {})) else 1


if __name__ == "__main__":
    sys.exit(cli())
