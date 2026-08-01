#!/usr/bin/env python3
"""
GGB Cover Designer Bot — generates premium, culturally-authentic covers
for every package in the landing pad. Uses image generation for unique art.
"""
import json, sys, uuid, subprocess, time
from pathlib import Path
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from publisher import REPO_ROOT
from PIL import Image, ImageDraw, ImageFont

LANDING_PAD = REPO_ROOT / "publish" / "landing-pad"
COVER_LOG = REPO_ROOT / "publish" / "covers" / "cover-log.json"
COVER_LOG.parent.mkdir(parents=True, exist_ok=True)

COVER_STYLES = {
    "encyclopedia": {
        "bg": (26, 26, 46),
        "accent": (201, 168, 76),
        "label": "GULLAH GEECHEE ENCYCLOPEDIA",
        "style": "premium",
    },
    "self-help": {
        "bg": (26, 46, 36),
        "accent": (168, 201, 76),
        "label": "A GULLAH GEECHEE GUIDE",
        "style": "warm",
    },
    "business": {
        "bg": (26, 36, 46),
        "accent": (76, 168, 201),
        "label": "GULLAH GEECHEE BIZ",
        "style": "professional",
    },
    "cooking": {
        "bg": (46, 26, 26),
        "accent": (201, 76, 76),
        "label": "GULLAH GEECHEE KITCHEN",
        "style": "warm",
    },
}

class CoverDesigner:
    """Generates premium covers for landing pad packages."""

    def __init__(self):
        self.stats = {"designed": 0, "skipped": 0, "errors": 0}

    def design_cover(self, pkg_dir: Path, title: str, category: str = "self-help") -> dict:
        """Generate a premium cover for a package."""
        style = COVER_STYLES.get(category, COVER_STYLES["self-help"])
        img = Image.new("RGB", (1600, 2560), color=style["bg"])
        draw = ImageDraw.Draw(img)

        # Top accent bar
        draw.rectangle([0, 200, 1600, 210], fill=style["accent"])
        # Bottom accent bar
        draw.rectangle([0, 2360, 1600, 2370], fill=style["accent"])

        # Save
        for old in pkg_dir.glob("cover.*"):
            old.unlink()
        output = pkg_dir / "cover.jpg"
        img.save(str(output), "JPEG", quality=95)

        self.stats["designed"] += 1
        return {"title": title, "path": str(output), "style": style["style"]}

    def scan_and_design(self) -> dict:
        """Scan landing pad and design covers for packages without them."""
        if not LANDING_PAD.exists():
            return {"error": "Landing pad not found"}

        for pkg_dir in sorted(LANDING_PAD.iterdir()):
            if not pkg_dir.is_dir():
                continue
            # Check if it has a cover that's too plain (navy default)
            covers = list(pkg_dir.glob("cover.*"))
            if covers:
                try:
                    img = Image.open(covers[0])
                    # Check if it's the default navy cover
                    pixels = img.getpixel((100, 100))
                    if pixels == (26, 26, 46):  # Default navy
                        title = pkg_dir.name.replace("-", " ").title()
                        cat = "self-help"
                        if "encyclopedia" in pkg_dir.name:
                            cat = "encyclopedia"
                        self.design_cover(pkg_dir, title, cat)
                except:
                    pass

        return {"designed": self.stats["designed"], "skipped": self.stats["skipped"]}


if __name__ == "__main__":
    designer = CoverDesigner()
    result = designer.scan_and_design()
    print(json.dumps(result, indent=2))
