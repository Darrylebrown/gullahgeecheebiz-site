"""Publisher Control Plane test suite.

Every check here is a bare `assert`. There is no scoreboard helper, no counter, and no
way for a failing check to be reported as anything other than a failure — under pytest
or under run_tests.py. A suite whose failures are printed rather than raised has zero
detection power in CI, which is how a prior version of this file reported success while
21 real checks were failing.

Test functions take no arguments so both runners can invoke them identically.
"""

import json
import os
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import publisher  # noqa: E402
from harness import RecordingAdapter, cli_env, harness  # noqa: E402
from publisher import (  # noqa: E402
    APPROVED_PACKAGE_ROOTS, EVIDENCE_ISOLATED_TEST, EVIDENCE_MOCK,
    EVIDENCE_OUTCOME_FAILURE, EVIDENCE_OUTCOME_SUCCESS, GATED_STATES,
    PRODUCTION_ADAPTERS, REQUIRED_BINDING_PROPERTIES, STATE_TRANSITIONS, EvidenceGate,
    EvidenceKeyring, GateAuthority, IsolatedTestAdapter, MockKDPAdapter, PublishState,
    StateStore, build_canonical_manifest_hash, check_protected_draft, detect_mime,
    enforce_price, hash_file, operation_outcome, resolve_canonical_id, validate_manifest_id,
)

PUBLISHER_PY = Path(publisher.__file__).resolve()


# ─── Title resolution fails closed ───────────────────────────────────────────

def test_registered_titles_resolve():
    assert resolve_canonical_id("Sweetgrass") == "sweetgrass"
    assert resolve_canonical_id("Hear the Home Tongue") == "hear-the-home-tongue"
    assert resolve_canonical_id("Blood Remembers") == "blood-remembers"
    assert resolve_canonical_id("The Gullah Geechee Encyclopedia: Volume 1") == "encyclopedia-volume-01"


def test_unknown_title_resolves_to_none():
    for unknown in ("Sweetgras", "Some Other Book", "", "   ", "Sweet grass"):
        assert resolve_canonical_id(unknown) is None, f"{unknown!r} must not resolve"


def test_unknown_title_blocks_price_approval():
    allowed, msg = enforce_price(None, 3.99)
    assert allowed is False
    assert "Owner approval required" in msg


def test_price_lock_enforced():
    assert enforce_price("sweetgrass", 3.99)[0] is True
    assert enforce_price("sweetgrass", 99.99)[0] is False
    assert enforce_price("sweetgrass", 0.99)[0] is False
    assert enforce_price("encyclopedia-volume-01", 9.99)[0] is True
    assert enforce_price("encyclopedia-volume-01", 3.99)[0] is False


def test_protected_titles_never_priced():
    for cid in ("blood-remembers", "hear-the-home-tongue"):
        allowed, msg = enforce_price(cid, 3.99)
        assert allowed is False
        assert "Protected" in msg


# ─── Protected drafts (F-14) ─────────────────────────────────────────────────

def test_never_duplicate_admits_only_the_known_draft_id():
    assert check_protected_draft("sweetgrass", "kdp", "AYK5W5QVJCJOE")[0] is True
    assert check_protected_draft("sweetgrass", "kdp", "SOMETHING-ELSE")[0] is False
    assert check_protected_draft("sweetgrass", "kdp", None)[0] is False


def test_never_modify_always_refuses():
    assert check_protected_draft("hear-the-home-tongue", "kdp", "A11PYUZCEIJZPV")[0] is False


def test_protection_is_platform_independent():
    """Routing a protected title through a different platform must not launder it."""
    for platform in ("kdp", "d2d", "acx", "site", None, "", "KDP"):
        allowed, _ = check_protected_draft("hear-the-home-tongue", platform, "A11PYUZCEIJZPV")
        assert allowed is False, f"platform {platform!r} bypassed never_modify"
        allowed, _ = check_protected_draft("sweetgrass", platform, "IMPOSTOR")
        assert allowed is False, f"platform {platform!r} bypassed never_duplicate"


# ─── State machine and gate tokens (F-11, F-12) ──────────────────────────────

def test_state_store_has_no_private_state_setter():
    """_set_state let any caller move a manifest anywhere with no audit trail."""
    assert not hasattr(StateStore, "_set_state")


def test_archived_is_terminal():
    assert STATE_TRANSITIONS[PublishState.ARCHIVED] == []


def test_raw_transition_into_gated_state_is_refused():
    with harness() as h:
        mid = h.discover(h.make_package())
        assert h.engine.audit(mid)["passed"]
        assert "error" not in h.engine.stage(mid)

        for target in (PublishState.PLATFORM_UPLOADED, PublishState.PLATFORM_PROCESSED,
                       PublishState.PREVIEW_CLEAN, PublishState.AWAITING_OWNER_APPROVAL,
                       PublishState.APPROVED, PublishState.SUBMITTED):
            ok, msg = h.db.transition(mid, PublishState.STAGED, target, actor="attacker")
            assert ok is False, f"raw transition to {target.value} succeeded"
            assert "gate token" in msg
        assert h.db.get_state(mid) == PublishState.STAGED.value


def test_every_consequential_state_is_gated():
    for state in (PublishState.PLATFORM_UPLOADED, PublishState.PLATFORM_PROCESSED,
                  PublishState.PREVIEW_CLEAN, PublishState.AWAITING_OWNER_APPROVAL,
                  PublishState.APPROVED, PublishState.SUBMITTED):
        assert state in GATED_STATES


def test_gate_token_is_single_use():
    authority = GateAuthority()
    token = authority.issue("m", PublishState.APPROVED)
    assert authority.redeem(token, "m", PublishState.APPROVED)[0] is True
    assert authority.redeem(token, "m", PublishState.APPROVED)[0] is False


def test_gate_token_is_bound_to_manifest_and_state():
    authority = GateAuthority()
    token = authority.issue("m1", PublishState.APPROVED)
    assert authority.redeem(token, "m2", PublishState.APPROVED)[0] is False
    token = authority.issue("m1", PublishState.APPROVED)
    assert authority.redeem(token, "m1", PublishState.SUBMITTED)[0] is False


def test_forced_state_is_audited_and_blocks_readiness():
    with harness() as h:
        mid = h.advance_to_awaiting_approval()
        assert "error" not in h.engine.approve(mid)
        assert h.engine.get_status(mid)["ready"] is True

        ok, _ = h.repair_store().force_state(mid, "approved", actor="operator",
                                             reason="incident-1234")
        assert ok is True

        assert any(e["action"] == "force_state" for e in h.db.get_audit_trail(mid))

        status = h.engine.get_status(mid)
        assert status["ready"] is False
        assert any("forced out of band" in b for b in status["blockers"])


def test_force_state_requires_a_reason():
    with harness() as h:
        mid = h.discover(h.make_package())
        assert h.repair_store().force_state(mid, "approved", actor="op", reason="")[0] is False


# ─── Evidence binding (F-3, F-19) ────────────────────────────────────────────

def test_binding_covers_twelve_properties():
    assert len(REQUIRED_BINDING_PROPERTIES) == 12
    for prop in ("manifest_id", "canonical_id", "platform", "format", "draft_id",
                 "manifest_hash", "package_hash", "manuscript_hash", "cover_hash",
                 "kdp_draft_hash", "repair_revision", "adapter_identity"):
        assert prop in REQUIRED_BINDING_PROPERTIES


def test_no_production_adapter_ships():
    """The default gate must be honest that nothing in this build reaches a storefront."""
    assert PRODUCTION_ADAPTERS == frozenset()
    gate = EvidenceGate.production()
    assert gate.accepted_adapters == frozenset()
    assert "no adapter is authorised" in gate.describe()


def test_default_engine_cannot_advance_past_staged():
    with harness(adapter=MockKDPAdapter(), production_gate=True) as h:
        mid = h.discover(h.make_package())
        assert h.engine.audit(mid)["passed"]
        assert "error" not in h.engine.stage(mid)

        assert "error" in h.engine.preview(mid)
        assert h.db.get_state(mid) == PublishState.STAGED.value
        assert h.engine.get_status(mid)["ready"] is False


def test_mock_evidence_never_satisfies_the_gate():
    with harness(adapter=MockKDPAdapter(), gate=IsolatedTestAdapter.gate()) as h:
        mid = h.discover(h.make_package())
        assert h.engine.audit(mid)["passed"]
        assert "error" not in h.engine.stage(mid)
        assert "error" in h.engine.preview(mid)

        stored = h.db.get_platform_evidence(mid)
        assert stored, "evidence should still be recorded for the audit trail"
        assert all(row["evidence_class"] == EVIDENCE_MOCK for row in stored)
        assert h.db.get_state(mid) == PublishState.STAGED.value


def test_forged_evidence_row_does_not_satisfy_the_gate():
    """A hand-written platform_evidence row was the bypass the old suite relied on."""
    with harness() as h:
        mid = h.discover(h.make_package())
        assert h.engine.audit(mid)["passed"]
        assert "error" not in h.engine.stage(mid)

        manifest = h.db.load_manifest(mid)
        fingerprint = h.engine._revision_fingerprint(mid, manifest)

        # Correct binding, correct class, correct adapter name, claiming success —
        # but unsigned, so it must fall at the signature check specifically.
        h.db.save_platform_evidence(mid, {
            "adapter_type": "kdp-isolated-test",
            "evidence_class": EVIDENCE_ISOLATED_TEST,
            "platform": "kdp",
            "draft_id": "AYK5W5QVJCJOE",
            "operation_id": "preview",
            "binding": fingerprint.to_dict(),
            "signature": "0" * 64,
            "outcome": EVIDENCE_OUTCOME_SUCCESS,
            "data": {"forged": True},
        })
        ok, why = h.db.has_bound_evidence(mid, "preview", fingerprint, h.engine.evidence_gate)
        assert ok is False
        assert "signature" in why


def test_evidence_without_a_binding_is_refused():
    with harness() as h:
        mid = h.discover(h.make_package())
        fingerprint = h.engine._revision_fingerprint(mid, h.db.load_manifest(mid))

        h.db.save_platform_evidence(mid, {
            "adapter_type": "kdp-isolated-test",
            "evidence_class": EVIDENCE_ISOLATED_TEST,
            "operation_id": "preview",
            "data": {},
        })
        ok, why = h.db.has_bound_evidence(mid, "preview", fingerprint, h.engine.evidence_gate)
        assert ok is False
        assert "missing required properties" in why


def test_evidence_for_a_different_revision_is_refused():
    with harness() as h:
        mid = h.advance_to_awaiting_approval()
        fingerprint = h.engine._revision_fingerprint(mid, h.db.load_manifest(mid))
        assert h.db.has_bound_evidence(mid, "preview", fingerprint, h.engine.evidence_gate)[0]

        for field in ("manuscript_hash", "cover_hash", "kdp_draft_hash", "package_hash",
                      "manifest_hash", "repair_revision", "draft_id", "platform", "format",
                      "manifest_id", "canonical_id"):
            other = publisher.RevisionFingerprint(**{**fingerprint.to_dict(), field: "changed"})
            ok, why = h.db.has_bound_evidence(mid, "preview", other, h.engine.evidence_gate)
            assert ok is False, f"evidence accepted despite {field} mismatch"
            assert "different revision" in why


def test_stale_evidence_is_refused():
    with harness() as h:
        mid = h.advance_to_awaiting_approval()
        fingerprint = h.engine._revision_fingerprint(mid, h.db.load_manifest(mid))
        ok, why = h.db.has_bound_evidence(mid, "preview", fingerprint,
                                          IsolatedTestAdapter.gate(max_age_seconds=-1))
        assert ok is False
        assert "stale" in why


def test_keyring_rejects_unregistered_adapters():
    keyring = EvidenceKeyring()
    keyring.register("known")
    signature = keyring.sign("known", b"payload")
    assert keyring.verify("known", b"payload", signature) is True
    assert keyring.verify("known", b"tampered", signature) is False
    assert keyring.verify("unknown", b"payload", signature) is False


def test_isolated_adapter_cannot_satisfy_the_production_gate():
    with harness() as h:
        mid = h.advance_to_awaiting_approval()
        fingerprint = h.engine._revision_fingerprint(mid, h.db.load_manifest(mid))
        ok, why = h.db.has_bound_evidence(mid, "preview", fingerprint, EvidenceGate.production())
        assert ok is False
        assert "not accepted by gate" in why


# ─── Re-hashing before consequential actions (F-2) ───────────────────────────

def test_happy_path_reaches_approved():
    with harness() as h:
        mid = h.advance_to_awaiting_approval()
        result = h.engine.approve(mid)
        assert "error" not in result, result.get("error")
        assert h.db.get_state(mid) == PublishState.APPROVED.value
        assert h.engine.get_status(mid)["ready"] is True


def test_tampered_manuscript_cannot_be_approved():
    with harness() as h:
        pkg = h.make_package()
        mid = h.advance_to_awaiting_approval(pkg)

        (pkg / "manuscript.docx").write_bytes(b"PK\x03\x04" + b"\xff" * 4096)

        result = h.engine.approve(mid)
        assert "error" in result, "approve accepted a tampered manuscript"
        assert "changed on disk" in result["error"]
        assert h.db.get_state(mid) == PublishState.AWAITING_OWNER_APPROVAL.value


def test_tampering_after_approval_clears_readiness():
    with harness() as h:
        pkg = h.make_package()
        mid = h.advance_to_awaiting_approval(pkg)
        assert "error" not in h.engine.approve(mid)
        assert h.engine.get_status(mid)["ready"] is True

        (pkg / "manuscript.docx").write_bytes(b"PK\x03\x04" + b"\xee" * 4096)

        status = h.engine.get_status(mid)
        assert status["ready"] is False, "status still reported READY after tampering"
        assert status["blockers"], "status reported no blockers after tampering"
        assert "READY TO SUBMIT" not in status["report"]


def test_added_package_file_clears_readiness():
    """An artifact-by-artifact walk misses new files; the package hash does not."""
    with harness() as h:
        pkg = h.make_package()
        mid = h.advance_to_awaiting_approval(pkg)
        assert "error" not in h.engine.approve(mid)

        (pkg / "surprise.txt").write_text("smuggled in after approval")

        status = h.engine.get_status(mid)
        assert status["ready"] is False
        assert any("package changed" in b for b in status["blockers"])


def test_deleted_artifact_clears_readiness():
    with harness() as h:
        pkg = h.make_package()
        mid = h.advance_to_awaiting_approval(pkg)
        assert "error" not in h.engine.approve(mid)

        (pkg / "cover.jpg").unlink()

        status = h.engine.get_status(mid)
        assert status["ready"] is False
        assert any("missing from disk" in b for b in status["blockers"])


def test_submit_refuses_a_tampered_package():
    with harness() as h:
        pkg = h.make_package()
        mid = h.advance_to_awaiting_approval(pkg)
        assert "error" not in h.engine.approve(mid)

        (pkg / "manuscript.docx").write_bytes(b"PK\x03\x04" + b"\xaa" * 4096)

        assert "error" in h.engine.submit(mid)
        assert h.db.get_state(mid) == PublishState.APPROVED.value


# ─── No side effect may precede the preflight ────────────────────────────────
#
# "State did not advance" is a weaker claim than "nothing happened". Every test below
# counts adapter calls, because a submission that fires and is then disowned locally is
# still a submission.

def test_submit_does_not_touch_the_platform_when_the_manuscript_is_tampered():
    adapter = RecordingAdapter()
    with harness(adapter=adapter) as h:
        pkg = h.make_package()
        mid = h.advance_to_awaiting_approval(pkg)
        assert "error" not in h.engine.approve(mid)
        adapter.reset()

        (pkg / "manuscript.docx").write_bytes(b"PK\x03\x04" + b"\xaa" * 4096)

        result = h.engine.submit(mid)
        assert "error" in result
        assert adapter.count("submit") == 0, f"platform was contacted: {adapter.calls}"
        assert adapter.platform_calls == 0, f"platform was contacted: {adapter.calls}"
        assert h.db.get_state(mid) == PublishState.APPROVED.value


def test_submit_does_not_touch_the_platform_when_the_price_is_rewritten():
    adapter = RecordingAdapter()
    with harness(adapter=adapter) as h:
        pkg = h.make_package()
        mid = h.advance_to_awaiting_approval(pkg)
        assert "error" not in h.engine.approve(mid)
        adapter.reset()

        draft = pkg / "KDP-DRAFT.md"
        draft.write_text(draft.read_text().replace("$3.99", "$99.99"))

        assert "error" in h.engine.submit(mid)
        assert adapter.platform_calls == 0, f"platform was contacted: {adapter.calls}"


def test_submit_does_not_touch_the_platform_when_a_staged_copy_is_tampered():
    adapter = RecordingAdapter()
    with harness(adapter=adapter) as h:
        mid = h.advance_to_awaiting_approval()
        assert "error" not in h.engine.approve(mid)
        adapter.reset()

        staged = Path(h.db.load_manifest(mid)["files"]["manuscript"]["staged_path"])
        staged.write_bytes(b"PK\x03\x04" + b"\xcc" * 4096)

        assert "error" in h.engine.submit(mid)
        assert adapter.platform_calls == 0, f"platform was contacted: {adapter.calls}"


def test_preview_does_not_touch_the_platform_when_the_manuscript_is_tampered():
    adapter = RecordingAdapter()
    with harness(adapter=adapter) as h:
        pkg = h.make_package()
        mid = h.discover(pkg)
        assert h.engine.audit(mid)["passed"]
        assert "error" not in h.engine.stage(mid)
        adapter.reset()

        (pkg / "manuscript.docx").write_bytes(b"PK\x03\x04" + b"\xaa" * 4096)

        assert "error" in h.engine.preview(mid)
        assert adapter.platform_calls == 0, f"platform was contacted: {adapter.calls}"
        assert adapter.uploads == []
        assert h.db.get_state(mid) == PublishState.STAGED.value


def test_preview_uploads_the_staged_copy_not_the_live_package_file():
    adapter = RecordingAdapter()
    with harness(adapter=adapter) as h:
        mid = h.advance_to_awaiting_approval()
        manifest = h.db.load_manifest(mid)

        assert adapter.uploads, "no artifact was uploaded"
        stage_dir = (publisher.STAGING_DIR / mid).resolve()
        for upload in adapter.uploads:
            sent = Path(upload["path"]).resolve()
            assert sent.parent == stage_dir, f"uploaded from outside staging: {sent}"
            recorded = manifest["files"][upload["artifact_type"]]
            assert str(sent) == str(Path(recorded["staged_path"]).resolve())
            assert sent != Path(recorded["path"]).resolve()


def test_staged_path_is_recorded_for_every_artifact():
    with harness() as h:
        mid = h.discover(h.make_package())
        assert h.engine.audit(mid)["passed"]
        assert "error" not in h.engine.stage(mid)
        manifest = h.db.load_manifest(mid)
        for key, finfo in manifest["files"].items():
            staged = Path(finfo["staged_path"])
            assert staged.is_file(), f"{key} has no staged copy on disk"
            assert hash_file(staged) == finfo["sha256"]


def test_preview_refuses_when_a_staged_copy_was_replaced():
    adapter = RecordingAdapter()
    with harness(adapter=adapter) as h:
        mid = h.discover(h.make_package())
        assert h.engine.audit(mid)["passed"]
        assert "error" not in h.engine.stage(mid)
        adapter.reset()

        staged = Path(h.db.load_manifest(mid)["files"]["cover"]["staged_path"])
        staged.write_bytes(b"\xff" * 512)

        result = h.engine.preview(mid)
        assert "error" in result
        assert "Staged copy" in result["error"]
        assert adapter.platform_calls == 0, f"platform was contacted: {adapter.calls}"


# ─── Evidence must attest success, not merely existence ──────────────────────

def test_operation_outcome_rejects_unknown_operations():
    outcome, why = operation_outcome("teleport-manuscript", {"success": True}, [])
    assert outcome == EVIDENCE_OUTCOME_FAILURE
    assert "unknown operation" in why


def test_operation_outcome_reads_each_operations_own_success_signal():
    assert operation_outcome("upload-cover", {"success": True}, [])[0] == EVIDENCE_OUTCOME_SUCCESS
    assert operation_outcome("upload-cover", {"success": False}, [])[0] == EVIDENCE_OUTCOME_FAILURE
    assert operation_outcome("poll-processing", {"status": "processed"}, [])[0] == EVIDENCE_OUTCOME_SUCCESS
    assert operation_outcome("poll-processing", {"status": "failed"}, [])[0] == EVIDENCE_OUTCOME_FAILURE
    assert operation_outcome("submit", {"submitted": True}, [])[0] == EVIDENCE_OUTCOME_SUCCESS
    assert operation_outcome("submit", {"submitted": False}, [])[0] == EVIDENCE_OUTCOME_FAILURE
    assert operation_outcome("submit", {"submitted": True}, ["boom"])[0] == EVIDENCE_OUTCOME_FAILURE


def test_a_failed_upload_does_not_advance_state():
    adapter = RecordingAdapter(fail="upload-manuscript")
    with harness(adapter=adapter) as h:
        mid = h.discover(h.make_package())
        assert h.engine.audit(mid)["passed"]
        assert "error" not in h.engine.stage(mid)

        result = h.engine.preview(mid)
        assert "error" in result
        assert adapter.count("upload_artifact") >= 1, "the upload should have been attempted"
        assert h.db.get_state(mid) == PublishState.STAGED.value

        rows = h.db.get_platform_evidence(mid, "upload-manuscript")
        assert rows, "the failed attempt should still be recorded"
        assert all(r["outcome"] == EVIDENCE_OUTCOME_FAILURE for r in rows)


def test_failed_processing_does_not_advance_past_upload():
    adapter = RecordingAdapter(fail="poll-processing")
    with harness(adapter=adapter) as h:
        mid = h.discover(h.make_package())
        assert h.engine.audit(mid)["passed"]
        assert "error" not in h.engine.stage(mid)

        assert "error" in h.engine.preview(mid)
        assert h.db.get_state(mid) == PublishState.PLATFORM_UPLOADED.value


def test_a_previewer_that_never_opened_does_not_advance_state():
    adapter = RecordingAdapter(fail="preview")
    with harness(adapter=adapter) as h:
        mid = h.discover(h.make_package())
        assert h.engine.audit(mid)["passed"]
        assert "error" not in h.engine.stage(mid)

        assert "error" in h.engine.preview(mid)
        assert h.db.get_state(mid) == PublishState.PLATFORM_PROCESSED.value


def test_a_rejected_submission_does_not_reach_submitted():
    adapter = RecordingAdapter()
    with harness(adapter=adapter) as h:
        mid = h.advance_to_awaiting_approval()
        assert "error" not in h.engine.approve(mid)

        adapter.fail = "submit"
        result = h.engine.submit(mid)
        assert "error" in result
        assert adapter.count("submit") == 1
        assert h.db.get_state(mid) == PublishState.APPROVED.value

        rows = h.db.get_platform_evidence(mid, "submit")
        assert rows and all(r["outcome"] == EVIDENCE_OUTCOME_FAILURE for r in rows)


def test_failure_evidence_is_signed_so_it_cannot_be_relabelled():
    adapter = RecordingAdapter(fail="upload-manuscript")
    with harness(adapter=adapter) as h:
        mid = h.discover(h.make_package())
        assert h.engine.audit(mid)["passed"]
        assert "error" not in h.engine.stage(mid)
        assert "error" in h.engine.preview(mid)

        with sqlite3.connect(h.db.db_path) as conn:
            conn.execute("UPDATE platform_evidence SET outcome = ? WHERE operation_id = ?",
                         (EVIDENCE_OUTCOME_SUCCESS, "upload-manuscript"))

        manifest = h.db.load_manifest(mid)
        fingerprint = h.engine._revision_fingerprint(mid, manifest)
        ok, why = h.db.has_bound_evidence(mid, "upload-manuscript", fingerprint,
                                          h.engine.evidence_gate)
        assert ok is False
        assert "signature" in why


# ─── Evidence binds the draft the platform actually resolved ─────────────────

def test_a_draft_the_platform_resolves_differently_is_refused():
    adapter = RecordingAdapter(resolves_draft="AZZZZZZZZZZZZ")
    with harness(adapter=adapter) as h:
        mid = h.discover(h.make_package())
        assert h.engine.audit(mid)["passed"]
        assert "error" not in h.engine.stage(mid)

        result = h.engine.preview(mid)
        assert "error" in result
        assert "Draft mismatch" in result["error"]
        assert adapter.count("upload_artifact") == 0, "uploaded to a draft it could not identify"
        assert h.db.get_state(mid) == PublishState.STAGED.value


def test_every_operation_and_evidence_row_names_the_same_draft():
    adapter = RecordingAdapter(resolves_draft="AYK5W5QVJCJOE")
    with harness(adapter=adapter) as h:
        mid = h.advance_to_awaiting_approval()
        assert "error" not in h.engine.approve(mid)
        assert "error" not in h.engine.submit(mid)

        draft_id = h.db.load_manifest(mid)["draft_id"]
        assert draft_id == "AYK5W5QVJCJOE"

        addressed = {call[1] for call in adapter.calls
                     if call[0] in ("upload_artifact", "poll_processing", "launch_previewer",
                                    "capture_preview_evidence", "submit")}
        assert addressed == {draft_id}, f"operations addressed several drafts: {addressed}"

        for operation in ("upload-manuscript", "upload-cover", "poll-processing",
                          "preview", "submit"):
            rows = h.db.get_platform_evidence(mid, operation)
            assert rows, f"no evidence recorded for {operation}"
            for row in rows:
                assert row["binding"]["draft_id"] == draft_id
                assert row["draft_id"] == draft_id


def test_repointing_the_draft_after_approval_contacts_nothing():
    adapter = RecordingAdapter()
    with harness(adapter=adapter) as h:
        mid = h.advance_to_awaiting_approval()
        assert "error" not in h.engine.approve(mid)
        adapter.reset()

        manifest = h.db.load_manifest(mid)
        manifest["draft_id"] = "AWRONGDRAFT01"
        h.db.save_manifest(mid, manifest)

        assert "error" in h.engine.submit(mid)
        assert adapter.count("submit") == 0, f"platform was contacted: {adapter.calls}"
        assert h.db.get_state(mid) == PublishState.APPROVED.value


def test_submit_refuses_a_manifest_with_no_resolved_draft():
    adapter = RecordingAdapter()
    with harness(adapter=adapter) as h:
        mid = h.advance_to_awaiting_approval()
        assert "error" not in h.engine.approve(mid)
        adapter.reset()

        manifest = h.db.load_manifest(mid)
        manifest["draft_id"] = None
        h.db.save_manifest(mid, manifest)

        assert "error" in h.engine.submit(mid)
        assert adapter.count("submit") == 0, f"platform was contacted: {adapter.calls}"


# ─── KDP-DRAFT.md is consequential (F-5) ─────────────────────────────────────

def test_kdp_draft_is_a_hashed_artifact():
    with harness() as h:
        mid = h.discover(h.make_package())
        manifest = h.db.load_manifest(mid)
        assert "kdp_draft" in manifest["files"], "KDP-DRAFT.md was excluded from the artifact walk"
        recorded = manifest["files"]["kdp_draft"]
        assert recorded["sha256"] == hash_file(Path(recorded["path"]))


def test_kdp_draft_hash_is_bound_into_the_approval_hash():
    with harness() as h:
        mid = h.discover(h.make_package())
        manifest = h.db.load_manifest(mid)
        before = build_canonical_manifest_hash(manifest)
        manifest["files"]["kdp_draft"]["sha256"] = "f" * 64
        assert build_canonical_manifest_hash(manifest) != before


def test_kdp_draft_parses_every_consequential_field():
    with harness() as h:
        mid = h.discover(h.make_package(price="3.99", draft_id="AYK5W5QVJCJOE",
                                        drm="Yes", select="On", ai_text="Yes"))
        manifest = h.db.load_manifest(mid)
        assert manifest["draft_id"] == "AYK5W5QVJCJOE"
        assert manifest["publishing"]["price"] == 3.99
        assert manifest["publishing"]["drm"] == "yes"
        assert manifest["publishing"]["kdp_select"] == "on"
        assert manifest["metadata"]["categories"] == ["History", "Cultural Studies"]
        assert manifest["metadata"]["keywords"] == ["gullah", "geechee", "sweetgrass", "lowcountry"]
        assert manifest["metadata"]["ai_disclosure"]["text"] is True
        assert manifest["metadata"]["ai_disclosure"]["cover"] is False


def test_price_change_in_kdp_draft_is_caught_at_reaudit():
    with harness() as h:
        pkg = h.make_package()
        mid = h.discover(pkg)
        assert h.engine.audit(mid)["passed"]

        draft = pkg / "KDP-DRAFT.md"
        draft.write_text(draft.read_text().replace("$3.99", "$99.99"))

        result = h.engine.audit(mid)
        assert result["passed"] is False, "a $99.99 price change survived re-audit"
        assert any("drifted" in e or "changed on disk" in e for e in result["errors"])


def test_drm_flip_in_kdp_draft_is_caught_at_reaudit():
    with harness() as h:
        pkg = h.make_package()
        mid = h.discover(pkg)
        assert h.engine.audit(mid)["passed"]

        draft = pkg / "KDP-DRAFT.md"
        draft.write_text(draft.read_text().replace("- **DRM:** No", "- **DRM:** Yes"))

        assert h.engine.audit(mid)["passed"] is False


def test_false_ai_disclosure_is_caught_at_reaudit():
    with harness() as h:
        pkg = h.make_package(ai_text="Yes")
        mid = h.discover(pkg)
        assert h.engine.audit(mid)["passed"]

        draft = pkg / "KDP-DRAFT.md"
        draft.write_text(draft.read_text().replace("- **AI-generated text:** Yes",
                                                   "- **AI-generated text:** No"))

        assert h.engine.audit(mid)["passed"] is False, "a false AI disclosure survived re-audit"


def test_draft_id_change_in_kdp_draft_is_caught_at_reaudit():
    with harness() as h:
        pkg = h.make_package()
        mid = h.discover(pkg)
        assert h.engine.audit(mid)["passed"]

        draft = pkg / "KDP-DRAFT.md"
        draft.write_text(draft.read_text().replace("AYK5W5QVJCJOE", "SOMEOTHERDRAFT"))

        assert h.engine.audit(mid)["passed"] is False


# ─── Submission gating (F-17) ────────────────────────────────────────────────

def test_submit_refuses_awaiting_owner_approval():
    with harness() as h:
        mid = h.advance_to_awaiting_approval()
        result = h.engine.submit(mid)
        assert "error" in result
        assert "Must be APPROVED" in result["error"]
        assert h.db.get_state(mid) == PublishState.AWAITING_OWNER_APPROVAL.value


def test_submit_succeeds_only_after_approval():
    with harness() as h:
        mid = h.advance_to_awaiting_approval()
        assert "error" not in h.engine.approve(mid)
        result = h.engine.submit(mid)
        assert "error" not in result, result.get("error")
        assert h.db.get_state(mid) == PublishState.SUBMITTED.value


# ─── MIME detection (F-4, F-9) ───────────────────────────────────────────────

def test_mime_detection_is_signature_based():
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        cases = [
            (b"\x89PNG\r\n\x1a\n" + b"\x00" * 8, "cover.png", "image/png"),
            (b"\xff\xd8\xff\xe0" + b"\x00" * 12, "cover.jpg", "image/jpeg"),
            (b"PK\x03\x04" + b"\x00" * 12, "book.epub", "application/epub+zip"),
            (b"PK\x03\x04" + b"\x00" * 12, "manuscript.docx",
             "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
            (b"PK\x03\x04" + b"\x00" * 12, "bundle.zip", "application/zip"),
            (b"ID3" + b"\x00" * 13, "track.mp3", "audio/mpeg"),
        ]
        for content, name, expected in cases:
            path = tmp / name
            path.write_bytes(content)
            assert detect_mime(path) == expected, f"{name} detected as {detect_mime(path)}"


def test_mime_detection_does_not_use_libmagic():
    """libmagic's answers vary by installed magic database, so it is not a dependency."""
    assert "import magic" not in PUBLISHER_PY.read_text()
    assert "python-magic" not in (PUBLISHER_PY.parent / "requirements.txt").read_text()


def test_extension_cannot_override_signature():
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "cover.png"
        path.write_bytes(b"\xff\xd8\xff\xe0" + b"\x00" * 12)
        assert detect_mime(path) == "image/jpeg"


# ─── M1: price lock ──────────────────────────────────────────────────────────

def test_m1_price_lock_blocks_audit():
    with harness() as h:
        mid = h.discover(h.make_package(price="99.99"))
        result = h.engine.audit(mid)
        assert result["passed"] is False
        assert any("Price must be $3.99" in e for e in result["errors"])


# ─── M2: duplicate package suppression ───────────────────────────────────────

def test_m2a_duplicate_package_hash_is_rejected_by_the_database():
    """Asserts the constraint by violating it. Checking that an index *exists* proves
    nothing about whether it is unique."""
    with harness() as h:
        pkg_hash = h.db.get_package_hash(h.discover(h.make_package()))
        assert pkg_hash

        conn = sqlite3.connect(str(h.db.db_path))
        try:
            raised = None
            try:
                conn.execute(
                    "INSERT INTO manifests (manifest_id, data, state, package_hash, created_at, updated_at) "
                    "VALUES ('ggb-manifest-00000000-0000-0000-0000-000000000000', '{}', 'discovered', ?, 'x', 'x')",
                    (pkg_hash,))
                conn.commit()
            except sqlite3.IntegrityError as e:
                raised = e
            assert raised is not None, "database accepted a duplicate package_hash"
        finally:
            conn.close()


def test_m2b_rediscovering_a_package_returns_the_same_manifest():
    with harness() as h:
        pkg = h.make_package()
        first = h.engine.discover(str(pkg))
        second = h.engine.discover(str(pkg))
        assert second[0]["manifest_id"] == first[0]["manifest_id"]
        assert second[0].get("duplicate") is True

        rows = h.db.atomic(lambda c: c.execute("SELECT COUNT(*) FROM manifests").fetchone()[0])
        assert rows == 1, f"expected exactly one manifest, found {rows}"


# ─── M3: symlink and hard link rejection ─────────────────────────────────────

def test_m3_symlink_inside_an_approved_root_is_rejected():
    """The link and its target both live under an approved root, so only the symlink
    branch can reject it. Building the link in a bare temp dir would let the
    approved-root branch pass this test while symlink protection was broken."""
    with harness() as h:
        pkg = h.make_package()
        link = pkg / "manuscript-link.docx"
        link.symlink_to(pkg / "manuscript.docx")

        assert h.engine._is_approved_root(link.resolve()), "target must be inside an approved root"

        raised = None
        try:
            h.engine._safe_stage_path(link)
        except ValueError as e:
            raised = e
        assert raised is not None, "symlink was accepted for staging"
        assert "Symlink" in str(raised), f"rejected for the wrong reason: {raised}"


def test_m3_hard_link_inside_an_approved_root_is_rejected():
    with harness() as h:
        pkg = h.make_package()
        link = pkg / "manuscript-hard.docx"
        os.link(pkg / "manuscript.docx", link)

        raised = None
        try:
            h.engine._safe_stage_path(link)
        except ValueError as e:
            raised = e
        assert raised is not None, "hard link was accepted for staging"
        assert "Hard link" in str(raised), f"rejected for the wrong reason: {raised}"


def test_files_outside_approved_roots_are_rejected():
    with harness() as h:
        with tempfile.TemporaryDirectory() as outside:
            stray = Path(outside) / "manuscript.docx"
            stray.write_bytes(b"PK\x03\x04")
            raised = None
            try:
                h.engine._safe_stage_path(stray)
            except ValueError as e:
                raised = e
            assert raised is not None
            assert "approved package root" in str(raised)


def test_discover_ignores_packages_outside_approved_roots():
    with harness() as h:
        with tempfile.TemporaryDirectory() as outside:
            pkg = Path(outside) / "sweetgrass"
            pkg.mkdir()
            (pkg / "manuscript.docx").write_bytes(b"PK\x03\x04")
            assert h.engine.discover(str(pkg)) == []


# ─── M4: staging integrity ───────────────────────────────────────────────────

def test_m4_staging_rolls_back_completely_on_failure():
    with harness() as h:
        pkg = h.make_package()
        mid = h.discover(pkg)
        assert h.engine.audit(mid)["passed"]

        # 'manuscript' sorts after 'cover' and 'kdp_draft', so the first two copy cleanly
        # and the third fails mid-run. The whole staging directory must disappear.
        (pkg / "manuscript.docx").write_bytes(b"PK\x03\x04" + b"\x99" * 512)

        assert "error" in h.engine.stage(mid)
        assert not (publisher.STAGING_DIR / mid).exists(), "partial staging survived a failure"
        assert h.db.get_state(mid) == PublishState.VALIDATED.value


def test_staging_can_be_retried_after_a_failure():
    with harness() as h:
        pkg = h.make_package()
        mid = h.discover(pkg)
        assert h.engine.audit(mid)["passed"]

        original = (pkg / "manuscript.docx").read_bytes()
        (pkg / "manuscript.docx").write_bytes(b"PK\x03\x04" + b"\x99" * 512)
        assert "error" in h.engine.stage(mid)

        (pkg / "manuscript.docx").write_bytes(original)
        result = h.engine.stage(mid)
        assert "error" not in result, f"retry was wedged: {result.get('error')}"


def test_staged_copies_match_their_recorded_hashes():
    with harness() as h:
        mid = h.discover(h.make_package())
        assert h.engine.audit(mid)["passed"]
        result = h.engine.stage(mid)
        assert "error" not in result

        manifest = h.db.load_manifest(mid)
        by_name = {Path(p).name: Path(p) for p in result["staged_files"]}
        for finfo in manifest["files"].values():
            assert hash_file(by_name[Path(finfo["path"]).name]) == finfo["sha256"]


# ─── Verification and hashing gaps the audit called out ─────────────────────

def test_verify_artifacts_refuses_a_path_outside_the_approved_roots():
    with harness() as h:
        mid = h.discover(h.make_package())
        outsider = h.root / "smuggled.docx"
        outsider.write_bytes(b"PK\x03\x04" + b"\x11" * 2048)

        manifest = h.db.load_manifest(mid)
        manifest["files"]["manuscript"]["path"] = str(outsider)
        manifest["files"]["manuscript"]["sha256"] = hash_file(outsider)

        problems = h.engine._verify_artifacts(manifest)
        assert any("not under an approved root" in p for p in problems), problems


def test_package_hash_notices_a_file_moved_between_subdirectories():
    """Relocation, not content swapping, is what a basename-only digest cannot see.

    Swapping the contents of two same-named files in place still changes a basename digest,
    because the walk order is unchanged and the bytes move with it — an earlier version of
    this test did that and the mutation survived it. The change a basename walk genuinely
    cannot distinguish is the same file, same bytes, in a different directory. The two
    directory names sort after every top-level package file, which keeps the moved entry in
    the same position in the walk; otherwise the reordering alone would shift the digest and
    the test would pass without the guard being present.
    """
    with harness() as h:
        pkg = h.make_package()
        (pkg / "zzz-front").mkdir()
        (pkg / "zzz-front" / "matter.txt").write_text("alpha")
        before = h.engine._hash_package(pkg)

        (pkg / "zzz-back").mkdir()
        (pkg / "zzz-front" / "matter.txt").rename(pkg / "zzz-back" / "matter.txt")
        (pkg / "zzz-front").rmdir()

        assert h.engine._hash_package(pkg) != before, \
            "hashing basenames lets a file change directory unnoticed"


def test_the_repairs_directory_is_an_artifact_root_but_not_a_package_source():
    with harness() as h:
        assert publisher.REPAIRS_DIR in publisher.approved_artifact_roots()
        assert publisher.REPAIRS_DIR not in publisher.approved_package_roots(), \
            "the engine's own scratch directory must not be somewhere packages come from"

        stray = publisher.REPAIRS_DIR / "planted"
        stray.mkdir(parents=True, exist_ok=True)
        (stray / "KDP-DRAFT.md").write_text("# KDP Draft\n- **Title:** Sweetgrass\n")
        assert h.engine.discover(str(stray)) == []


def test_a_repaired_cover_is_still_stageable():
    from PIL import Image

    with harness() as h:
        pkg = h.make_package()
        Image.new("RGB", (500, 800), (9, 9, 9)).save(pkg / "cover.jpg", "JPEG", quality=90)
        mid = h.discover(pkg)
        assert not h.engine.audit(mid)["passed"], "undersized cover should fail the audit"

        assert h.engine.repair(mid)["count"] >= 1
        repaired = Path(h.db.load_manifest(mid)["files"]["cover"]["path"])
        assert h.engine._is_approved_root(repaired), \
            f"repair produced a path staging can never accept: {repaired}"

        assert h.engine.audit(mid)["passed"]
        result = h.engine.stage(mid)
        assert "error" not in result, result.get("error")


def test_gate_authority_reclaims_expired_tokens():
    authority = GateAuthority()
    mid = "ggb-manifest-00000000-0000-4000-8000-000000000000"
    for _ in range(50):
        authority.issue(mid, PublishState.APPROVED)
    assert authority.outstanding_count() == 50

    authority.TOKEN_TTL_SECONDS = -1  # every token already outstanding is now expired
    authority.issue(mid, PublishState.APPROVED)
    assert authority.outstanding_count() == 1, "expired tokens were never reclaimed"


def test_gate_authority_caps_outstanding_tokens():
    authority = GateAuthority()
    authority.MAX_OUTSTANDING = 8
    mid = "ggb-manifest-00000000-0000-4000-8000-000000000000"
    for _ in range(40):
        authority.issue(mid, PublishState.APPROVED)
    assert authority.outstanding_count() <= authority.MAX_OUTSTANDING + 1


def test_an_unexpired_token_still_redeems_exactly_once():
    authority = GateAuthority()
    mid = "ggb-manifest-00000000-0000-4000-8000-000000000000"
    token = authority.issue(mid, PublishState.APPROVED)
    for _ in range(20):
        authority.issue(mid, PublishState.APPROVED)

    ok, _ = authority.redeem(token, mid, PublishState.APPROVED)
    assert ok is True
    ok, _ = authority.redeem(token, mid, PublishState.APPROVED)
    assert ok is False


def test_direct_runner_refuses_to_silently_skip_a_test_it_cannot_call():
    import types

    import run_tests

    module = types.ModuleType("fake_suite")
    module.test_zero_arg = lambda: None

    def test_needs_a_fixture(tmp_path):
        pass

    module.test_needs_a_fixture = test_needs_a_fixture

    tests, uncollectable = run_tests.collect(module)
    assert [name for name, _ in tests] == ["test_zero_arg"]
    assert uncollectable == ["test_needs_a_fixture"], \
        "an arg-taking test must be reported, not dropped — pytest would have run it"


def test_network_scan_covers_the_whole_engine_and_still_bites():
    import network_scan

    assert network_scan.scan() == [], "unallowlisted network access under ggb-engine/"

    # The allowlist is the only thing standing between a file and a failed build, so
    # every entry must name a file that exists — a stale entry silently widens it.
    for rel in network_scan.ALLOWLIST:
        assert (network_scan.ENGINE_DIR / rel).is_file(), f"stale allowlist entry: {rel}"

    assert network_scan.violations_in("import urllib.parse\n", "x.py") == []
    assert network_scan.violations_in("import urllib.request\n", "x.py") == [(1, "urllib.request")]
    assert network_scan.violations_in("from requests import get\n", "x.py") == [(1, "requests")]
    assert network_scan.violations_in("import json, socket\n", "x.py") == [(1, "socket")]

    with tempfile.TemporaryDirectory() as tmp:
        planted = Path(tmp) / "sneaky.py"
        planted.write_text("import requests\n")
        assert network_scan.scan(Path(tmp)) == [("sneaky.py", 1, "requests")]


def test_publisher_itself_is_never_allowlisted_for_network_access():
    import network_scan

    assert "publisher.py" not in network_scan.ALLOWLIST
    assert network_scan.violations_in(PUBLISHER_PY.read_text(), "publisher.py") == []


def test_direct_runner_discovers_every_suite_file():
    import run_tests

    found = {p.name for p in run_tests.suite_files()}
    on_disk = {p.name for p in Path(__file__).resolve().parent.glob("test_*.py")}
    assert found == on_disk, "the runner hardcodes a filename instead of discovering them"


def test_resume_offers_no_action_it_cannot_perform():
    with harness() as h:
        mid = h.advance_to_awaiting_approval()
        with sqlite3.connect(h.db.db_path) as conn:
            conn.execute("UPDATE manifests SET state = 'preview_clean' WHERE manifest_id = ?",
                         (mid,))
        guidance = h.engine.resume(mid)
        assert guidance["next_action"] != "approve", \
            "approve() refuses preview_clean, so resume must not recommend it"
        assert guidance["can_resume"] is False


# ─── Test-mode roots (F-15) ──────────────────────────────────────────────────

def test_ggb_test_root_requires_test_mode():
    saved = {k: os.environ.pop(k, None) for k in ("GGB_TEST_MODE", "GGB_TEST_PACKAGE_ROOT")}
    try:
        assert publisher.test_mode_enabled() is False
        assert Path.home() / ".ggb-test" not in publisher.approved_package_roots()

        os.environ["GGB_TEST_MODE"] = "1"
        assert Path.home() / ".ggb-test" in publisher.approved_package_roots()
    finally:
        os.environ.pop("GGB_TEST_MODE", None)
        for key, value in saved.items():
            if value is not None:
                os.environ[key] = value


def test_production_roots_are_never_temp_directories():
    for root in APPROVED_PACKAGE_ROOTS:
        assert not str(root).startswith("/tmp"), f"{root} is a temp path"


# ─── Manifest ID validation ──────────────────────────────────────────────────

def test_manifest_id_validation_rejects_traversal():
    for bad in ("../../etc/passwd", "ggb-manifest-../x", "", None, "ggb-manifest-xyz",
                "ggb-manifest-00000000-0000-0000-0000-00000000000",
                "ggb-manifest-00000000-0000-0000-0000-000000000000/../x"):
        assert validate_manifest_id(bad) is False, f"{bad!r} was accepted"


def test_manifest_id_validation_accepts_real_ids():
    assert validate_manifest_id("ggb-manifest-0f8fad5b-d9cb-469f-a165-70867728950e") is True


# ─── Canonical hash coverage ─────────────────────────────────────────────────

def test_canonical_hash_binds_every_consequential_field():
    with harness() as h:
        manifest = h.db.load_manifest(h.discover(h.make_package()))
        baseline = build_canonical_manifest_hash(manifest)

        mutations = [
            lambda m: m["title"].update({"canonical": "Something Else"}),
            lambda m: m.update({"author": "Someone Else"}),
            lambda m: m.update({"publisher": "Another Press"}),
            lambda m: m.update({"target_platform": "d2d"}),
            lambda m: m.update({"draft_id": "OTHER"}),
            lambda m: m.update({"format": "paperback"}),
            lambda m: m.update({"language": "fr"}),
            lambda m: m["publishing"].update({"price": 99.99}),
            lambda m: m["publishing"].update({"drm": "yes"}),
            lambda m: m["publishing"].update({"kdp_select": "on"}),
            lambda m: m["rights"].update({"territories": "US only"}),
            lambda m: m["metadata"].update({"description": "different"}),
            lambda m: m["metadata"].update({"keywords": ["other"]}),
            lambda m: m["metadata"].update({"categories": ["Other"]}),
            lambda m: m["metadata"]["ai_disclosure"].update({"text": True}),
            lambda m: m["files"]["manuscript"].update({"sha256": "a" * 64}),
            lambda m: m["files"]["cover"].update({"sha256": "b" * 64}),
            lambda m: m["files"]["kdp_draft"].update({"sha256": "c" * 64}),
        ]
        for index, mutate in enumerate(mutations):
            copy_of = json.loads(json.dumps(manifest))
            mutate(copy_of)
            assert build_canonical_manifest_hash(copy_of) != baseline, \
                f"mutation {index} did not change the canonical hash"


# ─── CLI exit codes ──────────────────────────────────────────────────────────

def _run_cli(args, env=None):
    return subprocess.run([sys.executable, str(PUBLISHER_PY)] + args,
                          capture_output=True, text=True, timeout=120,
                          env=env or dict(os.environ))


def test_cli_rejects_an_invalid_manifest_id():
    with harness() as h:
        result = _run_cli(["--json", "status", "../../etc/passwd"], env=cli_env(h.root))
        assert result.returncode == 1
        assert "error" in result.stdout.lower()


def test_cli_reports_missing_manifests_with_exit_one():
    with harness() as h:
        result = _run_cli(["--json", "status",
                           "ggb-manifest-0f8fad5b-d9cb-469f-a165-70867728950e"],
                          env=cli_env(h.root))
        assert result.returncode == 1


def test_cli_requires_a_subcommand():
    with harness() as h:
        assert _run_cli([], env=cli_env(h.root)).returncode != 0


def test_cli_dry_run_makes_no_changes():
    with harness() as h:
        result = _run_cli(["--dry-run", "--json", "discover", str(h.make_package())],
                          env=cli_env(h.root))
        assert result.returncode == 0


# ─── Isolation (F-20) ────────────────────────────────────────────────────────

def test_tests_do_not_write_into_the_repository():
    repo_engine_dir = PUBLISHER_PY.parent
    with harness() as h:
        mid = h.advance_to_awaiting_approval()
        assert "error" not in h.engine.approve(mid)
        for stray in (repo_engine_dir.parent / "publish", repo_engine_dir / "publish"):
            assert not stray.exists(), f"test run created {stray} inside the repository"
