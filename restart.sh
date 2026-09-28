#!/usr/bin/env bash
# Restart local dev: backend (uvicorn, port 8000) in the background,
# frontend (Vite, https://localhost:5173) in the foreground.
# Ctrl+C stops the frontend and takes the backend down with it.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Kill whatever's already on either port, if anything
lsof -ti:5173 | xargs kill 2>/dev/null || true
lsof -ti:8000 | xargs kill 2>/dev/null || true

cleanup() {
  if [[ -n "${BACKEND_PID:-}" ]]; then
    kill "$BACKEND_PID" 2>/dev/null || true
  fi
}
trap cleanup EXIT INT TERM

# Backend, in the background
(cd "$SCRIPT_DIR/backend" && source venv/bin/activate && uvicorn main:app --reload --port 8000) &
BACKEND_PID=$!

# Frontend, in the foreground (serves https://localhost:5173)
cd "$SCRIPT_DIR/frontend" && npm run dev
