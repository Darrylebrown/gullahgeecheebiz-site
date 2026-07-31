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


def collect(module):
    return [(name, obj) for name, obj in sorted(vars(module).items())
            if name.startswith("test_") and callable(obj)
            and obj.__code__.co_argcount == 0]


def main() -> int:
    module = load_suite(TESTS_DIR / "test_publisher.py")
    tests = collect(module)
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
