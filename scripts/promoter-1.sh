#!/bin/bash
# Promoter 1 — Full promotion package for any content
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/security-core.sh"
API_KEY="sk-3b0dd42ffb454d0287697021e9fc2202"
CT=$(sanitize_input "$1")
CN=$(sanitize_input "$2")
PROMPT="Promote: $CT — $CN. Generate: 1. TIKTOK (3 versions: 15s, 30s, 60s with captions, hashtags, visuals, sounds) 2. PINTEREST (2 pins: title, description, board, link, visual) 3. SUBSTACK (subject line, opening, CTA) 4. X (2 tweets, 280 chars) 5. INSTAGRAM (caption, hashtags, visual) 6. EMAIL (subject, body, CTA). Brand: Gullah Geechee Biz — warm, culturally rooted, FROM the community."
ESCAPED=$(echo "$PROMPT" | json_escape)
DATA=$(cat <<EOF
{ "model": "deepseek-chat", "messages": [{"role": "user", "content": $ESCAPED}], "max_tokens": 3000, "temperature": 0.7 }
EOF
)
result=$(safe_api_call "https://api.deepseek.com/v1/chat/completions" "$DATA" "$API_KEY") || exit 1
echo "$result" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['choices'][0]['message']['content'])"
log_security_event "PROMOTER_1_CALL" "Type: $CT, Name: $CN"
