#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT_DIR"

if [ -x ".venv/bin/python" ]; then
  PYTHON="$ROOT_DIR/.venv/bin/python"
elif [ -x "venv/bin/python" ]; then
  PYTHON="$ROOT_DIR/venv/bin/python"
elif command -v python3 >/dev/null 2>&1; then
  PYTHON="$(command -v python3)"
elif command -v python >/dev/null 2>&1; then
  PYTHON="$(command -v python)"
else
  printf "ERROR: Python was not found. Install Python 3.11 or activate a conda environment.\n" >&2
  exit 1
fi

HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-8000}"
MAIX_API_TOKEN="${MAIX_API_TOKEN:-}"
export PYTHONIOENCODING="utf-8"
export PYTHONUTF8="1"

case "$HOST" in
  127.0.0.1|localhost|::1)
    ;;
  *)
    if [ -z "$MAIX_API_TOKEN" ]; then
      MAIX_API_TOKEN="$("$PYTHON" -c 'import secrets; print(secrets.token_urlsafe(24))')"
      printf "Generated API token for remote access: %s\n" "$MAIX_API_TOKEN"
      printf "Open the page with: http://<server-ip>:%s/?token=%s\n" "$PORT" "$MAIX_API_TOKEN"
    fi
    export MAIX_API_TOKEN
    ;;
esac

printf "Starting Maix Converter Platform...\n"
printf "Root directory: %s\n" "$ROOT_DIR"
printf "Host: %s  Port: %s\n" "$HOST" "$PORT"
printf "Python: %s\n" "$PYTHON"

printf "Using plain static frontend in web/static (HTML/CSS/JS, no npm required)\n"

printf "Launching backend server...\n"
exec "$PYTHON" -m uvicorn web.app:app --host "$HOST" --port "$PORT"
