"""Shared test harness.

Two rules this file exists to enforce:

1. Nothing is written inside the repository tree. Every test gets a fresh directory
   under the system temp dir, and it is removed afterwards. Tests that write into the
   repo and rely on .gitignore to hide the mess are not isolated, they are just quiet.

2. Tests never forge platform evidence. The happy path runs through IsolatedTestAdapter,
   a real adapter that signs real evidence with a real key. A test that writes its own
   row into platform_evidence is testing the row, not the gate.
"""

import os
import shutil
import sys
import tempfile
from contextlib import contextmanager
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import publisher  # noqa: E402
from publisher import (  # noqa: E402
    IsolatedTestAdapter, MigrationRepairStore, PublishEngine, PublishState, StateStore,
)

PACKAGE_ROOT_ENV = "GGB_TEST_PACKAGE_ROOT"
PUBLISH_DIR_ENV = "GGB_TEST_PUBLISH_DIR"


class RecordingAdapter(IsolatedTestAdapter):
    """IsolatedTestAdapter that records every platform-facing call, and can be told to
    fail one named operation.

    Local state being unchanged is not the same as nothing having happened. A test that
    only inspects the state machine cannot tell "the engine refused" from "the engine
    called the platform and then refused" — and the second one is the bug. Call counts
    make the difference visible.
    """

    def __init__(self, logger=None, fail: str = None, resolves_draft: str = None):
        super().__init__(logger)
        self.calls = []
        self.uploads = []
        self.fail = fail
        self.resolves_draft = resolves_draft

    def count(self, name: str) -> int:
        return sum(1 for call in self.calls if call[0] == name)

    @property
    def platform_calls(self) -> int:
        return len(self.calls)

    def reset(self) -> None:
        self.calls.clear()
        self.uploads.clear()

    def check_auth(self):
        self.calls.append(("check_auth",))
        return super().check_auth()

    def find_existing_draft(self, title):
        self.calls.append(("find_existing_draft", title))
        if self.resolves_draft:
            return {"draft_id": self.resolves_draft, "title": title}
        return super().find_existing_draft(title)

    def upload_artifact(self, draft_id, artifact_type, file_path):
        self.calls.append(("upload_artifact", draft_id, artifact_type, file_path))
        self.uploads.append({"draft_id": draft_id, "artifact_type": artifact_type,
                             "path": file_path})
        if self.fail == f"upload-{artifact_type}":
            return {"success": False, "error": "platform rejected the upload"}
        return super().upload_artifact(draft_id, artifact_type, file_path)

    def poll_processing(self, draft_id):
        self.calls.append(("poll_processing", draft_id))
        if self.fail == "poll-processing":
            return {"status": "failed", "errors": ["conversion failed"], "warnings": []}
        return super().poll_processing(draft_id)

    def launch_previewer(self, draft_id):
        self.calls.append(("launch_previewer", draft_id))
        if self.fail == "preview":
            return {"opened": False, "screenshots": [], "warnings": []}
        return super().launch_previewer(draft_id)

    def capture_preview_evidence(self, draft_id):
        self.calls.append(("capture_preview_evidence", draft_id))
        if self.fail == "preview":
            return {"screenshots": [], "warnings": [], "errors": ["previewer never opened"]}
        return super().capture_preview_evidence(draft_id)

    def submit(self, draft_id):
        self.calls.append(("submit", draft_id))
        if self.fail == "submit":
            return {"submitted": False, "error": "platform rejected the submission"}
        return super().submit(draft_id)


class Harness:
    """A fully isolated publisher instance: own temp root, own database, own adapter."""

    def __init__(self, root: Path, store: StateStore, engine: PublishEngine):
        self.root = root
        self.db = store
        self.engine = engine

    @property
    def packages(self) -> Path:
        return self.root / "packages"

    def make_package(self, name: str = "sweetgrass", title: str = "Sweetgrass",
                     price: str = "3.99", draft_id: str = "AYK5W5QVJCJOE",
                     drm: str = "No", select: str = "Off",
                     ai_text: str = "No", extra_lines: str = "") -> Path:
        from PIL import Image

        pkg = self.packages / name
        pkg.mkdir(parents=True, exist_ok=True)

        Image.new("RGB", (1600, 2560), (16, 32, 64)).save(pkg / "cover.jpg", "JPEG", quality=90)
        (pkg / "manuscript.docx").write_bytes(b"PK\x03\x04" + b"\x00" * 2048)
        (pkg / "KDP-DRAFT.md").write_text(
            "# KDP Draft\n"
            f"A full length study of {title} traditions along the Sea Island coast.\n"
            f"- **Title:** {title}\n"
            "- **Subtitle:** A Working Study\n"
            "- **Author:** Darryl Elliott Brown\n"
            "- **Publisher:** Gullah Geechee Biz\n"
            "- **Language:** English\n"
            f"- **Draft ID:** {draft_id}\n"
            f"- **Ebook price:** ${price}\n"
            f"- **DRM:** {drm}\n"
            f"- **KDP Select:** {select}\n"
            "- **Categories:** History; Cultural Studies\n"
            "- **Keywords:** gullah; geechee; sweetgrass; lowcountry\n"
            f"- **AI-generated text:** {ai_text}\n"
            "- **AI-generated cover:** No\n"
            f"{extra_lines}"
        )
        return pkg

    def discover(self, pkg: Path) -> str:
        found = self.engine.discover(str(pkg))
        assert found, f"discover returned nothing for {pkg}"
        return found[0]["manifest_id"]

    def advance_to_awaiting_approval(self, pkg: Path = None) -> str:
        """Drive a package all the way to AWAITING_OWNER_APPROVAL through public methods
        only — no direct transitions, no hand-written evidence."""
        pkg = pkg or self.make_package()
        mid = self.discover(pkg)

        result = self.engine.audit(mid)
        assert result.get("passed"), f"audit failed: {result.get('errors')}"

        staged = self.engine.stage(mid)
        assert "error" not in staged, staged.get("error")

        preview = self.engine.preview(mid)
        assert "error" not in preview, preview.get("error")

        assert self.db.get_state(mid) == PublishState.AWAITING_OWNER_APPROVAL.value
        return mid

    def repair_store(self) -> MigrationRepairStore:
        return MigrationRepairStore(self.db.db_path, gate_authority=self.db.gate_authority,
                                    keyring=self.db.keyring)


@contextmanager
def harness(adapter=None, gate=None, production_gate: bool = False):
    root = Path(tempfile.mkdtemp(prefix="ggb-pub-test-"))
    saved_env = {k: os.environ.get(k)
                 for k in ("GGB_TEST_MODE", PACKAGE_ROOT_ENV, PUBLISH_DIR_ENV)}
    saved_dirs = {name: getattr(publisher, name)
                  for name in ("PUBLISH_DIR", "STAGING_DIR", "REPAIRS_DIR", "MANIFESTS_DIR",
                               "LOGS_DIR", "STATE_DIR", "REGISTRY_DIR", "DB_PATH")}
    try:
        os.environ["GGB_TEST_MODE"] = "1"
        os.environ[PACKAGE_ROOT_ENV] = str(root / "packages")
        os.environ[PUBLISH_DIR_ENV] = str(root / "publish")
        (root / "packages").mkdir(parents=True, exist_ok=True)

        publisher.PUBLISH_DIR = root / "publish"
        publisher.STAGING_DIR = root / "publish" / "staging"
        publisher.REPAIRS_DIR = root / "publish" / "repairs"
        publisher.MANIFESTS_DIR = root / "publish" / "manifests"
        publisher.LOGS_DIR = root / "publish" / "logs"
        publisher.STATE_DIR = root / "publish" / "state"
        publisher.REGISTRY_DIR = root / "publish" / "registry"
        publisher.DB_PATH = root / "publish" / "publisher.db"

        store = StateStore(publisher.DB_PATH)
        adapter = adapter or IsolatedTestAdapter()
        if production_gate:
            gate = None
        else:
            gate = gate or IsolatedTestAdapter.gate()
        engine = PublishEngine(db=store, adapter=adapter, evidence_gate=gate)
        yield Harness(root, store, engine)
    finally:
        for name, value in saved_dirs.items():
            setattr(publisher, name, value)
        for key, value in saved_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        shutil.rmtree(root, ignore_errors=True)


def cli_env(root: Path) -> dict:
    env = dict(os.environ)
    env["GGB_TEST_MODE"] = "1"
    env[PACKAGE_ROOT_ENV] = str(root / "packages")
    env[PUBLISH_DIR_ENV] = str(root / "publish")
    return env
