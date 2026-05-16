#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SOPS_BIN="${SOPS_BIN:-sops}"

if ! command -v "$SOPS_BIN" >/dev/null 2>&1; then
  if [ -x "/tmp/finlens-tools/sops" ]; then
    SOPS_BIN="/tmp/finlens-tools/sops"
  else
    echo "sops is required. Install it, then rerun this script." >&2
    exit 1
  fi
fi

if [ ! -f "$ROOT_DIR/.env.enc" ]; then
  echo ".env.enc not found." >&2
  exit 1
fi

"$SOPS_BIN" --decrypt "$ROOT_DIR/.env.enc" > "$ROOT_DIR/.env"
chmod 600 "$ROOT_DIR/.env"
echo ".env created from .env.enc"
