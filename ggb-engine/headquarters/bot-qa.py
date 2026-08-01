#!/usr/bin/env python3
"""
GGB Quality Assurance Bot — reviews every package before it enters the pipeline.
Flags weak descriptions, missing keywords, formatting issues, metadata gaps.
"""
import json, sys
from pathlib import Path
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from publisher import REPO_ROOT

LANDING_PAD = REPO_ROOT / "publish" / "landing-pad"

class QABot:
    def __init__(self):
        self.stats = {"passed": 0, "flagged": 0, "errors": 0}

    def review_package(self, pkg_dir: Path) -> dict:
        issues = []
        draft = pkg_dir / "KDP-DRAFT.md"
        manuscript = pkg_dir / "manuscript.md"

        if not draft.exists():
            issues.append("Missing KDP-DRAFT.md")
        else:
            text = draft.read_text()
            if len(text) < 100:
                issues.append("KDP-DRAFT.md too short")
            if "## Description" not in text:
                issues.append("Missing description section")
            if "## Keywords" not in text:
                issues.append("Missing keywords section")
            if "## Categories" not in text:
                issues.append("Missing categories section")

        if not manuscript.exists():
            issues.append("Missing manuscript.md")
        else:
            text = manuscript.read_text()
            if len(text) < 500:
                issues.append("Manuscript too short (<500 chars)")
            if "## Chapter" not in text:
                issues.append("No chapters found")
            if "## Introduction" not in text:
                issues.append("No introduction section")

        covers = list(pkg_dir.glob("cover.*"))
        if not covers:
            issues.append("Missing cover image")

        if issues:
            self.stats["flagged"] += 1
        else:
            self.stats["passed"] += 1

        return {"package": pkg_dir.name, "passed": len(issues) == 0, "issues": issues}

    def scan_all(self) -> dict:
        results = []
        if LANDING_PAD.exists():
            for pkg_dir in sorted(LANDING_PAD.iterdir()):
                if pkg_dir.is_dir():
                    results.append(self.review_package(pkg_dir))
        return {"results": results, "stats": self.stats}


if __name__ == "__main__":
    bot = QABot()
    result = bot.scan_all()
    print(json.dumps(result, indent=2))
