#!/bin/bash
# Video Script Bot — TikTok + documentary scripts
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/security-core.sh"
API_KEY="${DEEPSEEK_API_KEY:-fallback}"
TOPIC=$(sanitize_input "$1")
PLATFORM="${2:-tiktok}"
DURATION="${3:-60}"
case "$PLATFORM" in
  tiktok) PROMPT="Write a ${DURATION}s TikTok script about: $TOPIC. Format: hook (3s) → body → CTA. Include: on-screen text, visual cues, sound ideas. 150-200 words. Warm, culturally rooted." ;;
  documentary) PROMPT="Write a ${DURATION}s documentary segment about: $TOPIC. Format: narration → scene → voice → reflection. Include: scene descriptions, narration, imagery, music mood. 200-300 words." ;;
  youtube) PROMPT="Write a ${DURATION}s YouTube script about: $TOPIC. Format: hook → intro → 3 key points → CTA. Include: visual cues, chapter markers, b-roll suggestions." ;;
esac
ESCAPED=$(echo "$PROMPT" | json_escape)
DATA=$(cat <<EOF
{ "model": "deepseek-chat", "messages": [{"role": "user", "content": $ESCAPED}], "max_tokens": 2000, "temperature": 0.7 }
EOF
)
result=$(safe_api_call "https://api.deepseek.com/v1/chat/completions" "$DATA" "$API_KEY") || exit 1
echo "$result" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['choices'][0]['message']['content'])"
log_security_event "VIDEO_SCRIPT_BOT_CALL" "Platform: $PLATFORM, Topic: $TOPIC"
