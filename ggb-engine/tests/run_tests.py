#!/usr/bin/env python3
"""Dependency-free runner for the publisher suite.

It exists so the suite can run where pytest is not installed. It must have exactly the
same detection power as pytest: every test is called, every AssertionError is a failure,
and any failure makes the process exit nonzero. The previous runner counted failures and
still exited 0, which is why 21 red checks were reported as a green build.
"""

import importlib.util
import sys
import time
import traceback
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent


def load_suite(path: Path):
    spec = importlib.util.spec_from_file_location(path.stem, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[path.stem] = module
    spec.loader.exec_module(module)
    return module


def suite_files():
    """Every test_*.py in this directory. Hardcoding one filename meant a new suite file
    would run under pytest and be invisible here, and CI would stay green either way."""
    return sorted(p for p in TESTS_DIR.glob("test_*.py") if p.is_file())


def collect(module):
    """Zero-argument test callables, and the names this runner cannot invoke.

    Silently dropping an arg-taking test_* is how the two runners drift apart: pytest
    would supply a fixture and run it, this runner would skip it, and the disagreement
    would never surface. Uncollectable tests are returned so the caller can fail on them.
    """
    tests, uncollectable = [], []
    for name, obj in sorted(vars(module).items()):
        if not name.startswith("test_") or not callable(obj):
            continue
        code = getattr(obj, "__code__", None)
        if code is None or code.co_argcount != 0:
            uncollectable.append(name)
        else:
            tests.append((name, obj))
    return tests, uncollectable


def main() -> int:
    tests, uncollectable = [], []
    for path in suite_files():
        module_tests, module_uncollectable = collect(load_suite(path))
        tests += [(f"{path.stem}::{name}", fn) for name, fn in module_tests]
        uncollectable += [f"{path.stem}::{name}" for name in module_uncollectable]

    if uncollectable:
        print("FATAL: these tests take arguments and cannot be run by this runner, "
              "so it and pytest would disagree:", file=sys.stderr)
        for name in uncollectable:
            print(f"  {name}", file=sys.stderr)
        return 2

    if not tests:
        print("FATAL: collected zero tests", file=sys.stderr)
        return 2

    failures = []
    start = time.time()
    for name, fn in tests:
        try:
            fn()
        except BaseException:  # noqa: BLE001 — a runner that swallows nothing
            failures.append((name, traceback.format_exc()))
            sys.stdout.write("F")
        else:
            sys.stdout.write(".")
        sys.stdout.flush()
    print()

    for name, tb in failures:
        print(f"\n{'=' * 70}\nFAILED {name}\n{'-' * 70}\n{tb}")

    elapsed = time.time() - start
    print(f"{len(tests) - len(failures)} passed, {len(failures)} failed in {elapsed:.2f}s")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
