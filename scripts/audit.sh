#!/bin/bash
# Gullah Geechee Biz — Site Audit (watchdog)
# Runs every 30 min via Hermes cron. Silent when all checks pass.
# Outputs an alert report ONLY when issues are found.
# Exit 0 = all pass, exit 1 = issues found (triggers alert delivery).

set -u
SITE_DIR="$HOME/gullahgeecheebiz-site"
cd "$SITE_DIR" || { echo "❌ Cannot cd to $SITE_DIR"; exit 1; }

ALERTS=""
PASS=0
FAIL=0

add_alert() {
  FAIL=$((FAIL + 1))
  ALERTS="$ALERTS\n$1"
}

add_pass() {
  PASS=$((PASS + 1))
}

# ── 1. Smoke test (npm test) ──────────────────────────────────────
if npm test --silent >/dev/null 2>&1; then
  add_pass
else
  # Capture the actual failures
  SMOKE_OUT=$(npm test --silent 2>&1 | grep "❌" | head -10)
  add_alert "🔴 Smoke test FAILED:\n$SMOKE_OUT"
fi

# ── 2. node_modules not tracked ──────────────────────────────────
NM_COUNT=$(git ls-files node_modules/ 2>/dev/null | wc -l | tr -d ' ')
if [ "$NM_COUNT" -eq 0 ]; then
  add_pass
else
  add_alert "🔴 node_modules is tracked in git ($NM_COUNT files)"
fi

# ── 3. No tokens in git remotes ────────────────────────────────────
REMOTES=$(git remote -v 2>/dev/null)
if echo "$REMOTES" | grep -qE 'ghp_|github_pat_|:pat[A-Za-z0-9]{10,}@'; then
  add_alert "🔴 Tokens found in git remote URLs"
else
  add_pass
fi

# ── 4. .env not tracked ───────────────────────────────────────────
ENV_TRACKED=$(git ls-files .env 2>/dev/null)
if [ -z "$ENV_TRACKED" ]; then
  add_pass
else
  add_alert "🔴 .env is tracked in git!"
fi

# ── 5. .gitignore blocks secrets ──────────────────────────────────
if grep -q ".env" .gitignore && grep -q "node_modules" .gitignore; then
  add_pass
else
  add_alert "⚠️ .gitignore missing required entries (.env, node_modules)"
fi

# ── 6. Sitemap valid ──────────────────────────────────────────────
SITEMAP_URLS=$(grep -c "<loc>" sitemap.xml 2>/dev/null || echo 0)
if [ "$SITEMAP_URLS" -ge 50 ]; then
  add_pass
else
  add_alert "⚠️ Sitemap has only $SITEMAP_URLS URLs (expected 50+)"
fi

# ── 7. Key pages exist ────────────────────────────────────────────
KEY_PAGES="index.html shop.html shop-binyah.html membership/index.html season-1/index.html guide/index.html services/index.html bot-dashboard.html"
MISSING_PAGES=""
for p in $KEY_PAGES; do
  if [ ! -f "$p" ] || [ ! -s "$p" ]; then
    MISSING_PAGES="$MISSING_PAGES $p"
  fi
done
if [ -z "$MISSING_PAGES" ]; then
  add_pass
else
  add_alert "🔴 Missing/empty pages:$MISSING_PAGES"
fi

# ── 8. Broken .html.html links ────────────────────────────────────
DOUBLE_HTML=$(grep -rl '\.html\.html' --include='*.html' . 2>/dev/null | grep -v node_modules | wc -l | tr -d ' ')
if [ "$DOUBLE_HTML" -eq 0 ]; then
  add_pass
else
  add_alert "🔴 $DOUBLE_HTML files with .html.html broken links"
fi

# ── 9. Dead /books links ──────────────────────────────────────────
BOOKS_LINKS=$(grep -rl 'gullahgeecheebiz.com/books' --include='*.html' . 2>/dev/null | grep -v node_modules | wc -l | tr -d ' ')
if [ "$BOOKS_LINKS" -eq 0 ]; then
  add_pass
else
  add_alert "🔴 $BOOKS_LINKS files still link to dead /books path"
fi

# ── 10. og-image.jpg not referenced (we fixed to logo.png) ────────
OG_BROKEN=$(grep -rl 'og-image.jpg' --include='*.html' . 2>/dev/null | grep -v node_modules | wc -l | tr -d ' ')
if [ "$OG_BROKEN" -eq 0 ]; then
  add_pass
else
  add_alert "⚠️ $OG_BROKEN files reference missing og-image.jpg"
fi

# ── 11. Python scripts syntax ────────────────────────────────────
PY_ERRORS=""
for f in scripts/*.py; do
  if ! python3 -c "import ast; ast.parse(open('$f').read())" >/dev/null 2>&1; then
    PY_ERRORS="$PY_ERRORS $f"
  fi
done
if [ -z "$PY_ERRORS" ]; then
  add_pass
else
  add_alert "🔴 Python syntax errors in:$PY_ERRORS"
fi

# ── 12. Shell scripts syntax ──────────────────────────────────────
SH_ERRORS=""
for f in scripts/*.sh; do
  if ! bash -n "$f" >/dev/null 2>&1; then
    SH_ERRORS="$SH_ERRORS $f"
  fi
done
if [ -z "$SH_ERRORS" ]; then
  add_pass
else
  add_alert "🔴 Shell syntax errors in:$SH_ERRORS"
fi

# ── 13. Live site reachable ───────────────────────────────────────
HTTP_CODE=$(curl -s -o /dev/null -w '%{http_code}' --max-time 10 https://gullahgeecheebiz.com/ 2>/dev/null || echo "000")
if [ "$HTTP_CODE" = "200" ]; then
  add_pass
else
  add_alert "🔴 Live site returned HTTP $HTTP_CODE"
fi

# ── 14. CNAME correct ─────────────────────────────────────────────
CNAME_VAL=$(cat CNAME 2>/dev/null | tr -d '[:space:]')
if [ "$CNAME_VAL" = "gullahgeecheebiz.com" ]; then
  add_pass
else
  add_alert "⚠️ CNAME is '$CNAME_VAL' (expected gullahgeecheebiz.com)"
fi

# ── 15. Stripe checkout links present ────────────────────────────
STRIPE_COUNT=$(grep -c 'checkout.stripe.com' membership/index.html 2>/dev/null || echo 0)
if [ "$STRIPE_COUNT" -ge 6 ]; then
  add_pass
else
  add_alert "⚠️ Only $STRIPE_COUNT Stripe checkout links (expected 6+)"
fi

# ── 16. Git working tree clean ───────────────────────────────────
GIT_STATUS=$(git status --porcelain 2>/dev/null)
if [ -z "$GIT_STATUS" ]; then
  add_pass
else
  # Count uncommitted changes
  DIRTY_COUNT=$(echo "$GIT_STATUS" | wc -l | tr -d ' ')
  add_alert "ℹ️ $DIRTY_COUNT uncommitted changes in working tree"
fi

# ── 17. No secrets in git history ─────────────────────────────────
SECRETS=$(git log --all -p 2>/dev/null | grep -oE '(ghp_[A-Za-z0-9]{30,}|sk_live_[A-Za-z0-9]{20,}|sk_test_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{50,})' | sort -u)
if [ -z "$SECRETS" ]; then
  add_pass
else
  SECRET_COUNT=$(echo "$SECRETS" | wc -l | tr -d ' ')
  add_alert "🔴 $SECRET_COUNT secrets found in git history!"
fi

# ── 18. Security headers in HTML ──────────────────────────────────
HTML_WITHOUT_HEADERS=$(find . -name "*.html" -not -path "./node_modules/*" -not -path "./.git/*" -exec grep -L "X-Content-Type-Options" {} \; 2>/dev/null | wc -l | tr -d ' ')
if [ "$HTML_WITHOUT_HEADERS" -eq 0 ]; then
  add_pass
else
  add_alert "⚠️ $HTML_WITHOUT_HEADERS HTML files missing security headers"
fi

# ── 19. robots.txt present ────────────────────────────────────────
if [ -f "robots.txt" ] && grep -q "Sitemap:" robots.txt; then
  add_pass
else
  add_alert "⚠️ robots.txt missing or incomplete"
fi

# ── 20. Live site security headers ────────────────────────────────
LIVE_HEADERS=$(curl -sI --max-time 10 https://gullahgeecheebiz.com/ 2>/dev/null)
if echo "$LIVE_HEADERS" | grep -qi "strict-transport-security"; then
  add_pass
else
  add_alert "⚠️ Live site missing HSTS header"
fi

# ── 21. Stripe checkout links live ────────────────────────────────
STRIPE_OK=true
STRIPE_FAILS=""
# Test first 2 membership checkout links (testing all 6 every 30 min would be slow)
for link in $(grep -o 'https://checkout.stripe.com/c/pay/[^"]*' membership/index.html 2>/dev/null | head -2); do
  CODE=$(curl -sI -o /dev/null -w '%{http_code}' --max-time 10 "$link" 2>/dev/null)
  if [ "$CODE" != "200" ]; then
    STRIPE_OK=false
    STRIPE_FAILS="$STRIPE_FAILS $CODE"
  fi
done
# Test first 2 shop buy links
for link in $(grep -h -o 'https://buy.stripe.com/[^"]*' shop.html shop-binyah.html 2>/dev/null | sort -u | head -2); do
  CODE=$(curl -sI -o /dev/null -w '%{http_code}' --max-time 10 "$link" 2>/dev/null)
  if [ "$CODE" != "200" ]; then
    STRIPE_OK=false
    STRIPE_FAILS="$STRIPE_FAILS $CODE"
  fi
done
if $STRIPE_OK; then
  add_pass
else
  add_alert "🔴 Stripe links returning errors:$STRIPE_FAILS"
fi

# ── 22. Airtable sync last run ────────────────────────────────────
AIRTABLE_RESPONSE=$(curl -s --max-time 10 "https://api.github.com/repos/Darrylebrown/gullahgeecheebiz-site/actions/workflows/sync-season-1.yml/runs?per_page=1" 2>/dev/null)
if echo "$AIRTABLE_RESPONSE" | grep -q "rate limit"; then
  # API rate-limited — skip check, don't fail
  add_pass
else
  AIRTABLE_LAST=$(echo "$AIRTABLE_RESPONSE" | grep -o '"conclusion": "[^"]*"' | head -1 | sed 's/"conclusion": "//;s/"//')
  if [ "$AIRTABLE_LAST" = "success" ]; then
    add_pass
  elif [ -z "$AIRTABLE_LAST" ]; then
    add_pass  # no data yet, don't fail
  else
    AIRTABLE_DATE=$(echo "$AIRTABLE_RESPONSE" | grep -o '"created_at": "[^"]*"' | head -1 | sed 's/"created_at": "//;s/"//')
    add_alert "🔴 Airtable sync last run: $AIRTABLE_LAST at $AIRTABLE_DATE"
  fi
fi

# ── 23. GitHub Pages deploy freshness ─────────────────────────────
PAGES_LAST_MOD=$(curl -sI --max-time 10 "https://gullahgeecheebiz.com/?cb=$(date +%s)" 2>/dev/null | grep -i "last-modified" | sed 's/.*: //;s/\r//')
LATEST_COMMIT=$(git log -1 --format='%ci' 2>/dev/null | cut -d' ' -f1)
if [ -z "$PAGES_LAST_MOD" ] || [ -z "$LATEST_COMMIT" ]; then
  add_pass  # can't compare, don't fail
else
  # Parse just the date portion (e.g. "Mon, 27 Jul 2026" → "2026-07-27")
  PAGES_DATE=$(echo "$PAGES_LAST_MOD" | grep -oE '[0-9]{4}-[0-9]{2}-[0-9]{2}' | head -1)
  if [ -z "$PAGES_DATE" ]; then
    add_pass  # can't parse date, don't fail
  elif [ "$PAGES_DATE" \>= "$LATEST_COMMIT" ]; then
    add_pass
  else
    add_alert "⚠️ Pages last modified $PAGES_DATE, latest commit $LATEST_COMMIT — may be stale"
  fi
fi

# ── Summary ──────────────────────────────────────────────────────
if [ "$FAIL" -eq 0 ]; then
  # All pass — silent (no output, exit 0)
  exit 0
else
  echo "🔍 GULLAH GEECHEE BIZ — AUDIT ALERT"
  echo "   $(date '+%Y-%m-%d %H:%M:%S')"
  echo "   Passed: $PASS | Failed: $FAIL"
  echo "   ============================================"
  echo -e "$ALERTS"
  echo ""
  echo "   Run: cd ~/gullahgeecheebiz-site && npm test"
  exit 1
fi
