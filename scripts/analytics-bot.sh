#!/bin/bash
# Analytics Bot — Daily revenue + subscriber report
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/security-core.sh"
API_KEY="${DEEPSEEK_API_KEY:-fallback}"
COMMAND="${1:-daily}"
case "$COMMAND" in
  daily) PROMPT="Generate a daily business snapshot: 1. Estimated revenue 2. Subscriber growth 3. Content performance 4. Top content 5. Recommendations 6. Red flags" ;;
  weekly) PROMPT="Generate a weekly business report: 1. Revenue vs last week 2. Growth trends 3. Best content/products 4. Platform comparison 5. Next week recommendations 6. Goals progress" ;;
  goals) PROMPT="Track progress toward: 1. \$10k/week retirement 2. 10K TikTok 3. 1K Substack 4. 50 books 5. Season 1 launch. For each: status, progress %, estimated completion, actions" ;;
esac
ESCAPED=$(echo "$PROMPT" | json_escape)
DATA=$(cat <<EOF
{ "model": "deepseek-chat", "messages": [{"role": "user", "content": $ESCAPED}], "max_tokens": 2000, "temperature": 0.3 }
EOF
)
result=$(safe_api_call "https://api.deepseek.com/v1/chat/completions" "$DATA" "$API_KEY") || exit 1
echo "$result" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['choices'][0]['message']['content'])"
log_security_event "ANALYTICS_BOT_CALL" "Command: $COMMAND"
