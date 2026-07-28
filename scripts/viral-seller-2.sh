#!/bin/bash
# Viral Seller 2 — Trend hunter, Amazon listings, bundles, pitches
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/security-core.sh"
API_KEY="sk-3b0dd42ffb454d0287697021e9fc2202"
COMMAND="${1:-trend}"
case "$COMMAND" in
  trend) PROMPT="Scan for trending products RIGHT NOW. Report: 5 trending on Amazon (books, history, culture, travel, decor), 5 on TikTok Shop, 3 seasonal items. For each: price, commission, why trending now." ;;
  amazon) PROMPT="Create Amazon affiliate listings for: $2. For each: SEO title, 5 bullet points, 2-paragraph description, categories, keywords, suggested price." ;;
  bundle) PROMPT="Create 3 product bundles from: books, audiobooks, merch, guides, documentary. For each: name, what's included, bundle vs individual price, why it appeals, best platform, hook." ;;
  pitch) PROMPT="Write a high-converting sales pitch for: $2. Format: hook, problem, solution, social proof, objection handling, urgency, CTA, post-purchase." ;;
esac
FULL="$PROMPT"
[ -n "$2" ] && FULL="$PROMPT\n\nProducts: $2"
ESCAPED=$(echo "$FULL" | json_escape)
DATA=$(cat <<EOF
{ "model": "deepseek-chat", "messages": [{"role": "user", "content": $ESCAPED}], "max_tokens": 2000, "temperature": 0.7 }
EOF
)
result=$(safe_api_call "https://api.deepseek.com/v1/chat/completions" "$DATA" "$API_KEY") || exit 1
echo "$result" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['choices'][0]['message']['content'])"
log_security_event "VIRAL_SELLER_2_CALL" "Command: $COMMAND"
