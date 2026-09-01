#!/bin/bash
# Promoter 2 — Distribution specialist, platform-specific
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/security-core.sh"
API_KEY="${DEEPSEEK_API_KEY:-fallback}"
CT=$(sanitize_input "$1")
CN=$(sanitize_input "$2")
PLATFORM="${3:-all}"
case "$PLATFORM" in
  tiktok) PROMPT="Distribute: $CT — $CN on TikTok. Generate: 5 video ideas, best posting time, sounds, duet/stitch opportunities, engagement strategy, cross-promotion, analytics to watch." ;;
  pinterest) PROMPT="Distribute: $CT — $CN on Pinterest. Generate: 5 pin ideas, best boards, posting times, SEO keywords, group boards, cross-promotion, analytics." ;;
  substack) PROMPT="Distribute: $CT — $CN on Substack. Generate: 3 subject lines, full email, free/paid strategy, best send time, cross-promotion, recommendations, analytics." ;;
  all|*) PROMPT="Distribute: $CT — $CN across ALL platforms. Generate: TikTok (3 ideas, times, sounds), Pinterest (3 pins, boards, keywords), Substack (subject, email, strategy), X (3 tweets), Instagram (post, story, reel), YouTube/Rumble (title, description, tags), cross-promotion plan, schedule, analytics." ;;
esac
ESCAPED=$(echo "$PROMPT" | json_escape)
DATA=$(cat <<EOF
{ "model": "deepseek-chat", "messages": [{"role": "user", "content": $ESCAPED}], "max_tokens": 3000, "temperature": 0.7 }
EOF
)
result=$(safe_api_call "https://api.deepseek.com/v1/chat/completions" "$DATA" "$API_KEY") || exit 1
echo "$result" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['choices'][0]['message']['content'])"
log_security_event "PROMOTER_2_CALL" "Type: $CT, Platform: $PLATFORM"
