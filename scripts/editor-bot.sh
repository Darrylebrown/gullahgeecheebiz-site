#!/bin/bash
# Editor Bot — DeepSeek R1 for quality review, compliance, editing
# Usage: ./editor-bot.sh <text> [mode]
# Modes: review, compliance, spellcheck, brand, all

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/security-core.sh"

API_KEY="sk-56a467c91ce8408fa6d60caa4e9c3f72"
MODE="${2:-all}"
validate_api_key "$API_KEY" || exit 1

TEXT=$(sanitize_input "${1:-$(cat)}")

case "$MODE" in
  review)     PROMPT="Review the following text for quality, accuracy, and completeness. Check for factual errors, unclear statements, and missing context. Provide specific feedback." ;;
  compliance) PROMPT="Review the following text for platform compliance. Check for: 1. Content that could be flagged by D2D, KDP, or ACX 2. Copyright issues 3. Sensitive topics that need disclaimers 4. Any policy violations" ;;
  spellcheck) PROMPT="Check the following text for spelling and grammar errors. List every error found, the correction, and the line number. Be 100% accurate." ;;
  brand)      PROMPT="Review the following text for Gullah Geechee Biz brand consistency: 1. Is the tone warm, culturally rooted, and respectful? 2. Does it feel FROM the community, not observed? 3. Are there any phrases that sound corporate or templated? 4. Does it match the brand voice: luxury frame, culture picture?" ;;
  all|*)      PROMPT="You are the Gullah Geechee Biz Editor Bot. Review the following text for ALL of the following: 1. SPELLING & GRAMMAR: List every error with correction 2. BRAND VOICE: Does it feel warm, culturally rooted, and FROM the community? 3. COMPLIANCE: Any content that could be flagged by D2D/KDP/ACX? 4. QUALITY: Is it clear, accurate, and complete? 5. CULTURAL ACCURACY: Is the Gullah Geechee perspective authentic? For each category, give a PASS/FAIL and specific feedback." ;;
esac

FULL="$PROMPT\n\nTEXT:\n$TEXT"
ESCAPED=$(echo "$FULL" | json_escape)

DATA=$(cat <<EOF
{
  "model": "deepseek-reasoner",
  "messages": [{"role": "user", "content": $ESCAPED}],
  "max_tokens": 2000,
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
log_security_event "EDITOR_BOT_CALL" "Mode: $MODE"
