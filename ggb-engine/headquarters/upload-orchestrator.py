#!/usr/bin/env python3
"""
GGB Upload Orchestrator — chains through upload methods with automatic fallback.
If v1 fails → v2 → cua-driver → manual instructions.
Reports which method succeeded for each book.
"""
import json, os, sys, time, uuid, sqlite3, asyncio, subprocess, importlib
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional, Dict, List, Tuple

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
PUB_DB = REPO_ROOT / "publish" / "publisher.db"
LOGS_DIR = Path(__file__).resolve().parent / "logs"
UPLOAD_LOG = LOGS_DIR / "upload-log.jsonl"
PLATFORM_DIR = REPO_ROOT / "publish" / "platform-ready"

LOGS_DIR.mkdir(parents=True, exist_ok=True)

# ─── Upload Methods (in priority order) ────────────────────────────────────

UPLOAD_METHODS = [
    {
        "name": "playwright-v1",
        "module": "platform-uploader",
        "class_name": "PlatformUploader",
        "description": "Playwright sync — primary uploader",
    },
    {
        "name": "playwright-v2",
        "module": "platform-uploader-v2",
        "class_name": "PlatformUploaderV2",
        "description": "Playwright async — backup uploader",
    },
    {
        "name": "cua-driver",
        "module": None,
        "class_name": None,
        "description": "macOS accessibility driver — last resort automation",
    },
    {
        "name": "manual",
        "module": None,
        "class_name": None,
        "description": "Generate instructions for manual upload",
    },
]

class UploadOrchestrator:
    """
    Chains through upload methods until one succeeds.
    Tracks which method worked for each book so future uploads
    start with the most reliable method.
    """
    
    def __init__(self):
        self.conn = sqlite3.connect(str(PUB_DB))
        self.method_scores = self._load_scores()
        self.results = []
    
    def _load_scores(self) -> Dict[str, int]:
        """Load method success scores from upload log."""
        scores = {m["name"]: 0 for m in UPLOAD_METHODS}
        if UPLOAD_LOG.exists():
            for line in UPLOAD_LOG.read_text().strip().split("\n"):
                if line:
                    try:
                        entry = json.loads(line)
                        if entry.get("success") and entry.get("method"):
                            scores[entry["method"]] = scores.get(entry["method"], 0) + 1
                    except:
                        pass
        return scores
    
    def _log_upload(self, manifest_id: str, title: str, platform: str, 
                    method: str, success: bool, error: str = ""):
        """Log an upload attempt."""
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "manifest_id": manifest_id,
            "title": title,
            "platform": platform,
            "method": method,
            "success": success,
            "error": error,
        }
        with open(UPLOAD_LOG, "a") as f:
            f.write(json.dumps(entry) + "\n")
        
        if success:
            self.method_scores[method] = self.method_scores.get(method, 0) + 1
    
    def _get_best_method(self) -> str:
        """Get the method with the highest success score."""
        sorted_methods = sorted(self.method_scores.items(), key=lambda x: -x[1])
        return sorted_methods[0][0] if sorted_methods else "playwright-v1"
    
    def _find_platform_files(self, manifest_id: str, platform: str) -> Tuple[Optional[Path], Optional[Path]]:
        """Find the platform-ready files for a manifest."""
        configs = {
            "d2d": (PLATFORM_DIR / "d2d", ".epub", ".jpg"),
            "kdp": (PLATFORM_DIR / "kdp", ".docx", ".jpg"),
            "kobo": (PLATFORM_DIR / "kobo", ".epub", ".jpg"),
            "acx": (PLATFORM_DIR / "acx", ".mp3", ".jpg"),
            "spotify": (PLATFORM_DIR / "spotify", ".mp3", ".jpg"),
            "distrokid": (PLATFORM_DIR / "distrokid", ".mp3", ".jpg"),
            "pinterest": (PLATFORM_DIR / "pinterest", ".jpg", ".jpg"),
        }
        
        cfg = configs.get(platform)
        if not cfg:
            return None, None
        
        file_dir, file_ext, cover_ext = cfg
        if not file_dir.exists():
            return None, None
        
        d = json.loads(self.conn.execute(
            "SELECT data FROM manifests WHERE manifest_id = ?", (manifest_id,)
        ).fetchone()[0])
        
        title = d.get("title", {}).get("canonical", "Unknown")
        title_slug = title.lower().replace(" ", "-").replace("'", "")[:40]
        
        files = list(file_dir.glob(f"*{title_slug}*{file_ext}"))
        covers = list(file_dir.glob(f"*{title_slug}*{cover_ext}"))
        
        if not files:
            files = list(file_dir.glob(f"*{title_slug[:15]}*{file_ext}"))
        
        return (files[0] if files else None), (covers[0] if covers else None)
    
    def _try_method_v1(self, platform: str, manifest_id: str, title: str) -> Tuple[bool, str]:
        """Try Playwright v1 (sync)."""
        try:
            spec = importlib.util.spec_from_file_location(
                "uploader_v1",
                str(REPO_ROOT / "ggb-engine" / "headquarters" / "platform-uploader.py")
            )
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            
            uploader = mod.PlatformUploader(headless=True, slow_mo=200)
            try:
                # Try to login with saved cookies
                uploader.login(platform)
                result = uploader.upload(platform, manifest_id, title)
                return result, "" if result else "Upload returned False"
            finally:
                uploader.close()
        except Exception as e:
            return False, str(e)[:200]
    
    def _try_method_v2(self, platform: str, manifest_id: str, title: str) -> Tuple[bool, str]:
        """Try Playwright v2 (async)."""
        try:
            spec = importlib.util.spec_from_file_location(
                "uploader_v2",
                str(REPO_ROOT / "ggb-engine" / "headquarters" / "platform-uploader-v2.py")
            )
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            
            async def _run():
                uploader = mod.PlatformUploaderV2(headless=True)
                try:
                    await uploader._start()
                    await uploader.login(platform)
                    result = await uploader.upload(platform, manifest_id, title)
                    return result, "" if result else "Upload returned False"
                finally:
                    await uploader._stop()
            
            result, error = asyncio.run(_run())
            return result, error
        except Exception as e:
            return False, str(e)[:200]
    
    def _try_method_cua(self, platform: str, manifest_id: str, title: str) -> Tuple[bool, str]:
        """Try cua-driver (macOS accessibility)."""
        try:
            # Launch the platform URL in Safari
            configs = {
                "d2d": "https://draft2digital.com/books/new",
                "kdp": "https://kdp.amazon.com/en_US/title-setup",
                "kobo": "https://writinglife.kobo.com/books/new",
            }
            url = configs.get(platform, f"https://{platform}.com")
            
            subprocess.run(["open", "-a", "Safari", url], timeout=5)
            print(f"  🖥️  Opened {url} in Safari — please fill in the form")
            print(f"     Title: {title}")
            
            # Find the file
            epub, cover = self._find_platform_files(manifest_id, platform)
            if epub:
                print(f"     File: {epub}")
            if cover:
                print(f"     Cover: {cover}")
            
            return False, "cua-driver requires manual interaction"
        except Exception as e:
            return False, str(e)[:200]
    
    def _try_method_manual(self, platform: str, manifest_id: str, title: str) -> Tuple[bool, str]:
        """Generate manual upload instructions."""
        epub, cover = self._find_platform_files(manifest_id, platform)
        
        instructions = f"""
╔══════════════════════════════════════════════════════════╗
║           MANUAL UPLOAD INSTRUCTIONS                     ║
╚══════════════════════════════════════════════════════════╝

Book: {title}
Platform: {platform}
Manifest: {manifest_id}

Steps:
1. Open {platform}.com in your browser
2. Log in to your account
3. Click "Add New Book" or "Create New"
4. Fill in the following:
   - Title: {title}
   - Author: Darryl E. Brown
   - Publisher: Gullah Geechee Biz
"""
        if epub:
            instructions += f"5. Upload manuscript: {epub}\n"
        if cover:
            instructions += f"6. Upload cover: {cover}\n"
        instructions += f"""
7. Set price and categories
8. Click Submit/Publish

After uploading, run: python3 publishing-ops.py --report
to mark the book as published.
"""
        print(instructions)
        return False, "Manual upload required"
    
    def upload(self, platform: str, manifest_id: str, title: str = None) -> bool:
        """Upload a book, chaining through methods until one succeeds."""
        if not title:
            d = json.loads(self.conn.execute(
                "SELECT data FROM manifests WHERE manifest_id = ?", (manifest_id,)
            ).fetchone()[0])
            title = d.get("title", {}).get("canonical", "Unknown")
        
        print(f"\n📤 Uploading: {title}")
        print(f"   Platform: {platform}")
        print(f"   Best method: {self._get_best_method()}")
        
        # Order methods by success score
        ordered = sorted(UPLOAD_METHODS, key=lambda m: -self.method_scores.get(m["name"], 0))
        
        for method in ordered:
            name = method["name"]
            print(f"\n   🔄 Trying: {method['description']}...")
            
            if name == "playwright-v1":
                success, error = self._try_method_v1(platform, manifest_id, title)
            elif name == "playwright-v2":
                success, error = self._try_method_v2(platform, manifest_id, title)
            elif name == "cua-driver":
                success, error = self._try_method_cua(platform, manifest_id, title)
            elif name == "manual":
                success, error = self._try_method_manual(platform, manifest_id, title)
            else:
                success, error = False, f"Unknown method: {name}"
            
            self._log_upload(manifest_id, title, platform, name, success, error)
            
            if success:
                print(f"   ✅ Succeeded with: {method['description']}")
                
                # Mark as published
                now = datetime.now(timezone.utc).isoformat()
                d = json.loads(self.conn.execute(
                    "SELECT data FROM manifests WHERE manifest_id = ?", (manifest_id,)
                ).fetchone()[0])
                d["status"] = "published"
                d["published_at"] = now
                d["published_to"] = platform
                d["upload_method"] = name
                self.conn.execute(
                    "UPDATE manifests SET data = ?, state = 'published' WHERE manifest_id = ?",
                    (json.dumps(d), manifest_id)
                )
                self.conn.commit()
                
                return True
            else:
                print(f"   ❌ Failed: {error[:100]}")
        
        print(f"\n   ❌ All methods failed for: {title}")
        return False
    
    def upload_batch(self, platform: str, limit: int = 5) -> Dict:
        """Upload a batch of books."""
        rows = self.conn.execute("""
            SELECT manifest_id, json_extract(data, '$.title.canonical')
            FROM manifests WHERE state = 'approved'
            AND manifest_id NOT IN (
                SELECT manifest_id FROM platform_evidence 
                WHERE operation_id = 'upload-manuscript' AND adapter_type LIKE 'Playwright%'
            )
            LIMIT ?
        """, (limit,)).fetchall()
        
        results = {"success": 0, "failed": 0, "methods": {}}
        
        for r in rows:
            ok = self.upload(platform, r[0], r[1])
            if ok:
                results["success"] += 1
            else:
                results["failed"] += 1
        
        # Summary
        print(f"\n{'='*60}")
        print(f"BATCH UPLOAD SUMMARY")
        print(f"{'='*60}")
        print(f"  Success: {results['success']}")
        print(f"  Failed:  {results['failed']}")
        print(f"\nMethod scores: {dict(sorted(self.method_scores.items(), key=lambda x: -x[1]))}")
        
        return results
    
    def status(self) -> Dict:
        """Show upload status."""
        # Count by method
        method_counts = {}
        if UPLOAD_LOG.exists():
            for line in UPLOAD_LOG.read_text().strip().split("\n"):
                if line:
                    try:
                        entry = json.loads(line)
                        m = entry.get("method", "?")
                        if m not in method_counts:
                            method_counts[m] = {"success": 0, "failed": 0}
                        if entry.get("success"):
                            method_counts[m]["success"] += 1
                        else:
                            method_counts[m]["failed"] += 1
                    except:
                        pass
        
        return {
            "method_scores": self.method_scores,
            "method_counts": method_counts,
            "best_method": self._get_best_method(),
            "total_attempts": sum(v["success"] + v["failed"] for v in method_counts.values()),
        }

# ─── CLI ────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="GGB Upload Orchestrator")
    parser.add_argument("--platform", "-p", default="d2d", help="Platform")
    parser.add_argument("--batch", type=int, default=1, help="Books to upload")
    parser.add_argument("--manifest", help="Specific manifest ID")
    parser.add_argument("--status", action="store_true", help="Show upload status")
    parser.add_argument("--title", help="Book title (for manual upload)")
    
    args = parser.parse_args()
    orch = UploadOrchestrator()
    
    if args.status:
        status = orch.status()
        print(f"Best method: {status['best_method']}")
        print(f"Total attempts: {status['total_attempts']}")
        print(f"\nMethod scores:")
        for m, s in sorted(status['method_scores'].items(), key=lambda x: -x[1]):
            print(f"  {m:20s}: {s} successes")
        print(f"\nMethod counts:")
        for m, c in status['method_counts'].items():
            print(f"  {m:20s}: {c['success']} success, {c['failed']} failed")
    
    elif args.manifest:
        orch.upload(args.platform, args.manifest, args.title)
    
    elif args.batch:
        orch.upload_batch(args.platform, args.batch)
    
    else:
        parser.print_help()
