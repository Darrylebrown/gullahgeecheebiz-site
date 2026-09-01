#!/bin/bash
# Writer Bot — DeepSeek API via curl
# Usage: ./writer-bot.sh <prompt> [model] [max_tokens]

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/security-core.sh"

API_KEY="${DEEPSEEK_API_KEY:-fallback}"
MODEL="${2:-deepseek-chat}"
MAX_TOKENS="${3:-2000}"

validate_api_key "$API_KEY" || exit 1
PROMPT=$(sanitize_input "$1")
ESCAPED=$(echo "$PROMPT" | json_escape)

DATA=$(cat <<EOF
{
  "model": "$MODEL",
  "messages": [{"role": "user", "content": $ESCAPED}],
  "max_tokens": $MAX_TOKENS,
  "temperature": 0.7
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
log_security_event "WRITER_BOT_CALL" "Model: $MODEL, Tokens: $MAX_TOKENS"
