#!/bin/bash
# Viral Seller 1 — Finds trending items, writes sales pitches
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/security-core.sh"
API_KEY="${DEEPSEEK_API_KEY:-fallback}"
COMMAND="${1:-find}"
case "$COMMAND" in
  find) PROMPT="Find 3 trending products on Amazon, 3 on Etsy, 3 on TikTok Shop for a Gullah Geechee audience. For each: title, price, why trending, commission estimate, best platform." ;;
  list) PROMPT="Generate a daily sales catalog of 10 items. For each: name, price, platform, why it sells today, hook, commission. Mix: books, cultural items, Lowcountry, heritage, decor." ;;
  promote) PROMPT="Create a promotion strategy for: $2. Include: best platform, caption, visual suggestion, CTA, timing, audience, hashtags." ;;
  sell) PROMPT="Write a direct sales pitch for: $2. Include: headline, problem/solution, social proof, urgency, CTA, price anchoring, risk reversal." ;;
esac
FULL="$PROMPT"
[ -n "$2" ] && FULL="$PROMPT\n\nProduct: $2"
ESCAPED=$(echo "$FULL" | json_escape)
DATA=$(cat <<EOF
{ "model": "deepseek-chat", "messages": [{"role": "user", "content": $ESCAPED}], "max_tokens": 2000, "temperature": 0.7 }
EOF
)
result=$(safe_api_call "https://api.deepseek.com/v1/chat/completions" "$DATA" "$API_KEY") || exit 1
echo "$result" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['choices'][0]['message']['content'])"
log_security_event "VIRAL_SELLER_1_CALL" "Command: $COMMAND"
