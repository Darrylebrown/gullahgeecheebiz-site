#!/usr/bin/env python3
"""
Gullah Geechee Biz — Deploy Bot
Pushes public pages to GitHub Pages. Internal systems stay local.
One-directional: local content → GitHub Pages → worldwide CDN.
"""

import json, os, sys, subprocess, datetime
from pathlib import Path

HOME = os.path.expanduser("~")
SITE_DIR = os.path.join(HOME, "gullahgeecheebiz-site")
LOGS = os.path.join(HOME, ".hermes", "logs")
os.makedirs(LOGS, exist_ok=True)

DEPLOY_LOG = os.path.join(LOGS, "deploy-bot.log")


def log(msg):
    """Write to deploy log."""
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] {msg}"
    print(line)
    with open(DEPLOY_LOG, "a") as f:
        f.write(line + "\n")


def run(cmd, cwd=None):
    """Run a shell command and return (success, output)."""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True,
                                timeout=60, cwd=cwd or SITE_DIR)
        if result.returncode == 0:
            return True, result.stdout
        else:
            return False, result.stderr
    except Exception as e:
        return False, str(e)


def build_site():
    """Build all public pages."""
    log("Building membership pages...")
    success, output = run("python3 scripts/build-membership.py")
    if not success:
        log(f"  ❌ Build failed: {output}")
        return False
    log("  ✅ Membership pages built")
    return True


def deploy():
    """Push to GitHub Pages."""
    log("Deploying to GitHub Pages...")
    
    # Check if we're in a git repo
    success, output = run("git rev-parse --git-dir")
    if not success:
        log(f"  ❌ Not a git repository: {output}")
        return False
    
    # Check for changes
    success, output = run("git status --porcelain")
    if not success:
        log(f"  ❌ Git status failed: {output}")
        return False
    
    if not output.strip():
        log("  ℹ️  No changes to deploy")
        return True
    
    # Pull latest from remote first (avoid push rejection)
    log("  ℹ️  Pulling latest from remote...")
    success, output = run("git pull --rebase origin main 2>&1")
    if not success:
        log(f"  ⚠️  Pull had issues (may be fine): {output[:200]}")
    
    # Add, commit, push — TARGETED add: public pages only.
    # NEVER `git add -A` alone: repo carries tracked internal trees (publish/, .agents/,
    # ggb-engine/, n8n/, tiktok-content/) that must stay local.
    # NOTE: pathspec-exclude form (`git add -A -- . ':(exclude)ggb-engine'`) ERRORS on
    # this repo (git 2.50.1 quirk: "paths are ignored by .gitignore" despite the exclude,
    # because ggb-engine/ is gitignored yet holds tracked files). Plain `git add -A`
    # works but would stage internal-tree changes — so add everything, then `git reset`
    # every internal path as a safety net (reset takes literal paths, no ignored-file check).
    add_cmd = "git add -A -- ."
    success, output = run(add_cmd)
    if success:
        internal = ("ggb-engine publish .agents n8n n8n-nodes-blotato tiktok-content "
                    "bot-dashboard.html command-center.html gumroad_products_report.json "
                    "scripts/workbook-series-generator.py")
        success, output = run(f"git reset -q -- {internal}")
        # verify: abort if anything under an internal tree is still staged
        v_ok, v_out = run("git diff --cached --name-only | grep -E '^(ggb-engine|publish|.agents|n8n|tiktok-content)/' || true")
        if v_ok and v_out.strip():
            log(f"  ❌ Internal paths still staged after safety net: {v_out[:200]}")
            return False
    if not success:
        log(f"  ❌ Git add failed: {output}")
        return False
    
    today = datetime.date.today().strftime("%Y-%m-%d")
    success, output = run(f'git commit -m "Auto-deploy {today}"')
    if not success and "nothing to commit" not in output:
        log(f"  ❌ Git commit failed: {output}")
        return False
    
    # Ensure upstream tracking is set, then push
    success, output = run("git rev-parse --abbrev-ref --symbolic-full-name @{u} 2>/dev/null")
    if not success:
        log("  ℹ️  Setting upstream tracking for main...")
        run("git branch --set-upstream-to=origin/main main 2>/dev/null || git push --set-upstream origin main 2>&1")

    success, output = run("git push origin main 2>&1")
    if not success:
        log(f"  ❌ Git push failed: {output}")
        return False

    log("  ✅ Deployed to GitHub Pages")
    return True


def verify():
    """Verify the deployment is live."""
    log("Verifying deployment...")
    success, output = run("curl -s -o /dev/null -w '%{http_code}' https://gullahgeecheebiz.com/")
    if success and output.strip() == "200":
        log("  ✅ Site is live (200 OK)")
        return True
    else:
        log(f"  ⚠️  Site check: {output}")
        return False


def main():
    print("=" * 60)
    print("  GULLAH GEECHEE BIZ — DEPLOY BOT")
    print(f"  Date: {datetime.date.today().strftime('%B %d, %Y')}")
    print("=" * 60)
    print()
    
    log("=== Deploy Bot started ===")
    
    # Step 1: Build
    if not build_site():
        log("=== Deploy Bot failed at build ===")
        sys.exit(1)
    
    # Step 2: Deploy
    if not deploy():
        log("=== Deploy Bot failed at deploy ===")
        sys.exit(1)
    
    # Step 3: Verify
    verify()
    
    log("=== Deploy Bot complete ===")
    print()
    print("  ✅ Deploy complete")
    print("=" * 60)


if __name__ == "__main__":
    main()
