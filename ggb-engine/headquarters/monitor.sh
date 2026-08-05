#!/usr/bin/env bash
# Lightweight GGB monitor. Add to crontab: */5 * * * *
set -uo pipefail
LOG="/Users/darrylsmac/gullahgeecheebiz-site/ggb-engine/logs/monitor.log"
mkdir -p "$(dirname "$LOG")"
ALERT() { echo "[$(date)] ALERT: $*" >> "$LOG"; osascript -e "display notification \"$*\" with title \"GGB Security\""; }
for p in 8086 8087 8090 8091; do
  lsof -nP -iTCP:$p -sTCP:LISTEN >/dev/null 2>&1 || ALERT "Port $p not listening"
done
# Detect new 0.0.0.0 listeners
lsof -nP -iTCP -sTCP:LISTEN 2>/dev/null | awk '$9 ~ /\*:|0\.0\.0\.0:|\[::\]:/{print}' \
  >> "$LOG"
