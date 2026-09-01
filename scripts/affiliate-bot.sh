#!/bin/bash
# Affiliate Bot — Manages Amazon Associates links, tracks commissions, optimizes placements
# Usage: ./affiliate-bot.sh <command> [args]
# Commands: track, optimize, suggest, promote, report

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/security-core.sh"

API_KEY="${DEEPSEEK_API_KEY:-fallback}"
COMMAND="${1:-report}"
validate_api_key "$API_KEY" || exit 1
ARGS=$(sanitize_input "${2:-}")

case "$COMMAND" in
  track)    PROMPT="Analyze this affiliate link performance data. Identify: 1. Links with clicks but no conversions 2. Best conversion rate products 3. Better placement suggestions 4. Broken/expired links" ;;
  optimize) PROMPT="Review this content and suggest best affiliate product placements. 1. Which products to link 2. Where to place links 3. Anchor text 4. Natural feel" ;;
  suggest)  PROMPT="Based on current Gullah Geechee content and audience, suggest: 1. New affiliate products 2. Best Amazon categories 3. Seasonal/trending products 4. Cross-promotion opportunities" ;;
  promote)  PROMPT="Create a promotion strategy for this product. 1. Best platforms 2. Caption/hook 3. Visual suggestions 4. CTA 5. Timing" ;;
  report|*) PROMPT="Generate a weekly affiliate performance report. 1. Top links/products 2. CTR and conversion rates 3. Revenue 4. Recommendations 5. New products to add" ;;
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
log_security_event "AFFILIATE_BOT_CALL" "Command: $COMMAND"
