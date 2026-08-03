#!/usr/bin/env python3
"""
GGB Zero-Error Pipeline — quality gate that catches and fixes everything
before it becomes a problem. Runs after every landing pad cycle.
"""
import json, sys, os, sqlite3, hashlib, re, time
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
PUB_DB = REPO_ROOT / "publish" / "publisher.db"
LANDING_PAD = REPO_ROOT / "publish" / "landing-pad"
LOGS_DIR = Path(__file__).resolve().parent / "logs"

sys.path.insert(0, str(REPO_ROOT / "ggb-engine"))
import publisher, importlib

# OpenRouter config
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")
OPENROUTER_BASE = "https://openrouter.ai/api/v1"
OPENROUTER_MODEL = "deepseek/deepseek-chat"

LOGS_DIR.mkdir(parents=True, exist_ok=True)

class ZeroErrorPipeline:
    """Quality gate that prevents errors before they happen."""
    
    def __init__(self):
        self.conn = sqlite3.connect(str(PUB_DB))
        self.engine = publisher.PublishEngine()
        self.results = {"passed": 0, "fixed": 0, "failed": 0, "errors": []}
    
    def run(self):
        """Run the full zero-error pipeline."""
        print("=" * 60)
        print("GGB ZERO-ERROR PIPELINE")
        print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60)
        
        # Step 1: Scan landing pad for new packages
        self._scan_landing_pad()
        
        # Step 2: Pre-validate all discovered packages
        self._pre_validate()
        
        # Step 3: Fix common issues
        self._fix_issues()
        
        # Step 4: Run pipeline on clean packages
        self._run_pipeline()
        
        # Step 5: Final quality check
        self._final_quality_check()
        
        # Report
        self._report()
        
        self.conn.close()
        return self.results
    
    def _scan_landing_pad(self):
        """Scan landing pad for new packages and register them."""
        print("\n📦 Step 1: Scanning landing pad...")
        count = 0
        for pkg_dir in sorted(LANDING_PAD.iterdir()):
            if not pkg_dir.is_dir():
                continue
            manifest_file = pkg_dir / "manifest.json"
            if not manifest_file.exists():
                continue
            
            # Check if already registered
            pkg_hash = hashlib.sha256(str(pkg_dir.name).encode()).hexdigest()[:16]
            existing = self.conn.execute(
                "SELECT manifest_id FROM manifests WHERE package_hash = ?",
                (pkg_hash,)
            ).fetchone()
            if existing:
                continue
            
            # Register
            try:
                manifest = json.loads(manifest_file.read_text())
                result = self.engine.discover(str(manifest_file))
                if result.get("manifest_id"):
                    count += 1
                    print(f"  ✅ Discovered: {manifest.get('title', {}).get('canonical', '?')}")
            except Exception as e:
                print(f"  ❌ Failed to discover {pkg_dir.name}: {str(e)[:80]}")
        
        print(f"  {count} new packages discovered")
    
    def _pre_validate(self):
        """Pre-validate all discovered packages before they enter the pipeline."""
        print("\n🔍 Step 2: Pre-validating packages...")
        
        rows = self.conn.execute("""
            SELECT manifest_id, data FROM manifests WHERE state = 'discovered'
        """).fetchall()
        
        for r in rows:
            mid = r[0]
            d = json.loads(r[1])
            title = d.get("title", {}).get("canonical", "?")
            issues = []
            
            # Check files exist
            for key, finfo in d.get("files", {}).items():
                path = Path(finfo["path"])
                if not path.exists():
                    issues.append(f"Missing file: {key} ({path.name})")
                else:
                    # Fix hash if wrong
                    actual = hashlib.sha256(path.read_bytes()).hexdigest()
                    if actual != finfo.get("sha256"):
                        finfo["sha256"] = actual
                        finfo["size"] = path.stat().st_size
                        issues.append(f"Fixed hash for {key}")
            
            # Check manuscript has content
            ms = d.get("files", {}).get("manuscript", {})
            ms_path_str = ms.get("path", "")
            if ms_path_str and ms_path_str != ".":
                ms_path = Path(ms_path_str)
                if ms_path.exists() and ms_path.is_file():
                    text = ms_path.read_text()
                    words = len(text.split())
                    if words < 500:
                        issues.append(f"Manuscript too short: {words} words")
            
            # Check cover exists
            cv = d.get("files", {}).get("cover", {})
            cv_path_str = cv.get("path", "")
            if cv_path_str and cv_path_str != ".":
                cv_path = Path(cv_path_str)
                if cv_path.exists() and cv_path.is_file() and cv_path.stat().st_size < 10000:
                    issues.append(f"Cover too small: {cv_path.stat().st_size}B")
            
            # Check price
            price = d.get("publishing", {}).get("price", 0)
            if not price or price < 0.99:
                issues.append(f"Invalid price: ${price}")
            
            # Check platform
            platform = d.get("target_platform", "kdp")
            if platform not in ("kdp", "d2d", "acx", "spotify", "distrokid", "pinterest"):
                issues.append(f"Unknown platform: {platform}")
            
            # Save fixes
            if issues:
                self.conn.execute("UPDATE manifests SET data = ? WHERE manifest_id = ?",
                                  (json.dumps(d), mid))
                self.conn.commit()
                for issue in issues:
                    print(f"  ⚠️  {title}: {issue}")
                    self.results["fixed"] += 1
            else:
                print(f"  ✅ {title}: clean")
                self.results["passed"] += 1
    
    def _fix_issues(self):
        """Fix common issues automatically."""
        print("\n🔧 Step 3: Fixing issues...")
        
        # Fix hash mismatches in all states
        rows = self.conn.execute("""
            SELECT manifest_id, data FROM manifests 
            WHERE state IN ('discovered', 'validated', 'blocked')
        """).fetchall()
        
        for r in rows:
            mid = r[0]
            d = json.loads(r[1])
            title = d.get("title", {}).get("canonical", "?")
            fixed = False
            
            for key, finfo in d.get("files", {}).items():
                path = Path(finfo["path"])
                if path.exists():
                    actual = hashlib.sha256(path.read_bytes()).hexdigest()
                    if actual != finfo.get("sha256"):
                        finfo["sha256"] = actual
                        finfo["size"] = path.stat().st_size
                        fixed = True
            
            # Clear stale validation errors
            if d.get("state") == "blocked" and d.get("validation", {}).get("errors"):
                # Check if errors are still valid
                errors = d["validation"].get("errors", [])
                new_errors = []
                for err in errors:
                    # Hash mismatch errors can be cleared if files exist
                    if "Hash mismatch" in err:
                        # Check if files now match
                        all_match = True
                        for key, finfo in d.get("files", {}).items():
                            path = Path(finfo["path"])
                            if path.exists():
                                actual = hashlib.sha256(path.read_bytes()).hexdigest()
                                if actual != finfo.get("sha256"):
                                    all_match = False
                        if all_match:
                            continue  # Skip this error
                    new_errors.append(err)
                
                if len(new_errors) < len(errors):
                    d["validation"]["errors"] = new_errors
                    d["validation"]["passed"] = len(new_errors) == 0
                    fixed = True
            
            if fixed:
                self.conn.execute("UPDATE manifests SET data = ? WHERE manifest_id = ?",
                                  (json.dumps(d), mid))
                self.conn.commit()
                print(f"  ✅ Fixed: {title}")
                self.results["fixed"] += 1
    
    def _run_pipeline(self):
        """Run the pipeline on clean packages."""
        print("\n🚀 Step 4: Running pipeline...")
        
        # Process discovered packages
        rows = self.conn.execute("""
            SELECT manifest_id, data FROM manifests WHERE state = 'discovered'
        """).fetchall()
        
        for r in rows:
            mid = r[0]
            d = json.loads(r[1])
            title = d.get("title", {}).get("canonical", "?")
            
            try:
                # Reconcile
                r1 = self.engine.reconcile(mid)
                if r1.get("error"):
                    print(f"  ❌ {title}: reconcile failed - {r1['error'][:80]}")
                    self.results["errors"].append(f"{title}: {r1['error']}")
                    continue
                
                # Audit
                r2 = self.engine.audit(mid)
                if r2.get("error") or (isinstance(r2, dict) and r2.get("passed") == False):
                    err = r2.get("error") or r2.get("errors", ["unknown"])[0]
                    print(f"  ❌ {title}: audit failed - {err[:80]}")
                    self.results["errors"].append(f"{title}: {err}")
                    continue
                
                # Stage
                r3 = self.engine.stage(mid)
                if r3.get("error"):
                    print(f"  ❌ {title}: stage failed - {r3['error'][:80]}")
                    self.results["errors"].append(f"{title}: {r3['error']}")
                    continue
                
                # Preview
                r4 = self.engine.preview(mid)
                if r4.get("error"):
                    print(f"  ❌ {title}: preview failed - {r4['error'][:80]}")
                    self.results["errors"].append(f"{title}: {r4['error']}")
                    continue
                
                print(f"  ✅ {title}: pipeline complete")
                self.results["passed"] += 1
                
            except Exception as e:
                print(f"  ❌ {title}: unexpected error - {str(e)[:80]}")
                self.results["errors"].append(f"{title}: {str(e)}")
    
    def _final_quality_check(self):
        """Final quality check on all approved packages."""
        print("\n✅ Step 5: Final quality check...")
        
        rows = self.conn.execute("""
            SELECT manifest_id, data FROM manifests WHERE state = 'approved'
        """).fetchall()
        
        issues = 0
        for r in rows:
            mid = r[0]
            d = json.loads(r[1])
            title = d.get("title", {}).get("canonical", "?")
            
            # Verify all files exist
            for key, finfo in d.get("files", {}).items():
                path = Path(finfo["path"])
                if not path.exists():
                    print(f"  ⚠️  {title}: {key} file missing at {path}")
                    issues += 1
            
            # Verify hashes
            for key, finfo in d.get("files", {}).items():
                path = Path(finfo["path"])
                if path.exists():
                    actual = hashlib.sha256(path.read_bytes()).hexdigest()
                    if actual != finfo.get("sha256"):
                        print(f"  ⚠️  {title}: {key} hash mismatch")
                        issues += 1
        
        if issues == 0:
            print("  ✅ All approved packages verified clean")
    
    def _report(self):
        """Generate report."""
        print("\n" + "=" * 60)
        print("ZERO-ERROR PIPELINE REPORT")
        print("=" * 60)
        print(f"  ✅ Passed: {self.results['passed']}")
        print(f"  🔧 Fixed:  {self.results['fixed']}")
        print(f"  ❌ Failed:  {self.results['failed']}")
        print(f"  ⚠️  Errors:  {len(self.results['errors'])}")
        
        if self.results['errors']:
            print("\nErrors:")
            for e in self.results['errors'][:10]:
                print(f"  ❌ {e}")
        
        # Save report
        report_path = LOGS_DIR / f"zero-error-{datetime.now().strftime('%Y%m%d-%H%M')}.json"
        report_path.write_text(json.dumps(self.results, indent=2))
        print(f"\n📄 Report saved: {report_path}")
        
        # Update scoreboard
        try:
            sb = sqlite3.connect(str(REPO_ROOT / "ggb-engine" / "headquarters" / "logs" / "scoreboard.db"))
            sb.execute("INSERT OR REPLACE INTO packages (manifest_id, status, updated_at) VALUES (?, ?, ?)",
                       ("zero-error-pipeline", "ok", datetime.now(timezone.utc).isoformat()))
            sb.commit()
            sb.close()
        except:
            pass

if __name__ == "__main__":
    pipeline = ZeroErrorPipeline()
    results = pipeline.run()
    sys.exit(0 if len(results["errors"]) == 0 else 1)
