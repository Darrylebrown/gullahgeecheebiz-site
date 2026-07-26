#!/bin/bash
# Uploader Bot — DeepSeek-powered upload decision engine
# Usage: ./uploader-bot.sh <content-description> [platform]

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/security-core.sh"

API_KEY="sk-885b367411e8418bb553fb3d24d7fe48"
PLATFORM="${2:-auto}"
validate_api_key "$API_KEY" || exit 1
CONTENT=$(sanitize_input "$1")

case "$PLATFORM" in
  d2d|D2D)     PROMPT="Analyze this content for D2D upload. Check: 1. Complete book? 2. Meets D2D policies? 3. Metadata needed? 4. Format? 5. Potential flags?" ;;
  pinterest|Pinterest) PROMPT="Analyze this content for Pinterest upload. Check: 1. Pin-ready? 2. Board? 3. Description/hashtags? 4. Link?" ;;
  substack|Substack) PROMPT="Analyze this content for Substack. Check: 1. Ready for newsletter? 2. Subject line? 3. Free or paid? 4. Images/formatting?" ;;
  auto|*)      PROMPT="Analyze this content and decide the best platform(s). Consider: 1. Content type? 2. Best platform? 3. Format needed? 4. Metadata/tags? 5. Potential issues?" ;;
esac

FULL="$PROMPT\n\nContent: $CONTENT"
ESCAPED=$(echo "$FULL" | json_escape)

DATA=$(cat <<EOF
{
  "model": "deepseek-chat",
  "messages": [{"role": "user", "content": $ESCAPED}],
  "max_tokens": 1500,
  "temperature": 0.3
}
EOF
)

result=$(safe_api_call "https://api.deepseek.com/v1/chat/completions" "$DATA" "$API_KEY") || {
  echo "Error: API call failed" >&2
  exit 1
}

echo "$result" | python3 -c "
import sys, json
d = json.load(sys.stdin)
if 'choices' in d:
    print(d['choices'][0]['message']['content'])
elif 'error' in d:
    print(f'Error: {d[\"error\"][\"message\"]}')
else:
    print(json.dumps(d, indent=2)[:500])
"
log_security_event "UPLOADER_BOT_CALL" "Platform: $PLATFORM"
