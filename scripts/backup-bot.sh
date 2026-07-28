#!/bin/bash
# Backup Bot — Daily backup of critical files
# Runs daily at 2am via cron
# Backs up: scripts, configs, generated content

BACKUP_DIR="$HOME/.hermes/backups"
TIMESTAMP=$(date "+%Y-%m-%d_%H%M%S")
BACKUP_PATH="$BACKUP_DIR/backup-$TIMESTAMP"
LOG="$BACKUP_DIR/backup.log"
mkdir -p "$BACKUP_PATH"

echo "=== Backup started: $TIMESTAMP ===" | tee -a "$LOG"

# 1. Backup scripts
if [ -d "$HOME/gullahgeecheebiz-site/scripts" ]; then
    cp -r "$HOME/gullahgeecheebiz-site/scripts" "$BACKUP_PATH/"
    echo "  ✅ Scripts backed up" | tee -a "$LOG"
fi

# 2. Backup membership pages
if [ -d "$HOME/gullahgeecheebiz-site/membership" ]; then
    cp -r "$HOME/gullahgeecheebiz-site/membership" "$BACKUP_PATH/"
    echo "  ✅ Membership pages backed up" | tee -a "$LOG"
fi

# 3. Backup cron jobs config
if [ -f "$HOME/.hermes/cron/jobs.json" ]; then
    cp "$HOME/.hermes/cron/jobs.json" "$BACKUP_PATH/"
    echo "  ✅ Cron jobs config backed up" | tee -a "$LOG"
fi

# 4. Backup Hermes config
if [ -f "$HOME/.hermes/config.yaml" ]; then
    cp "$HOME/.hermes/config.yaml" "$BACKUP_PATH/"
    echo "  ✅ Hermes config backed up" | tee -a "$LOG"
fi

# 5. Backup accounting data
if [ -d "$HOME/.hermes/accounting" ]; then
    cp -r "$HOME/.hermes/accounting" "$BACKUP_PATH/"
    echo "  ✅ Accounting data backed up" | tee -a "$LOG"
fi

# 6. Backup deploy logs
if [ -d "$HOME/.hermes/logs" ]; then
    cp -r "$HOME/.hermes/logs" "$BACKUP_PATH/"
    echo "  ✅ Logs backed up" | tee -a "$LOG"
fi

# 7. Clean up old backups (keep last 14)
TOTAL_SIZE=$(du -sh "$BACKUP_PATH" | cut -f1)
echo "  📦 Backup size: $TOTAL_SIZE" | tee -a "$LOG"

# Remove backups older than 14 days
find "$BACKUP_DIR" -maxdepth 1 -type d -name "backup-*" -mtime +14 -exec rm -rf {} \; 2>/dev/null
echo "  🧹 Old backups cleaned (kept last 14 days)" | tee -a "$LOG"

echo "=== Backup complete: $TIMESTAMP ===" | tee -a "$LOG"
echo "Total backup size: $TOTAL_SIZE"
