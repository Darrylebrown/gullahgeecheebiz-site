#!/usr/bin/env python3
"""
GGB Encyclopedia Skeleton Generator — creates landing pad packages
for all 50 encyclopedia volumes from Claude's drafts.
Prep team and pipeline handle the rest.
"""
import json, sys, shutil
from pathlib import Path
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from publisher import REPO_ROOT
from PIL import Image

# ─── Paths ─────────────────────────────────────────────────────────────────

CLAUDES_DIR = Path.home() / "gullah-geechee-project" / "gullah_geechee_project" / "ebooks"
COVERS_DIR = Path.home() / "gullah-geechee-project" / "covers"
LANDING_PAD = REPO_ROOT / "publish" / "landing-pad"
MANIFEST = Path.home() / "gullah-geechee-project" / "gullah_geechee_project" / "MANIFEST.csv"

# ─── Volume Titles from MANIFEST ──────────────────────────────────────────

def load_manifest() -> list:
    """Load unique volume titles from the MANIFEST.csv.
    Extracts volume numbers from filenames like 'Volume_01_Manuscript.md'."""
    volumes = []
    seen = set()
    if MANIFEST.exists():
        for line in MANIFEST.read_text().strip().split("\n")[1:]:  # Skip header
            parts = line.split(",")
            if len(parts) >= 2:
                rel_path = parts[0].strip()
                # Extract volume number from filename like "Volume_01_Manuscript.md"
                import re
                match = re.search(r'Volume_(\d+)_', rel_path)
                if match:
                    vol_num = int(match.group(1))
                    if vol_num not in seen:
                        seen.add(vol_num)
                        # Get title from the filename or use a default
                        title = f"Encyclopedia Volume {vol_num:02d}"
                        volumes.append((vol_num, title))
    # Sort by volume number
    volumes.sort(key=lambda x: x[0])
    return volumes

# ─── Skeleton Generator ──────────────────────────────────────────────────

class EncyclopediaSkeletonGenerator:
    """Creates landing pad packages for all 50 encyclopedia volumes."""

    def __init__(self):
        self.stats = {"skeletons": 0, "covers_copied": 0, "errors": 0}

    def generate_all(self) -> dict:
        """Generate skeletons for all 50 volumes in the landing pad."""
        volumes = load_manifest()
        if not volumes:
            print("  No manifest found. Using default volume list.")
            volumes = [(f"Volume {i:02d}", f"Encyclopedia Volume {i:02d}") for i in range(1, 51)]

        print(f"\n  📚 GGB Encyclopedia Skeleton Generator")
        print(f"  ─────────────────────────────────────")
        print(f"  Source: {CLAUDES_DIR}")
        print(f"  Covers: {COVERS_DIR}")
        print(f"  Target: {LANDING_PAD}")
        print(f"  Volumes: {len(volumes)}")
        print()

        for i, (vol_num, title) in enumerate(volumes):
            try:
                slug = f"encyclopedia-vol-{i+1:02d}"
                pkg_dir = LANDING_PAD / slug
                pkg_dir.mkdir(parents=True, exist_ok=True)

                # Copy Claude's manuscript if it exists
                manuscript_name = f"Volume_{i+1:02d}_Manuscript.md"
                claude_manuscript = CLAUDES_DIR / manuscript_name
                if claude_manuscript.exists():
                    shutil.copy2(str(claude_manuscript), str(pkg_dir / "manuscript.md"))
                else:
                    # Create a minimal skeleton
                    (pkg_dir / "manuscript.md").write_text(f"""# {title}

## Gullah Geechee Encyclopedia

### By Darryl Elliott Brown

---

## Introduction
Volume {i+1} of the Gullah Geechee Encyclopedia explores {title.lower()}.

## Content
This volume covers the history, culture, and significance of {title.lower()} in the Gullah Geechee tradition.

## References
- Gullah Geechee Cultural Heritage Corridor
- Penn Center Archives
- Community oral histories

---

*Gullah Geechee Biz · Encyclopedia Series*
""")

                # KDP Draft
                (pkg_dir / "KDP-DRAFT.md").write_text(f"""# KDP Draft — {title}
- **Title:** {title}
- **Author:** Darryl Elliott Brown
- **Publisher:** Gullah Geechee Biz
- **Language:** English
- **Ebook price:** $9.99
- **DRM:** No
- **KDP Select:** Off
## Description
Volume {i+1} of the Gullah Geechee Encyclopedia. A comprehensive exploration of {title.lower()}, drawing on community knowledge, historical research, and cultural preservation.
## Categories
- REFERENCE / Encyclopedias
- SOCIAL SCIENCE / Ethnic Studies / American / African American & Black Studies
- HISTORY / African American & Black
## Keywords
gullah geechee, encyclopedia, {title.lower()}, african american history, sea islands, lowcountry
""")

                # Copy premium cover if it exists
                cover_name = f"volume-{i+1:02d}-cover.png"
                cover_path = COVERS_DIR / cover_name
                if cover_path.exists():
                    shutil.copy2(str(cover_path), str(pkg_dir / "cover.png"))
                    self.stats["covers_copied"] += 1
                else:
                    # Generate a simple cover
                    cover = Image.new("RGB", (1600, 2560), color=(26, 26, 46))
                    cover.save(str(pkg_dir / "cover.jpg"), "JPEG", quality=95)

                self.stats["skeletons"] += 1

                if (i + 1) % 10 == 0:
                    print(f"  [{i+1:>2}/50] {title[:50]}...")

            except Exception as e:
                self.stats["errors"] += 1
                print(f"  [ERROR] Volume {i+1}: {str(e)[:100]}")

        print(f"\n  ─────────────────────────────────────")
        print(f"  Skeletons: {self.stats['skeletons']}")
        print(f"  Covers:    {self.stats['covers_copied']}")
        print(f"  Errors:    {self.stats['errors']}")
        print(f"\n  Next: Run 'landing-pad.py cycle' to discover and pipeline.")

        return self.stats


if __name__ == "__main__":
    gen = EncyclopediaSkeletonGenerator()
    result = gen.generate_all()
    print(json.dumps(result, indent=2))
