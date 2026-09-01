#!/bin/bash
# Pricing Bot — Analyzes sales data, recommends pricing, tracks revenue
# Usage: ./pricing-bot.sh <command> [data]
# Commands: analyze, recommend, promote, alert, report

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/security-core.sh"

API_KEY="${DEEPSEEK_API_KEY:-fallback}"
COMMAND="${1:-report}"
validate_api_key "$API_KEY" || exit 1
ARGS=$(sanitize_input "${2:-}")

case "$COMMAND" in
  analyze)   PROMPT="Analyze this sales data. Identify: 1. Best/worst sellers 2. Converting price points 3. Seasonal trends 4. Best revenue platforms" ;;
  recommend) PROMPT="Based on this data, recommend: 1. Optimal price points 2. Bundle opportunities 3. Discount timing 4. Price changes with rationale 5. Free vs paid strategy" ;;
  promote)   PROMPT="Create a pricing + promotion strategy for this product. 1. Optimal price 2. Best discount/bundle 3. Promotion platforms 4. Value hook 5. CTA 6. Timing" ;;
  alert)     PROMPT="Review this data for alerts. 1. Products not sold in 30+ days 2. Underperforming price points 3. Competitor pricing 4. Churn risks 5. Revenue drops/spikes" ;;
  report|*)  PROMPT="Generate a weekly revenue report. 1. Total revenue 2. By platform 3. Best/worst products 4. Pricing recommendations 5. Next week forecast" ;;
esac

FULL="$PROMPT\n\nData: $ARGS"
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
log_security_event "PRICING_BOT_CALL" "Command: $COMMAND"
