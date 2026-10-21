#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$PROJECT_DIR/backend"
FRONTEND_DIR="$PROJECT_DIR/frontend"
backend_pid=""
frontend_pid=""

for command in python3 node npm; do
  if ! command -v "$command" >/dev/null 2>&1; then
    printf 'Required command not found: %s\n' "$command" >&2
    exit 1
  fi
done

printf 'Setting up backend dependencies...\n'
if [[ ! -x "$BACKEND_DIR/.venv/bin/python" ]]; then
  python3 -m venv "$BACKEND_DIR/.venv"
fi
"$BACKEND_DIR/.venv/bin/python" -m pip install --quiet --disable-pip-version-check \
  -r "$BACKEND_DIR/requirements.txt"

printf 'Setting up frontend dependencies...\n'
(cd "$FRONTEND_DIR" && npm install --no-audit --no-fund --silent)

cleanup() {
  trap - EXIT INT TERM
  printf '\nStopping servers...\n'
  # Each server has its own process group, including reload workers.
  for pid in "$backend_pid" "$frontend_pid"; do
    if [[ -n "$pid" ]]; then
      kill -TERM -- "-$pid" 2>/dev/null || true
    fi
  done
  wait 2>/dev/null || true
}

trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

# Job control gives each background server a separate process group.
set -m
(
  cd "$BACKEND_DIR"
  exec .venv/bin/python -m uvicorn app.main:app --reload --host localhost --port 8000
) &
backend_pid=$!

(
  cd "$FRONTEND_DIR"
  exec node node_modules/vite/bin/vite.js --host localhost --port 5173 --strictPort
) &
frontend_pid=$!

printf '\nStarting Support Ticket App:\n'
printf '  Frontend:  http://localhost:5173\n'
printf '  Backend:   http://localhost:8000\n'
printf '  API docs:  http://localhost:8000/docs\n'
printf '\nPress Ctrl+C to stop both servers.\n\n'

# Stop the other server if either process exits or fails to start.
while kill -0 "$backend_pid" 2>/dev/null && kill -0 "$frontend_pid" 2>/dev/null; do
  sleep 1
done

printf '\nA server stopped. Check the output above for details.\n' >&2
exit 1
