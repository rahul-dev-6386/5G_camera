#!/usr/bin/env bash

set -euo pipefail

# Kill existing process on port 8000
echo "Checking for existing process on port 8000..."
if command -v lsof >/dev/null 2>&1; then
    lsof -ti:8000 | xargs kill -9 2>/dev/null || true
elif command -v fuser >/dev/null 2>&1; then
    fuser -k 8000/tcp 2>/dev/null || true
else
    pkill -f "uvicorn.*8000" 2>/dev/null || true
fi

cd "$(dirname "$0")/../"
PYTHONPATH=. python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
