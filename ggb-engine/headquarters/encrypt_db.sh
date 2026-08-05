#!/usr/bin/env bash
# Encrypt SQLite backup with AES-256-CBC. Requires openssl.
set -euo pipefail
if [ "$#" -ne 2 ]; then
  echo "Usage: $0 <input.db> <output.db.enc>"
  exit 1
fi
IN="$1"; OUT="$2"
KEY_FILE="${HOME}/.ggb_db_key"
if [ ! -f "$KEY_FILE" ]; then
  openssl rand -hex 32 > "$KEY_FILE"
  chmod 600 "$KEY_FILE"
  echo "[!] New encryption key created at $KEY_FILE — back it up offline!"
fi
KEY=$(cat "$KEY_FILE")
openssl enc -aes-256-cbc -salt -pbkdf2 -in "$IN" -out "$OUT" -k "$KEY"
echo "[+] Encrypted: $OUT"
