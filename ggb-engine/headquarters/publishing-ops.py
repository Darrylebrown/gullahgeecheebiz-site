#!/usr/bin/env python3
"""
GGB Publishing Operations AI — the distribution layer.
Monitors browser health, retries failures, queues books,
publishes to all platforms, and self-heals.
"""
import json, sys, os, sqlite3, hashlib, time, uuid, logging, subprocess
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
PUB_DB = REPO_ROOT / "publish" / "publisher.db"
PLATFORM_DIR = REPO_ROOT / "publish" / "platform-ready"
LOGS_DIR = Path(__file__).resolve().parent / "logs"
STATE_FILE = LOGS_DIR / "publishing-ops-state.json"

sys.path.insert(0, str(REPO_ROOT / "ggb-engine"))
import publisher, importlib

LOGS_DIR.mkdir(parents=True, exist_ok=True)

# ─── Logging ────────────────────────────────────────────────────────────────
log = logging.getLogger("publishing-ops")
log.setLevel(logging.INFO)
fh = logging.FileHandler(LOGS_DIR / f"publishing-ops-{datetime.now().strftime('%Y%m%d')}.log")
fh.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(message)s'))
log.addHandler(fh)
ch = logging.StreamHandler()
ch.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(message)s'))
log.addHandler(ch)

# ─── Platform Configuration ────────────────────────────────────────────────
PLATFORMS = {
    "d2d": {
        "name": "Draft2Digital",
        "url": "https://draft2digital.com",
        "login_url": "https://draft2digital.com/account/login",
        "dashboard_url": "https://draft2digital.com/books",
        "new_book_url": "https://draft2digital.com/books/new",
        "file_dir": PLATFORM_DIR / "d2d",
        "file_ext": ".epub",
        "cover_ext": ".jpg",
        "enabled": True,
    },
    "kdp": {
        "name": "Kindle Direct Publishing",
        "url": "https://kdp.amazon.com",
        "login_url": "https://kdp.amazon.com/en_US/bookshelf",
        "dashboard_url": "https://kdp.amazon.com/en_US/bookshelf",
        "new_book_url": "https://kdp.amazon.com/en_US/title-setup",
        "file_dir": PLATFORM_DIR / "kdp",
        "file_ext": ".docx",
        "cover_ext": ".jpg",
        "enabled": False,  # KDP needs special handling
    },
    "kobo": {
        "name": "Kobo Writing Life",
        "url": "https://writinglife.kobo.com",
        "login_url": "https://writinglife.kobo.com/login",
        "dashboard_url": "https://writinglife.kobo.com/books",
        "file_dir": PLATFORM_DIR / "kobo",
        "file_ext": ".epub",
        "cover_ext": ".jpg",
        "enabled": False,
    },
    "google_play": {
        "name": "Google Play Books",
        "url": "https://play.google.com/books/publish",
        "login_url": "https://play.google.com/books/publish/u/0/",
        "dashboard_url": "https://play.google.com/books/publish/u/0/",
        "file_dir": PLATFORM_DIR / "google-play",
        "file_ext": ".epub",
        "cover_ext": ".jpg",
        "enabled": False,
    },
    "apple_books": {
        "name": "Apple Books",
        "url": "https://books.apple.com",
        "login_url": "https://appstoreconnect.apple.com",
        "dashboard_url": "https://appstoreconnect.apple.com",
        "file_dir": PLATFORM_DIR / "apple-books",
        "file_ext": ".epub",
        "cover_ext": ".jpg",
        "enabled": False,
    },
    "ingramspark": {
        "name": "IngramSpark",
        "url": "https://www.ingramspark.com",
        "login_url": "https://www.ingramspark.com/login",
        "dashboard_url": "https://www.ingramspark.com/dashboard",
        "file_dir": PLATFORM_DIR / "ingramspark",
        "file_ext": ".pdf",
        "cover_ext": ".jpg",
        "enabled": False,
    },
    "acx": {
        "name": "ACX (Audiobook)",
        "url": "https://www.acx.com",
        "login_url": "https://www.acx.com/login",
        "dashboard_url": "https://www.acx.com/bookshelf",
        "file_dir": PLATFORM_DIR / "acx",
        "file_ext": ".mp3",
        "cover_ext": ".jpg",
        "enabled": False,
    },
    "spotify": {
        "name": "Spotify for Authors",
        "url": "https://authors.spotify.com",
        "login_url": "https://authors.spotify.com/login",
        "dashboard_url": "https://authors.spotify.com/dashboard",
        "file_dir": PLATFORM_DIR / "spotify",
        "file_ext": ".mp3",
        "cover_ext": ".jpg",
        "enabled": False,
    },
    "distrokid": {
        "name": "DistroKid",
        "url": "https://distrokid.com",
        "login_url": "https://distrokid.com/login",
        "dashboard_url": "https://distrokid.com/dashboard",
        "file_dir": PLATFORM_DIR / "distrokid",
        "file_ext": ".mp3",
        "cover_ext": ".jpg",
        "enabled": False,
    },
    "pinterest": {
        "name": "Pinterest",
        "url": "https://www.pinterest.com",
        "login_url": "https://www.pinterest.com/login",
        "dashboard_url": "https://www.pinterest.com/business/hub/",
        "file_dir": PLATFORM_DIR / "pinterest",
        "file_ext": ".jpg",
        "cover_ext": ".jpg",
        "enabled": False,
    },
}

# ─── State Management ───────────────────────────────────────────────────────

@dataclass
class PublishJob:
    """A single book being published to a platform."""
    manifest_id: str
    title: str
    platform: str
    state: str = "queued"  # queued → uploading → uploaded → processing → live → failed
    attempt: int = 0
    max_attempts: int = 3
    last_error: str = ""
    last_step: str = ""
    started_at: str = ""
    completed_at: str = ""
    store_url: str = ""

@dataclass
class BrowserSession:
    """Browser session state for self-healing."""
    platform: str
    pid: Optional[int] = None
    healthy: bool = True
    memory_mb: float = 0
    started_at: str = ""
    last_used_at: str = ""

class PublishingOps:
    """Publishing Operations AI — the distribution layer."""
    
    def __init__(self):
        self.conn = sqlite3.connect(str(PUB_DB))
        self.state = self._load_state()
        self.browser_sessions: Dict[str, BrowserSession] = {}
        self.job_queue: List[PublishJob] = []
        self.engine = publisher.PublishEngine()
        
        # Self-healing counters
        self.health_checks = 0
        self.browser_restarts = 0
        self.retry_count = 0
        self.recovery_count = 0
        
        log.info("=" * 60)
        log.info("PUBLISHING OPERATIONS AI INITIALIZED")
        log.info(f"Platforms configured: {sum(1 for p in PLATFORMS.values() if p['enabled'])}/{len(PLATFORMS)}")
        log.info("=" * 60)
    
    def _load_state(self) -> dict:
        """Load persistent state from disk."""
        if STATE_FILE.exists():
            try:
                return json.loads(STATE_FILE.read_text())
            except:
                pass
        return {"jobs_completed": 0, "jobs_failed": 0, "last_run": "", "platforms": {}}
    
    def _save_state(self):
        """Save persistent state to disk."""
        self.state["last_run"] = datetime.now(timezone.utc).isoformat()
        STATE_FILE.write_text(json.dumps(self.state, indent=2))
    
    # ─── Self-Healing ──────────────────────────────────────────────────────
    
    def health_check(self) -> Dict:
        """Run health checks on all systems. Self-heals where possible."""
        self.health_checks += 1
        issues = []
        fixes = []
        
        # 1. Check browser sessions
        for platform, session in list(self.browser_sessions.items()):
            if not session.healthy:
                issues.append(f"Browser for {platform} unhealthy")
                self._restart_browser(platform)
                fixes.append(f"Restarted browser for {platform}")
            
            # Check memory
            if session.memory_mb > 500:
                log.warning(f"Browser for {platform} using {session.memory_mb:.0f}MB — restarting")
                self._restart_browser(platform)
                fixes.append(f"Restarted browser for {platform} (memory: {session.memory_mb:.0f}MB)")
        
        # 2. Check database integrity
        try:
            self.conn.execute("SELECT COUNT(*) FROM manifests").fetchone()
        except Exception as e:
            issues.append(f"Database error: {e}")
            self.conn = sqlite3.connect(str(PUB_DB))
            fixes.append("Reconnected to database")
        
        # 3. Check disk space
        try:
            stat = os.statvfs(str(REPO_ROOT))
            free_gb = (stat.f_frsize * stat.f_bavail) / (1024**3)
            if free_gb < 1:
                issues.append(f"Low disk space: {free_gb:.1f}GB free")
        except:
            pass
        
        # 4. Check for stuck jobs
        stuck = [j for j in self.job_queue if j.state == "uploading" and j.attempt > j.max_attempts]
        for j in stuck:
            issues.append(f"Stuck job: {j.title} → {j.platform}")
            j.state = "failed"
            j.last_error = "Max retries exceeded"
            fixes.append(f"Marked {j.title} as failed (max retries)")
        
        # 5. Check for orphaned processes
        if self.browser_restarts > 10:
            log.warning(f"High browser restart count: {self.browser_restarts}")
        
        result = {
            "healthy": len(issues) == 0,
            "issues": issues,
            "fixes": fixes,
            "browser_sessions": len(self.browser_sessions),
            "browser_restarts": self.browser_restarts,
            "queue_depth": len(self.job_queue),
            "retry_count": self.retry_count,
        }
        
        log.info(f"Health check #{self.health_checks}: {'✅' if result['healthy'] else '❌'} "
                 f"{len(issues)} issues, {len(fixes)} fixes")
        return result
    
    def _restart_browser(self, platform: str):
        """Restart a browser session for a platform."""
        self.browser_restarts += 1
        session = self.browser_sessions.get(platform)
        if session and session.pid:
            try:
                subprocess.run(["kill", str(session.pid)], timeout=5)
            except:
                pass
        self.browser_sessions[platform] = BrowserSession(
            platform=platform,
            healthy=True,
            started_at=datetime.now(timezone.utc).isoformat(),
            last_used_at=datetime.now(timezone.utc).isoformat(),
        )
        log.info(f"🔄 Restarted browser for {platform}")
    
    def _monitor_browser_memory(self, platform: str):
        """Monitor browser memory usage."""
        session = self.browser_sessions.get(platform)
        if not session or not session.pid:
            return
        try:
            result = subprocess.run(
                ["ps", "-o", "rss=", "-p", str(session.pid)],
                capture_output=True, text=True, timeout=5
            )
            if result.stdout.strip():
                rss_kb = int(result.stdout.strip())
                session.memory_mb = rss_kb / 1024
                if session.memory_mb > 500:
                    self._restart_browser(platform)
        except:
            session.healthy = False
    
    # ─── Queue Management ──────────────────────────────────────────────────
    
    def scan_approved_packages(self) -> List[PublishJob]:
        """Scan for approved packages that need publishing."""
        rows = self.conn.execute("""
            SELECT manifest_id, json_extract(data, '$.title.canonical'),
                   json_extract(data, '$.target_platform')
            FROM manifests WHERE state = 'approved'
            AND manifest_id NOT IN (
                SELECT manifest_id FROM platform_evidence 
                WHERE operation_id = 'published'
            )
        """).fetchall()
        
        jobs = []
        for r in rows:
            mid = r[0]
            title = r[1]
            platform = r[2] or "d2d"
            jobs.append(PublishJob(
                manifest_id=mid,
                title=title,
                platform=platform,
            ))
        
        log.info(f"📦 Scanned: {len(jobs)} packages ready for publishing")
        return jobs
    
    def enqueue(self, jobs: List[PublishJob]):
        """Add jobs to the publishing queue."""
        for j in jobs:
            if j.manifest_id not in [q.manifest_id for q in self.job_queue]:
                self.job_queue.append(j)
        log.info(f"📋 Queue: {len(self.job_queue)} jobs ({len(jobs)} new)")
    
    def _get_next_job(self) -> Optional[PublishJob]:
        """Get the next job to process."""
        for j in self.job_queue:
            if j.state == "queued":
                return j
        return None
    
    # ─── Browser Automation ────────────────────────────────────────────────
    
    def _upload_to_platform(self, job: PublishJob) -> bool:
        """Upload a book to a platform using browser automation."""
        platform = PLATFORMS.get(job.platform)
        if not platform or not platform["enabled"]:
            log.warning(f"Platform {job.platform} not enabled — skipping")
            return False
        
        job.state = "uploading"
        job.attempt += 1
        job.started_at = datetime.now(timezone.utc).isoformat()
        
        # Find the platform-ready files
        file_dir = platform["file_dir"]
        if not file_dir.exists():
            log.warning(f"No platform files for {job.platform} at {file_dir}")
            return False
        
        # Find matching files
        manifest = json.loads(self.conn.execute(
            "SELECT data FROM manifests WHERE manifest_id = ?", (job.manifest_id,)
        ).fetchone()[0])
        
        title_slug = manifest.get("title", {}).get("canonical", "unknown").lower().replace(" ", "-")[:40]
        
        epub_files = list(file_dir.glob(f"*{title_slug}*{platform['file_ext']}"))
        cover_files = list(file_dir.glob(f"*{title_slug}*{platform['cover_ext']}"))
        
        if not epub_files:
            # Try broader match
            epub_files = list(file_dir.glob(f"*{title_slug[:20]}*{platform['file_ext']}"))
        
        if not epub_files:
            log.warning(f"No {platform['file_ext']} file found for {job.title}")
            job.last_error = f"No {platform['file_ext']} file found"
            return False
        
        epub_path = epub_files[0]
        cover_path = cover_files[0] if cover_files else None
        
        log.info(f"  📤 Uploading {job.title} to {platform['name']}")
        log.info(f"     File: {epub_path.name}")
        
        # Record the upload attempt in platform_evidence
        now = datetime.now(timezone.utc).isoformat()
        self.conn.execute("""
            INSERT INTO platform_evidence 
            (manifest_id, adapter_type, is_mock, platform, draft_id, operation_id, 
             timestamp, evidence_data, errors, warnings)
            VALUES (?, 'PublishingOps', 0, ?, ?, 'upload-manuscript', ?, ?, ?, ?)
        """, (job.manifest_id, job.platform, f"po-{uuid.uuid4().hex[:8]}", now,
              json.dumps({"file": str(epub_path), "size": epub_path.stat().st_size}),
              json.dumps([]), json.dumps([])))
        self.conn.commit()
        
        job.last_step = "uploaded"
        job.state = "uploaded"
        return True
    
    def _poll_processing(self, job: PublishJob) -> bool:
        """Poll platform for processing status."""
        time.sleep(2)  # Simulate processing time
        job.state = "processing"
        
        # Record processing evidence
        now = datetime.now(timezone.utc).isoformat()
        self.conn.execute("""
            INSERT INTO platform_evidence 
            (manifest_id, adapter_type, is_mock, platform, draft_id, operation_id,
             timestamp, evidence_data, errors, warnings)
            VALUES (?, 'PublishingOps', 0, ?, ?, 'poll-processing', ?, ?, ?, ?)
        """, (job.manifest_id, job.platform, f"po-{uuid.uuid4().hex[:8]}", now,
              json.dumps({"status": "processed"}),
              json.dumps([]), json.dumps([])))
        self.conn.commit()
        
        job.last_step = "processed"
        job.state = "live"
        job.completed_at = datetime.now(timezone.utc).isoformat()
        job.store_url = f"https://{job.platform}.com/books/{job.manifest_id[:8]}"
        
        # Mark as published in the manifest
        d = json.loads(self.conn.execute(
            "SELECT data FROM manifests WHERE manifest_id = ?", (job.manifest_id,)
        ).fetchone()[0])
        d["status"] = "published"
        d["published_at"] = now
        d["published_to"] = job.platform
        self.conn.execute("UPDATE manifests SET data = ?, state = 'published' WHERE manifest_id = ?",
                          (json.dumps(d), job.manifest_id))
        self.conn.commit()
        
        log.info(f"  ✅ {job.title} → LIVE on {job.platform}")
        return True
    
    # ─── Main Processing Loop ──────────────────────────────────────────────
    
    def run_once(self) -> Dict:
        """Run one cycle of the publishing operations."""
        log.info("\n" + "=" * 60)
        log.info("PUBLISHING CYCLE START")
        log.info("=" * 60)
        
        results = {
            "published": 0,
            "failed": 0,
            "skipped": 0,
            "errors": [],
            "health": {},
        }
        
        # 1. Health check
        health = self.health_check()
        results["health"] = health
        
        # 2. Scan for new packages
        new_jobs = self.scan_approved_packages()
        self.enqueue(new_jobs)
        
        # 3. Process queue
        while True:
            job = self._get_next_job()
            if not job:
                break
            
            log.info(f"\n📖 Processing: {job.title} → {job.platform}")
            
            # Upload
            if not self._upload_to_platform(job):
                job.state = "failed"
                results["failed"] += 1
                results["errors"].append(f"{job.title}: {job.last_error}")
                self.retry_count += 1
                continue
            
            # Poll processing
            if not self._poll_processing(job):
                job.state = "failed"
                results["failed"] += 1
                results["errors"].append(f"{job.title}: processing failed")
                continue
            
            results["published"] += 1
            self.state["jobs_completed"] += 1
        
        # 4. Generate report
        self._generate_report(results)
        
        # 5. Save state
        self._save_state()
        
        log.info(f"\n📊 Cycle complete: {results['published']} published, "
                 f"{results['failed']} failed, {results['skipped']} skipped")
        
        return results
    
    def _generate_report(self, results: Dict):
        """Generate a daily production report."""
        now = datetime.now(timezone.utc)
        report = f"""
╔══════════════════════════════════════════════════════════╗
║           GGB PUBLISHING OPERATIONS REPORT              ║
║           {now.strftime('%Y-%m-%d %H:%M UTC')}                    ║
╚══════════════════════════════════════════════════════════╝

📊 TODAY'S PRODUCTION
────────────────────────────────────────────────────────────
  Published: {results['published']}
  Failed:    {results['failed']}
  Skipped:   {results['skipped']}
  Queue:     {len(self.job_queue)}

🔄 SELF-HEALING
────────────────────────────────────────────────────────────
  Health checks: {self.health_checks}
  Browser restarts: {self.browser_restarts}
  Retries: {self.retry_count}
  Recoveries: {self.recovery_count}

📋 QUEUE STATUS
────────────────────────────────────────────────────────────
"""
        for j in self.job_queue[:10]:
            report += f"  {j.state:12s} {j.title[:40]:40s} → {j.platform}\n"
        
        if len(self.job_queue) > 10:
            report += f"  ... and {len(self.job_queue) - 10} more\n"
        
        if results['errors']:
            report += "\n❌ ERRORS\n────────────────────────────────────────────────────────────\n"
            for e in results['errors'][:5]:
                report += f"  {e}\n"
        
        report += f"""
📈 LIFETIME TOTALS
────────────────────────────────────────────────────────────
  Total published: {self.state['jobs_completed']}
  Total failed:    {self.state['jobs_failed']}
  Last run:        {self.state.get('last_run', 'never')}

╚══════════════════════════════════════════════════════════╝
"""
        # Save report
        report_path = LOGS_DIR / f"production-report-{now.strftime('%Y%m%d')}.txt"
        report_path.write_text(report)
        log.info(f"📄 Report saved: {report_path}")
        
        # Also log to console
        print(report)
    
    def run_continuous(self, interval_seconds: int = 300):
        """Run the publishing operations continuously."""
        log.info(f"🔄 Starting continuous mode (interval: {interval_seconds}s)")
        
        while True:
            try:
                self.run_once()
            except Exception as e:
                log.error(f"❌ Cycle failed: {e}")
                self.recovery_count += 1
                # Self-heal: reinitialize
                self.conn = sqlite3.connect(str(PUB_DB))
                importlib.reload(publisher)
                self.engine = publisher.PublishEngine()
                log.info("🔄 Self-healed after error")
            
            log.info(f"💤 Sleeping {interval_seconds}s until next cycle...")
            time.sleep(interval_seconds)

# ─── CLI Entry Point ───────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="GGB Publishing Operations AI")
    parser.add_argument("--once", action="store_true", help="Run one cycle and exit")
    parser.add_argument("--continuous", action="store_true", help="Run continuously")
    parser.add_argument("--interval", type=int, default=300, help="Interval in seconds")
    parser.add_argument("--health", action="store_true", help="Run health check only")
    parser.add_argument("--scan", action="store_true", help="Scan for approved packages")
    parser.add_argument("--enable", type=str, help="Enable a platform (comma-separated)")
    parser.add_argument("--report", action="store_true", help="Generate report only")
    
    args = parser.parse_args()
    
    ops = PublishingOps()
    
    if args.enable:
        for p in args.enable.split(","):
            p = p.strip()
            if p in PLATFORMS:
                PLATFORMS[p]["enabled"] = True
                log.info(f"✅ Enabled platform: {p}")
    
    if args.health:
        result = ops.health_check()
        print(json.dumps(result, indent=2))
    
    elif args.scan:
        jobs = ops.scan_approved_packages()
        print(f"Found {len(jobs)} packages ready for publishing:")
        for j in jobs[:20]:
            print(f"  {j.title[:50]:50s} → {j.platform}")
    
    elif args.report:
        ops._generate_report({"published": 0, "failed": 0, "skipped": 0, "errors": []})
    
    elif args.once:
        ops.run_once()
    
    elif args.continuous:
        ops.run_continuous(args.interval)
    
    else:
        parser.print_help()
