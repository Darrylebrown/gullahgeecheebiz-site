#!/usr/bin/env bash
# Encrypted, timestamped backup of GGB engine.
set -euo pipefail
SRC="/Users/darrylsmac/gullahgeecheebiz-site/ggb-engine"
DST="${HOME}/ggb-backups"
mkdir -p "$DST"
STAMP=$(date +%Y%m%d-%H%M%S)
TAR="$DST/ggb-$STAMP.tar.gz"
ENC="$TAR.enc"
KEY_FILE="${HOME}/.ggb_backup_key"
[ -f "$KEY_FILE" ] || { openssl rand -hex 32 > "$KEY_FILE"; chmod 600 "$KEY_FILE"; }
tar --exclude='.git' --exclude='node_modules' --exclude='__pycache__'     -czf "$TAR" -C "$(dirname "$SRC")" "$(basename "$SRC")"
openssl enc -aes-256-cbc -salt -pbkdf2 -in "$TAR" -out "$ENC" -k "$(cat "$KEY_FILE")"
rm -f "$TAR"
# Retain last 14 backups
ls -t "$DST"/*.enc | tail -n +15 | xargs -r rm -f
echo "[+] Backup: $ENC"
