#!/usr/bin/env python3
"""
GGB Agent Training Ground — runs the batch production engine through
the full agent pipeline: discovery → validation → staging → preview → readiness.
All mock. All safe. All training.
"""
import json, sys, uuid, subprocess, time
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from publisher import PublishEngine, StateStore, REPO_ROOT
from PIL import Image
import shutil

TRAINING_DIR = REPO_ROOT / "ggb-engine" / "headquarters" / "training"
PYTHON = sys.executable
BOTS_DIR = Path(__file__).resolve().parent.parent / "bots"
HQ_DIR = Path(__file__).resolve().parent

class AgentTrainingGround:
    """Runs batch production through the full agent pipeline for training."""

    def __init__(self):
        self.start_time = datetime.now(timezone.utc)
        self.stats = {
            "packages_created": 0,
            "packages_discovered": 0,
            "packages_validated": 0,
            "packages_staged": 0,
            "packages_previewed": 0,
            "packages_approved": 0,
            "packages_uploaded": 0,
            "errors": [],
        }

    def setup_training_batch(self, count: int = 10) -> Path:
        """Create a small training batch of packages."""
        batch_dir = TRAINING_DIR / f"batch-{uuid.uuid4().hex[:8]}"
        batch_dir.mkdir(parents=True, exist_ok=True)

        topics = [
            ("Encyclopedia Volume 01", "self-help", 9.99),
            ("Encyclopedia Volume 01", "self-help", 9.99),
            ("Encyclopedia Volume 01", "self-help", 9.99),
            ("Encyclopedia Volume 01", "self-help", 9.99),
            ("Encyclopedia Volume 01", "self-help", 9.99),
            ("Encyclopedia Volume 01", "self-help", 9.99),
            ("Encyclopedia Volume 01", "self-help", 9.99),
            ("Encyclopedia Volume 01", "self-help", 9.99),
            ("Encyclopedia Volume 01", "self-help", 9.99),
            ("Encyclopedia Volume 01", "self-help", 9.99),
        ][:count]

        for i, (title, category, price) in enumerate(topics):
            slug = f"training-{i+1:03d}-{title.lower().replace(' ', '-')}"
            pkg = batch_dir / slug
            pkg.mkdir(parents=True, exist_ok=True)

            # Manuscript
            (pkg / "manuscript.md").write_text(f"""# {title}

## A Gullah Geechee Guide

### By Darryl Elliott Brown

---

## Introduction
Welcome to {title.lower()}. This guide draws on the wisdom of the Gullah Geechee people.

## Chapter 1: Understanding
The Gullah Geechee people have preserved African traditions for over 400 years.

## Chapter 2: Practical Steps
Every journey begins with a single step.

## Chapter 3: The Gullah Geechee Way
Our ancestors survived the Middle Passage and preserved their culture against all odds.

## Conclusion
{title} is not just a skill — it's a journey.

*Darryl Elliott Brown*
*Gullah Geechee Biz*
""")

            # KDP Draft
            (pkg / "KDP-DRAFT.md").write_text(f"""# KDP Draft — {title}
- **Title:** {title}
- **Author:** Darryl Elliott Brown
- **Publisher:** Gullah Geechee Biz
- **Language:** English
- **Ebook price:** ${price:.2f}
- **DRM:** No
- **KDP Select:** Off
## Description
A guide to {title.lower()}, drawing on Gullah Geechee wisdom.
## Categories
- {category.title()}
## Keywords
{title.lower()}, gullah geechee, {category}
""")

            # Cover
            cover = Image.new("RGB", (1600, 2560), color=(26, 26, 46))
            cover.save(str(pkg / "cover.jpg"), "JPEG", quality=95)
            self.stats["packages_created"] += 1

        print(f"  Created {count} training packages in {batch_dir}")
        return batch_dir

    def run_pipeline(self, batch_dir: Path) -> Dict:
        """Run all packages through the full agent pipeline."""
        db_path = batch_dir / "training.db"
        store = StateStore(db_path)
        engine = PublishEngine(db=store)

        # 1. Discover all packages
        print(f"\n  Phase 1: Discovery")
        discovered = []
        for pkg_dir in sorted(batch_dir.iterdir()):
            if pkg_dir.is_dir():
                result = engine.discover(str(pkg_dir))
                discovered.extend(result)
        self.stats["packages_discovered"] = len(discovered)
        print(f"  Discovered {len(discovered)} packages")

        # 2. Run each through the pipeline
        print(f"\n  Phase 2: Pipeline")
        for i, pkg_info in enumerate(discovered):
            mid = pkg_info["manifest_id"]
            title = pkg_info.get("title", f"Package {i+1}")

            try:
                # Reconcile
                engine.reconcile(mid)
                self.stats["packages_validated"] += 1

                # Audit
                audit = engine.audit(mid)
                if not audit.get("passed"):
                    self.stats["errors"].append(f"{title}: audit failed")
                    continue

                # Stage
                stage = engine.stage(mid)
                if "error" in stage:
                    self.stats["errors"].append(f"{title}: stage failed - {stage['error']}")
                    continue
                self.stats["packages_staged"] += 1

                # Preview
                preview = engine.preview(mid)
                if "error" in preview:
                    self.stats["errors"].append(f"{title}: preview failed - {preview['error']}")
                    continue
                self.stats["packages_previewed"] += 1

                if (i + 1) % 5 == 0:
                    print(f"  [{i+1}/{len(discovered)}] {title[:40]}...")

            except Exception as e:
                self.stats["errors"].append(f"{title}: {str(e)[:100]}")

        # 3. Run Agent A review (via engine directly)
        print(f"\n  Phase 3: Agent A Review")
        for i, pkg_info in enumerate(discovered):
            mid = pkg_info["manifest_id"]
            title = pkg_info.get("title", f"Package {i+1}")
            try:
                result = engine.approve(mid, owner="agent-a-training")
                if "approval_hash" in result:
                    self.stats["packages_approved"] += 1
            except Exception as e:
                self.stats["errors"].append(f"{title}: Agent A approval failed - {str(e)[:100]}")

        # 4. Run Agent B upload (via engine adapter directly)
        print(f"\n  Phase 4: Agent B Upload (Mock)")
        for i, pkg_info in enumerate(discovered):
            mid = pkg_info["manifest_id"]
            title = pkg_info.get("title", f"Package {i+1}")
            try:
                manifest = engine.db.load_manifest(mid)
                if manifest:
                    auth = engine.adapter.check_auth()
                    if auth.get("authenticated"):
                        draft_id = manifest.get("draft_id", "mock-draft")
                        for key in ["manuscript", "cover"]:
                            finfo = manifest.get("files", {}).get(key)
                            if finfo:
                                engine.adapter.upload_artifact(draft_id, key, finfo["path"])
                        self.stats["packages_uploaded"] += 1
            except Exception as e:
                self.stats["errors"].append(f"{title}: Agent B upload failed - {str(e)[:100]}")

        return self.stats

    def run_training(self, count: int = 10) -> Dict:
        """Full training run: create batch, run pipeline, report results."""
        print(f"\n  🎓 GGB Agent Training Ground")
        print(f"  ──────────────────────────")
        print(f"  Packages: {count}")
        print(f"  Started:  {self.start_time.strftime('%H:%M:%S')}")
        print()

        batch_dir = self.setup_training_batch(count)
        results = self.run_pipeline(batch_dir)

        elapsed = (datetime.now(timezone.utc) - self.start_time).total_seconds()
        print(f"\n  ──────────────────────────")
        print(f"  Training completed in {elapsed:.1f}s")
        print(f"  Created:    {results['packages_created']}")
        print(f"  Discovered: {results['packages_discovered']}")
        print(f"  Validated:  {results['packages_validated']}")
        print(f"  Staged:     {results['packages_staged']}")
        print(f"  Previewed:  {results['packages_previewed']}")
        print(f"  Approved:   {results['packages_approved']}")
        print(f"  Uploaded:   {results['packages_uploaded']}")
        if results["errors"]:
            print(f"  Errors:     {len(results['errors'])}")
            for e in results["errors"][:5]:
                print(f"    - {e}")

        # Cleanup
        shutil.rmtree(batch_dir, ignore_errors=True)
        return results


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="GGB Agent Training Ground")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--count", type=int, default=10, help="Number of training packages")
    args = parser.parse_args()

    ground = AgentTrainingGround()
    result = ground.run_training(args.count)

    if args.json:
        print(json.dumps(result, indent=2, default=str))
