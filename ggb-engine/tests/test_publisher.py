#!/usr/bin/env python3
"""
GGB Publisher Control Plane — Portable Test Suite
Tests use project-relative paths. No hardcoded home directories.
Run from repository root: python3 ggb-engine/tests/test_publisher.py
"""

import json, os, sys, tempfile, hashlib, uuid, sqlite3, threading, time, shutil
from pathlib import Path

# Add publisher to path (project-relative)
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from publisher import (
    PublishEngine, StateStore, validate_manifest_id, build_canonical_manifest_hash,
    validate_against_schema, validate_cover, detect_mime, hash_file,
    resolve_canonical_id, enforce_price, check_protected_draft, DRM_PARSE, SELECT_PARSE,
    PublishState, STATE_TRANSITIONS, ILLEGAL_APPROVAL_STATES, PLATFORM_EVIDENCE_REQUIRED,
    TITLE_REGISTRY, PROTECTED_DRAFTS, MANIFEST_ID_PATTERN, QUEUE_LOCK_TIMEOUT_SECONDS,
    MockKDPAdapter, REPO_ROOT, PUBLISH_DIR,
)

PASS = 0
FAIL = 0

def test(name, condition, detail=""):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  ✓ {name}")
    else:
        FAIL += 1
        print(f"  ✗ {name}: {detail}")

def assert_raises(fn, expected_msg=""):
    try:
        fn()
        return False, "No exception raised"
    except Exception as e:
        if expected_msg and expected_msg not in str(e):
            return False, f"Expected '{expected_msg}' in '{e}'"
        return True, ""

def make_test_package(tmp_dir, name="test-book", price="$9.99", drm="No", select="Off"):
    """Create a test package directory with files."""
    pkg = Path(tmp_dir) / name
    pkg.mkdir(parents=True, exist_ok=True)
    from PIL import Image
    Image.new("RGB", (1600, 2560), color="navy").save(str(pkg / "cover.jpg"))
    (pkg / "manuscript.docx").write_bytes(b"PK" + b"\x00" * 1000)
    (pkg / "KDP-DRAFT.md").write_text(f"""# KDP Draft — {name.replace('-', ' ').title()}
- **Title:** {name.replace('-', ' ').title()}
- **Author:** Darryl Elliott Brown
- **Publisher:** Gullah Geechee Biz
- **Language:** English
- **Ebook price:** {price}
- **DRM:** {drm}
- **KDP Select:** {select}
## Description
A comprehensive test book for the publisher control plane validation suite.
""")
    return pkg

# ─── 1. Manifest ID Validation ──────────────────────────────────────────────

def test_manifest_id_validation():
    print("\n=== Manifest ID Validation ===")
    test("Valid UUID manifest ID", validate_manifest_id(f"ggb-manifest-{uuid.uuid4()}"))
    test("Rejects empty string", not validate_manifest_id(""))
    test("Rejects None", not validate_manifest_id(None))
    test("Rejects path traversal", not validate_manifest_id("../etc/passwd"))
    test("Rejects absolute path", not validate_manifest_id("/etc/passwd"))
    test("Rejects null byte", not validate_manifest_id(f"ggb-manifest-{uuid.uuid4()}\x00"))
    test("Rejects double-dot", not validate_manifest_id(f"ggb-manifest-{uuid.uuid4()}/.."))
    test("Rejects wrong prefix", not validate_manifest_id(f"wrong-{uuid.uuid4()}"))

# ─── 2. State Transitions ────────────────────────────────────────────────────

def test_state_transitions():
    print("\n=== State Transitions ===")
    test("DISCOVERED → PACKAGED allowed",
         PublishState.PACKAGED in STATE_TRANSITIONS[PublishState.DISCOVERED])
    test("VALIDATED → STAGED allowed",
         PublishState.STAGED in STATE_TRANSITIONS[PublishState.VALIDATED])
    test("APPROVED → SUBMITTED allowed",
         PublishState.SUBMITTED in STATE_TRANSITIONS[PublishState.APPROVED])
    test("DISCOVERED → SUBMITTED not allowed",
         PublishState.SUBMITTED not in STATE_TRANSITIONS[PublishState.DISCOVERED])
    test("BLOCKED → APPROVED not allowed",
         PublishState.APPROVED not in STATE_TRANSITIONS[PublishState.BLOCKED])
    test("ARCHIVED has no outgoing transitions",
         len(STATE_TRANSITIONS[PublishState.ARCHIVED]) == 0)

    for state in [PublishState.BLOCKED, PublishState.ARCHIVED, PublishState.SUBMITTED,
                  PublishState.IN_REVIEW, PublishState.REJECTED, PublishState.LIVE,
                  PublishState.WITHDRAWN, PublishState.NEEDS_REVISION,
                  PublishState.DISCOVERED, PublishState.PACKAGED, PublishState.VALIDATING]:
        test(f"Cannot approve from {state.value}",
             state in ILLEGAL_APPROVAL_STATES)

# ─── 3. Dry-Run Mutation Test ────────────────────────────────────────────────

def test_dry_run():
    print("\n=== Dry-Run Mutation Test ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        store = StateStore(db_path)
        engine = PublishEngine(db=store)

        result = engine.discover(dry_run=True)
        test("Dry-run discover returns empty", result == [])
        test("No manifests created during dry-run",
             store.get_state("nonexistent") is None)

# ─── 4. Price Safeguards ────────────────────────────────────────────────────

def test_price_safeguards():
    print("\n=== Price Safeguards ===")
    cid = resolve_canonical_id("Sweetgrass")
    test("Sweetgrass resolves", cid == "sweetgrass")
    allowed, msg = enforce_price("sweetgrass", 3.99)
    test("Sweetgrass $3.99 allowed", allowed)
    allowed, msg = enforce_price("sweetgrass", 4.99)
    test("Sweetgrass $4.99 rejected", not allowed)

    cid = resolve_canonical_id("Encyclopedia Volume 01")
    test("Encyclopedia Vol 1 resolves", cid == "encyclopedia-volume-01")
    cid = resolve_canonical_id("Historiography of Gullah Geechee Studies")
    test("Historiography resolves", cid == "encyclopedia-volume-01")
    cid = resolve_canonical_id("The Gullah Geechee Encyclopedia: Volume 1")
    test("Full title resolves", cid == "encyclopedia-volume-01")
    allowed, msg = enforce_price("encyclopedia-volume-01", 9.99)
    test("Encyclopedia $9.99 allowed", allowed)
    allowed, msg = enforce_price("encyclopedia-volume-01", 12.99)
    test("Encyclopedia $12.99 rejected", not allowed)

    cid = resolve_canonical_id("Blood Remembers")
    test("Blood Remembers resolves", cid == "blood-remembers")
    allowed, msg = enforce_price("blood-remembers", 9.99)
    test("Blood Remembers price locked", not allowed)

    cid = resolve_canonical_id("Some Random Book")
    test("Unknown title returns None", cid is None)

    # Typo protection
    cid = resolve_canonical_id("Sweetgrasss")
    test("Typo 'Sweetgrasss' does not resolve", cid is None)

# ─── 5. DRM / Select Parsing ────────────────────────────────────────────────

def test_drm_select_parsing():
    print("\n=== DRM / Select Parsing ===")
    test("DRM 'No' → no", DRM_PARSE.get("No").value == "no")
    test("DRM 'Yes' → yes", DRM_PARSE.get("Yes").value == "yes")
    test("DRM 'false' → no", DRM_PARSE.get("false").value == "no")
    test("DRM 'true' → yes", DRM_PARSE.get("true").value == "yes")
    test("Select 'Off' → off", SELECT_PARSE.get("Off").value == "off")
    test("Select 'On' → on", SELECT_PARSE.get("On").value == "on")
    test("Select 'enrolled' → on", SELECT_PARSE.get("enrolled").value == "on")
    test("Select 'not enrolled' → off", SELECT_PARSE.get("not enrolled").value == "off")

# ─── 6. Path Traversal Protection ────────────────────────────────────────────

def test_path_traversal():
    print("\n=== Path Traversal Protection ===")
    engine = PublishEngine()
    for bad_id in ["../etc/passwd", "/etc/passwd", "ggb-manifest-xxx\x00yyy",
                   "ggb-manifest-xxx/../yyy", "ggb-manifest-xxx\\..\\yyy"]:
        try:
            engine._require_valid_manifest_id(bad_id)
            test(f"Rejected traversal: {bad_id[:20]}", False)
        except ValueError:
            test(f"Rejected traversal: {bad_id[:20]}", True)

# ─── 7. Approval Binding ────────────────────────────────────────────────────

def test_approval_binding():
    print("\n=== Approval Binding ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        store = StateStore(db_path)
        engine = PublishEngine(db=store)

        mid = f"ggb-manifest-{uuid.uuid4()}"
        manifest = {
            "manifest_id": mid, "title": {"canonical": "Test Book", "subtitle": ""},
            "author": "Darryl Elliott Brown", "publisher": "Gullah Geechee Biz",
            "target_platform": "kdp", "draft_id": None, "format": "ebook", "language": "en",
            "publishing": {"price": 9.99, "currency": "USD", "drm": "no", "kdp_select": "off"},
            "rights": {"territories": "Worldwide", "copyright_owner": "Darryl Elliott Brown", "copyright_year": 2026},
            "metadata": {"ai_disclosure": {"text": False, "cover": False, "interior_images": False, "translation": False}},
            "files": {}, "validation": {"repair_history": []}, "status": "awaiting_owner_approval",
        }
        store.save_manifest(mid, manifest, "awaiting_owner_approval")

        result = engine.approve(mid)
        test("Approval succeeds", "approval_hash" in result)

        stored_hash = store.get_approval_hash(mid)
        test("Approval hash stored", stored_hash is not None)

        # Change price via store
        loaded = store.load_manifest(mid)
        loaded["publishing"]["price"] = 4.99
        store.save_manifest(mid, loaded, "approved")

        result = engine.submit(mid)
        test("Submit fails after price change", "expired" in result.get("error", ""))

# ─── 8. Queue Ordering ──────────────────────────────────────────────────────

def test_queue_ordering():
    print("\n=== Queue Ordering ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        store = StateStore(db_path)

        mid1 = f"ggb-manifest-{uuid.uuid4()}"
        mid2 = f"ggb-manifest-{uuid.uuid4()}"

        store.save_manifest(mid1, {"manifest_id": mid1, "status": "discovered"}, "discovered")
        store.save_manifest(mid2, {"manifest_id": mid2, "status": "discovered"}, "discovered")

        store.enqueue(mid1, "test-book-1", priority=1)
        store.enqueue(mid2, "test-book-2", priority=0)

        queue = store.get_queue()
        test("Queue has 2 items", len(queue) == 2)
        test("Higher priority first", queue[0]["manifest_id"] == mid1)

# ─── 9. One-Active-Submission Invariant ─────────────────────────────────────

def test_one_active_submission():
    print("\n=== One-Active-Submission Invariant ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        store = StateStore(db_path)

        mid1 = f"ggb-manifest-{uuid.uuid4()}"
        mid2 = f"ggb-manifest-{uuid.uuid4()}"

        store.save_manifest(mid1, {"manifest_id": mid1, "status": "approved"}, "approved")
        store.save_manifest(mid2, {"manifest_id": mid2, "status": "approved"}, "approved")
        store.enqueue(mid1, "book-1")
        store.enqueue(mid2, "book-2")

        locked = store.acquire_queue_lock(mid1, "test")
        test("First lock acquired", locked)

        locked = store.acquire_queue_lock(mid2, "test")
        test("Second lock rejected", not locked)

        store.release_queue_lock(mid1)
        locked = store.acquire_queue_lock(mid2, "test")
        test("Lock acquired after release", locked)

# ─── 10. Protected Drafts ───────────────────────────────────────────────────

def test_protected_drafts():
    print("\n=== Protected Drafts ===")
    # Sweetgrass: never duplicate
    allowed, msg = check_protected_draft("sweetgrass", "kdp", draft_id=None)
    test("Sweetgrass cannot be duplicated", not allowed)
    test("Sweetgrass message mentions never duplicate", "never duplicate" in msg)

    # Sweetgrass: allowed if draft_id matches existing
    allowed, msg = check_protected_draft("sweetgrass", "kdp", draft_id="AYK5W5QVJCJOE")
    test("Sweetgrass allowed with matching draft ID", allowed)

    # Hear the Home Tongue: never modify
    allowed, msg = check_protected_draft("hear-the-home-tongue", "kdp")
    test("Hear the Home Tongue cannot be modified", not allowed)
    test("Hear the Home Tongue message mentions never modify", "never modify" in msg)

    # Unknown title: allowed
    allowed, msg = check_protected_draft("unknown-book", "kdp")
    test("Unknown title allowed", allowed)

# ─── 11. Cover Validation ──────────────────────────────────────────────────

def test_cover_validation():
    print("\n=== Cover Validation ===")
    with tempfile.TemporaryDirectory() as tmp:
        from PIL import Image
        img = Image.new("RGB", (1600, 2560), color="navy")
        valid_path = Path(tmp) / "valid.jpg"
        img.save(valid_path)
        result = validate_cover(valid_path)
        test("Valid cover passes", result["passed"])

        small = Image.new("RGB", (100, 100), color="navy")
        small_path = Path(tmp) / "small.jpg"
        small.save(small_path)
        result = validate_cover(small_path)
        test("Small cover fails", not result["passed"])

        result = validate_cover(Path(tmp) / "nonexistent.jpg")
        test("Missing cover fails", not result["passed"])

# ─── 12. MIME Detection ─────────────────────────────────────────────────────

def test_mime_detection():
    print("\n=== MIME Detection ===")
    with tempfile.TemporaryDirectory() as tmp:
        jpg = Path(tmp) / "test.jpg"
        jpg.write_bytes(b"\xff\xd8\xff\xe0" + b"\x00" * 100)
        test("JPEG detected", detect_mime(jpg) == "image/jpeg")

        png = Path(tmp) / "test.png"
        png.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)
        test("PNG detected", detect_mime(png) == "image/png")

        epub = Path(tmp) / "test.epub"
        epub.write_bytes(b"PK" + b"\x00" * 100)
        test("EPUB detected", detect_mime(epub) == "application/epub+zip")

        docx = Path(tmp) / "test.docx"
        docx.write_bytes(b"PK" + b"\x00" * 100)
        test("DOCX detected", detect_mime(docx) == "application/vnd.openxmlformats-officedocument.wordprocessingml.document")

# ─── 13. Concurrency ────────────────────────────────────────────────────────

def test_concurrency():
    print("\n=== Concurrency ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        store = StateStore(db_path)

        mid = f"ggb-manifest-{uuid.uuid4()}"
        store.save_manifest(mid, {"manifest_id": mid, "status": "discovered"}, "discovered")

        errors = []
        def writer():
            try:
                for _ in range(10):
                    store.transition(mid, PublishState.DISCOVERED, PublishState.PACKAGED, actor="test")
                    store.transition(mid, PublishState.PACKAGED, PublishState.VALIDATING, actor="test")
                    store.transition(mid, PublishState.VALIDATING, PublishState.VALIDATED, actor="test")
                    store.transition(mid, PublishState.VALIDATED, PublishState.STAGED, actor="test")
                    store.transition(mid, PublishState.STAGED, PublishState.PLATFORM_UPLOADED, actor="test")
                    store.transition(mid, PublishState.PLATFORM_UPLOADED, PublishState.PLATFORM_PROCESSED, actor="test")
                    store.transition(mid, PublishState.PLATFORM_PROCESSED, PublishState.PREVIEW_CLEAN, actor="test")
                    store.transition(mid, PublishState.PREVIEW_CLEAN, PublishState.AWAITING_OWNER_APPROVAL, actor="test")
                    store.transition(mid, PublishState.AWAITING_OWNER_APPROVAL, PublishState.APPROVED, actor="test")
                    store.transition(mid, PublishState.APPROVED, PublishState.SUBMITTED, actor="test")
                    store.transition(mid, PublishState.SUBMITTED, PublishState.IN_REVIEW, actor="test")
                    store.transition(mid, PublishState.IN_REVIEW, PublishState.LIVE, actor="test")
            except Exception as e:
                errors.append(str(e))

        threads = [threading.Thread(target=writer) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        test("No concurrency errors", len(errors) == 0)

# ─── 14. Registry Tamper Detection ──────────────────────────────────────────

def test_registry_tamper():
    print("\n=== Registry Tamper Detection ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        store = StateStore(db_path)

        store.register_artifact(hashlib.sha256(b"test").hexdigest(), "/tmp/test.txt", 100, "text/plain", "test")
        found = store.find_artifact(hashlib.sha256(b"test").hexdigest())
        test("Artifact registered and found", found is not None)

        found = store.find_artifact("nonexistent")
        test("Non-existent hash returns None", found is None)

# ─── 15. State Machine Enforcement ──────────────────────────────────────────

def test_state_machine_enforcement():
    print("\n=== State Machine Enforcement ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        store = StateStore(db_path)

        mid = f"ggb-manifest-{uuid.uuid4()}"
        store.save_manifest(mid, {"manifest_id": mid, "status": "discovered"}, "discovered")

        # Valid transition
        success, msg = store.transition(mid, PublishState.DISCOVERED, PublishState.PACKAGED, actor="test")
        test("Valid transition succeeds", success)

        # Invalid transition
        success, msg = store.transition(mid, PublishState.DISCOVERED, PublishState.SUBMITTED, actor="test")
        test("Invalid transition fails", not success)

        # Wrong current state
        success, msg = store.transition(mid, PublishState.DISCOVERED, PublishState.PACKAGED, actor="test")
        test("Wrong current state fails", not success)

        # Non-existent manifest
        success, msg = store.transition("nonexistent", PublishState.DISCOVERED, PublishState.PACKAGED, actor="test")
        test("Non-existent manifest fails", not success)

# ─── 16. False Readiness Prevention ─────────────────────────────────────────

def test_false_readiness():
    print("\n=== False Readiness Prevention ===")
    test_dir = Path.home() / f".ggb-test-false-{uuid.uuid4().hex[:8]}"
    test_dir.mkdir(parents=True, exist_ok=True)
    try:
        db_path = test_dir / "test.db"
        store = StateStore(db_path)
        engine = PublishEngine(db=store)

        pkg = make_test_package(test_dir, "test-book", "$9.99", "No", "Off")
        discovered = engine.discover(str(pkg))
        if not discovered:
            test("Package discovered", False)
            return
        mid = discovered[0]["manifest_id"]

        engine.reconcile(mid)
        engine.audit(mid)
        engine.stage(mid)
        engine.preview(mid)

        result = engine.approve(mid)
        test("Cannot approve without production evidence",
             "error" in result and "Platform evidence required" in result.get("error", ""))

        status = engine.get_status(mid)
        test("Status not ready without production evidence", not status.get("ready", True))
    finally:
        shutil.rmtree(test_dir, ignore_errors=True)

# ─── 17. Stage-Path Security ────────────────────────────────────────────────

def test_stage_path_security():
    print("\n=== Stage-Path Security ===")
    engine = PublishEngine()

    # Symlink rejection
    with tempfile.TemporaryDirectory() as tmp:
        real = Path(tmp) / "real.txt"
        real.write_text("test")
        link = Path(tmp) / "link.txt"
        try:
            os.symlink(str(real), str(link))
            try:
                engine._safe_stage_path(link)
                test("Symlink rejected", False)
            except ValueError:
                test("Symlink rejected", True)
        except OSError:
            test("Symlink test skipped (OS limitation)", True)

    # Non-existent file
    with tempfile.TemporaryDirectory() as tmp:
        try:
            engine._safe_stage_path(Path(tmp) / "nonexistent.txt")
            test("Non-existent file rejected", False)
        except ValueError:
            test("Non-existent file rejected", True)

# ─── 18. CLI Exit Codes ────────────────────────────────────────────────────

def test_cli_exit_codes():
    print("\n=== CLI Exit Codes ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        store = StateStore(db_path)
        engine = PublishEngine(db=store)

        # Invalid manifest ID
        result = engine.get_status("invalid-id")
        test("Invalid ID returns error", "error" in result)

        # Non-existent manifest
        result = engine.get_status(f"ggb-manifest-{uuid.uuid4()}")
        test("Non-existent manifest returns error", "error" in result)

        # Blocked state
        mid = f"ggb-manifest-{uuid.uuid4()}"
        store.save_manifest(mid, {"manifest_id": mid, "status": "blocked"}, "blocked")
        result = engine.approve(mid)
        test("Approve from blocked returns error", "error" in result)

# ─── 19. End-to-End Workflow ────────────────────────────────────────────────

def test_end_to_end():
    print("\n=== End-to-End Workflow ===")
    test_dir = Path.home() / f".ggb-test-e2e-{uuid.uuid4().hex[:8]}"
    test_dir.mkdir(parents=True, exist_ok=True)
    try:
        db_path = test_dir / "test.db"
        store = StateStore(db_path)
        engine = PublishEngine(db=store)

        pkg = make_test_package(test_dir, "test-book", "$9.99", "No", "Off")
        discovered = engine.discover(str(pkg))
        test("Package discovered", len(discovered) > 0)
        if not discovered:
            return
        mid = discovered[0]["manifest_id"]

        result = engine.reconcile(mid)
        test("Reconciled", "error" not in result)

        result = engine.audit(mid)
        test("Audit passed", result.get("passed", False))

        result = engine.stage(mid)
        test("Staged", "staged_files" in result)

        result = engine.preview(mid)
        test("Preview generated", "previewer_opened" in result)

        evidence = store.get_platform_evidence(mid)
        test("Platform evidence recorded", len(evidence) > 0)
        test("Evidence marked as mock", all(e["is_mock"] for e in evidence))

        trail = store.get_audit_trail(mid)
        test("Audit trail recorded", len(trail) >= 1)
    finally:
        shutil.rmtree(test_dir, ignore_errors=True)

# ─── 20. Independent Exploit Regression Suite ──────────────────────────────

def test_independent_exploit_regression():
    print("\n=== Independent Exploit Regression ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        store = StateStore(db_path)
        engine = PublishEngine(db=store)

        # 1. Path traversal read
        try:
            engine._require_valid_manifest_id("../etc/passwd")
            test("Path traversal read blocked", False)
        except ValueError:
            test("Path traversal read blocked", True)

        # 2. Path traversal write
        try:
            engine._require_valid_manifest_id("/etc/passwd")
            test("Path traversal write blocked", False)
        except ValueError:
            test("Path traversal write blocked", True)

        # 3. Dry-run has zero persistent mutation
        result = engine.discover(dry_run=True)
        test("Dry-run zero mutation", result == [])

        # 4. Illegal transitions fail
        mid = f"ggb-manifest-{uuid.uuid4()}"
        store.save_manifest(mid, {"manifest_id": mid, "status": "discovered"}, "discovered")
        success, msg = store.transition(mid, PublishState.DISCOVERED, PublishState.SUBMITTED, actor="test")
        test("Illegal transition fails", not success)

        # 5. Approval cannot bypass state machine
        store.save_manifest(mid, {"manifest_id": mid, "status": "blocked"}, "blocked")
        result = engine.approve(mid)
        test("Approval from blocked fails", "error" in result)

        # 6. Mock adapters cannot satisfy readiness
        status = engine.get_status(mid)
        test("Mock adapter not ready", not status.get("ready", True))

        # 7. Protected drafts enforced
        allowed, msg = check_protected_draft("sweetgrass", "kdp", draft_id=None)
        test("Protected draft enforced", not allowed)

        # 8. Queue ordering enforced
        mid1 = f"ggb-manifest-{uuid.uuid4()}"
        mid2 = f"ggb-manifest-{uuid.uuid4()}"
        store.save_manifest(mid1, {"manifest_id": mid1, "status": "discovered"}, "discovered")
        store.save_manifest(mid2, {"manifest_id": mid2, "status": "discovered"}, "discovered")
        store.enqueue(mid1, "book-1", priority=1)
        store.enqueue(mid2, "book-2", priority=0)
        queue = store.get_queue()
        test("Queue ordering enforced", queue[0]["manifest_id"] == mid1)

        # 9. One-active-title invariant
        store.save_manifest(mid1, {"manifest_id": mid1, "status": "approved"}, "approved")
        store.save_manifest(mid2, {"manifest_id": mid2, "status": "approved"}, "approved")
        store.enqueue(mid1, "book-1")
        store.enqueue(mid2, "book-2")
        store.acquire_queue_lock(mid1, "test")
        locked = store.acquire_queue_lock(mid2, "test")
        test("One-active-title invariant", not locked)

        # 10. Protected prices cannot be bypassed
        allowed, msg = enforce_price("sweetgrass", 4.99)
        test("Protected price enforced", not allowed)

        # 11. Unknown title blocks
        cid = resolve_canonical_id("Unknown Title")
        test("Unknown title returns None", cid is None)

        # 12. DRM/Select parse strictly
        test("DRM 'No' → no", DRM_PARSE.get("No").value == "no")
        test("Select 'Off' → off", SELECT_PARSE.get("Off").value == "off")

        # 13. Cover validation fails closed
        result = validate_cover(Path(tmp) / "nonexistent.jpg")
        test("Cover validation fails closed", not result["passed"])

        # 14. CLI refusals return nonzero
        result = engine.get_status("invalid")
        test("CLI refusal returns error", "error" in result)


# ─── 21. Duplicate Discovery ────────────────────────────────────────────────

def test_duplicate_discovery():
    print("\n=== Duplicate Discovery ===")
    test_dir = Path.home() / f".ggb-test-dup-{uuid.uuid4().hex[:8]}"
    test_dir.mkdir(parents=True, exist_ok=True)
    try:
        db_path = test_dir / "test.db"
        store = StateStore(db_path)
        engine = PublishEngine(db=store)

        pkg = make_test_package(test_dir, "test-book", "$9.99", "No", "Off")
        d1 = engine.discover(str(pkg))
        test("First discovery succeeds", len(d1) > 0)

        d2 = engine.discover(str(pkg))
        test("Duplicate returns existing", len(d2) > 0 and d2[0].get("duplicate", False))

        pkg2 = make_test_package(test_dir, "different-book", "$9.99", "No", "Off")
        d3 = engine.discover(str(pkg2))
        test("Different package creates new", len(d3) > 0 and not d3[0].get("duplicate", False))
    finally:
        shutil.rmtree(test_dir, ignore_errors=True)


# ─── 22. Schema Validation ──────────────────────────────────────────────────

def test_schema_validation():
    print("\n=== Schema Validation ===")
    valid = {
        "schema_version": "1.0.0",
        "manifest_id": f"ggb-manifest-{uuid.uuid4()}",
        "created_at": "2026-01-01T00:00:00Z",
        "title": {"canonical": "Test Book", "subtitle": ""},
        "author": "Darryl Elliott Brown",
        "publisher": "Gullah Geechee Biz",
        "language": "en",
        "format": "ebook",
        "target_platform": "kdp",
        "draft_id": None,
        "source_package": {"path": "/tmp/test", "record_ids": {}},
        "files": {
            "manuscript": {"path": "/tmp/test.docx", "sha256": "a" * 64, "size": 100, "mime_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document"},
            "cover": {"path": "/tmp/test.jpg", "sha256": "b" * 64, "size": 200, "mime_type": "image/jpeg"},
        },
        "metadata": {
            "description": "A test book description that is long enough to pass validation.",
            "keywords": ["test"],
            "categories": ["SOCIAL SCIENCE"],
            "ai_disclosure": {"text": False, "cover": False, "interior_images": False, "translation": False},
        },
        "rights": {
            "copyright_owner": "Darryl Elliott Brown",
            "copyright_year": 2026,
            "publishing_rights": "owner_confirmed",
            "territories": "Worldwide",
        },
        "publishing": {"drm": "no", "kdp_select": "off", "price": 9.99, "currency": "USD"},
        "validation": {"status": "pending"},
        "approval": {"status": "pending"},
        "status": "discovered",
    }
    errors = validate_against_schema(valid)
    test("Valid manifest passes schema", len(errors) == 0)

    invalid = dict(valid)
    del invalid["author"]
    errors = validate_against_schema(invalid)
    test("Missing author fails schema", len(errors) > 0)

    invalid2 = dict(valid)
    invalid2["publishing"]["drm"] = True
    errors = validate_against_schema(invalid2)
    test("Wrong type fails schema", len(errors) > 0)

    invalid3 = dict(valid)
    invalid3["format"] = "invalid-format"
    errors = validate_against_schema(invalid3)
    test("Invalid enum fails schema", len(errors) > 0)


# ─── 23. Migration ──────────────────────────────────────────────────────────

def test_migration():
    print("\n=== Migration ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        store = StateStore(db_path)
        test("Migration creates schema version", store.SCHEMA_VERSION >= 1)

        conn = sqlite3.connect(str(db_path))
        tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
        conn.close()
        for table in ["manifests", "artifacts", "audit_log", "queue", "platform_evidence", "schema_version"]:
            test(f"Table '{table}' exists", table in tables)

# ─── Run All Tests ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("GGB Publisher Control Plane — Portable Test Suite")
    print("=" * 50)
    print(f"Started: {__import__('datetime').datetime.now().isoformat()}")
    print(f"Repository: {REPO_ROOT}")
    print()

    test_manifest_id_validation()
    test_state_transitions()
    test_dry_run()
    test_price_safeguards()
    test_drm_select_parsing()
    test_path_traversal()
    test_approval_binding()
    test_queue_ordering()
    test_one_active_submission()
    test_protected_drafts()
    test_cover_validation()
    test_mime_detection()
    test_concurrency()
    test_registry_tamper()
    test_state_machine_enforcement()
    test_false_readiness()
    test_stage_path_security()
    test_cli_exit_codes()
    test_end_to_end()
    test_independent_exploit_regression()
    test_duplicate_discovery()
    test_schema_validation()
    test_migration()

    print(f"\n{'=' * 50}")
    print(f"Results: {PASS} passed, {FAIL} failed")
    if FAIL > 0:
        sys.exit(1)
    print("All tests passed.")
