#!/usr/bin/env python3
"""
ELITE PUBLISHING EXECUTION ENGINE
==================================
"Published books change lives. Unsubmitted books do nothing."

This script is the master controller that:
1. Verifies all prerequisites (DB, files, API keys)
2. Fires publishing bots for each platform
3. Tracks progress in real-time
4. Reports final results

Usage: python3 execute-publishing.py
"""

import os
import sys
import json
import time
import sqlite3
import subprocess
import signal
from pathlib import Path
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from dotenv import load_dotenv
import requests

# === CONFIGURATION ===
BASE_DIR = Path("/Users/darrylsmac/gullahgeecheebiz-site")
ENGINE_DIR = BASE_DIR / "ggb-engine" / "headquarters"
PUBLISH_DIR = BASE_DIR / "publish"
DB_PATH = PUBLISH_DIR / "publisher.db"
EPUB_DIR = PUBLISH_DIR / "for-distribution" / "google-play"
CSV_DIR = ENGINE_DIR / "logs" / "universal-submitter" / "csv"
ENV_FILE = BASE_DIR / ".env"
LOG_DIR = ENGINE_DIR / "logs" / "execution"

# Bot paths
GUMROAD_BOT = ENGINE_DIR / "gumroad-publisher.py"
SHOPIFY_BOT = ENGINE_DIR / "shopify-uploader.py"
PINTEREST_BOT = ENGINE_DIR / "pinterest-uploader.py"
UNIVERSAL_TRACKER = ENGINE_DIR / "universal-submitter.py"

TOTAL_EXPECTED = 1817
TOTAL_EPUBS = 2823

# === DATA CLASSES ===
@dataclass
class PlatformStatus:
    name: str
    enabled: bool = False
    api_key_present: bool = False
    process: Optional[subprocess.Popen] = None
    books_submitted: int = 0
    books_failed: int = 0
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    errors: List[str] = field(default_factory=list)
    pid: Optional[int] = None

    @property
    def elapsed(self) -> str:
        if not self.start_time:
            return "Not started"
        end = self.end_time or datetime.now()
        delta = end - self.start_time
        hours, remainder = divmod(int(delta.total_seconds()), 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

    @property
    def rate(self) -> float:
        if not self.start_time:
            return 0
        elapsed_min = (datetime.now() - self.start_time).total_seconds() / 60
        return self.books_submitted / elapsed_min if elapsed_min > 0 else 0

    @property
    def eta(self) -> str:
        if self.rate <= 0:
            return "Unknown"
        remaining = TOTAL_EXPECTED - self.books_submitted
        minutes_left = remaining / self.rate
        return str(timedelta(minutes=int(minutes_left)))


@dataclass
class ExecutionReport:
    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    platforms: Dict[str, PlatformStatus] = field(default_factory=dict)
    db_intact: bool = False
    db_book_count: int = 0
    epub_count: int = 0
    csv_count: int = 0
    prereqs_passed: bool = False

    @property
    def total_submitted(self) -> int:
        return sum(p.books_submitted for p in self.platforms.values())

    @property
    def total_failed(self) -> int:
        return sum(p.books_failed for p in self.platforms.values())

    @property
    def total_elapsed(self) -> str:
        end = self.end_time or datetime.now()
        delta = end - self.start_time
        hours, remainder = divmod(int(delta.total_seconds()), 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


# === PREREQUISITE CHECKS ===
def check_database(report: ExecutionReport) -> bool:
    """Verify database integrity and count books."""
    print("\n[CHECK] Database integrity...")
    if not DB_PATH.exists():
        print(f"  ❌ Database not found: {DB_PATH}")
        return False

    try:
        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()

        # Check integrity
        cursor.execute("PRAGMA integrity_check")
        integrity = cursor.fetchone()[0]
        if integrity != "ok":
            print(f"  ❌ Database integrity check failed: {integrity}")
            conn.close()
            return False

        # Count books
        cursor.execute("SELECT COUNT(*) FROM books")
        count = cursor.fetchone()[0]
        report.db_book_count = count

        conn.close()
        report.db_intact = True
        print(f"  ✅ Database OK — {count} books verified")
        return count >= TOTAL_EXPECTED

    except Exception as e:
        print(f"  ❌ Database error: {e}")
        return False


def check_epubs(report: ExecutionReport) -> bool:
    """Verify EPUB files exist."""
    print("\n[CHECK] EPUB file availability...")
    if not EPUB_DIR.exists():
        print(f"  ❌ EPUB directory not found: {EPUB_DIR}")
        return False

    epub_files = list(EPUB_DIR.glob("*.epub"))
    report.epub_count = len(epub_files)
    print(f"  ✅ Found {len(epub_files)} EPUB files (expected ~{TOTAL_EPUBS})")
    return len(epub_files) >= TOTAL_EXPECTED


def check_csvs(report: ExecutionReport) -> bool:
    """Verify CSV submission logs exist."""
    print("\n[CHECK] CSV submission logs...")
    if not CSV_DIR.exists():
        print(f"  ⚠️  CSV directory not found: {CSV_DIR}")
        report.csv_count = 0
        return True  # Non-blocking

    csv_files = list(CSV_DIR.glob("*.csv"))
    report.csv_count = len(csv_files)
    print(f"  ✅ Found {len(csv_files)} CSV logs")
    return True


def check_api_keys(report: ExecutionReport) -> Dict[str, bool]:
    """Check for API keys in .env file."""
    print("\n[CHECK] API key presence...")

    # Load .env
    load_dotenv(ENV_FILE)

    keys = {
        "gumroad": {
            "env_var": "GUMROAD_API_TOKEN",
            "present": False
        },
        "shopify": {
            "env_var": "SHOPIFY_ACCESS_TOKEN",
            "present": False
        },
        "pinterest": {
            "env_var": "PINTEREST_ACCESS_TOKEN",
            "present": False
        }
    }

    for platform, config in keys.items():
        token = os.getenv(config["env_var"], "")
        config["present"] = bool(token and len(token) > 10)

        if config["present"]:
            print(f"  ✅ {platform.upper()} API token found ({token[:8]}...)")
            report.platforms[platform].api_key_present = True
            report.platforms[platform].enabled = True
        else:
            print(f"  ❌ {platform.upper()} API token missing — set {config['env_var']}")

    return keys


def check_bot_exists(bot_path: Path, name: str) -> bool:
    """Check if a bot script exists."""
    if not bot_path.exists():
        print(f"  ⚠️  {name} bot not found at: {bot_path}")
        return False
    return True


# === BOT EXECUTION ===
def fire_bot(platform: str, bot_path: Path, report: ExecutionReport) -> Optional[subprocess.Popen]:
    """Launch a publishing bot as a subprocess."""
    status = report.platforms[platform]

    if not check_bot_exists(bot_path, platform):
        status.errors.append(f"Bot script not found: {bot_path}")
        return None

    if not status.api_key_present:
        status.errors.append("API key not configured")
        return None

    print(f"\n[LAUNCH] Firing {platform.upper()} publisher bot...")
    print(f"  Script: {bot_path}")

    # Build environment with API keys
    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    env["PLATFORM"] = platform.upper()

    try:
        process = subprocess.Popen(
            [sys.executable, str(bot_path)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
            cwd=str(ENGINE_DIR),
            text=True,
            bufsize=1
        )

        status.process = process
        status.pid = process.pid
        status.start_time = datetime.now()
        status.enabled = True

        print(f"  ✅ Launched (PID: {process.pid})")
        return process

    except Exception as e:
        print(f"  ❌ Failed to launch: {e}")
        status.errors.append(f"Launch failed: {e}")
        return None


def monitor_progress(report: ExecutionReport, duration_seconds: int = 60):
    """Monitor bot progress for a set duration."""
    print(f"\n[MONITOR] Watching progress for {duration_seconds}s...")
    print("=" * 60)

    start = time.time()
    while time.time() - start < duration_seconds:
        print(f"\n{'─' * 60}")
        print(f"  ⏱️  Elapsed: {report.total_elapsed}")
        print(f"{'─' * 60}")

        for name, status in report.platforms.items():
            if not status.enabled:
                continue

            # Check if process is still running
            if status.process:
                poll = status.process.poll()
                state = "🟢 Running" if poll is None else f"🔴 Exited ({poll})"

                if poll is not None:
                    status.end_time = datetime.now()
                    # Capture any remaining output
                    try:
                        stdout, stderr = status.process.communicate(timeout=2)
                        if stdout:
                            # Count submissions from output
                            lines = stdout.strip().split('\n')
                            for line in lines:
                                if "submitted" in line.lower() or "success" in line.lower():
                                    status.books_submitted += 1
                                if "failed" in line.lower() or "error" in line.lower():
                                    status.books_failed += 1
                    except:
                        pass
            else:
                state = "⚪ Not launched"

            print(f"  [{name.upper():10s}] {state}")
            print(f"             Submitted: {status.books_submitted}/{TOTAL_EXPECTED}")
            print(f"             Failed: {status.books_failed}")
            print(f"             Rate: {status.rate:.1f} books/min")
            print(f"             ETA: {status.eta}")
            print(f"             Time: {status.elapsed}")

            if status.errors:
                print(f"             Errors: {status.errors[-1][:50]}")

        # Check for progress files (bots may write progress)
        check_progress_files(report)

        time.sleep(10)

    print(f"\n{'=' * 60}")


def check_progress_files(report: ExecutionReport):
    """Check for progress files that bots may write."""
    progress_dir = LOG_DIR / "progress"
    if not progress_dir.exists():
        return

    for name in report.platforms:
        progress_file = progress_dir / f"{name}_progress.json"
        if progress_file.exists():
            try:
                with open(progress_file) as f:
                    data = json.load(f)
                report.platforms[name].books_submitted = data.get("submitted", 0)
                report.platforms[name].books_failed = data.get("failed", 0)
            except:
                pass


# === REPORTING ===
def generate_report(report: ExecutionReport) -> str:
    """Generate a comprehensive execution report."""
    report.end_time = datetime.now()

    lines = [
        "",
        "╔══════════════════════════════════════════════════════════╗",
        "║         ELITE PUBLISHING EXECUTION REPORT               ║",
        "║    'Published books change lives.                       ║",
        "║     Unsubmitted books do nothing.'                      ║",
        "╚══════════════════════════════════════════════════════════╝",
        "",
        f"  Execution Time: {report.total_elapsed}",
        f"  Started: {report.start_time.strftime('%Y-%m-%d %H:%M:%S')}",
        f"  Ended:   {report.end_time.strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "  ┌─────────────────────────────────────────────────────┐",
        "  │  PREREQUISITES                                      │",
        "  ├─────────────────────────────────────────────────────┤",
        f"  │  Database:   {'✅ Intact' if report.db_intact else '❌ Failed'} ({report.db_book_count} books)  │",
        f"  │  EPUBs:      {report.epub_count:,} files found                │",
        f"  │  CSV Logs:   {report.csv_count} files found                     │",
        "  └─────────────────────────────────────────────────────┘",
        "",
        "  ┌─────────────────────────────────────────────────────────────┐",
        "  │  PLATFORM RESULTS                                           │",
        "  ├──────────────┬──────────┬──────────┬─────────┬──────────────┤",
        "  │  Platform    │ Status   │Submitted │ Failed  │    Time      │",
        "  ├──────────────┼──────────┼──────────┼─────────┼──────────────┤",
    ]

    for name, status in report.platforms.items():
        if not status.enabled:
            state = "DISABLED"
        elif status.process and status.process.poll() is None:
            state = "RUNNING"
        elif status.books_submitted > 0:
            state = "SUCCESS"
        else:
            state = "FAILED"

        lines.append(
            f"  │  {name.upper():12s}│ {state:8s} │ {status.books_submitted:>8d} │ {status.books_failed:>7d} │ {status.elapsed:>12s} │"
        )

    lines.extend([
        "  └──────────────┴──────────┴──────────┴─────────┴──────────────┘",
        "",
        f"  TOTAL SUBMITTED: {report.total_submitted:,}",
        f"  TOTAL FAILED:    {report.total_failed:,}",
        f"  TARGET:          {TOTAL_EXPECTED:,} per platform",
        "",
    ])

    # Next steps
    lines.append("  ┌─────────────────────────────────────────────────────┐")
    lines.append("  │  NEXT STEPS                                         │")
    lines.append("  ├─────────────────────────────────────────────────────┤")

    for name, status in report.platforms.items():
        if not status.api_key_present:
            lines.append(f"  │  • Get {name.upper()} API token → set in .env          │")
        elif status.books_submitted == 0 and not status.enabled:
            lines.append(f"  │  • Debug {name.upper()} bot (0 submissions)            │")
        elif status.books_submitted < TOTAL_EXPECTED:
            lines.append(f"  │  • Re-run {name.upper()} for remaining books            │")

    if report.total_submitted >= TOTAL_EXPECTED * 2:
        lines.append("  │  • 🎉 Multi-platform success! Scale to more!       │")

    lines.append("  └─────────────────────────────────────────────────────┘")
    lines.append("")

    return "\n".join(lines)


def save_report(report: ExecutionReport, report_text: str):
    """Save report to disk."""
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Text report
    report_file = LOG_DIR / f"execution_report_{timestamp}.txt"
    with open(report_file, "w") as f:
        f.write(report_text)

    # JSON report
    json_file = LOG_DIR / f"execution_report_{timestamp}.json"
    json_data = {
        "start_time": report.start_time.isoformat(),
        "end_time": report.end_time.isoformat() if report.end_time else None,
        "total_submitted": report.total_submitted,
        "total_failed": report.total_failed,
        "db_intact": report.db_intact,
        "db_book_count": report.db_book_count,
        "epub_count": report.epub_count,
        "platforms": {}
    }
    for name, status in report.platforms.items():
        json_data["platforms"][name] = {
            "enabled": status.enabled,
            "api_key_present": status.api_key_present,
            "books_submitted": status.books_submitted,
            "books_failed": status.books_failed,
            "elapsed": status.elapsed,
            "errors": status.errors
        }

    with open(json_file, "w") as f:
        json.dump(json_data, f, indent=2)

    print(f"\n  📄 Report saved: {report_file}")
    print(f"  📊 JSON saved:   {json_file}")


# === QUICK SETUP HELPERS ===
def show_api_setup_instructions():
    """Show instructions for getting API keys."""
    print("""
╔══════════════════════════════════════════════════════════╗
║              API TOKEN SETUP GUIDE                       ║
╠══════════════════════════════════════════════════════════╣
║                                                          ║
║  GUMROAD:                                                ║
║  1. Go to https://gumroad.com/settings/advanced          ║
║  2. Create Application → Get Access Token                ║
║  3. Add to .env: GUMROAD_API_TOKEN=your_token            ║
║                                                          ║
║  SHOPIFY:                                                ║
║  1. Go to Shopify Admin → Settings → Apps                ║
║  2. Create private app → Get API credentials             ║
║  3. Add to .env: SHOPIFY_ACCESS_TOKEN=shpat_xxxx         ║
║                                                          ║
║  PINTEREST:                                              ║
║  1. Go to https://developers.pinterest.com               ║
║  2. Create app → Set to Public → Get Access Token        ║
║  3. Add to .env: PINTEREST_ACCESS_TOKEN=your_token       ║
║                                                          ║
╚══════════════════════════════════════════════════════════╝
""")


def create_progress_tracking_files():
    """Create progress tracking files for inter-process communication."""
    progress_dir = LOG_DIR / "progress"
    progress_dir.mkdir(parents=True, exist_ok=True)

    for platform in ["gumroad", "shopify", "pinterest"]:
        progress_file = progress_dir / f"{platform}_progress.json"
        if not progress_file.exists():
            with open(progress_file, "w") as f:
                json.dump({"submitted": 0, "failed": 0, "last_update": None}, f)


# === MAIN EXECUTION ===
def main():
    print("""
╔══════════════════════════════════════════════════════════╗
║                                                          ║
║        ⚡ ELITE PUBLISHING EXECUTION ENGINE ⚡            ║
║                                                          ║
║   "Published books change lives.                         ║
║    Unsubmitted books do nothing."                        ║
║                                                          ║
║   Target: 1,817 books × 3 platforms = 5,451 uploads     ║
║                                                          ║
╚══════════════════════════════════════════════════════════╝
    """)

    # Initialize report
    report = ExecutionReport()
    report.platforms = {
        "gumroad": PlatformStatus("gumroad"),
        "shopify": PlatformStatus("shopify"),
        "pinterest": PlatformStatus("pinterest"),
    }

    # === PHASE 1: PREREQUISITES ===
    print("\n" + "=" * 60)
    print("  PHASE 1: PREREQUISITE CHECKS")
    print("=" * 60)

    checks_passed = 0
    total_checks = 4

    if check_database(report):
        checks_passed += 1
    if check_epubs(report):
        checks_passed += 1
    if check_csvs(report):
        checks_passed += 1

    api_keys = check_api_keys(report)
    keys_found = sum(1 for k in api_keys.values() if k["present"])
    if keys_found > 0:
        checks_passed += 1

    report.prereqs_passed = checks_passed >= 3  # Allow partial execution

    print(f"\n  Prerequisites: {checks_passed}/{total_checks} passed")

    if checks_passed == 0:
        print("\n  ❌ No prerequisites met. Cannot proceed.")
        show_api_setup_instructions()
        sys.exit(1)

    if keys_found == 0:
        print("\n  ⚠️  No API tokens found. Showing setup instructions...")
        show_api_setup_instructions()
        print("  Add at least one API token to .env and re-run this script.")
        sys.exit(1)

    # === PHASE 2: EXECUTE QUICK WINS ===
    print("\n" + "=" * 60)
    print("  PHASE 2: EXECUTING QUICK WINS")
    print("=" * 60)

    # Create progress tracking
    create_progress_tracking_files()

    # Fire enabled bots
    bots_to_launch = [
        ("gumroad", GUMROAD_BOT),
        ("shopify", SHOPIFY_BOT),
        ("pinterest", PINTEREST_BOT),
    ]

    launched = 0
    for platform, bot_path in bots_to_launch:
        if report.platforms[platform].enabled:
            result = fire_bot(platform, bot_path, report)
            if result:
                launched += 1
            time.sleep(2)  # Stagger launches

    if launched == 0:
        print("\n  ❌ No bots could be launched. Check API keys and bot scripts.")
        sys.exit(1)

    print(f"\n  ✅ {launched} bot(s) launched successfully!")

    # === PHASE 3: MONITOR PROGRESS ===
    print("\n" + "=" * 60)
    print("  PHASE 3: MONITORING PROGRESS")
    print("=" * 60)

    # Monitor for 2 minutes initially (adjust as needed)
    monitor_duration = 120  # seconds
    monitor_progress(report, monitor_duration)

    # === PHASE 4: COLLECT RESULTS ===
    print("\n" + "=" * 60)
    print("  PHASE 4: COLLECTING RESULTS")
    print("=" * 60)

    # Final status check
    for name, status in report.platforms.items():
        if status.process and status.process.poll() is None:
            print(f"  [{name.upper()}] Still running (PID: {status.pid})")
        elif status.process:
            exit_code = status.process.poll()
            print(f"  [{name.upper()}] Completed with exit code: {exit_code}")

    # === PHASE 5: REPORT ===
    report_text = generate_report(report)
    print(report_text)

    # Save report
    save_report(report, report_text)

    # Final message
    print("\n" + "=" * 60)
    print("  EXECUTION COMPLETE")
    print("=" * 60)
    print("""
  💡 REMEMBER:
  • Bots may still be running in the background
  • Check logs in: {log_dir}
  • Re-run this script to monitor ongoing progress
  • Add more API tokens to expand to more platforms

  "Every book published is a seed planted.
   The more you plant, the more you harvest."

  Next command: python3 execute-publishing.py
    """.format(log_dir=LOG_DIR))

    return 0


if __name__ == "__main__":
    # Handle graceful shutdown
    def signal_handler(sig, frame):
        print("\n\n  ⚠️  Shutdown requested. Stopping bots...")
        print("  (Bots will continue in background unless killed)")
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    sys.exit(main())
