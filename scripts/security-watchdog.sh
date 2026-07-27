#!/bin/bash
# Security Watchdog — Real-time 24/7 monitoring
# Runs every 15 minutes via cron
# Alerts via Make.com webhook when issues found

MAKE_WEBHOOK="https://hook.us2.make.com/ehcke4kqax3ac4ln4ueumw1bjakz5198"
ENV_FILES=(
  "$HOME/publish-automation/.env"
  "$HOME/.hermes/.env"
  "$HOME/.hermes/config.yaml"
)
GIT_REPOS=(
  "$HOME/gullahgeecheebiz-site"
  "$HOME/publish-automation"
  "$HOME/ebooks"
)
ALERTS=""

# 1. Check .env files exist and have expected keys
for f in "${ENV_FILES[@]}"; do
  if [ ! -f "$f" ]; then
    ALERTS="$ALERTS\n⚠️ MISSING: $f"
  elif [ ! -r "$f" ]; then
    ALERTS="$ALERTS\n🔴 UNREADABLE: $f — permissions changed!"
  else
    # Check file permissions — should be 600 (owner only)
    PERMS=$(stat -f "%OLp" "$f" 2>/dev/null)
    if [ "$PERMS" != "600" ] && [ "$PERMS" != "400" ]; then
      ALERTS="$ALERTS\n⚠️ PERMISSIONS: $f is $PERMS (should be 600)"
    fi
  fi
done

# 2. Check .env files are NOT in any git repo
for repo in "${GIT_REPOS[@]}"; do
  if [ -d "$repo/.git" ]; then
    # Check if .env is tracked
    TRACKED=$(cd "$repo" && git ls-files .env 2>/dev/null)
    if [ -n "$TRACKED" ]; then
      ALERTS="$ALERTS\n🔴 LEAKED: .env tracked in $repo!"
    fi
    # Check .gitignore has .env
    if [ -f "$repo/.gitignore" ]; then
      if ! grep -q ".env" "$repo/.gitignore" 2>/dev/null; then
        ALERTS="$ALERTS\n⚠️ MISSING: $repo/.gitignore doesn't block .env"
      fi
    else
      ALERTS="$ALERTS\n⚠️ MISSING: $repo has no .gitignore"
    fi
  fi
done

# 3. Check for any .env files accidentally left in public dirs
PUBLIC_ENVS=$(find "$HOME/gullahgeecheebiz-site" -name ".env" -not -path "*/node_modules/*" 2>/dev/null)
if [ -n "$PUBLIC_ENVS" ]; then
  ALERTS="$ALERTS\n🔴 EXPOSED: .env files found in public directory!"
  echo "$PUBLIC_ENVS" | while read f; do
    ALERTS="$ALERTS\n  - $f"
  done
fi

# 4. Check disk space and RAM
DISK=$(df -h / | tail -1 | awk '{print $5}' | sed 's/%//')
if [ "$DISK" -gt 90 ]; then
  ALERTS="$ALERTS\n🔴 DISK: ${DISK}% full"
elif [ "$DISK" -gt 80 ]; then
  ALERTS="$ALERTS\n⚠️ DISK: ${DISK}% full"
fi

# 5. Check if gateway is running
if ! ps aux | grep -v grep | grep -q "gateway run"; then
  ALERTS="$ALERTS\n⚠️ GATEWAY: Hermes gateway is not running"
fi

# 6. Report
TIMESTAMP=$(date "+%Y-%m-%d %H:%M:%S")
if [ -n "$ALERTS" ]; then
  MESSAGE="🛡️ **Security Alert — $TIMESTAMP**$ALERTS"
  echo "$MESSAGE"
  # Send to Make.com webhook
  curl -s -X POST "$MAKE_WEBHOOK" \
    -H "Content-Type: application/json" \
    -d "{\"type\":\"security_alert\",\"timestamp\":\"$TIMESTAMP\",\"message\":\"$MESSAGE\"}" \
    -o /dev/null 2>&1
else
  echo "✅ Security Watchdog — $TIMESTAMP — All clear"
fi
