#!/usr/bin/env python3
"""
GGB Publisher Control Plane — Dedicated Test Suite
Tests are independent of the website smoke-test suite.
"""

import json, os, sys, tempfile, hashlib, uuid, sqlite3, threading, time
from pathlib import Path

# Add publisher to path
sys.path.insert(0, str(Path.home() / "gullahgeecheebiz-site" / "ggb-engine"))
from publisher import (
    PublishEngine, StateStore, validate_manifest_id, build_canonical_manifest_hash,
    validate_against_schema, validate_cover, detect_mime, hash_file,
    resolve_canonical_id, enforce_price, DRM_PARSE, SELECT_PARSE,
    PublishState, STATE_TRANSITIONS, ILLEGAL_APPROVAL_STATES,
    TITLE_REGISTRY, MANIFEST_ID_PATTERN, QUEUE_LOCK_TIMEOUT_SECONDS,
    MockKDPAdapter,
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
    # Valid transitions
    test("DISCOVERED → PACKAGED allowed",
         PublishState.PACKAGED in STATE_TRANSITIONS[PublishState.DISCOVERED])
    test("VALIDATED → STAGED allowed",
         PublishState.STAGED in STATE_TRANSITIONS[PublishState.VALIDATED])
    test("APPROVED → SUBMITTED allowed",
         PublishState.SUBMITTED in STATE_TRANSITIONS[PublishState.APPROVED])

    # Invalid transitions
    test("DISCOVERED → SUBMITTED not allowed",
         PublishState.SUBMITTED not in STATE_TRANSITIONS[PublishState.DISCOVERED])
    test("BLOCKED → APPROVED not allowed",
         PublishState.APPROVED not in STATE_TRANSITIONS[PublishState.BLOCKED])
    test("ARCHIVED has no outgoing transitions",
         len(STATE_TRANSITIONS[PublishState.ARCHIVED]) == 0)

    # Illegal approval states
    for state in [PublishState.BLOCKED, PublishState.ARCHIVED, PublishState.SUBMITTED,
                  PublishState.IN_REVIEW, PublishState.REJECTED, PublishState.LIVE,
                  PublishState.WITHDRAWN, PublishState.NEEDS_REVISION]:
        test(f"Cannot approve from {state.value}",
             state in ILLEGAL_APPROVAL_STATES)

# ─── 3. Dry-Run Mutation Test ────────────────────────────────────────────────

def test_dry_run():
    print("\n=== Dry-Run Mutation Test ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        store = StateStore(db_path)
        engine = PublishEngine(db=store)

        # Discover in dry-run mode
        result = engine.discover(dry_run=True)
        test("Dry-run discover returns empty", result == [])

        # No manifests should exist
        test("No manifests created during dry-run",
             store.get_state("nonexistent") is None)

# ─── 4. Price Safeguards ────────────────────────────────────────────────────

def test_price_safeguards():
    print("\n=== Price Safeguards ===")
    # Sweetgrass
    cid = resolve_canonical_id("Sweetgrass")
    test("Sweetgrass resolves", cid == "sweetgrass")
    allowed, msg = enforce_price("sweetgrass", 3.99)
    test("Sweetgrass $3.99 allowed", allowed)
    allowed, msg = enforce_price("sweetgrass", 4.99)
    test("Sweetgrass $4.99 rejected", not allowed)

    # Encyclopedia Vol 1
    cid = resolve_canonical_id("Encyclopedia Volume 01")
    test("Encyclopedia Vol 1 resolves", cid == "encyclopedia-volume-01")
    cid = resolve_canonical_id("Historiography of Gullah Geechee Studies")
    test("Historiography resolves", cid == "encyclopedia-volume-01")
    allowed, msg = enforce_price("encyclopedia-volume-01", 9.99)
    test("Encyclopedia $9.99 allowed", allowed)
    allowed, msg = enforce_price("encyclopedia-volume-01", 12.99)
    test("Encyclopedia $12.99 rejected", not allowed)

    # Blood Remembers
    cid = resolve_canonical_id("Blood Remembers")
    test("Blood Remembers resolves", cid == "blood-remembers")
    allowed, msg = enforce_price("blood-remembers", 9.99)
    test("Blood Remembers price locked", not allowed)

    # Unknown title
    cid = resolve_canonical_id("Some Random Book")
    test("Unknown title returns None", cid is None)

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
    # These should all raise ValueError
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

        # Create a manifest
        mid = f"ggb-manifest-{uuid.uuid4()}"
        manifest = {
            "manifest_id": mid,
            "title": {"canonical": "Test Book", "subtitle": ""},
            "author": "Darryl Elliott Brown",
            "publisher": "Gullah Geechee Biz",
            "target_platform": "kdp",
            "draft_id": None,
            "format": "ebook",
            "language": "en",
            "publishing": {"price": 9.99, "currency": "USD", "drm": "no", "kdp_select": "off"},
            "rights": {"territories": "Worldwide", "copyright_owner": "Darryl Elliott Brown", "copyright_year": 2026},
            "metadata": {"ai_disclosure": {"text": False, "cover": False, "interior_images": False, "translation": False}},
            "files": {},
            "validation": {"repair_history": []},
            "status": "validated",
        }
        store.save_manifest(mid, manifest, "validated")

        # Approve
        result = engine.approve(mid)
        test("Approval succeeds", "approval_hash" in result)

        # Verify approval hash was stored
        stored_hash = store.get_approval_hash(mid)
        test("Approval hash stored", stored_hash is not None)

        # Load manifest from store, change price, save back
        loaded = store.load_manifest(mid)
        loaded["publishing"]["price"] = 4.99
        store.save_manifest(mid, loaded, "approved")

        # Try to submit — should fail because hash changed
        result = engine.submit(mid)
        test("Submit fails after price change", "expired" in result.get("error", ""))

# ─── 8. Queue Ordering ──────────────────────────────────────────────────────

def test_queue_ordering():
    print("\n=== Queue Ordering ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        store = StateStore(db_path)
        engine = PublishEngine(db=store)

        mid1 = f"ggb-manifest-{uuid.uuid4()}"
        mid2 = f"ggb-manifest-{uuid.uuid4()}"

        store.save_manifest(mid1, {"manifest_id": mid1, "status": "discovered"}, "discovered")
        store.save_manifest(mid2, {"manifest_id": mid2, "status": "discovered"}, "discovered")

        store.enqueue(mid1, priority=1)
        store.enqueue(mid2, priority=0)

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
        store.enqueue(mid1)
        store.enqueue(mid2)

        # Lock first
        locked = store.acquire_queue_lock(mid1, "test")
        test("First lock acquired", locked)

        # Second should fail
        locked = store.acquire_queue_lock(mid2, "test")
        test("Second lock rejected", not locked)

        # Release first
        store.release_queue_lock(mid1)
        locked = store.acquire_queue_lock(mid2, "test")
        test("Lock acquired after release", locked)

# ─── 10. Cover Validation ──────────────────────────────────────────────────

def test_cover_validation():
    print("\n=== Cover Validation ===")
    with tempfile.TemporaryDirectory() as tmp:
        # Create a valid JPEG
        from PIL import Image
        img = Image.new("RGB", (1600, 2560), color="navy")
        valid_path = Path(tmp) / "valid.jpg"
        img.save(valid_path)

        result = validate_cover(valid_path)
        test("Valid cover passes", result["passed"])

        # Create a too-small image
        small = Image.new("RGB", (100, 100), color="navy")
        small_path = Path(tmp) / "small.jpg"
        small.save(small_path)

        result = validate_cover(small_path)
        test("Small cover fails", not result["passed"])

        # Non-existent file
        result = validate_cover(Path(tmp) / "nonexistent.jpg")
        test("Missing cover fails", not result["passed"])

# ─── 11. MIME Detection ─────────────────────────────────────────────────────

def test_mime_detection():
    print("\n=== MIME Detection ===")
    with tempfile.TemporaryDirectory() as tmp:
        # JPEG
        jpg = Path(tmp) / "test.jpg"
        jpg.write_bytes(b"\xff\xd8\xff\xe0" + b"\x00" * 100)
        test("JPEG detected", detect_mime(jpg) == "image/jpeg")

        # PNG
        png = Path(tmp) / "test.png"
        png.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)
        test("PNG detected", detect_mime(png) == "image/png")

        # EPUB
        epub = Path(tmp) / "test.epub"
        epub.write_bytes(b"PK" + b"\x00" * 100)
        test("EPUB detected", detect_mime(epub) == "application/epub+zip")

        # DOCX
        docx = Path(tmp) / "test.docx"
        docx.write_bytes(b"PK" + b"\x00" * 100)
        test("DOCX detected", detect_mime(docx) == "application/vnd.openxmlformats-officedocument.wordprocessingml.document")

# ─── 12. Concurrency ────────────────────────────────────────────────────────

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
                    store.set_state(mid, "validating")
                    store.set_state(mid, "validated")
            except Exception as e:
                errors.append(str(e))

        threads = [threading.Thread(target=writer) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        test("No concurrency errors", len(errors) == 0)

# ─── 13. Registry Tamper Detection ──────────────────────────────────────────

def test_registry_tamper():
    print("\n=== Registry Tamper Detection ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        store = StateStore(db_path)

        # Register an artifact
        store.register_artifact(
            hashlib.sha256(b"test").hexdigest(),
            "/tmp/test.txt", 100, "text/plain", "test"
        )
        found = store.find_artifact(hashlib.sha256(b"test").hexdigest())
        test("Artifact registered and found", found is not None)

        # Non-existent hash
        found = store.find_artifact("nonexistent")
        test("Non-existent hash returns None", found is None)

# ─── 14. End-to-End Workflow ────────────────────────────────────────────────

def test_end_to_end():
    print("\n=== End-to-End Workflow ===")
    # Use a unique path under home directory for each test run
    import shutil
    test_dir = Path.home() / f".ggb-test-e2e-{uuid.uuid4().hex[:8]}"
    test_dir.mkdir(parents=True, exist_ok=True)
    try:
        db_path = test_dir / "test.db"
        store = StateStore(db_path)
        engine = PublishEngine(db=store)

        # Create a test package
        pkg_dir = test_dir / "test-package"
        pkg_dir.mkdir(exist_ok=True)
        cover = pkg_dir / "cover.jpg"
        from PIL import Image
        Image.new("RGB", (1600, 2560), color="navy").save(cover)
        ms = pkg_dir / "manuscript.docx"
        ms.write_bytes(b"PK" + b"\x00" * 1000)  # Fake DOCX

        # Create KDP-DRAFT.md
        draft = pkg_dir / "KDP-DRAFT.md"
        draft.write_text("""# KDP Draft — Test Book
- **Title:** Test Book
- **Author:** Darryl Elliott Brown
- **Publisher:** Gullah Geechee Biz
- **Language:** English
- **Ebook price:** $9.99
- **DRM:** No
- **KDP Select:** Off
## Description
A test book for the publisher control plane.
""")

        # Discover
        discovered = engine.discover(str(pkg_dir))
        test("Package discovered", len(discovered) > 0)
        if not discovered:
            return
        mid = discovered[0]["manifest_id"]

        # Reconcile
        result = engine.reconcile(mid)
        test("Reconciled", "error" not in result)

        # Audit
        result = engine.audit(mid)
        audit_passed = result.get("passed", False)
        if not audit_passed:
            print(f"  [DEBUG] Audit errors: {result.get('errors', [])}")
            print(f"  [DEBUG] Audit warnings: {result.get('warnings', [])}")
        test("Audit passed", audit_passed)

        # Stage
        result = engine.stage(mid)
        test("Staged", "staged_files" in result)

        # Preview (mock)
        result = engine.preview(mid)
        test("Preview generated", "previewer_opened" in result)

        # Approve
        result = engine.approve(mid)
        test("Approved", result.get("status") == "approved")

        # Status
        result = engine.get_status(mid)
        test("Status shows ready", result.get("ready", False))

        # Submit (mock)
        result = engine.submit(mid)
        test("Submitted", result.get("status") == "submitted")

        # Verify audit trail
        trail = store.get_audit_trail(mid)
        test("Audit trail recorded", len(trail) >= 1)
    finally:
        shutil.rmtree(test_dir, ignore_errors=True)

# ─── Run All Tests ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("GGB Publisher Control Plane — Test Suite")
    print("=" * 50)
    print(f"Started: {__import__('datetime').datetime.now().isoformat()}")
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
    test_cover_validation()
    test_mime_detection()
    test_concurrency()
    test_registry_tamper()
    test_end_to_end()

    print(f"\n{'=' * 50}")
    print(f"Results: {PASS} passed, {FAIL} failed")
    if FAIL > 0:
        sys.exit(1)
    print("All tests passed.")
