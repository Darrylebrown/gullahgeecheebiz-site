#!/bin/bash
# SEO Bot — Optimizes pages, suggests keywords
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/security-core.sh"
API_KEY="${DEEPSEEK_API_KEY:-fallback}"
CONTENT=$(sanitize_input "$1")
COMMAND="${2:-audit}"
case "$COMMAND" in
  audit) PROMPT="SEO audit this content. Check: title, meta description, headings, keywords, internal links, readability. Give specific recommendations." ;;
  keywords) PROMPT="Based on this content, suggest: primary keyword, 5-10 secondary keywords, long-tail phrases, related terms. Focus on Gullah Geechee, Lowcountry, cultural heritage." ;;
  optimize) PROMPT="Rewrite this content for better SEO while keeping cultural voice intact. Improve title, meta, headings, keywords. Don't change authenticity." ;;
esac
FULL="$PROMPT\n\nContent: $CONTENT"
ESCAPED=$(echo "$FULL" | json_escape)
DATA=$(cat <<EOF
{ "model": "deepseek-chat", "messages": [{"role": "user", "content": $ESCAPED}], "max_tokens": 2000, "temperature": 0.3 }
EOF
)
result=$(safe_api_call "https://api.deepseek.com/v1/chat/completions" "$DATA" "$API_KEY") || exit 1
echo "$result" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['choices'][0]['message']['content'])"
log_security_event "SEO_BOT_CALL" "Command: $COMMAND"
