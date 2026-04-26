#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

PYTHON_BIN=""
if [[ -x ".venv/bin/python" ]]; then
  PYTHON_BIN=".venv/bin/python"
elif command -v python3 >/dev/null 2>&1; then
  PYTHON_BIN="python3"
else
  echo "Python not found. Install Python 3.11+ and dependencies first."
  exit 1
fi

exec "$PYTHON_BIN" -m uvicorn apps.api.src.app.main:app --host 0.0.0.0 --port 8000 --reload
