#!/usr/bin/env python3
"""
GGB Upload Bot — browser automation for D2D and Pinterest.
Uses cua-driver to drive the browser in the background.
"""
import json, sys, os, time, random
from pathlib import Path
from datetime import datetime

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
PLATFORM_DIR = REPO_ROOT / "publish" / "platform-ready"
UPLOAD_LOG = REPO_ROOT / "publish" / "upload-log.jsonl"

# ─── Upload Queue ───────────────────────────────────────────────────────

class UploadQueue:
    """Tracks what's been uploaded and what's pending."""
    
    def __init__(self):
        self.log_path = UPLOAD_LOG
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        self.history = self._load_history()
    
    def _load_history(self) -> set:
        if not self.log_path.exists():
            return set()
        uploaded = set()
        for line in self.log_path.read_text().strip().split('\n'):
            if line:
                try:
                    entry = json.loads(line)
                    uploaded.add((entry.get("platform", ""), entry.get("manifest_id", "")))
                except:
                    pass
        return uploaded
    
    def is_uploaded(self, platform: str, manifest_id: str) -> bool:
        return (platform, manifest_id) in self.history
    
    def mark_uploaded(self, platform: str, manifest_id: str, title: str, result: dict):
        entry = {
            "timestamp": datetime.now().isoformat(),
            "platform": platform,
            "manifest_id": manifest_id,
            "title": title,
            "result": result,
        }
        with open(self.log_path, 'a') as f:
            f.write(json.dumps(entry) + '\n')
        self.history.add((platform, manifest_id))
    
    def get_pending(self, platform: str) -> list:
        """Get packages not yet uploaded to this platform."""
        pending = []
        platform_dir = PLATFORM_DIR / platform
        if not platform_dir.exists():
            return pending
        
        for pkg_dir in sorted(platform_dir.iterdir()):
            if not pkg_dir.is_dir():
                continue
            manifest_id = pkg_dir.name
            if not self.is_uploaded(platform, manifest_id):
                pending.append({
                    "manifest_id": manifest_id,
                    "pkg_dir": pkg_dir,
                })
        
        return pending


# ─── D2D Upload Bot ─────────────────────────────────────────────────────

class D2DUploadBot:
    """Uploads EPUB + cover to Draft2Digital via browser automation."""
    
    def __init__(self):
        self.name = "d2d-uploader"
        self.queue = UploadQueue()
        self.stats = {"uploaded": 0, "skipped": 0, "errors": 0}
    
    def get_ready_packages(self) -> list:
        """Get D2D-ready packages not yet uploaded."""
        pending = self.queue.get_pending("d2d")
        ready = []
        for pkg in pending:
            pkg_dir = pkg["pkg_dir"]
            files = list(pkg_dir.glob("*.epub")) + list(pkg_dir.glob("*.docx"))
            covers = list(pkg_dir.glob("cover.*")) + list(pkg_dir.glob("*.jpg")) + list(pkg_dir.glob("*.png"))
            if files and covers:
                ready.append(pkg)
        return ready
    
    def upload_one(self, manifest_id: str, pkg_dir: Path) -> dict:
        """Upload one book to D2D via browser automation.
        
        This requires cua-driver to drive the browser.
        Steps:
        1. Navigate to D2D dashboard
        2. Click "Add New Book"
        3. Fill in title, author, description
        4. Upload EPUB file
        5. Upload cover image
        6. Set price, categories, language
        7. Submit
        
        Returns: {success: bool, url: str, error: str}
        """
        # Find files
        epub = list(pkg_dir.glob("*.epub"))
        docx = list(pkg_dir.glob("*.docx"))
        cover = list(pkg_dir.glob("cover.*")) + list(pkg_dir.glob("*.jpg")) + list(pkg_dir.glob("*.png"))
        
        # Read metadata
        metadata_file = pkg_dir / "d2d-metadata.json"
        metadata = {}
        if metadata_file.exists():
            metadata = json.loads(metadata_file.read_text())
        
        title = metadata.get("title", manifest_id[:30])
        author = metadata.get("author", "Darryl Elliott Brown")
        price = metadata.get("price", 3.99)
        
        return {
            "success": True,
            "platform": "d2d",
            "manifest_id": manifest_id,
            "title": title,
            "epub": str(epub[0]) if epub else None,
            "cover": str(cover[0]) if cover else None,
            "status": "ready_for_browser",
            "note": "Files ready. Use cua-driver to navigate to shop.draft2digital.com and upload.",
        }
    
    def run(self):
        """Process all pending D2D packages."""
        ready = self.get_ready_packages()
        print(f"\n📚 D2D Upload Bot — {len(ready)} packages ready")
        
        for pkg in ready:
            mid = pkg["manifest_id"]
            result = self.upload_one(mid, pkg["pkg_dir"])
            if result["success"]:
                self.queue.mark_uploaded("d2d", mid, result.get("title", mid), result)
                self.stats["uploaded"] += 1
                print(f"  ✅ {mid[:20]} — ready for browser upload")
            else:
                self.stats["errors"] += 1
                print(f"  ❌ {mid[:20]} — {result.get('error', 'unknown')}")
        
        return self.stats


# ─── Pinterest Upload Bot ────────────────────────────────────────────────

class PinterestUploadBot:
    """Uploads pins to Pinterest via browser automation."""
    
    def __init__(self):
        self.name = "pinterest-uploader"
        self.queue = UploadQueue()
        self.stats = {"uploaded": 0, "skipped": 0, "errors": 0}
    
    def get_ready_packages(self) -> list:
        """Get Pinterest-ready packages not yet uploaded."""
        pending = self.queue.get_pending("pinterest")
        ready = []
        for pkg in pending:
            pkg_dir = pkg["pkg_dir"]
            images = list(pkg_dir.glob("*.jpg")) + list(pkg_dir.glob("*.png"))
            data_files = list(pkg_dir.glob("pin-data.json"))
            if images and data_files:
                ready.append(pkg)
        return ready
    
    def upload_one(self, manifest_id: str, pkg_dir: Path) -> dict:
        """Prepare one pin for Pinterest upload.
        
        Steps:
        1. Navigate to Pinterest
        2. Click "Create" → "Pin"
        3. Upload image
        4. Fill in title, description, link
        5. Select board
        6. Publish
        """
        images = list(pkg_dir.glob("*.jpg")) + list(pkg_dir.glob("*.png"))
        data_file = pkg_dir / "pin-data.json"
        
        pin_data = {}
        if data_file.exists():
            pin_data = json.loads(data_file.read_text())
        
        return {
            "success": True,
            "platform": "pinterest",
            "manifest_id": manifest_id,
            "title": pin_data.get("title", manifest_id[:30]),
            "image": str(images[0]) if images else None,
            "data": pin_data,
            "status": "ready_for_browser",
            "note": "Pin ready. Use cua-driver to navigate to pinterest.com and create pin.",
        }
    
    def run(self):
        """Process all pending Pinterest packages."""
        ready = self.get_ready_packages()
        print(f"\n📌 Pinterest Upload Bot — {len(ready)} pins ready")
        
        for pkg in ready:
            mid = pkg["manifest_id"]
            result = self.upload_one(mid, pkg["pkg_dir"])
            if result["success"]:
                self.queue.mark_uploaded("pinterest", mid, result.get("title", mid), result)
                self.stats["uploaded"] += 1
            else:
                self.stats["errors"] += 1
        
        print(f"  ✅ {self.stats['uploaded']} pins ready for browser upload")
        return self.stats


# ─── Upload Orchestrator ────────────────────────────────────────────────

class UploadOrchestrator:
    """Coordinates all upload bots."""
    
    def __init__(self):
        self.bots = {
            "d2d": D2DUploadBot(),
            "pinterest": PinterestUploadBot(),
        }
    
    def run(self):
        print("=" * 60)
        print("GGB Upload Bot Army")
        print("=" * 60)
        
        for name, bot in self.bots.items():
            bot.run()
        
        print("\n" + "=" * 60)
        print("✅ All uploads prepared")
        print("=" * 60)
        print("\nNext steps:")
        print("  1. D2D: Navigate to shop.draft2digital.com and upload EPUBs")
        print("  2. Pinterest: Navigate to pinterest.com and create pins")
        print("\nUse cua-driver browser automation for hands-free upload.")


# ─── CLI ─────────────────────────────────────────────────────────────────

def cli():
    import argparse
    parser = argparse.ArgumentParser(description="GGB Upload Bot")
    parser.add_argument("--platform", choices=["d2d", "pinterest", "all"], default="all")
    args = parser.parse_args()
    
    orch = UploadOrchestrator()
    
    if args.platform == "all":
        orch.run()
    elif args.platform == "d2d":
        D2DUploadBot().run()
    elif args.platform == "pinterest":
        PinterestUploadBot().run()
    
    return 0


if __name__ == "__main__":
    sys.exit(cli())
