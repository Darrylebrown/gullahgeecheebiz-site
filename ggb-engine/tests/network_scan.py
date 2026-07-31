#!/usr/bin/env python3
"""Fail if anything under ggb-engine/ reaches the network, except where allowlisted.

The previous CI step was named "no network calls in the engine" but only looked at
publisher.py and tests/, while engine.py has called out to a local hub since before this
control plane existed. A check that is narrower than its name is worse than no check,
because it is quoted as evidence. This one walks the whole tree and states its exceptions.

It works on the AST rather than by grepping, so `urllib.parse` — string handling, no I/O
— does not trip it while `urllib.request` does.
"""

import ast
import sys
from pathlib import Path

ENGINE_DIR = Path(__file__).resolve().parent.parent

NETWORK_MODULES = {
    "aiohttp", "asyncio.streams", "ftplib", "http.client", "http.server", "httplib2",
    "httpx", "paramiko", "requests", "smtplib", "socket", "socketserver", "telnetlib",
    "urllib.request", "urllib3", "websocket", "websockets", "xmlrpc.client",
}

# Path relative to ggb-engine/ → why it is allowed to reach the network. Both entries
# predate the publisher control plane and are byte-identical to main; the point of the
# allowlist is that they are named here rather than hidden by a narrow search path.
ALLOWLIST = {
    "engine.py": "registers with the local content hub on 127.0.0.1:8770",
    "hub.py": "is the local content hub — it binds a loopback HTTP server",
    "buffer.py": "serves the local job-queue dashboard over a loopback HTTP server",
}


def _module_is_network(name: str) -> bool:
    if not name:
        return False
    parts = name.split(".")
    return any(".".join(parts[:i]) in NETWORK_MODULES for i in range(1, len(parts) + 1))


def violations_in(source: str, label: str):
    """Every import of a networking module, as (line, offending name) pairs."""
    found = []
    for node in ast.walk(ast.parse(source, filename=label)):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if _module_is_network(alias.name):
                    found.append((node.lineno, alias.name))
        elif isinstance(node, ast.ImportFrom) and node.level == 0:
            if _module_is_network(node.module or ""):
                found.append((node.lineno, node.module))
    return found


def scan(root: Path = ENGINE_DIR):
    report = []
    for path in sorted(root.rglob("*.py")):
        rel = path.relative_to(root).as_posix()
        if rel in ALLOWLIST:
            continue
        for lineno, name in violations_in(path.read_text(encoding="utf-8"), rel):
            report.append((rel, lineno, name))
    return report


def main() -> int:
    report = scan()
    if report:
        print("Network access outside the allowlist:", file=sys.stderr)
        for rel, lineno, name in report:
            print(f"  {rel}:{lineno} imports {name}", file=sys.stderr)
        return 1
    covered = ", ".join(sorted(ALLOWLIST)) or "none"
    print(f"No unallowlisted network access under {ENGINE_DIR.name}/ (allowlisted: {covered})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
