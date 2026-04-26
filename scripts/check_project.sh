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

echo "Checking Python sources..."
"$PYTHON_BIN" -m compileall apps/api/src tools

echo "Building frontend..."
cd apps/web
npm install
npm run build

echo "Project checks passed."
