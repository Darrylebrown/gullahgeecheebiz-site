#!/bin/bash
# Auto-remediate hardcoded API keys in bot scripts
# GGB Security Orchestrator — automated fix

SCRIPT_DIR="/Users/darrylsmac/gullahgeecheebiz-site/scripts"
LOG_FILE="$SCRIPT_DIR/security-fixes.log"
COUNT=0

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Starting security remediation..." >> "$LOG_FILE"

for script in "$SCRIPT_DIR"/*.sh; do
  if [ -f "$script" ]; then
    # Check for hardcoded API keys (not redacted)
    if grep -qE 'API_KEY="sk-[a-zA-Z0-9]{3,}[^"]*"' "$script" 2>/dev/null; then
      if ! grep -q 'redacted' "$script" 2>/dev/null; then
        # Replace hardcoded key with environment variable fallback
        sed -i '' 's/API_KEY="sk-[a-zA-Z0-9_./-]*/API_KEY="${DEEPSEEK_API_KEY:-$'"'"'DEEPSEEK_API_KEY'"'"'}"/g' "$script"
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] FIXED: $script - replaced hardcoded key with env var" >> "$LOG_FILE"
        COUNT=$((COUNT + 1))
      fi
    fi
  fi
done

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Remediation complete: $COUNT scripts fixed" >> "$LOG_FILE"
echo "Fixed $COUNT scripts with hardcoded API keys"
