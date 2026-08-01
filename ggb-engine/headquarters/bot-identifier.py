#!/usr/bin/env python3
"""
GGB ISBN/Identifier Bot — assigns identifiers, registers metadata,
and prepares catalog entries for every package in the pipeline.
"""
import json, sys, uuid
from pathlib import Path
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from publisher import REPO_ROOT

IDENTIFIER_DB = REPO_ROOT / "publish" / "identifiers" / "identifiers.json"
IDENTIFIER_DB.parent.mkdir(parents=True, exist_ok=True)

class IdentifierBot:
    def __init__(self):
        self.stats = {"assigned": 0}
        self._load_db()

    def _load_db(self):
        if IDENTIFIER_DB.exists():
            self.db = json.loads(IDENTIFIER_DB.read_text())
        else:
            self.db = {"next_isbn": 9780000000001, "identifiers": []}

    def _save_db(self):
        IDENTIFIER_DB.write_text(json.dumps(self.db, indent=2))

    def assign_identifiers(self, title: str, category: str = "self-help") -> dict:
        isbn = str(self.db["next_isbn"])
        self.db["next_isbn"] += 1
        entry = {
            "id": f"ggb-id-{uuid.uuid4().hex[:8]}",
            "title": title,
            "isbn": isbn,
            "category": category,
            "language": "en",
            "publisher": "Gullah Geechee Biz",
            "author": "Darryl Elliott Brown",
            "registered_at": datetime.now(timezone.utc).isoformat(),
        }
        self.db["identifiers"].append(entry)
        self._save_db()
        self.stats["assigned"] += 1
        return entry


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("title", help="Book title")
    parser.add_argument("--category", default="self-help")
    args = parser.parse_args()
    bot = IdentifierBot()
    result = bot.assign_identifiers(args.title, args.category)
    print(json.dumps(result, indent=2))
