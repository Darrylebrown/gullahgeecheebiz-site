#!/bin/bash
# Newsletter Bot — Writes Substack posts
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/security-core.sh"
API_KEY="sk-3b0dd42ffb454d0287697021e9fc2202"
TOPIC=$(sanitize_input "$1")
TONE="${2:-warm}"
PROMPT="Write a Substack newsletter about: $TOPIC. Tone: $TONE, culturally rooted. Include: subject line, hook, 3-4 paragraphs, CTA. 500-800 words. Brand: Gullah Geechee Biz."
ESCAPED=$(echo "$PROMPT" | json_escape)
DATA=$(cat <<EOF
{ "model": "deepseek-chat", "messages": [{"role": "user", "content": $ESCAPED}], "max_tokens": 2000, "temperature": 0.7 }
EOF
)
result=$(safe_api_call "https://api.deepseek.com/v1/chat/completions" "$DATA" "$API_KEY") || exit 1
echo "$result" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['choices'][0]['message']['content'])"
log_security_event "NEWSLETTER_BOT_CALL" "Topic: $TOPIC"
