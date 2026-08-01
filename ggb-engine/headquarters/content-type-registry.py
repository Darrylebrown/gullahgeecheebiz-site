#!/usr/bin/env python3
"""
GGB Content Type Registry — extends the landing pad to handle all formats:
books, audio, ads, commercials, movies, pins.
Each content type gets its own prep, pipeline, and distribution path.
"""
import json, sys, uuid, subprocess
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from publisher import REPO_ROOT
from PIL import Image, ImageDraw

LANDING_PAD = REPO_ROOT / "publish" / "landing-pad"
CONTENT_TYPES_DB = REPO_ROOT / "publish" / "content-types" / "registry.json"
CONTENT_TYPES_DB.parent.mkdir(parents=True, exist_ok=True)

# ─── Content Type Registry ────────────────────────────────────────────────

CONTENT_TYPES = {
    "book": {
        "name": "Ebook / Paperback",
        "extensions": [".md", ".docx", ".epub", ".pdf"],
        "prep_bot": "prep-team.py",
        "pipeline_bot": "bot-qa.py",
        "distribution": ["kdp", "draft2digital", "ingramspark"],
        "icon": "📚",
        "requires_cover": True,
        "requires_audio": False,
        "requires_video": False,
    },
    "audiobook": {
        "name": "Audiobook",
        "extensions": [".md", ".mp3", ".wav", ".m4b"],
        "prep_bot": "human-voice-engine.py",
        "pipeline_bot": "bot-qa.py",
        "distribution": ["acx", "audible", "spotify"],
        "icon": "🎧",
        "requires_cover": True,
        "requires_audio": True,
        "requires_video": False,
    },
    "ad": {
        "name": "Advertisement",
        "extensions": [".md", ".mp4", ".jpg", ".png"],
        "prep_bot": "ad-generator.py",
        "pipeline_bot": "bot-qa.py",
        "distribution": ["tiktok", "instagram", "facebook"],
        "icon": "📢",
        "requires_cover": False,
        "requires_audio": False,
        "requires_video": True,
    },
    "commercial": {
        "name": "TV Commercial",
        "extensions": [".md", ".mp4", ".mov"],
        "prep_bot": "commercial-studio.py",
        "pipeline_bot": "bot-qa.py",
        "distribution": ["youtube", "tiktok", "instagram", "tv"],
        "icon": "📺",
        "requires_cover": False,
        "requires_audio": True,
        "requires_video": True,
    },
    "movie": {
        "name": "Film / Documentary",
        "extensions": [".md", ".mp4", ".mov", ".srt"],
        "prep_bot": "movie-studio.py",
        "pipeline_bot": "bot-qa.py",
        "distribution": ["youtube", "vimeo", "amazon-prime", "distrokid"],
        "icon": "🎬",
        "requires_cover": True,
        "requires_audio": True,
        "requires_video": True,
    },
    "pin": {
        "name": "Pinterest Pin",
        "extensions": [".jpg", ".png"],
        "prep_bot": "pin-generator.py",
        "pipeline_bot": "bot-qa.py",
        "distribution": ["pinterest"],
        "icon": "📌",
        "requires_cover": False,
        "requires_audio": False,
        "requires_video": False,
    },
    "music": {
        "name": "Music Track / Album",
        "extensions": [".mp3", ".wav", ".flac", ".md"],
        "prep_bot": "music-studio.py",
        "pipeline_bot": "bot-qa.py",
        "distribution": ["distrokid", "spotify", "apple-music"],
        "icon": "🎵",
        "requires_cover": True,
        "requires_audio": True,
        "requires_video": False,
    },
    "magazine": {
        "name": "Digital Magazine",
        "extensions": [".html", ".md", ".pdf"],
        "prep_bot": "magazine-studio.py",
        "pipeline_bot": "bot-qa.py",
        "distribution": ["substack", "website", "issuu"],
        "icon": "📰",
        "requires_cover": True,
        "requires_audio": False,
        "requires_video": False,
    },
}

# ─── Content Type Manager ────────────────────────────────────────────────

class ContentTypeManager:
    """Manages all content types through the pipeline."""

    def __init__(self):
        self._load_registry()

    def _load_registry(self):
        if CONTENT_TYPES_DB.exists():
            self.registry = json.loads(CONTENT_TYPES_DB.read_text())
        else:
            self.registry = {"types": {}, "packages": []}
            for key, info in CONTENT_TYPES.items():
                self.registry["types"][key] = info
            self._save_registry()

    def _save_registry(self):
        CONTENT_TYPES_DB.write_text(json.dumps(self.registry, indent=2))

    def register_package(self, content_type: str, title: str, slug: str) -> Dict:
        """Register a package of a specific content type in the landing pad."""
        type_info = CONTENT_TYPES.get(content_type)
        if not type_info:
            return {"error": f"Unknown content type: {content_type}"}

        pkg_dir = LANDING_PAD / f"{content_type}-{slug}"
        pkg_dir.mkdir(parents=True, exist_ok=True)

        # Create type marker
        (pkg_dir / "CONTENT_TYPE").write_text(content_type)

        # Create KDP-style draft for metadata
        (pkg_dir / "KDP-DRAFT.md").write_text(f"""# {type_info['icon']} {title}
- **Content Type:** {content_type}
- **Title:** {title}
- **Author:** Darryl Elliott Brown
- **Publisher:** Gullah Geechee Biz
- **Language:** English
## Description
A {content_type} from Gullah Geechee Biz.
## Distribution
{', '.join(type_info['distribution'])}
""")

        # Create cover if required
        if type_info["requires_cover"]:
            cover = Image.new("RGB", (1600, 2560), color=(26, 26, 46))
            draw = ImageDraw.Draw(cover)
            draw.rectangle([0, 800, 1600, 820], fill=(201, 168, 76))
            draw.rectangle([0, 1740, 1600, 1760], fill=(201, 168, 76))
            cover.save(str(pkg_dir / "cover.jpg"), "JPEG", quality=95)

        # Register
        entry = {
            "id": f"ggb-{content_type}-{uuid.uuid4().hex[:8]}",
            "content_type": content_type,
            "title": title,
            "slug": slug,
            "path": str(pkg_dir),
            "status": "registered",
            "registered_at": datetime.now(timezone.utc).isoformat(),
        }
        self.registry["packages"].append(entry)
        self._save_registry()

        return entry

    def scan_landing_pad(self) -> Dict:
        """Scan landing pad and categorize all packages by content type."""
        counts = {}
        if LANDING_PAD.exists():
            for pkg_dir in LANDING_PAD.iterdir():
                if pkg_dir.is_dir():
                    type_file = pkg_dir / "CONTENT_TYPE"
                    if type_file.exists():
                        ct = type_file.read_text().strip()
                        counts[ct] = counts.get(ct, 0) + 1
                    else:
                        counts["untyped"] = counts.get("untyped", 0) + 1
        return counts

    def get_pipeline_for_type(self, content_type: str) -> Dict:
        """Get the full pipeline definition for a content type."""
        type_info = CONTENT_TYPES.get(content_type)
        if not type_info:
            return {"error": f"Unknown content type: {content_type}"}
        return {
            "type": content_type,
            "name": type_info["name"],
            "icon": type_info["icon"],
            "prep": type_info["prep_bot"],
            "qa": type_info["pipeline_bot"],
            "distribution": type_info["distribution"],
            "requirements": {
                "cover": type_info["requires_cover"],
                "audio": type_info["requires_audio"],
                "video": type_info["requires_video"],
            },
        }

    def report(self) -> Dict:
        """Full content type report."""
        counts = self.scan_landing_pad()
        return {
            "content_types": len(CONTENT_TYPES),
            "types": {k: v["name"] for k, v in CONTENT_TYPES.items()},
            "packages_in_pad": counts,
            "total_packages": sum(counts.values()),
            "registered_packages": len(self.registry["packages"]),
        }


# ─── CLI ───────────────────────────────────────────────────────────────────

def cli():
    import argparse
    parser = argparse.ArgumentParser(description="GGB Content Type Registry")
    parser.add_argument("--json", action="store_true")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("report", help="Content type report")
    sub.add_parser("scan", help="Scan landing pad by content type")

    register = sub.add_parser("register", help="Register a new package")
    register.add_argument("content_type", choices=list(CONTENT_TYPES.keys()), help="Content type")
    register.add_argument("title", help="Package title")
    register.add_argument("--slug", default="", help="URL slug")

    pipeline = sub.add_parser("pipeline", help="Get pipeline for a content type")
    pipeline.add_argument("content_type", choices=list(CONTENT_TYPES.keys()))

    args = parser.parse_args()
    mgr = ContentTypeManager()

    if args.command == "report":
        result = mgr.report()
    elif args.command == "scan":
        result = mgr.scan_landing_pad()
    elif args.command == "register":
        slug = args.slug or args.title.lower().replace(" ", "-").replace(":", "").replace("'", "")[:40]
        result = mgr.register_package(args.content_type, args.title, slug)
    elif args.command == "pipeline":
        result = mgr.get_pipeline_for_type(args.content_type)

    if args.json:
        print(json.dumps(result, indent=2, default=str))
    else:
        if isinstance(result, dict):
            if "content_types" in result:
                print(f"📋 GGB Content Type Registry")
                print(f"   Types: {result['content_types']}")
                print(f"   In pad: {result['total_packages']}")
                print()
                for name, desc in result["types"].items():
                    count = result.get("packages_in_pad", {}).get(name, 0)
                    icon = CONTENT_TYPES.get(name, {}).get("icon", "📦")
                    print(f"  {icon} {name:>15}: {desc} ({count} in pad)")
            elif "type" in result:
                print(f"{result['icon']} {result['name']}")
                print(f"   Prep: {result['prep']}")
                print(f"   QA: {result['qa']}")
                print(f"   Distribution: {', '.join(result['distribution'])}")
                print(f"   Requirements: {result['requirements']}")
            elif "content_type" in result:
                print(f"✅ Registered: {result['title']} ({result['content_type']})")
                print(f"   Path: {result['path']}")
            elif isinstance(result, dict):
                for k, v in result.items():
                    print(f"{k}: {v}")
        else:
            print(result)

    return 0

if __name__ == "__main__":
    sys.exit(cli())
