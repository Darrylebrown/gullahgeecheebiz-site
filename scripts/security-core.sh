#!/bin/bash
# Security Core — shared security functions for all bots
# Source this at the top of every bot: source "$(dirname "$0")/security-core.sh"

# ── Config ──────────────────────────────────────────────────────────
MAX_RETRIES=3
RETRY_DELAY=2
REQUEST_TIMEOUT=30
RATE_LIMIT_SECONDS=1

# ── Rate Limiting ───────────────────────────────────────────────────
__LAST_CALL=0
rate_limit() {
  local now
  now=$(date +%s)
  local elapsed=$((now - __LAST_CALL))
  if [ "$elapsed" -lt "$RATE_LIMIT_SECONDS" ]; then
    sleep $((RATE_LIMIT_SECONDS - elapsed))
  fi
  __LAST_CALL=$(date +%s)
}

# ── Safe API Call with Retry, Timeout, and Error Handling ───────────
safe_api_call() {
  local url="$1"
  local data="$2"
  local api_key="$3"
  local attempt=0
  local result=""

  while [ "$attempt" -lt "$MAX_RETRIES" ]; do
    rate_limit
    result=$(curl -s --max-time "$REQUEST_TIMEOUT" \
      -H "Content-Type: application/json" \
      -H "Authorization: Bearer $api_key" \
      -d "$data" \
      "$url" 2>/dev/null)
    
    # Validate response is valid JSON
    if echo "$result" | python3 -c "import sys,json; json.load(sys.stdin)" 2>/dev/null; then
      # Check for API-level errors
      local error_msg
      error_msg=$(echo "$result" | python3 -c "
import sys, json
d = json.load(sys.stdin)
if 'error' in d:
    print(d['error'].get('message', 'Unknown API error'))
elif 'choices' in d and len(d['choices']) > 0:
    print('OK')
else:
    print('Unexpected response format')
" 2>/dev/null)
      
      if [ "$error_msg" = "OK" ]; then
        echo "$result"
        return 0
      elif [ "$error_msg" != "OK" ]; then
        # Rate limited or server error — retry
        attempt=$((attempt + 1))
        if [ "$attempt" -lt "$MAX_RETRIES" ]; then
          sleep "$RETRY_DELAY"
        else
          echo "{\"error\": \"API_ERROR\", \"message\": \"$error_msg\"}" >&2
          return 1
        fi
      fi
    else
      # Not valid JSON — retry
      attempt=$((attempt + 1))
      if [ "$attempt" -lt "$MAX_RETRIES" ]; then
        sleep "$RETRY_DELAY"
      else
        echo "{\"error\": \"NETWORK_ERROR\", \"message\": \"Failed after $MAX_RETRIES attempts\"}" >&2
        return 1
      fi
    fi
  done
}

# ── Input Sanitization ──────────────────────────────────────────────
sanitize_input() {
  # Strip control characters, limit length, prevent injection
  echo "$1" | tr -d '\000-\010\016-\037' | head -c 10000
}

# ── Safe JSON Escape ────────────────────────────────────────────────
json_escape() {
  python3 -c "
import sys, json
text = sys.stdin.read()
print(json.dumps(text))
" 2>/dev/null
}

# ── Validate API Key Format ─────────────────────────────────────────
validate_api_key() {
  local key="$1"
  local prefix="${2:-sk-}"
  if [ -z "$key" ]; then
    echo "❌ ERROR: API key is empty" >&2
    return 1
  fi
  if [[ "$key" != "$prefix"* ]]; then
    echo "❌ ERROR: API key has invalid format (expected $prefix...)" >&2
    return 1
  fi
  if [ ${#key} -lt 20 ]; then
    echo "❌ ERROR: API key too short (${#key} chars, expected 20+)" >&2
    return 1
  fi
  return 0
}

# ── Secure Output — Never Leak Keys ─────────────────────────────────
secure_output() {
  # Redact any sk-... patterns in output
  echo "$1" | sed 's/sk-[a-zA-Z0-9]\{20,\}/sk-…[REDACTED]/g'
}

# ── Log Security Event ──────────────────────────────────────────────
log_security_event() {
  local event="$1"
  local details="$2"
  local logfile="$HOME/.hermes/logs/security-events.log"
  local activity_log="$HOME/.hermes/logs/bot-activity.log"
  local timestamp
  timestamp=$(date "+%Y-%m-%d %H:%M:%S")
  echo "[$timestamp] $event: $details" >> "$logfile"
  
  # Also write to activity log with emoji
  local emoji="🤖"
  case "$event" in
    WRITER_BOT*) emoji="✍️" ;;
    EDITOR_BOT*) emoji="📝" ;;
    UPLOADER_BOT*) emoji="🚀" ;;
    AFFILIATE_BOT*) emoji="💰" ;;
    PRICING_BOT*) emoji="📈" ;;
    SECURITY_WATCH*) emoji="🛡️" ;;
    PUBLISHER_BOT*) emoji="🧠" ;;
    TRANSLATOR_BOT*) emoji="🌍" ;;
  esac
  echo "$emoji [$timestamp] $event: $details" >> "$activity_log"
  
  # Keep logs under 1MB
  for f in "$logfile" "$activity_log"; do
    if [ -f "$f" ] && [ "$(stat -f%z "$f" 2>/dev/null)" -gt 1048576 ]; then
      tail -1000 "$f" > "${f}.tmp" && mv "${f}.tmp" "$f"
    fi
  done
}

# ── Verify Script Integrity ─────────────────────────────────────────
verify_script_integrity() {
  local script="$1"
  if [ ! -f "$script" ]; then
    log_security_event "INTEGRITY_FAIL" "Script missing: $script"
    return 1
  fi
  local perms
  perms=$(stat -f "%OLp" "$script" 2>/dev/null)
  if [ "$perms" != "755" ] && [ "$perms" != "700" ]; then
    log_security_event "PERMISSION_WARN" "Script $script has permissions $perms (expected 755)"
  fi
  return 0
}
