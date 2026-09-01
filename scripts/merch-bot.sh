#!/bin/bash
# Merch Bot — Printful product descriptions
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/security-core.sh"
API_KEY="${DEEPSEEK_API_KEY:-fallback}"
PRODUCT=$(sanitize_input "$1")
DESIGN=$(sanitize_input "$2")
PROMPT="Create a Printful listing for: $PRODUCT — $DESIGN. Generate: title, 2-3 paragraph description, 5 bullet points, 10-15 tags, size/color recs, retail price, social hook. Brand: Gullah Geechee Biz — luxury frame, culture picture. Navy + gold. Warm, proud, FROM the community."
ESCAPED=$(echo "$PROMPT" | json_escape)
DATA=$(cat <<EOF
{ "model": "deepseek-chat", "messages": [{"role": "user", "content": $ESCAPED}], "max_tokens": 2000, "temperature": 0.7 }
EOF
)
result=$(safe_api_call "https://api.deepseek.com/v1/chat/completions" "$DATA" "$API_KEY") || exit 1
echo "$result" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['choices'][0]['message']['content'])"
log_security_event "MERCH_BOT_CALL" "Product: $PRODUCT, Design: $DESIGN"
