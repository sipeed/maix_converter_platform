#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT_DIR"

# Activate Python virtual environment if available
if [ -f ".venv/bin/activate" ]; then
  # shellcheck source=/dev/null
  source ".venv/bin/activate"
elif [ -f "venv/bin/activate" ]; then
  # shellcheck source=/dev/null
  source "venv/bin/activate"
fi

HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-8000}"

printf "Starting Maix Converter Platform...\n"
printf "Root directory: %s\n" "$ROOT_DIR"
printf "Host: %s  Port: %s\n" "$HOST" "$PORT"

printf "Using prebuilt static frontend in web/static (no npm required)\n"

printf "Launching backend server...\n"
exec uvicorn web.app:app --host "$HOST" --port "$PORT"
