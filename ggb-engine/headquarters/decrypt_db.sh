#!/usr/bin/env bash
set -euo pipefail
IN="$1"; OUT="$2"
KEY=$(cat "${HOME}/.ggb_db_key")
openssl enc -d -aes-256-cbc -pbkdf2 -in "$IN" -out "$OUT" -k "$KEY"
