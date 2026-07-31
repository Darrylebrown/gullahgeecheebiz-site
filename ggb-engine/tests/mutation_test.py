#!/usr/bin/env python3
"""Mutation testing for the publisher's four load-bearing guards.

A passing test suite proves nothing on its own — it may simply not be looking. This
harness removes one guard at a time from a throwaway copy of publisher.py and requires
the suite to go red. A mutation that survives is a guard nobody is testing.

Both runners are exercised for every mutation. A prior version of this system had a
suite that failed under the direct runner and passed under pytest, so "the suite went
red" is only meaningful if it is true of the runner CI actually invokes.
"""

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
ENGINE_DIR = TESTS_DIR.parent

# (id, description, original source, replacement)
MUTATIONS = [
    (
        "M1",
        "price lock no longer rejects an off-policy price",
        "    if policy.price_locked and policy.price is not None:\n"
        "        if abs(requested_price - policy.price) > 0.01:\n"
        "            return False, f\"Price must be ${policy.price:.2f} for "
        "'{canonical_id}' (got ${requested_price:.2f})\"\n",
        "",
    ),
    (
        "M2",
        "package_hash index is no longer UNIQUE, so duplicates can be inserted",
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_manifests_package_hash "
        "ON manifests(package_hash);",
        "CREATE INDEX IF NOT EXISTS idx_manifests_package_hash ON manifests(package_hash);",
    ),
    (
        "M3",
        "staging no longer rejects symlinks",
        "        if path.is_symlink():\n"
        "            raise ValueError(f\"Symlinks not allowed: {path}\")\n",
        "",
    ),
    (
        "M4",
        "gated transitions no longer re-verify artifact and package hashes",
        "        if to_state in HASH_REVALIDATION_STATES:\n"
        "            problems += self._verify_artifacts(manifest)\n"
        "            problems += self._verify_package(manifest_id, manifest)\n"
        "            problems += self._verify_kdp_draft(manifest)\n",
        "",
    ),
]

RUNNERS = [
    ("pytest", [sys.executable, "-m", "pytest", "-q", "test_publisher.py"]),
    ("run_tests", [sys.executable, "run_tests.py"]),
]


def build_sandbox(root: Path) -> Path:
    """A self-contained copy of the engine, so a mutated publisher.py never touches
    the working tree."""
    engine = root / "ggb-engine"
    (engine / "tests").mkdir(parents=True)
    shutil.copy2(ENGINE_DIR / "publisher.py", engine / "publisher.py")
    shutil.copy2(ENGINE_DIR / "requirements.txt", engine / "requirements.txt")
    shutil.copytree(ENGINE_DIR / "schemas", engine / "schemas")
    for name in ("harness.py", "test_publisher.py", "run_tests.py"):
        shutil.copy2(TESTS_DIR / name, engine / "tests" / name)
    (root / "package.json").write_text('{"name":"mutation-sandbox"}')
    return engine


def run_suite(engine: Path, runner: list) -> subprocess.CompletedProcess:
    return subprocess.run(runner, cwd=engine / "tests", capture_output=True,
                          text=True, timeout=900)


def apply_mutation(engine: Path, original: str, replacement: str) -> None:
    source = (engine / "publisher.py").read_text()
    if source.count(original) != 1:
        raise SystemExit(
            f"mutation target is not unique in publisher.py "
            f"(found {source.count(original)} occurrences) — the harness is stale")
    (engine / "publisher.py").write_text(source.replace(original, replacement))


def main() -> int:
    survivors = []

    # Baseline: the unmutated copy must be green under both runners, otherwise a red
    # result below proves nothing.
    with tempfile.TemporaryDirectory(prefix="ggb-mutation-base-") as tmp:
        engine = build_sandbox(Path(tmp))
        for name, runner in RUNNERS:
            result = run_suite(engine, runner)
            if result.returncode != 0:
                print(f"BASELINE FAILED under {name}; mutation results would be "
                      f"meaningless.\n{result.stdout[-4000:]}\n{result.stderr[-4000:]}")
                return 2
        print("baseline: green under pytest and run_tests")

    for mid, description, original, replacement in MUTATIONS:
        for runner_name, runner in RUNNERS:
            with tempfile.TemporaryDirectory(prefix=f"ggb-mutation-{mid}-") as tmp:
                engine = build_sandbox(Path(tmp))
                apply_mutation(engine, original, replacement)
                result = run_suite(engine, runner)
                killed = result.returncode != 0
                print(f"{mid} [{runner_name}] {'KILLED ' if killed else 'SURVIVED'} "
                      f"— {description}")
                if not killed:
                    survivors.append(f"{mid} under {runner_name}")

    if survivors:
        print(f"\n{len(survivors)} surviving mutation(s): {', '.join(survivors)}")
        return 1
    print("\nall mutations killed under both runners")
    return 0


if __name__ == "__main__":
    sys.exit(main())
